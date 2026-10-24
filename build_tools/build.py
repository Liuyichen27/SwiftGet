"""打包脚本：生成单文件 exe。

用法::

    .venv/Scripts/python.exe build_tools/build.py

产物：``dist/SwiftGet.exe``
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
APP_NAME = "SwiftGet"
SPEC = ROOT / f"{APP_NAME}.spec"


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    env = os.environ.copy()
    env["SWIFTGET_ROOT"] = str(ROOT)
    subprocess.run(cmd, check=True, cwd=ROOT, env=env)


def main() -> int:
    if not SPEC.exists():
        print(f"缺少打包配置: {SPEC}")
        return 1

    version = time.strftime("%Y%m%d")
    run([
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--distpath", str(DIST),
        "--workpath", str(BUILD),
        str(SPEC),
    ])

    exe = DIST / f"{APP_NAME}.exe"
    if exe.exists():
        size = exe.stat().st_size / 1024 / 1024
        print(f"\n✅ 打包完成: {exe}  ({size:.1f} MB)  build={version}")
        return 0
    print("\n❌ 未找到产物")
    return 1


if __name__ == "__main__":
    sys.exit(main())
