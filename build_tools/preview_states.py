"""预览各种状态：选中 / 下载中 / 完成 / 失败。"""
from __future__ import annotations

import ctypes
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "build_tools" / "preview_states.png"


def main() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    from ui.app import SwiftGetApp

    app = SwiftGetApp()
    app.update()

    page = app.apps_page
    cards = page.cards

    # 场景 1：选中
    page._toggle_card(cards["chrome"])
    page._toggle_card(cards["wechat"])
    # 场景 2：下载中
    cards["qq"].set_selected(True)
    page._selected.add("qq")
    cards["qq"].show_progress(0.42, "75.6 MB / 180 MB · 8.4 MB/s · 16 线程")
    # 场景 3：完成
    cards["wps"].show_done("安装完成")
    page.refresh_status()
    app.update()

    def capture() -> None:
        try:
            from PIL import ImageGrab

            app.attributes("-topmost", True)
            app.update_idletasks()
            app.lift()
            app.focus_force()
            app.update()
            time.sleep(0.6)
            app.update()
            x, y = app.winfo_rootx(), app.winfo_rooty()
            w, h = app.winfo_width(), app.winfo_height()
            ImageGrab.grab((x, y, x + w, y + h)).save(OUT)
            print(f"saved {OUT}")
        except Exception:
            traceback.print_exc()
        finally:
            app._closing = True
            try:
                app.engine.stop()
            except Exception:
                pass
            app.destroy()

    app.after(1600, capture)
    app.mainloop()


if __name__ == "__main__":
    main()
