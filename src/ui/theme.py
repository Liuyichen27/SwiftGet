"""视觉主题：配色、字体、间距。

整体走「简洁」路线 —— 大量留白、单一主色、低对比边框、圆角卡片。
"""
from __future__ import annotations

import tkinter.font as tkfont

PRIMARY = "#2F6BFF"
PRIMARY_HOVER = "#1E57E0"
PRIMARY_SOFT_LIGHT = "#E9EFFF"
PRIMARY_SOFT_DARK = "#1B2A4A"

SUCCESS = "#12B76A"
WARNING = "#F79009"
DANGER = "#F04438"

FONT_FAMILY = "Microsoft YaHei UI"
MONO_FAMILY = "Consolas"

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


def apply_font_scaling(root) -> None:
    """统一全局默认字体，避免不同系统下字号错乱。"""
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        try:
            tkfont.nametofont(name).configure(family=FONT_FAMILY, size=10)
        except Exception:  # noqa: BLE001
            pass
