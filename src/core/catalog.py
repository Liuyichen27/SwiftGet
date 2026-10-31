"""常用软件清单。

设计要点
--------
1. 每个软件支持多个下载源，运行时按顺序预检，取第一个可用源。
2. 清单可被 ``%APPDATA%/SwiftGet/catalog.json`` 覆盖，也可从远程 URL 更新，
   链接失效时无需重新打包即可修复。
3. 安装方式全部使用静默参数，安装过程不打扰用户。
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Iterable

import requests

from . import plat
from .paths import data_root

# --------------------------------------------------------------------------
# 数据结构
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Source:
    url: str
    label: str = "官方"


@dataclass
class AppEntry:
    id: str
    name: str
    vendor: str
    category: str
    desc: str
    color: str
    sources: list[Source]
    size_label: str
    installer: str = "exe"                    # exe | msi
    silent_args: list[str] = field(default_factory=list)
    lang_args: dict[str, list[str]] = field(default_factory=dict)
    homepage: str = ""
    note: str = ""
    # 安装器是否真的支持完全静默。False 表示会弹安装界面，需要用户点几下
    silent_ok: bool = True
    manual_hint: str = ""
    # installer：正常安装包；portable：绿色版，下载完直接跑；archive：源码压缩包
    kind: str = "installer"
    # 指定下载后的文件名（不填则按 id 生成 xxx_setup.exe）
    filename: str = ""
    # 源码包/命令行工具的用法（一行命令），显示在卡片上，省得用户解压后翻 README
    usage: str = ""

    # -- 安装命令 ---------------------------------------------------------
    def install_command(self, file_path: str, lang: str = "zh") -> list[str]:
        """构造静默安装命令。"""
        if self.installer == "msi":
            base = ["msiexec", "/i", file_path, "/qn", "/norestart"]
            return base + self.lang_args.get(lang, [])
        args = list(self.silent_args)
        if lang in self.lang_args:
            args = list(self.lang_args[lang]) + args
        return [file_path, *args]

    @property
    def supports_language(self) -> bool:
        return bool(self.lang_args)

    @property
    def primary_url(self) -> str:
        return self.sources[0].url if self.sources else ""

    @property
    def file_ext(self) -> str:
        # 按文件名判断，别只看 installer：Linux 上有 deb / AppImage / tar.xz
        low = self.filename.lower()
        for ext in (".tar.xz", ".tar.gz", ".tar.bz2", ".appimage", ".deb", ".zip"):
            if low.endswith(ext):
                return ext
        return ".msi" if self.installer == "msi" else ".exe"

    def suggested_filename(self) -> str:
        if self.filename:
            return self.filename
        base = "".join(c for c in self.name if c.isalnum() or c in "-_ ")
        base = base.strip().replace(" ", "_") or self.id
        return f"{base}_setup{self.file_ext}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "vendor": self.vendor,
            "category": self.category,
            "desc": self.desc,
            "color": self.color,
            "size_label": self.size_label,
            "installer": self.installer,
            "silent_args": self.silent_args,
            "lang_args": self.lang_args,
            "homepage": self.homepage,
            "note": self.note,
            "silent_ok": self.silent_ok,
            "manual_hint": self.manual_hint,
            "kind": self.kind,
            "filename": self.filename,
            "usage": self.usage,
            "sources": [{"url": s.url, "label": s.label} for s in self.sources],
        }


def _e(**kw: Any) -> AppEntry:
    """便捷构造。sources 可传 url 字符串或 (url, label) 元组。"""
    srcs: list[Source] = []
    for item in kw.pop("sources", []):
        if isinstance(item, str):
            srcs.append(Source(item, "官方"))
        else:
            url, label = item
            srcs.append(Source(url, label))
    return AppEntry(sources=srcs, **kw)


# --------------------------------------------------------------------------
# 内置清单
# --------------------------------------------------------------------------

BUILTIN: list[AppEntry] = [
    _e(
        id="chrome",
        name="Google Chrome",
        vendor="Google",
        category="浏览器",
        desc="全球使用最广的浏览器，极速且稳定",
        color="#4285F4",
        size_label="≈156 MB",
        installer="msi",
        silent_args=["/qn", "/norestart"],
        homepage="https://www.google.cn/chrome/",
        sources=[
            ("https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi", "官方 MSI"),
            ("https://dl.google.com/chrome/install/ChromeStandaloneSetup64.exe", "官方 EXE"),
        ],
        note="企业版 MSI 包，静默安装最稳定。",
    ),
    _e(
        id="wechat",
        name="微信 WeChat",
        vendor="腾讯",
        category="社交办公",
        desc="国民级即时通讯工具",
        color="#07C160",
        size_label="≈270 MB",
        silent_args=["/S"],
        homepage="https://weixin.qq.com/",
        sources=[
            ("https://dldir1.qq.com/weixin/Windows/WeChatSetup.exe", "官方"),
            ("https://dldir1v6.qq.com/weixin/Windows/WeChatSetup.exe", "官方 IPv6"),
        ],
    ),
    _e(
        id="qq",
        name="QQ",
        vendor="腾讯",
        category="社交办公",
        desc="QQ NT 全新架构版本",
        color="#12B7F5",
        size_label="≈180 MB",
        silent_args=["/S"],
        homepage="https://im.qq.com/pcqq",
        sources=[
            ("https://dldir1.qq.com/qqfile/qq/QQNT/Windows/QQ_9.9.19_250610_x64_01.exe", "官方"),
            ("https://dldir1v6.qq.com/qqfile/qq/QQNT/Windows/QQ_9.9.19_250610_x64_01.exe", "官方 IPv6"),
        ],
        note="版本号随官方更新，若失效可在官网页更新链接。",
    ),
    _e(
        id="dingtalk",
        name="钉钉 DingTalk",
        vendor="阿里",
        category="社交办公",
        desc="企业协同办公平台",
        color="#1677FF",
        size_label="≈200 MB",
        silent_args=["/S"],
        homepage="https://www.dingtalk.com/download",
        sources=[
            ("https://dtapp-pub.dingtalk.com/dingtalk-desktop/win_installer/Release/DingTalk_v7.8.2.412240121.exe", "官方"),
        ],
    ),
    _e(
        id="wps",
        name="WPS Office",
        vendor="金山",
        category="社交办公",
        desc="国产办公套件，兼容 Office 格式",
        color="#FA5A3C",
        size_label="≈220 MB",
        silent_args=["/S"],
        silent_ok=False,
        manual_hint="WPS 安装器不支持完全静默，会弹出安装向导",
        homepage="https://www.wps.cn/",
        sources=[
            ("https://package.wpscdn.cn/wps/download/ep/WPS_Setup.exe", "官方"),
        ],
    ),
    _e(
        id="360",
        name="360 安全卫士",
        vendor="360",
        category="安全防护",
        desc="国内主流安全软件，功能全面",
        color="#1BB44A",
        size_label="≈106 MB",
        silent_args=["/S"],
        silent_ok=False,
        manual_hint="360 安装器会弹出组件选择界面，需要手动点击",
        homepage="https://weishi.360.cn/",
        sources=[
            ("https://down.360safe.com/setup.exe", "完整安装包"),
            ("https://down.360safe.com/inst.exe", "在线安装器"),
        ],
        note="安装包可能附带推广组件，可在安装后关闭。",
    ),
    _e(
        id="huorong",
        name="火绒安全软件",
        vendor="火绒",
        category="安全防护",
        desc="轻量无广告的国产杀毒软件",
        color="#F04A23",
        size_label="≈30 MB",
        silent_args=["/S"],
        homepage="https://www.huorong.cn/person",
        sources=[
            ("https://down5.huorong.cn/hrswcksingle.exe", "官方"),
            ("https://down.huorong.cn/hrswcksingle.exe", "官方备用"),
        ],
        note="官方直链随版本变动，失效时可从下载页更新。",
    ),
    _e(
        id="7zip",
        name="7-Zip",
        vendor="Igor Pavlov",
        category="系统工具",
        desc="开源免费的高压缩率解压工具",
        color="#EDC52E",
        size_label="≈1.6 MB",
        silent_args=["/S"],
        homepage="https://www.7-zip.org/",
        sources=[
            # 官方 7-zip.org 会 302 到 GitHub Release（国内直连常超时），
            # 旧版清华镜像路径已 404 下线，换 gh-proxy 加速镜像兜底
            ("https://www.7-zip.org/a/7z2409-x64.exe", "官方"),
            ("https://gh-proxy.com/https://github.com/ip7z/7zip/releases/download/24.09/7z2409-x64.exe", "GitHub 加速镜像"),
        ],
    ),
    _e(
        id="everything",
        name="Everything",
        vendor="voidtools",
        category="系统工具",
        desc="毫秒级文件名搜索，装机必备",
        color="#F58220",
        size_label="≈1.8 MB",
        silent_args=["/S"],
        homepage="https://www.voidtools.com/zh-cn/",
        sources=[
            ("https://www.voidtools.com/Everything-1.4.1.1026.x64-Setup.exe", "官方"),
        ],
    ),
    _e(
        id="bandizip",
        name="Bandizip",
        vendor="Bandisoft",
        category="系统工具",
        desc="好用的压缩软件，支持多格式",
        color="#2F7DF6",
        size_label="≈7 MB",
        silent_args=["/S"],
        silent_ok=False,
        manual_hint="Bandizip 安装器会要求选择版本类型，需要手动确认",
        homepage="https://www.bandisoft.com/bandizip/",
        sources=[
            ("https://dl.bandisoft.com/bandizip.std/BANDIZIP-SETUP-STD-X64.EXE", "官方"),
        ],
    ),
    _e(
        id="notepadpp",
        name="Notepad++",
        vendor="Don Ho",
        category="系统工具",
        desc="轻量强大的开源文本编辑器",
        color="#90C23A",
        size_label="≈5 MB",
        silent_args=["/S"],
        homepage="https://notepad-plus-plus.org/",
        sources=[
            ("https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.7.1/npp.8.7.1.Installer.x64.exe", "GitHub"),
            ("https://gh-proxy.com/https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.7.1/npp.8.7.1.Installer.x64.exe", "GitHub 加速"),
        ],
    ),
    _e(
        id="vlc",
        name="VLC media player",
        vendor="VideoLAN",
        category="影音播放",
        desc="全格式开源播放器，无需解码器",
        color="#FF8800",
        size_label="≈40 MB",
        silent_args=["/S"],
        # VLC 使用 NSIS，支持 /L=<LCID> 指定安装界面语言
        lang_args={"zh": ["/L=2052"], "en": ["/L=1033"]},
        homepage="https://www.videolan.org/vlc/",
        sources=[
            ("https://get.videolan.org/vlc/3.0.21/win64/vlc-3.0.21-win64.exe", "官方"),
            ("https://mirrors.ustc.edu.cn/videolan-ftp/vlc/3.0.21/win64/vlc-3.0.21-win64.exe", "中科大镜像"),
        ],
    ),
]

CATEGORIES = ["全部", "浏览器", "社交办公", "安全防护", "系统工具", "影音播放"]


# --------------------------------------------------------------------------
# 清单管理
# --------------------------------------------------------------------------


def builtin_apps() -> list[AppEntry]:
    """当前平台的内置清单。

    Windows 那套是 exe + 静默安装参数，到 Linux 上一点用没有，所以分成
    两份独立的清单，按平台选（catalog_linux 反过来 import 本模块，
    这里用函数内 import 避开循环）。
    """
    if plat.IS_LINUX:
        from .catalog_linux import linux_catalog
        return linux_catalog()
    return BUILTIN


def _download_os(text: str) -> str:
    """从文件名/URL 猜这个包是给哪个系统用的（''=看不出来）。"""
    low = (text or "").split("?")[0].strip().lower()
    if low.endswith((".exe", ".msi")):
        return "win"
    if low.endswith((".deb", ".appimage", ".tar.xz", ".tar.gz", ".tar.bz2", ".tgz")):
        return "linux"
    return ""


def _plausible_here(raw: dict[str, Any]) -> bool:
    """远程/本地清单里某条是不是当前系统能用的。

    清单是跨平台共用的，一份 Windows 清单塞进 Linux 版会让用户下到
    一个装不上的 exe。这里只看扩展名，看不出来就放行。
    """
    probe = str(raw.get("filename") or "")
    if not probe:
        for s in raw.get("sources") or []:
            probe = s.get("url", "") if isinstance(s, dict) else str(s)
            if probe:
                break
    target = _download_os(probe)
    if not target:
        return True
    return (target == "win") == bool(plat.IS_WIN)


class Catalog:
    """内置清单 + 本地覆盖 + 远程更新。"""

    def __init__(self) -> None:
        self._builtin = builtin_apps()
        self._apps: dict[str, AppEntry] = {a.id: a for a in self._builtin}
        self.catalog_file = data_root() / "catalog.json"
        self._load_local_override()

    # -- 查询 -------------------------------------------------------------
    @property
    def apps(self) -> list[AppEntry]:
        order = {a.id: i for i, a in enumerate(self._builtin)}
        return sorted(self._apps.values(), key=lambda a: order.get(a.id, 999))

    def get(self, app_id: str) -> AppEntry | None:
        return self._apps.get(app_id)

    def by_category(self, category: str) -> list[AppEntry]:
        if category in ("", "全部"):
            return self.apps
        return [a for a in self.apps if a.category == category]

    # -- 覆盖与更新 -------------------------------------------------------
    def _load_local_override(self) -> None:
        if not self.catalog_file.exists():
            return
        try:
            data = json.loads(self.catalog_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        self._apply(data)

    def _apply(self, data: Any) -> None:
        apps = data.get("apps") if isinstance(data, dict) else data
        if not isinstance(apps, list):
            return
        for raw in apps:
            if not isinstance(raw, dict) or "id" not in raw:
                continue
            app_id = raw["id"]
            if not _plausible_here(raw):
                continue
            existing = self._apps.get(app_id)
            srcs = [
                Source(s["url"], s.get("label", "自定义")) if isinstance(s, dict) else Source(str(s))
                for s in raw.get("sources", [])
            ]
            if existing is None:
                self._apps[app_id] = AppEntry(
                    id=app_id,
                    name=raw.get("name", app_id),
                    vendor=raw.get("vendor", ""),
                    category=raw.get("category", "自定义"),
                    desc=raw.get("desc", ""),
                    color=raw.get("color", "#4F7CFF"),
                    sources=srcs,
                    size_label=raw.get("size_label", ""),
                    installer=raw.get("installer", "exe"),
                    silent_args=raw.get("silent_args", ["/S"]),
                    lang_args=raw.get("lang_args", {}),
                    homepage=raw.get("homepage", ""),
                    note=raw.get("note", ""),
                    silent_ok=raw.get("silent_ok", True),
                    manual_hint=raw.get("manual_hint", ""),
                    kind=raw.get("kind", "installer"),
                    filename=raw.get("filename", ""),
                    usage=raw.get("usage", ""),
                )
                continue
            # 仅覆盖显式提供的字段
            if srcs:
                existing.sources = srcs
            for key in ("name", "vendor", "category", "desc", "size_label",
                        "installer", "homepage", "note", "silent_ok", "manual_hint",
                        "kind", "filename", "usage"):
                if key in raw:
                    setattr(existing, key, raw[key])
            if "silent_args" in raw:
                existing.silent_args = raw["silent_args"]
            if "lang_args" in raw:
                existing.lang_args = raw["lang_args"]

    def export_local(self) -> str:
        payload = {"version": 1, "apps": [a.to_dict() for a in self.apps]}
        self.catalog_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return str(self.catalog_file)

    def update_from_url(self, url: str, timeout: float = 8.0) -> int:
        """从远程拉取清单覆盖。返回更新的条目数，失败抛异常。"""
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "SwiftGet/1.0"})
        r.raise_for_status()
        data = r.json()
        before = len(self._apps)
        self._apply(data)
        return len(self._apps) - before

    def update_async(self, url: str, done=None) -> None:
        def worker() -> None:
            count = -1
            try:
                count = self.update_from_url(url)
            except Exception:  # noqa: BLE001
                pass
            if done:
                done(count)

        threading.Thread(target=worker, daemon=True).start()


# --------------------------------------------------------------------------
# 下载源预检
# --------------------------------------------------------------------------


def _probe_once(url: str, timeout: float) -> tuple[bool, int]:
    try:
        r = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SwiftGet/1.2",
                "Range": "bytes=0-0",
            },
            stream=True,
            timeout=timeout,
            allow_redirects=True,
        )
        ctype = r.headers.get("Content-Type", "").lower()
        crange = r.headers.get("Content-Range", "")
        total = 0
        if "/" in crange:
            try:
                total = int(crange.split("/")[-1])
            except ValueError:
                total = 0
        if not total:
            try:
                total = int(r.headers.get("Content-Length", "0") or 0)
            except ValueError:
                total = 0
        r.close()
        # HTML 响应说明是错误页或跳转页，不是安装包
        if "text/html" in ctype and total < 100_000:
            return False, 0
        return r.status_code in (200, 206), total
    except Exception:  # noqa: BLE001
        return False, 0


def probe_source(url: str, timeout: float = 6.0) -> tuple[bool, int]:
    """返回 (可用, 字节大小)。用 Range 请求避免下载整个文件。

    弱网下第一次探测很容易超时（GitHub 的 Release 尤其），一次失败就判
    「下载源不可用」太武断 —— 所以这里自己重试一次，第二次超时放宽 5 秒。
    两次都失败才算真不可用，而且调用方还有兜底（预检全挂也会直连试一次）。
    """
    ok, size = _probe_once(url, timeout)
    if ok:
        return ok, size
    time.sleep(0.4)
    return _probe_once(url, timeout + 5.0)


def resolve_sources(app: AppEntry) -> Iterable[tuple[Source, bool, int]]:
    """串行预检每个源，逐个 yield 结果。"""
    for src in app.sources:
        ok, size = probe_source(src.url)
        yield src, ok, size
