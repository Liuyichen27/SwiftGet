"""SwiftGet 启动入口。"""
from __future__ import annotations

import ctypes
import os
import sys
import traceback
from pathlib import Path


def _bootstrap_path() -> None:
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, here)


def _enable_dpi_awareness() -> None:
    """声明 Per-Monitor DPI 感知，高分屏下界面才不会被系统二次拉伸。

    customtkinter 会按 DPI 缩放控件，窗口尺寸在 ``SwiftGetApp._center`` 里
    同步处理，两者必须使用同一种感知模式，否则布局会错位。
    """
    try:
        # 2 = PROCESS_PER_MONITOR_DPI_AWARE
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:  # noqa: BLE001
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:  # noqa: BLE001
            pass


def _crash_log_path() -> Path:
    base = Path(os.environ.get("APPDATA") or Path.home()) / "SwiftGet"
    base.mkdir(parents=True, exist_ok=True)
    return base / "crash.log"


def _report_crash(exc: BaseException) -> None:
    """打包成窗口程序后没有控制台，把异常落到日志并弹窗提示。"""
    detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    try:
        _crash_log_path().write_text(detail, encoding="utf-8")
    except OSError:
        pass
    try:
        ctypes.windll.user32.MessageBoxW(
            None,
            f"程序遇到一个错误：\n\n{exc}\n\n详细日志：\n{_crash_log_path()}",
            "SwiftGet 错误",
            0x10,
        )
    except Exception:  # noqa: BLE001
        pass
    print(detail, file=sys.stderr)


def main() -> int:
    _bootstrap_path()
    _enable_dpi_awareness()

    if sys.platform != "win32":
        print("SwiftGet 仅支持 Windows。")
        return 1

    try:
        from ui.app import run

        run()
    except BaseException as exc:  # noqa: BLE001
        _report_crash(exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
