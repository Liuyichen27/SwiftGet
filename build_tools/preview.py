"""开发期预览：启动界面，几秒后自动截图并退出。"""
from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

PAGE = int(sys.argv[1]) if len(sys.argv) > 1 else 0
OUT = ROOT / "build_tools" / f"preview_{PAGE}.png"


def main() -> None:
    import ctypes

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    from ui.app import SwiftGetApp

    app = SwiftGetApp()
    app.update()
    if PAGE:
        app._switch_page(PAGE)
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
            img = ImageGrab.grab((x, y, x + w, y + h))
            img.save(OUT)
            print(f"saved {OUT} {img.size}")
        except Exception:
            traceback.print_exc()
        finally:
            app._closing = True
            try:
                app.engine.stop()
            except Exception:
                pass
            app.destroy()

    app.after(1800, capture)
    app.mainloop()


if __name__ == "__main__":
    main()
