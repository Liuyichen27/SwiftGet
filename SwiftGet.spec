# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：单文件 + Per-Monitor DPI 清单 + 内嵌 aria2 内核。"""
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(os.environ.get("SWIFTGET_ROOT") or Path(SPECPATH)).resolve()
if not (ROOT / "src" / "main.py").exists():
    ROOT = Path(os.getcwd()).resolve()
assert (ROOT / "src" / "main.py").exists(), f"源码目录定位失败: {ROOT}"

ctk_datas, ctk_binaries, ctk_hidden = collect_all("customtkinter")

a = Analysis(
    [str(ROOT / "src" / "main.py")],
    pathex=[str(ROOT / "src")],
    binaries=[(str(ROOT / "assets" / "aria2c.exe"), "assets")] + ctk_binaries,
    datas=[
        (str(ROOT / "assets" / "app.ico"), "assets"),
        (str(ROOT / "assets" / "app.png"), "assets"),
    ] + ctk_datas,
    hiddenimports=["darkdetect", "PIL._tkinter_finder"] + ctk_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["numpy", "pandas", "matplotlib", "scipy", "test", "unittest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SwiftGet",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "app.ico"),
    manifest=str(ROOT / "assets" / "app.manifest"),
)
