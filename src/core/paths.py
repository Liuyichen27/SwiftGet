"""路径与资源定位。兼容源码运行与 PyInstaller 单文件打包。"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from . import plat

APP_NAME = "SwiftGet"
APP_TITLE = "SwiftGet · 极速软件下载器"
APP_VERSION = "1.3.0"
APP_ID = "SwiftGet"


def is_frozen() -> bool:
    """是否运行在 PyInstaller 打包环境中。"""
    return bool(getattr(sys, "frozen", False))


def _asset_root(start: Path) -> Path:
    """从当前文件往上找带 ``assets/`` 的那层目录。

    Windows 打包/源码两种布局相对固定，但 deb 里源码被摊到 ``/usr/lib/swiftget``
    （main.py、core/、ui/ 与 assets/ 同级，深度比源码树浅一层），
    写死 ``parents[2]`` 会指到 ``/usr/lib``。这里按「哪层有 assets 就用哪层」判断。
    """
    for p in (start, *start.parents):
        if (p / "assets").is_dir():
            return p
    return start


def resource_root() -> Path:
    """只读资源根目录（打包后在 _MEIPASS）。"""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return _asset_root(Path(__file__).resolve().parent)


def app_root() -> Path:
    """可写的程序根目录（exe 所在目录 / 源码根目录）。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return _asset_root(Path(__file__).resolve().parent)


def data_root() -> Path:
    """用户数据目录：Windows 是 %APPDATA%\\SwiftGet，Linux 是 ~/.config/SwiftGet。"""
    target = plat.base_dir() / APP_NAME
    target.mkdir(parents=True, exist_ok=True)
    return target


def bin_dir() -> Path:
    target = data_root() / "bin"
    target.mkdir(parents=True, exist_ok=True)
    return target


def asset(name: str) -> Path:
    return resource_root() / "assets" / name


def ensure_aria2() -> Path:
    """返回可用的 aria2c 路径。

    Windows：把内置的 aria2c.exe 释放到数据目录（绿色版不带外部依赖）。
    Linux：用系统装的 ``aria2c``（apt install aria2）——不内置二进制，
    因为各发行版 glibc 版本不同，塞一个进去很容易「能装不能用」。
    """
    if plat.IS_LINUX or plat.IS_MAC:
        found = plat.find_aria2()
        if found:
            return found
        return Path("aria2c")      # 让调用方拿到一个不存在的路径，由 start() 报缺依赖

    dst = bin_dir() / "aria2c.exe"
    src = asset("aria2c.exe")
    if src.exists():
        need_copy = True
        if dst.exists():
            try:
                need_copy = dst.stat().st_size != src.stat().st_size
            except OSError:
                need_copy = True
        if need_copy:
            shutil.copy2(src, dst)
    if not dst.exists():
        # 源码环境下允许退回到 build_tools 里的下载件
        fallback = app_root() / "build_tools" / "aria2c.exe"
        if fallback.exists():
            shutil.copy2(fallback, dst)
    return dst


def default_download_dir() -> Path:
    downloads = plat.downloads_home()
    target = downloads / "SwiftGet"
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError:
        target = data_root() / "downloads"
        target.mkdir(parents=True, exist_ok=True)
    return target


def open_in_explorer(path: Path) -> None:
    """在文件管理器里定位文件或目录（Linux 走 xdg-open）。"""
    plat.open_path(path)
