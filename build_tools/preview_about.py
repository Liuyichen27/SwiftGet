"""临时：设��页滚到底截图，确认「关于」卡片和检查更新按钮渲染正常。"""
from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "build_tools" / "preview_about.png"


def main() -> None:
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    from ui.app import SwiftGetApp

    app = SwiftGetApp()
    app.update()
    app._switch_page(3)
    app.update()

    def capture() -> None:
        try:
            from PIL import ImageGrab

            app.settings_page.scroll._parent_canvas.yview_moveto(1.0)
            app.update()
            time.sleep(0.8)
            app.attributes("-topmost", True)
            app.lift()
            app.update()
            x, y = app.winfo_rootx(), app.winfo_rooty()
            w, h = app.winfo_width(), app.winfo_height()
            img = ImageGrab.grab((x, y, x + w, y + h))
            img.save(OUT)
            print(f"saved {OUT} {img.size}")
            btn = getattr(app.settings_page, "update_btn", None)
            print("update_btn:", btn.cget("text") if btn is not None else "缺失")
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
