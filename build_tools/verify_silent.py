"""静默安装参数验证：启动安装包并检测是否弹出 GUI。

原理：传入静默参数后，如果安装器仍然创建了可见窗口，说明该参数无效。
使用 /D 指定临时目录，避免污染真实系统。
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
TMP = ROOT / "build_tools" / "_silent_test"

user32 = ctypes.windll.user32
CREATE_NO_WINDOW = 0x08000000

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SwiftGet/1.0"

# (名称, 下载地址, 参数列表)
CASES = [
    (
        "Bandizip",
        "https://dl.bandisoft.com/bandizip.std/BANDIZIP-SETUP-STD-X64.EXE",
        ["/S"],
    ),
    (
        "7-Zip",
        "https://www.7-zip.org/a/7z2409-x64.exe",
        ["/S"],
    ),
]

EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def visible_windows_of(pid: int) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []

    def callback(hwnd, _lparam):
        win_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(win_pid))
        if win_pid.value == pid and user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            found.append((hwnd, buf.value))
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    return found


def download(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 500_000:
        return True
    try:
        with requests.get(url, headers={"User-Agent": UA}, stream=True, timeout=60) as r:
            r.raise_for_status()
            with dest.open("wb") as fh:
                for chunk in r.iter_content(256 * 1024):
                    fh.write(chunk)
        return True
    except Exception as exc:
        print(f"   下载失败: {exc}")
        return False


def test_case(name: str, url: str, args: list[str]) -> None:
    print(f"\n=== {name}")
    TMP.mkdir(parents=True, exist_ok=True)
    exe = TMP / Path(url).name.split("?")[0]
    if not download(url, exe):
        print("   跳过")
        return
    print(f"   包大小 {exe.stat().st_size / 1024 / 1024:.1f} MB")

    target_dir = TMP / f"install_{name}"
    cmd = [str(exe), *args, f"/D={target_dir}"]
    print(f"   执行: {' '.join(cmd)}")

    proc = subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW, close_fds=True)

    deadline = time.time() + 12
    seen: dict[int, str] = {}
    while time.time() < deadline:
        for hwnd, title in visible_windows_of(proc.pid):
            if hwnd not in seen:
                seen[hwnd] = title
        if proc.poll() is not None:
            break
        time.sleep(0.5)

    code = proc.poll()
    print(f"   退出码: {code if code is not None else '仍在运行'}")

    if seen:
        print(f"   ❌ 弹出 {len(seen)} 个窗口（静默失败）:")
        for title in list(seen.values())[:5]:
            print(f"      · {title[:60]!r}")
    else:
        print("   ✅ 无窗口，静默成功")
        if target_dir.exists():
            size = sum(f.stat().st_size for f in target_dir.rglob("*") if f.is_file())
            print(f"      已安装 {size / 1024 / 1024:.1f} MB 到 {target_dir}")

    if proc.poll() is None:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, creationflags=CREATE_NO_WINDOW)

    # 清理本次安装产物
    time.sleep(0.5)
    if target_dir.exists():
        subprocess.run(["cmd", "/c", "rmdir", "/S", "/Q", str(target_dir)],
                       capture_output=True, creationflags=CREATE_NO_WINDOW)


def main() -> int:
    for name, url, args in CASES:
        try:
            test_case(name, url, args)
        except Exception as exc:  # noqa: BLE001
            print(f"   异常: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
