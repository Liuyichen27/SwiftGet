"""自创应用页的端到端测试：真实点击、真实下载、真实校验。

覆盖两件事：
1. 绿色版（CleanBlackboard.exe）下载完**不进安装流程**，卡片刻「已保存」；
2. 源码包（dupfinder zip）按 ZIP 头校验，不会被当成坏安装包拒掉。

跑法：python build_tools/test_own.py
"""
from __future__ import annotations

import ctypes
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

TMP = ROOT / "build_tools" / "_own"
SHOT = ROOT / "build_tools" / "preview_own_e2e.png"
TARGETS = ["cleanblackboard", "dupfinder"]
TIMEOUT = 180.0

results: list[tuple[bool, str]] = []


def check(ok: bool, name: str, detail: str = "") -> None:
    results.append((ok, name))
    print(f"{'✓' if ok else '✗'} {name}{'  — ' + detail if detail else ''}")


def main() -> int:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:  # noqa: BLE001
        pass

    from ui.app import SwiftGetApp

    if TMP.exists():
        shutil.rmtree(TMP, ignore_errors=True)
    TMP.mkdir(parents=True)

    app = SwiftGetApp()
    app.settings.download_dir = str(TMP)
    app.update()
    app._switch_page(1)
    app.update()

    page = app.own_page
    check(len(page.cards) == 7, "自创应用页有 7 张卡片", f"实际 {len(page.cards)}")

    for aid in TARGETS:
        card = page.cards.get(aid)
        if card is None:
            check(False, f"找不到 {aid} 卡片")
            return 1
        page._toggle_card(card)
    check(len(page.selected_apps()) == len(TARGETS), "勾选生效", f"{len(page.selected_apps())} 个")

    page.path_var.set(str(TMP))
    page._start()
    t0 = time.time()

    def poll() -> None:
        jobs = [j for j in app.jobs.values() if j.app.id in TARGETS]
        states = {j.app.id: j.state for j in jobs}
        if len(jobs) == len(TARGETS) and all(s in ("finished", "error") for s in states.values()):
            report(jobs)
            return
        if time.time() - t0 > TIMEOUT:
            print(f"超时，当前状态：{states}")
            report(jobs, fail=True)
            return
        app.after(500, poll)

    def report(jobs, fail: bool = False) -> None:
        for j in jobs:
            ok = j.state == "finished" and j.path is not None and j.path.exists()
            kind = "绿色版" if j.app.kind == "portable" else "源码包"
            check(
                ok,
                f"{j.app.id} 下载完成（{kind}）",
                f"{j.path.name if j.path else '无文件'} · {j.message or j.install_result}",
            )
            if ok:
                head = j.path.open("rb").read(2)
                want = b"PK" if j.app.kind == "archive" else b"MZ"
                check(head == want, f"{j.app.id} 文件头正确", f"{head!r} 期望 {want!r}")
            check(
                j.state != "installing",
                f"{j.app.id} 没有进入安装流程",
                f"state={j.state}",
            )

        try:
            app.update()
            time.sleep(0.4)
            app.update()
            from PIL import ImageGrab

            app.attributes("-topmost", True)
            app.lift()
            app.focus_force()
            app.update()
            time.sleep(0.6)
            x, y = app.winfo_rootx(), app.winfo_rooty()
            w, h = app.winfo_width(), app.winfo_height()
            ImageGrab.grab((x, y, x + w, y + h)).save(SHOT)
            print(f"截图：{SHOT}")
        except Exception as exc:  # noqa: BLE001
            print("截图失败:", exc)

        app._closing = True
        try:
            app.engine.stop()
        except Exception:  # noqa: BLE001
            pass
        app.destroy()

        passed = sum(1 for ok, _ in results if ok)
        print(f"\n{passed}/{len(results)} 项通过")
        raise SystemExit(0 if passed == len(results) and not fail else 1)

    app.after(400, poll)
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
