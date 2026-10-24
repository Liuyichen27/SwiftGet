"""主窗口：导航、全局状态、下载调度、进度轮询。"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import queue
import threading
import time
import tkinter.messagebox as messagebox
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import customtkinter as ctk

from core.aria2 import Aria2Engine, Aria2Error, Aria2Options, human_size, human_speed
from core.catalog import AppEntry, Catalog, probe_source
from core.installer import launch_after_install, run_silent, verify_installer
from core.paths import APP_TITLE, APP_VERSION, data_root, open_in_explorer
from core.settings import Settings

from . import theme, widgets
from .page_apps import AppsPage
from .page_link import LinkPage
from .page_settings import SettingsPage


def dpi_scale(hwnd: int = 0) -> float:
    """获取 DPI 缩放比（1.0 / 1.25 / 1.5 / 2.0 …）。

    优先用窗口自身的 DPI：``GetDpiForSystem`` 在打包进程里可能返回被
    虚拟化后的 96，导致界面尺寸算错。
    """
    user32 = ctypes.windll.user32
    if hwnd:
        try:
            return max(1.0, user32.GetDpiForWindow(hwnd) / 96.0)
        except Exception:  # noqa: BLE001
            pass
    try:
        return max(1.0, user32.GetDpiForSystem() / 96.0)
    except Exception:  # noqa: BLE001
        return 1.0


@dataclass
class DownloadJob:
    """一次「软件 -> 安装包」的下载任务。"""

    app: AppEntry
    lang: str = "zh"
    gid: str = ""
    url: str = ""
    path: Path | None = None
    total: int = 0
    done: int = 0
    speed: float = 0.0
    state: str = "pending"     # pending|downloading|verifying|installing|finished|error
    message: str = ""
    install_result: str = ""
    card: object | None = None


class SwiftGetApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.settings = Settings.load()
        self.dark = theme.is_dark_mode(self.settings.theme)
        self.colors = theme.palette(self.dark)
        self.catalog = Catalog()

        self.engine = Aria2Engine(
            Aria2Options(
                max_connections=self.settings.max_connections,
                split=self.settings.split,
                p2p_enabled=self.settings.p2p_enabled,
                bt_port=self.settings.bt_port,
            )
        )

        self.jobs: dict[str, DownloadJob] = {}
        self._install_queue: queue.Queue[DownloadJob] = queue.Queue()
        self._ui_queue: queue.Queue = queue.Queue()
        self._install_worker_started = False
        self._closing = False

        ctk.set_appearance_mode("dark" if self.dark else "light")
        theme.apply_font_scaling(self)

        self.title(APP_TITLE)
        self._center(1120, 760)
        self.configure(fg_color=self.colors["bg"])
        self._set_icon()

        self._build_shell()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if self.settings.catalog_url:
            self.catalog.update_async(self.settings.catalog_url, self._on_catalog_updated)

        self._start_poll()
        self.after(300, self._warm_up_engine)

    # ------------------------------------------------------------------
    # 窗口基础
    # ------------------------------------------------------------------
    def _center(self, w: int, h: int) -> None:
        """设置窗口尺寸并居中。

        直接使用 Tk 原生 ``wm geometry`` 并传入物理像素，绕开 customtkinter
        对 geometry 的二次缩放（源码运行与打包后的行为不一致）。
        控件本身由 customtkinter 按 DPI 放大，窗口尺寸与之匹配即可。
        """
        self.update_idletasks()
        scale = dpi_scale(self.winfo_id())

        # GetSystemMetrics 返回物理像素，不受 DPI 虚拟化影响
        try:
            sw = ctypes.windll.user32.GetSystemMetrics(0)
            sh = ctypes.windll.user32.GetSystemMetrics(1)
        except Exception:  # noqa: BLE001
            sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        if sw < 640 or sh < 480:
            sw, sh = 1280, 720

        target_w = min(int(w * scale), int(sw * 0.94))
        target_h = min(int(h * scale), int(sh * 0.90))
        x = max(0, (sw - target_w) // 2)
        y = max(0, (sh - target_h) // 2 - int(14 * scale))

        self.tk.call("wm", "geometry", self._w, f"{target_w}x{target_h}+{x}+{y}")
        self.tk.call(
            "wm", "minsize", self._w,
            int(880 * scale), int(560 * scale),
        )

    def _set_icon(self) -> None:
        from core.paths import asset

        ico = asset("app.ico")
        if ico.exists():
            try:
                self.iconbitmap(str(ico))
            except Exception:  # noqa: BLE001
                pass

    def _warm_up_engine(self) -> None:
        """后台预热 aria2，减少首次点击的等待。"""
        def worker() -> None:
            try:
                self.engine.start()
            except Exception:  # noqa: BLE001
                pass

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # 布局
    # ------------------------------------------------------------------
    def _build_shell(self) -> None:
        c = self.colors
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ---- 顶栏 ----
        header = ctk.CTkFrame(self, height=62, corner_radius=0, fg_color=c["surface"])
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(2, weight=1)

        logo = ctk.CTkLabel(
            header, text="⚡", width=34, height=34, corner_radius=9,
            fg_color=c["primary"], text_color="#FFFFFF",
            font=(theme.FONT_FAMILY, 17),
        )
        logo.grid(row=0, column=0, padx=(22, 10), pady=14)

        brand = ctk.CTkLabel(
            header, text="SwiftGet", anchor="w",
            font=(theme.FONT_FAMILY, 15, "bold"), text_color=c["text"],
        )
        brand.grid(row=0, column=1, sticky="w")

        nav = ctk.CTkFrame(header, fg_color="transparent")
        nav.grid(row=0, column=2, sticky="e", padx=(0, 12))
        self.tabs = widgets.SegmentedTabs(
            nav,
            c,
            ["常用软件", "链接 / P2P 加速", "设置"],
            command=self._switch_page,
        )
        self.tabs.pack()

        theme_btn = ctk.CTkButton(
            header, text="🌙" if not self.dark else "☀",
            width=34, height=34, corner_radius=9,
            fg_color=c["surface_alt"], hover_color=c["track"],
            text_color=c["text_muted"], font=(theme.FONT_FAMILY, 14),
            command=self._toggle_theme,
        )
        theme_btn.grid(row=0, column=3, padx=(0, 20))

        div = ctk.CTkFrame(self, height=1, corner_radius=0, fg_color=c["border"])
        div.grid(row=0, column=0, sticky="sew")

        # ---- 内容区 ----
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.body.grid_rowconfigure(0, weight=1)
        self.body.grid_columnconfigure(0, weight=1)

        self.pages: list[ctk.CTkFrame] = []
        self.apps_page = AppsPage(self.body, self)
        self.link_page = LinkPage(self.body, self)
        self.settings_page = SettingsPage(self.body, self)
        for page in (self.apps_page, self.link_page, self.settings_page):
            page.grid(row=0, column=0, sticky="nsew")
            self.pages.append(page)
        self._switch_page(0)

    def _switch_page(self, index: int) -> None:
        for i, page in enumerate(self.pages):
            if i == index:
                page.tkraise()
        if self.tabs.active != index:
            self.tabs.select(index, notify=False)
        if index == 2:
            self.settings_page.refresh()

    def _toggle_theme(self) -> None:
        self.dark = not self.dark
        self.settings.theme = "dark" if self.dark else "light"
        self.settings.save()
        messagebox.showinfo(
            "主题已切换",
            "颜色切换将在下次启动时完全生效。\n（部分控件需要重建以应用新配色）",
            parent=self,
        )
        self.colors = theme.palette(self.dark)
        ctk.set_appearance_mode("dark" if self.dark else "light")

    # ------------------------------------------------------------------
    # 下载调度
    # ------------------------------------------------------------------
    def ensure_engine(self) -> bool:
        if self.engine.running:
            return True
        try:
            self.engine.start()
            return True
        except Aria2Error as exc:
            messagebox.showerror("下载引擎错误", str(exc), parent=self)
            return False

    def enqueue_apps(self, apps: list[AppEntry], lang: str) -> None:
        """把选中的软件加入下载队列，逐个预检源并提交给 aria2。"""
        if not apps:
            messagebox.showinfo("提示", "请先选择要下载的软件。", parent=self)
            return
        if not self.ensure_engine():
            return

        target_dir = self.settings.download_path
        for app in apps:
            if any(j.app.id == app.id and j.state in ("downloading", "pending")
                   for j in self.jobs.values()):
                continue
            job = DownloadJob(app=app, lang=lang)
            job.card = self.apps_page.card_for(app.id)
            self.jobs[f"{app.id}_{time.time_ns()}"] = job
            threading.Thread(
                target=self._download_worker, args=(job, target_dir), daemon=True
            ).start()

        self.apps_page.refresh_status()

    def _download_worker(self, job: DownloadJob, target_dir: Path) -> None:
        """后台线程：预检源 -> 提交 aria2 -> 等待完成 -> 校验 -> 排队安装。"""
        app = job.app
        self._ui(job, "pending", "正在选择下载源…")

        chosen: tuple[str, str] | None = None
        for src in app.sources:
            ok, size = probe_source(src.url)
            if ok:
                chosen = (src.url, src.label)
                if size:
                    job.total = size
                break
        if chosen is None:
            job.state = "error"
            job.message = "所有下载源都不可用，请检查网络或到官网手动下载"
            self._ui(job, "error", job.message)
            return

        url, label = chosen
        job.url = url
        out_name = app.suggested_filename()

        try:
            gid = self.engine.add_uri(url, out_name, target_dir)
        except Exception as exc:  # noqa: BLE001
            job.state = "error"
            job.message = f"提交下载失败：{exc}"
            self._ui(job, "error", job.message)
            return

        job.gid = gid
        job.state = "downloading"
        self._ui(job, "downloading", f"来自{label} · 已开始")

        # 等待 aria2 完成
        while not self._closing:
            status = self.engine.tell(gid)
            if not status:
                time.sleep(0.5)
                continue

            # 磁力链会先下载元数据，然后派生新 gid
            followed = status.get("followedBy")
            if followed:
                gid = followed[0]
                job.gid = gid
                continue

            st = status.get("status", "")
            if st == "error":
                job.state = "error"
                job.message = status.get("errorMessage") or "下载出错"
                self._ui(job, "error", job.message)
                return
            if st in ("complete",):
                break
            if st == "removed":
                job.state = "error"
                job.message = "任务已取消"
                self._ui(job, "error", job.message)
                return
            time.sleep(0.4)

        # 定位文件
        status = self.engine.tell(job.gid)
        files = status.get("files") or []
        if files:
            job.path = Path(files[0].get("path", ""))
        if not job.path or not job.path.exists():
            job.path = target_dir / out_name

        job.state = "verifying"
        self._ui(job, "verifying", "下载完成，正在校验文件…")

        ok, msg = verify_installer(job.path) if job.path else (False, "找不到下载的文件")
        if not ok:
            job.state = "error"
            job.message = f"文件校验失败：{msg}"
            self._ui(job, "error", job.message)
            return

        if self.settings.auto_install:
            self._ui(job, "installing", "下载完成，等待静默安装…")
            self._install_queue.put(job)
            self._start_install_worker()
        else:
            job.state = "finished"
            self._ui(job, "finished", f"已保存到 {job.path.parent.name}")

    # -- 安装队列 --------------------------------------------------------
    def _start_install_worker(self) -> None:
        if self._install_worker_started:
            return
        self._install_worker_started = True

        def worker() -> None:
            while not self._closing:
                try:
                    job = self._install_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                self._install_one(job)

        threading.Thread(target=worker, daemon=True).start()

    def _install_one(self, job: DownloadJob) -> None:
        job.state = "installing"
        app_entry = job.app
        workdir = str(job.path.parent) if job.path else None

        if not app_entry.silent_ok:
            # 安装器不支持静默：直接拉起安装向导，用户点几下即可
            self._ui(
                job, "installing",
                app_entry.manual_hint or "正在打开安装向导，请按提示完成安装…",
            )
            result = run_silent([str(job.path)], workdir=workdir, silent=False)
            job.install_result = "安装向导已结束"
            job.state = "finished"
            self._ui(job, "finished", "已打开安装向导，安装流程已结束")
            return

        self._ui(job, "installing", "正在静默安装（如弹出授权请点「是」）…")
        cmd = app_entry.install_command(str(job.path), job.lang)
        result = run_silent(cmd, workdir=workdir, silent=True)

        job.install_result = result.message
        if result.ok:
            job.state = "finished"
            self._ui(job, "finished", result.message)
            if self.settings.auto_launch:
                launch_after_install()
            if self.settings.delete_after_install and job.path and job.path.exists():
                try:
                    job.path.unlink()
                except OSError:
                    pass
        else:
            job.state = "error"
            job.message = result.message
            self._ui(job, "error", f"安装失败：{result.message}")

    # -- UI 线程安全 -----------------------------------------------------
    def post(self, fn) -> None:
        """从任意线程提交一个 UI 操作，由主线程统一执行。

        tkinter 不是线程安全的，子线程直接调用 ``after`` 可能静默失效，
        因此统一走队列。
        """
        self._ui_queue.put(fn)

    def _drain_ui_queue(self) -> None:
        while True:
            try:
                fn = self._ui_queue.get_nowait()
            except queue.Empty:
                return
            try:
                fn()
            except Exception:  # noqa: BLE001
                pass

    def _ui(self, job: DownloadJob, state: str, text: str) -> None:
        self.post(lambda: self._apply_job_ui(job, state, text))

    def _apply_job_ui(self, job: DownloadJob, state: str, text: str) -> None:
        card = job.card
        if card is not None:
            try:
                if state == "error":
                    card.show_error(text)
                elif state == "finished":
                    card.show_done(text)
                else:
                    frac = (job.done / job.total) if job.total else 0.0
                    card.show_progress(frac, text)
            except Exception as exc:  # noqa: BLE001
                print("[UI] 卡片状态更新失败:", exc)
        self.apps_page.refresh_status()

    # ------------------------------------------------------------------
    # 进度轮询
    # ------------------------------------------------------------------
    def _start_poll(self) -> None:
        def loop() -> None:
            if self._closing:
                return
            try:
                self._poll_once()
            except Exception:  # noqa: BLE001
                pass
            self.after(600, loop)

        self.after(600, loop)

    def _poll_once(self) -> None:
        self._drain_ui_queue()
        if not self.engine.running:
            return
        active_jobs = [j for j in self.jobs.values()
                       if j.state in ("downloading", "verifying", "installing")]
        if not active_jobs:
            self.apps_page.set_global_speed(0)
            return

        statuses: dict[str, dict] = {}
        if any(j.state == "downloading" for j in active_jobs):
            for item in self.engine.tell_active() + self.engine.tell_waiting():
                gid = item.get("gid")
                if gid:
                    statuses[gid] = item

        total_speed = 0.0
        for job in active_jobs:
            if job.state != "downloading":
                continue
            st = statuses.get(job.gid) or self.engine.tell(job.gid)
            if not st:
                continue
            job.total = int(st.get("totalLength") or job.total or 0)
            job.done = int(st.get("completedLength") or 0)
            job.speed = float(st.get("downloadSpeed") or 0)
            total_speed += job.speed

            if job.total:
                frac = job.done / job.total
                text = f"{human_size(job.done)} / {human_size(job.total)} · {human_speed(job.speed)}"
                if st.get("numSeeders") and int(st["numSeeders"]) > 0:
                    text += f" · {st['numSeeders']} 个节点"
                conns = st.get("connections")
                if conns and int(conns) > 1:
                    text += f" · {conns} 线程"
                self._apply_job_progress(job, frac, text)
            else:
                text = f"已下载 {human_size(job.done)} · {human_speed(job.speed)}"
                self._apply_job_progress(job, 0.0, text)

        self.apps_page.set_global_speed(total_speed)
        self.link_page.sync_statuses()

    def _apply_job_progress(self, job: DownloadJob, frac: float, text: str) -> None:
        job.message = text
        card = job.card
        if card is not None:
            try:
                card.show_progress(frac, text)
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------
    # 其它
    # ------------------------------------------------------------------
    def _on_catalog_updated(self, count: int) -> None:
        if count > 0:
            self.post(self.apps_page.rebuild)

    def open_data_dir(self) -> None:
        open_in_explorer(data_root())

    def _on_close(self) -> None:
        self._closing = True
        try:
            self.settings.last_selected = [
                c.app.id for c in self.apps_page.selected_cards()
            ]
            self.settings.save()
        except Exception:  # noqa: BLE001
            pass
        try:
            self.engine.stop()
        except Exception:  # noqa: BLE001
            pass
        self.destroy()


def run() -> None:
    app = SwiftGetApp()
    app.mainloop()
