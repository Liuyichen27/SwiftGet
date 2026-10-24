"""验证打包后的 exe：进程存活 + 窗口尺寸 + 界面渲染。"""
from __future__ import annotations

import ctypes
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

try:
    # 测试进程必须与目标进程同为 DPI 感知，否则读到的是虚拟化坐标
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
EXE = ROOT / "dist" / "SwiftGet.exe"
SHOT = ROOT / "build_tools" / "exe_shot.png"
TITLE = "SwiftGet · 极速软件下载器"
DETACHED = 0x00000008
CREATE_NO_WINDOW = 0x08000000

user32 = ctypes.windll.user32


def find_window(title: str, timeout: float) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        hwnd = user32.FindWindowW(None, title)
        if hwnd:
            return hwnd
        time.sleep(0.5)
    return 0


def wait_stable(hwnd: int, timeout: float = 15.0):
    deadline = time.time() + timeout
    last = None
    rect = wintypes.RECT()
    while time.time() < deadline:
        if user32.IsWindowVisible(hwnd):
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            size = (rect.right - rect.left, rect.bottom - rect.top)
            if size == last and size[0] > 600:
                return rect
            last = size
        time.sleep(0.4)
    return rect


def main() -> int:
    if not EXE.exists():
        print("exe 不存在")
        return 1

    print(f"启动 {EXE.name} ({EXE.stat().st_size / 1024 / 1024:.1f} MB) …")
    t0 = time.time()
    proc = subprocess.Popen([str(EXE)], creationflags=DETACHED, close_fds=True)

    hwnd = find_window(TITLE, 30)
    if not hwnd:
        print("未找到窗口")
        if proc.poll() is not None:
            print(f"   进程退出 code={proc.returncode}")
            log = Path.home() / "AppData/Roaming/SwiftGet/crash.log"
            if log.exists():
                print(log.read_text(encoding="utf-8", errors="replace")[-1500:])
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/F"],
                       capture_output=True, creationflags=CREATE_NO_WINDOW)
        return 2

    print(f"窗口已创建，用时 {time.time()-t0:.1f}s  hwnd=0x{hwnd:X}")

    rect = wait_stable(hwnd)
    w, h = rect.right - rect.left, rect.bottom - rect.top
    print(f"窗口物理尺寸 {w}x{h} @ ({rect.left},{rect.top})")
    print(f"屏幕物理尺寸 {user32.GetSystemMetrics(0)}x{user32.GetSystemMetrics(1)}")

    user32.SetForegroundWindow(hwnd)
    time.sleep(1.2)

    try:
        from PIL import ImageGrab

        img = ImageGrab.grab((rect.left, rect.top, rect.right, rect.bottom))
        img.save(SHOT)
        print(f"截图 {SHOT} {img.size}")
    except Exception as exc:
        print("截图失败:", exc)

    subprocess.run(["taskkill", "/PID", str(proc.pid), "/F"],
                   capture_output=True, creationflags=CREATE_NO_WINDOW)
    print("已结束进程")
    return 0


if __name__ == "__main__":
    sys.exit(main())
