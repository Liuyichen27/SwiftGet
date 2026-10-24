"""安装器指纹识别：只下文件头/尾部片段，判断安装器类型以确定静默参数。"""
from __future__ import annotations

import concurrent.futures as cf
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402

from core.catalog import BUILTIN  # noqa: E402

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

# 安装器特征串 -> (类型, 推荐静默参数)
SIGNATURES = [
    (b"Nullsoft", "NSIS", "/S"),
    (b"NSIS", "NSIS", "/S"),
    (b"Inno Setup", "Inno Setup", "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /NOCANCEL"),
    (b"InstallShield", "InstallShield", "/s /v\"/qn\""),
    (b"Wise Installation", "Wise", "/s"),
    (b"Bandizip Setup", "Bandisoft 自研", "/S"),
    (b"Bandisoft", "Bandisoft 自研", "/S"),
    (b"7-Zip", "7-Zip 自研", "/S"),
    (b"Tencent", "腾讯自研", "未知"),
    (b"Microsoft Corporation", "MSI/PE", "视情况"),
]


def fetch_slices(url: str, head: int = 1_500_000, tail: int = 1_500_000) -> bytes:
    h = {"User-Agent": UA}
    buf = b""
    try:
        r = requests.get(url, headers={**h, "Range": f"bytes=0-{head}"}, timeout=25)
        if r.status_code in (200, 206):
            buf += r.content
        # 取尾部
        r2 = requests.get(url, headers={**h, "Range": f"bytes=-{tail}"}, timeout=25)
        if r2.status_code in (200, 206):
            buf += r2.content
    except Exception:  # noqa: BLE001
        pass
    return buf


def identify(url: str) -> tuple[str, str, str]:
    data = fetch_slices(url)
    if not data:
        return "无法获取", "-", ""
    hits: list[tuple[str, str]] = []
    for sig, kind, param in SIGNATURES:
        if sig in data:
            hits.append((kind, param))
    # 去重保序
    seen = set()
    uniq = []
    for kind, param in hits:
        if kind not in seen:
            seen.add(kind)
            uniq.append((kind, param))
    if not uniq:
        # 看看有没有可疑的 updater / 版本提示
        extra = ""
        for kw in (b"updat", b"Silent", b"/S"):
            if kw in data:
                extra = "含静默相关字样"
                break
        return "未识别", "未知", extra
    kind, param = uniq[0]
    extra = " / ".join(k for k, _ in uniq[1:3])
    return kind, param, extra


def main() -> None:
    tasks = []
    for app in BUILTIN:
        src = app.sources[0]
        tasks.append((app, src.url))

    with cf.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda t: (t[0], identify(t[1])), tasks))

    print(f"{'软件':<18}{'安装器类型':<16}{'建议静默参数':<48}备注")
    print("-" * 110)
    for app, (kind, param, extra) in results:
        current = " ".join(app.silent_args)
        flag = "" if param.lower() in (current.lower(), "") or param == "未知" else f"  ← 当前用的是 {current!r}"
        print(f"{app.name:<18}{kind:<16}{param:<48}{extra}{flag}")


if __name__ == "__main__":
    main()
