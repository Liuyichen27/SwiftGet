"""视觉主题：配色、字体、间距。

整体走「简洁」路线 —— 大量留白、单一主色、低对比边框、圆角卡片。
"""
from __future__ import annotations

import tkinter.font as tkfont

from core import plat as _plat

PRIMARY = "#2F6BFF"
PRIMARY_HOVER = "#1E57E0"
PRIMARY_SOFT_LIGHT = "#E9EFFF"
PRIMARY_SOFT_DARK = "#1B2A4A"

SUCCESS = "#12B76A"
WARNING = "#F79009"
DANGER = "#F04438"

# Windows 上雅黑最稳；Linux 用 Noto/文泉驿，都没有就交给 Tk 自己挑
_CJK_CANDIDATES = {
    "win32": ["Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI"],
    "linux": ["Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Micro Hei",
              "Noto Sans", "DejaVu Sans"],
    "darwin": ["PingFang SC", "Helvetica Neue"],
}
_MONO_CANDIDATES = {
    "win32": ["Consolas", "Cascadia Mono"],
    "linux": ["JetBrains Mono", "Noto Sans Mono", "DejaVu Sans Mono", "Liberation Mono"],
    "darwin": ["Menlo", "Monaco"],
}


def _key() -> str:
    if _plat.IS_WIN:
        return "win32"
    if _plat.IS_LINUX:
        return "linux"
    return "darwin"


FONT_FAMILY = _CJK_CANDIDATES[_key()][0]
MONO_FAMILY = _MONO_CANDIDATES[_key()][0]

_RADIUS = 14


LIGHT = {
    "bg": "#F5F6F8",
    "surface": "#FFFFFF",
    "surface_alt": "#FAFBFC",
    "border": "#E4E7EC",
    "border_strong": "#D0D5DD",
    "text": "#14161A",
    "text_muted": "#667085",
    "text_faint": "#98A2B3",
    "primary": PRIMARY,
    "primary_hover": PRIMARY_HOVER,
    "primary_soft": PRIMARY_SOFT_LIGHT,
    "success": SUCCESS,
    "warning": WARNING,
    "danger": DANGER,
    "track": "#EDF0F4",
    "selection": "#F0F5FF",
}

DARK = {
    "bg": "#0F1115",
    "surface": "#181B21",
    "surface_alt": "#1F2329",
    "border": "#2A2F37",
    "border_strong": "#3A4049",
    "text": "#F2F4F7",
    "text_muted": "#98A2B3",
    "text_faint": "#6B7280",
    "primary": "#4F8BFF",
    "primary_hover": "#6BA0FF",
    "primary_soft": PRIMARY_SOFT_DARK,
    "success": "#32D583",
    "warning": "#FDB022",
    "danger": "#F97066",
    "track": "#262B33",
    "selection": "#15203A",
}


def palette(dark: bool) -> dict[str, str]:
    return DARK if dark else LIGHT


def is_dark_mode(mode: str) -> bool:
    if mode == "dark":
        return True
    if mode == "light":
        return False
    try:
        import darkdetect

        return bool(darkdetect.isDark())
    except Exception:  # noqa: BLE001
        return False


def font(size: int = 13, weight: str = "normal", family: str | None = None):
    """创建字体对象（需在 Tk 根窗口创建之后调用）。"""
    return (family or FONT_FAMILY, size, weight)


def _first_available(candidates: list[str], fallback: str) -> str:
    """挑第一个系统里真装了的字体，避免 Linux 上整屏方块。"""
    try:
        have = {f.lower() for f in tkfont.families()}
    except Exception:  # noqa: BLE001
        return candidates[0] if candidates else fallback
    for name in candidates:
        if name.lower() in have:
            return name
    return fallback


def apply_font_scaling(root) -> None:
    """统一全局默认字体，避免不同系统下字号错乱。

    Linux 发行版自带的字体差别很大，写死一个家族很容易整屏豆腐块，
    所以这里按候选表挑第一个真实存在的。
    """
    global FONT_FAMILY, MONO_FAMILY
    try:
        default_family = tkfont.nametofont("TkDefaultFont").cget("family")
    except Exception:  # noqa: BLE001
        default_family = "DejaVu Sans"
    FONT_FAMILY = _first_available(_CJK_CANDIDATES[_key()], default_family)
    MONO_FAMILY = _first_available(_MONO_CANDIDATES[_key()], "TkFixedFont")
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.nametofont(name).configure(family=FONT_FAMILY, size=10)
        except Exception:  # noqa: BLE001
            pass
