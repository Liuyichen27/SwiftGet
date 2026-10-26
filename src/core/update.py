"""自更新：查 GitHub 最新 Release、下载、替换自身并重启。

只针对单文件绿色版（PyInstaller onefile）。流程刻意做得简单可验证：

1. 查 ``releases/latest``，直连与 ``gh-proxy.com`` 镜像各试一轮；
2. 结果缓存到 ``%APPDATA%\\SwiftGet\\update.json``（查到 24 小时内不重查，
   查不到 6 小时后再试）——否则弱网下每次开窗口都要把两个源全超时一遍；
3. 下载新 exe 到临时目录，**先校验 PE 头**再落盘，免得把 200 的 HTML
   错误页当成 exe；
4. 写一个 bat：等本进程完全退出后覆盖自己，再启动新版。

源码运行（非 frozen）时 ``apply_update`` 直接返回失败，不会去覆盖 python.exe。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Callable

from .paths import APP_VERSION, data_root, is_frozen

REPO = "Liuyichen27/SwiftGet"
ASSET = "SwiftGet.exe"
PROXY = "https://gh-proxy.com/"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
MAX_BYTES = 300 * 1024 * 1024
UA = "SwiftGet-Updater"


# ----------------------------------------------------------------------
# 小工具
# ----------------------------------------------------------------------
def ver_tuple(text: str) -> tuple[int, ...]:
    """把 ``v1.10.2`` 拆成 ``(1, 10, 2)``；非数字段按 0 算。"""
    nums: list[int] = []
    for part in str(text or "").lstrip("vV").split("."):
        m = re.match(r"\d+", part)
        nums.append(int(m.group()) if m else 0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)


def _opener(url: str, timeout: float, direct: bool):
    """直连失败时借系统代理再试一轮（很多机器只有代理能出网）。"""
    if direct:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    else:
        opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", UA), ("Accept", "*/*")]
    return opener.open(url, timeout=timeout)


def _get_json(url: str, timeout: float = 20.0) -> dict:
    with _opener(url, timeout, True) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


# ----------------------------------------------------------------------
# 缓存
# ----------------------------------------------------------------------
def _cache_file() -> Path:
    return data_root() / "update.json"


def _read_cache() -> dict | None:
    try:
        data = json.loads(_cache_file().read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        ttl = 24 * 3600 if data.get("version") else 6 * 3600
        if time.time() - float(data.get("at") or 0) > ttl:
            return None
        return data
    except Exception:  # noqa: BLE001
        return None


def _write_cache(info: dict) -> None:
    try:
        _cache_file().write_text(
            json.dumps({**info, "at": time.time()}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:  # noqa: BLE001
        pass


# ----------------------------------------------------------------------
# 查版本
# ----------------------------------------------------------------------
def fetch_latest(tries: int = 3, use_cache: bool = True) -> dict | None:
    fake = os.environ.get("SWIFTGET_FAKE_LATEST")
    if fake:
        return {
            "tag": fake if fake.startswith("v") else f"v{fake}",
            "version": fake.lstrip("vV"),
            "date": "2026-10-26",
            "notes": "自测用假版本",
            "assets": {ASSET: ""},
            "page": RELEASES_PAGE,
        }

    if use_cache:
        cached = _read_cache()
        if cached is not None:
            return cached

    urls = [
        f"https://api.github.com/repos/{REPO}/releases/latest",
        f"{PROXY}https://api.github.com/repos/{REPO}/releases/latest",
    ]
    for attempt in range(tries):
        for url in urls:
            try:
                data = _get_json(url)
            except Exception:  # noqa: BLE001
                continue
            tag = str(data.get("tag_name") or "").strip()
            if not tag:
                continue
            assets = {
                a.get("name"): a.get("browser_download_url")
                for a in data.get("assets") or []
                if a.get("name")
            }
            info = {
                "tag": tag,
                "version": tag.lstrip("vV"),
                "date": str(data.get("published_at") or "")[:10],
                "notes": str(data.get("body") or "")[:800],
                "assets": assets,
                "page": data.get("html_url") or RELEASES_PAGE,
            }
            _write_cache(info)
            return info
        time.sleep(0.8 + attempt)
    _write_cache({})   # 记一笔失败，6 小时内别再试
    return None


def check_update() -> dict:
    """返回 dict：ok / current / latest / has_update / page / asset_url / error。"""
    cur = APP_VERSION
    info = fetch_latest()
    if not info:
        return {"ok": False, "current": cur, "error": "连不上 GitHub，稍后再试"}
    has = ver_tuple(info["version"]) > ver_tuple(cur)
    return {
        "ok": True,
        "current": cur,
        "latest": info["version"],
        "date": info.get("date") or "",
        "notes": info.get("notes") or "",
        "has_update": has,
        "page": info.get("page") or RELEASES_PAGE,
        "asset_url": (info.get("assets") or {}).get(ASSET) or "",
    }


def asset_urls(url: str) -> list[str]:
    """官方直链 + 镜像；调用方传空则退回默认资产地址。"""
    if not url:
        url = f"https://github.com/{REPO}/releases/latest/download/{ASSET}"
    return [url, f"{PROXY}{url}"] if not url.startswith(PROXY) else [url]


# ----------------------------------------------------------------------
# 下载
# ----------------------------------------------------------------------
def download(urls: list[str], dest: Path,
             on_progress: Callable[[int, int], None] | None = None) -> Path:
    """按顺序试源下载，边下边回报进度，落盘前校验 PE 头。"""
    last: Exception | None = None
    targets = [u for u in urls if u]
    dest.parent.mkdir(parents=True, exist_ok=True)

    for direct in (True, False):
        for url in targets:
            try:
                tmp = dest.with_suffix(dest.suffix + ".part")
                tick = 0.0
                with _opener(url, 30.0, direct) as r:
                    total = int(r.headers.get("Content-Length") or 0)
                    got = 0
                    head = b""
                    with open(tmp, "wb") as fh:
                        while True:
                            chunk = r.read(1 << 16)
                            if not chunk:
                                break
                            if not head:
                                head = chunk[:2]
                            got += len(chunk)
                            if got > MAX_BYTES:
                                raise ValueError("文件超过上限")
                            fh.write(chunk)
                            now = time.time()
                            if on_progress and (now - tick > 0.4 or (total and got >= total)):
                                tick = now
                                try:
                                    on_progress(got, total)
                                except Exception:  # noqa: BLE001
                                    pass
                if head != b"MZ":
                    tmp.unlink(missing_ok=True)
                    raise ValueError("下载回来的不是 exe（可能被拦截或代理返回了错误页）")
                tmp.replace(dest)
                return dest
            except Exception as e:  # noqa: BLE001
                last = e
    raise last or RuntimeError("所有下载源都失败")


# ----------------------------------------------------------------------
# 替换自身
# ----------------------------------------------------------------------
def apply_update(new_exe: Path) -> dict:
    """写 bat：等本进程退出 → 覆盖自身 → 启动新版。

    调用方拿到 ``ok=True`` 后应立刻 ``os._exit(0)``，让文件锁释放。
    """
    if not is_frozen():
        return {"ok": False, "error": "源码运行模式下不能自更新，请用绿色版 exe"}
    target = Path(sys.executable).resolve()
    if not new_exe.exists():
        return {"ok": False, "error": "新版本文件不存在，请重新下载"}

    bat = Path(os.environ.get("TEMP") or data_root()) / "swiftget_update.bat"
    # bat 用 ANSI 编码写，路径里全是 ASCII（TEMP 目录），不需要 chcp
    script = f'''@echo off
:wait
tasklist /FI "IMAGENAME eq {target.name}" 2>nul | find /I "{target.name}" >nul
if not errorlevel 1 (
  timeout /t 1 /nobreak >nul
  goto wait
)
copy /Y "{new_exe}" "{target}" >nul
start "" "{target}"
del "%~f0"
'''
    try:
        bat.write_text(script, encoding="mbcs", errors="replace")
    except Exception:  # noqa: BLE001
        bat.write_text(script, encoding="utf-8", errors="replace")

    try:
        subprocess.Popen(["cmd", "/c", str(bat)], close_fds=True,
                         creationflags=0x08000000)  # CREATE_NO_WINDOW
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"启动替换脚本失败：{e}"}
    return {"ok": True, "target": str(target), "bat": str(bat)}
