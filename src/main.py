"""SwiftGet 启动入口。"""
from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

IS_WIN = sys.platform.startswith("win")


def _bootstrap_path() -> None:
    """把程序目录（和 deb 里的 vendor 依赖目录）挂到 sys.path 最前面。

    deb 版把 customtkinter / darkdetect 一起打进了 ``vendor/``，
    这样运行时不依赖 pip、也不用联网装 Python 包。
    """
    here = Path(__file__).resolve().parent
    for p in (here / "vendor", here):
        s = str(p)
        if p.is_dir() and s not in sys.path:
            sys.path.insert(0, s)


def _enable_dpi_awareness() -> None:
    """声明 Per-Monitor DPI 感知，高分屏下界面才不会被系统二次拉伸。

    customtkinter 会按 DPI 缩放控件，窗口尺寸在 ``SwiftGetApp._center`` 里
    同步处理，两者必须使用同一种感知模式，否则布局会错位。
    Windows 独有；Linux 交给 Tk 自己的缩放处理。
    """
    if not IS_WIN:
        return
    import ctypes

    try:
        # 2 = PROCESS_PER_MONITOR_DPI_AWARE
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:  # noqa: BLE001
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:  # noqa: BLE001
            pass


def _crash_log_path() -> Path:
    if IS_WIN:
        base = Path(os.environ.get("APPDATA") or Path.home()) / "SwiftGet"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")) / "SwiftGet"
    base.mkdir(parents=True, exist_ok=True)
    return base / "crash.log"


def _report_crash(exc: BaseException) -> None:
    """打包成窗口程序后没有控制台，把异常落到日志并弹窗提示。"""
    detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    try:
        _crash_log_path().write_text(detail, encoding="utf-8")
    except OSError:
        pass
    if IS_WIN:
        import ctypes

        try:
            ctypes.windll.user32.MessageBoxW(
                None,
                f"程序遇到一个错误：\n\n{exc}\n\n详细日志：\n{_crash_log_path()}",
                "SwiftGet 错误",
                0x10,
            )
        except Exception:  # noqa: BLE001
            pass
    else:
        # Linux 上终端里跑会有 stderr；从桌面启动时日志文件就是唯一线索
        print(f"SwiftGet 出错：{exc}\n详细日志：{_crash_log_path()}", file=sys.stderr)
    print(detail, file=sys.stderr)


def main() -> int:
    _bootstrap_path()
    _enable_dpi_awareness()

    try:
        from ui.app import run

        run()
    except BaseException as exc:  # noqa: BLE001
        _report_crash(exc)
        return 1
    return 0


def cli_probe(argv: list[str]) -> int | None:
    """轻量命令行探针，给 deb 安装后的自检用（不启动图形界面）。"""
    _bootstrap_path()
    from core.paths import APP_TITLE, APP_VERSION, ensure_aria2, data_root

    if "--version" in argv:
        print(f"SwiftGet {APP_VERSION}")
        return 0
    if "--check" in argv:
        ok = True
        print(f"{APP_TITLE}  v{APP_VERSION}")
        print(f"  platform : {sys.platform}")
        print(f"  python   : {sys.version.split()[0]}")

        aria = ensure_aria2()
        exists = aria.exists() or bool(__import__("shutil").which(str(aria)))
        print(f"  aria2c   : {'[ok  ]' if exists else '[fail]'} {aria}")
        ok = ok and exists
        if not exists:
            print("            安装：sudo apt install aria2")

        try:
            import tkinter  # noqa: F401

            print("  tkinter  : [ok  ]")
        except Exception as exc:  # noqa: BLE001
            print(f"  tkinter  : [fail] {exc}")
            ok = False

        for mod in ("customtkinter", "PIL"):
            try:
                __import__(mod)
                print(f"  {mod:<9}: [ok  ]")
            except Exception as exc:  # noqa: BLE001
                print(f"  {mod:<9}: [fail] {exc}")
                ok = False

        print(f"  data dir : {data_root()}")
        return 0 if ok else 2
    return None


if __name__ == "__main__":
    probe = cli_probe(sys.argv[1:])
    sys.exit(probe if probe is not None else main())
