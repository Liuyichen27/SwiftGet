"""端到端测试：走真实 UI 流程下载一个软件（不自动安装）。"""
from __future__ import annotations

import ctypes
import shutil
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

TMP = ROOT / "build_tools" / "_e2e"
SHOT = ROOT / "build_tools" / "preview_e2e.png"


def main() -> int:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    from ui.app import SwiftGetApp

    if TMP.exists():
        shutil.rmtree(TMP, ignore_errors=True)
    TMP.mkdir(parents=True)

    app = SwiftGetApp()
    app.settings.auto_install = False
    app.settings.download_dir = str(TMP)
    app.update()

    state = {"phase": "start", "t0": time.time()}

    def start() -> None:
        page = app.apps_page
        card = page.cards.get("everything")
        if card is None:
            print("找不到 everything 卡片")
            app.destroy()
            return
        page._toggle_card(card)
        page.path_var.set(str(TMP))
        print("点击开始下载…")
        page._start()
        state["phase"] = "downloading"

    def check() -> None:
        jobs = list(app.jobs.values())
        if not jobs:
            if time.time() - state["t0"] > 20:
                print("没有产生任务")
                finish(1)
            else:
                app.after(500, check)
            return

        job = jobs[0]
        elapsed = time.time() - state["t0"]
        print(f"  [{elapsed:5.1f}s] state={job.state} "
              f"{job.done}/{job.total}  {job.message[:60]}")

        if job.state in ("finished", "error"):
            if job.state == "error":
                print("下载失败:", job.message)
                finish(1)
                return
            path = job.path
            ok = bool(path and path.exists() and path.stat().st_size > 1_000_000)
            print(f"文件: {path}  存在={bool(path and path.exists())} "
                  f"大小={path.stat().st_size if path and path.exists() else 0}")

            def done() -> None:
                card = app.apps_page.cards.get("everything")
                if card is not None:
                    print(f"[debug] card={card} job_card={job.card is card} "
                          f"state={job.state} msg={job.message!r}")
                    print(f"[debug] progress mapped={card.progress.winfo_ismapped()} "
                          f"card_h={card.winfo_height()} meta={card.meta.cget('text')!r}")
                else:
                    print("[debug] card 缺失")
                capture()
                finish(0 if ok else 1)

            # 留出时间让 UI 渲染完成态
            app.after(1200, done)
            return

        if elapsed > 120:
            print("超时")
            finish(1)
            return
        app.after(600, check)

    def capture() -> None:
        try:
            from PIL import ImageGrab

            app.attributes("-topmost", True)
            app.update_idletasks()
            app.lift()
            app.focus_force()
            app.update()
            time.sleep(0.5)
            app.update()
            x, y = app.winfo_rootx(), app.winfo_rooty()
            w, h = app.winfo_width(), app.winfo_height()
            ImageGrab.grab((x, y, x + w, y + h)).save(SHOT)
            print("截图:", SHOT)
        except Exception:
            traceback.print_exc()

    code = {"v": 1}

    def finish(result: int) -> None:
        code["v"] = result
        app._closing = True
        try:
            app.engine.stop()
        except Exception:
            pass
        app.destroy()

    app.after(700, start)
    app.after(1500, check)
    app.mainloop()
    shutil.rmtree(TMP, ignore_errors=True)
    print("\n✅ E2E 通过" if code["v"] == 0 else "\n❌ E2E 失败")
    return code["v"]


if __name__ == "__main__":
    sys.exit(main())
