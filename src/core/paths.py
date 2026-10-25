"""路径与资源定位。兼容源码运行与 PyInstaller 单文件打包。"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "SwiftGet"
APP_TITLE = "SwiftGet · 极速软件下载器"
APP_VERSION = "1.1.0"
APP_ID = "SwiftGet"


def is_frozen() -> bool:
    """是否运行在 PyInstaller 打包环境中。"""
    return bool(getattr(sys, "frozen", False))


def resource_root() -> Path:
    """只读资源根目录（打包后在 _MEIPASS）。"""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[2]


def app_root() -> Path:
    """可写的程序根目录（exe 所在目录 / 源码根目录）。"""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def data_root() -> Path:
    """用户数据目录：%APPDATA%\\SwiftGet"""
    base = Path(os.environ.get("APPDATA") or (Path.home() / ".config"))
    target = base / APP_NAME
    target.mkdir(parents=True, exist_ok=True)
    return target


def bin_dir() -> Path:
    target = data_root() / "bin"
    target.mkdir(parents=True, exist_ok=True)
    return target


def asset(name: str) -> Path:
    return resource_root() / "assets" / name


def ensure_aria2() -> Path:
    """将内置 aria2c 释放到数据目录，返回可执行路径。"""
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
    downloads = Path(os.environ.get("USERPROFILE") or Path.home()) / "Downloads"
    target = downloads / "SwiftGet"
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError:
        target = data_root() / "downloads"
        target.mkdir(parents=True, exist_ok=True)
    return target


def open_in_explorer(path: Path) -> None:
    """在资源管理器中定位文件或目录。"""
    import subprocess

    if path.is_dir():
        subprocess.Popen(["explorer", str(path)])
    elif path.exists():
        subprocess.Popen(["explorer", "/select,", str(path)])
    else:
        subprocess.Popen(["explorer", str(path.parent)])
