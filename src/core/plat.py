"""平台判定与跨平台小工具。

为什么单独一个模块：下载器原来满世界写 ``ctypes.windll`` 和 ``aria2c.exe``，
一旦要出 Linux 版，这些散在各处的判断就会漏。这里集中一层，其它模块只问
``IS_WIN`` / ``IS_LINUX``，不再自己嗅 ``sys.platform``。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

IS_WIN = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")
IS_MAC = sys.platform == "darwin"
PLATFORM = "windows" if IS_WIN else ("linux" if IS_LINUX else sys.platform)

# CREATE_NO_WINDOW：Windows 上避免弹黑框；其它平台传 0
CREATE_NO_WINDOW = 0x08000000


def creation_flags() -> int:
    return CREATE_NO_WINDOW if IS_WIN else 0


def base_dir() -> Path:
    """配置目录的上级：Windows 是 %APPDATA%，Linux 是 $XDG_CONFIG_HOME。"""
    if IS_WIN:
        return Path(os.environ.get("APPDATA") or Path.home())
    return Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))


def data_home() -> Path:
    """Linux 的数据目录（下 deb、解压 AppImage 用）。"""
    return Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))


def downloads_home() -> Path:
    return Path.home() / "Downloads"


def find_aria2() -> Path | None:
    """Linux 上找系统装的 aria2c；Windows 走内置的那份。"""
    exe = shutil.which("aria2c")
    return Path(exe) if exe else None


def open_path(path: Path) -> None:
    """在文件管理器里定位文件/目录。"""
    p = str(path)
    if IS_WIN:
        if path.is_dir():
            subprocess.Popen(["explorer", p])
        elif path.exists():
            subprocess.Popen(["explorer", "/select,", p])
        else:
            subprocess.Popen(["explorer", str(path.parent)])
        return

    target = path if path.is_dir() else path.parent
    for opener in ("xdg-open", "gio"):
        exe = shutil.which(opener)
        if exe:
            args = [exe, str(target)] if opener == "xdg-open" else [exe, "open", str(target)]
            try:
                subprocess.Popen(args)
                return
            except OSError:
                continue


def has(cmd: str) -> bool:
    return shutil.which(cmd) is not None
