"""自创应用页：作者自己写的几个小工具，直接从这里下载。

和「常用软件」页的区别：
* 数据来自 ``core.own_apps``，不走 catalog，也不受远程清单覆盖；
* 没有安装环节——绿色版下载完就是成品，源码包下载完就是压缩包；
* 多一个「打开仓库」按钮，方便看源码和 README。
"""
from __future__ import annotations

import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.aria2 import human_speed
from core.own_apps import OWN_APPS, OWN_CATEGORIES, by_category

from . import theme, widgets


class OwnAppsPage(ctk.CTkFrame):
    COLUMNS = 3

    def __init__(self, master, host) -> None:
        super().__init__(master, fg_color="transparent")
        self.host = host
        self.colors = host.colors
        self.cards: dict[str, widgets.AppCard] = {}
        self._category = "全部"
        self._selected: set[str] = set()

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_scroll()
        self._build_footer()
        self.rebuild()

    # ------------------------------------------------------------------
    def _build_header(self) -> None:
        c = self.colors
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=26, pady=(20, 6))
        head.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            head, text="自创应用", anchor="w",
            font=(theme.FONT_FAMILY, 19, "bold"), text_color=c["text"],
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            head, text="我自己写的小工具，独立打包；绿色版下载完双击就能用，源码包解压即用",
            anchor="w", font=(theme.FONT_FAMILY, 11), text_color=c["text_muted"],
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        actions = ctk.CTkFrame(head, fg_color="transparent")
        actions.grid(row=0, column=2, rowspan=2, sticky="e")

        ctk.CTkButton(
            actions, text="全选", width=54, height=28, corner_radius=8,
            fg_color="transparent", hover_color=c["surface_alt"],
            text_color=c["text_muted"], border_width=1, border_color=c["border_strong"],
            font=(theme.FONT_FAMILY, 11), command=self._select_all,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            actions, text="清空", width=54, height=28, corner_radius=8,
            fg_color="transparent", hover_color=c["surface_alt"],
            text_color=c["text_muted"], border_width=1, border_color=c["border_strong"],
            font=(theme.FONT_FAMILY, 11), command=self._clear_all,
        ).pack(side="left")

        # 分类筛选
        cat_bar = ctk.CTkFrame(self, fg_color="transparent")
        cat_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(6, 0))
        self.cat_buttons: dict[str, ctk.CTkButton] = {}
        for cat in OWN_CATEGORIES:
            btn = ctk.CTkButton(
                cat_bar, text=cat, width=0, height=26, corner_radius=8,
                fg_color="transparent", hover_color=c["surface_alt"],
                text_color=c["text_muted"], font=(theme.FONT_FAMILY, 11),
                command=lambda k=cat: self._set_category(k),
            )
            btn.pack(side="left", padx=(0, 4))
            self.cat_buttons[cat] = btn
        self._paint_categories()

    def _build_scroll(self) -> None:
        c = self.colors
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=c["border"],
            scrollbar_button_hover_color=c["border_strong"],
        )
        self.scroll.grid(row=2, column=0, sticky="nsew", padx=18, pady=(4, 0))
        for i in range(self.COLUMNS):
            self.scroll.grid_columnconfigure(i, weight=1)

    def _build_footer(self) -> None:
        c = self.colors
        footer = ctk.CTkFrame(
            self, fg_color=c["surface"], corner_radius=0,
            border_width=1, border_color=c["border"],
        )
        footer.grid(row=3, column=0, sticky="ew", pady=(10, 12))

        inner = ctk.CTkFrame(footer, fg_color="transparent")
        inner.pack(fill="x", padx=26, pady=14)

        # ---- 第一行：保存路径 ----
        row0 = ctk.CTkFrame(inner, fg_color="transparent")
        row0.pack(fill="x")

        ctk.CTkLabel(
            row0, text="保存到", width=52, anchor="w",
            font=(theme.FONT_FAMILY, 11), text_color=c["text_muted"],
        ).pack(side="left")

        ctk.CTkButton(
            row0, text="打开", width=58, height=34, corner_radius=9,
            fg_color="transparent", hover_color=c["surface_alt"],
            text_color=c["text_muted"], border_width=1, border_color=c["border_strong"],
            font=(theme.FONT_FAMILY, 11), command=self._open_dir,
        ).pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            row0, text="浏览", width=58, height=34, corner_radius=9,
            fg_color=c["surface_alt"], hover_color=c["track"],
            text_color=c["text"], font=(theme.FONT_FAMILY, 11),
            command=self._choose_dir,
        ).pack(side="right")

        self.path_var = ctk.StringVar(value=self.host.settings.download_dir)
        ctk.CTkEntry(
            row0, textvariable=self.path_var, height=34, corner_radius=9,
            fg_color=c["surface_alt"], border_color=c["border"],
            text_color=c["text"], font=(theme.FONT_FAMILY, 11),
        ).pack(side="left", fill="x", expand=True, padx=8)

        # ---- 第二行：操作 ----
        row1 = ctk.CTkFrame(inner, fg_color="transparent")
        row1.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(
            row1, text="打开仓库", width=86, height=34, corner_radius=9,
            fg_color="transparent", hover_color=c["surface_alt"],
            text_color=c["text_muted"], border_width=1, border_color=c["border_strong"],
            font=(theme.FONT_FAMILY, 11), command=self._open_repo,
        ).pack(side="left")

        self.hint = ctk.CTkLabel(
            row1, text="", anchor="w",
            font=(theme.FONT_FAMILY, 10), text_color=c["text_faint"],
        )
        self.hint.pack(side="left", padx=(12, 0))

        self.start_btn = widgets.PillButton(
            row1, c, text="开始下载", width=112, command=self._start,
        )
        self.start_btn.pack(side="right")

        self.speed_label = ctk.CTkLabel(
            row1, text="", anchor="e",
            font=(theme.FONT_FAMILY, 10), text_color=c["primary"],
        )
        self.speed_label.pack(side="right", padx=(12, 12))

        self.sel_label = ctk.CTkLabel(
            row1, text="已选 0 个", anchor="e",
            font=(theme.FONT_FAMILY, 11), text_color=c["text_muted"],
        )
        self.sel_label.pack(side="right")

    # ------------------------------------------------------------------
    def rebuild(self) -> None:
        for widget in self.scroll.winfo_children():
            widget.destroy()
        self.cards.clear()

        for idx, app in enumerate(by_category(self._category)):
            card = widgets.AppCard(
                self.scroll, app, self.colors, self._toggle_card,
                desc_wrap=238, card_height=138,
            )
            row, col = divmod(idx, self.COLUMNS)
            card.grid(row=row, column=col, padx=7, pady=7, sticky="new")
            self.cards[app.id] = card
            if app.id in self._selected:
                card.set_selected(True)

        self._restore_job_cards()
        self.refresh_status()

    def _restore_job_cards(self) -> None:
        """页面重建后把进行中任务的进度重新挂回卡片。"""
        for job in getattr(self.host, "jobs", {}).values():
            card = self.cards.get(job.app.id)
            if card is None:
                continue
            job.card = card
            try:
                if job.state == "error":
                    card.show_error(job.message or "出错")
                elif job.state == "finished":
                    card.show_done(job.install_result or "已保存")
                elif job.state in ("downloading", "verifying", "installing"):
                    frac = (job.done / job.total) if job.total else 0.0
                    card.show_progress(frac, job.message or "下载中…")
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------
    def _toggle_card(self, card) -> None:
        if card.selected:
            card.set_selected(False)
            self._selected.discard(card.app.id)
        else:
            card.set_selected(True)
            self._selected.add(card.app.id)
        self.refresh_status()

    def _select_all(self) -> None:
        for aid, card in self.cards.items():
            card.set_selected(True)
            self._selected.add(aid)
        self.refresh_status()

    def _clear_all(self) -> None:
        for card in self.cards.values():
            card.set_selected(False)
        self._selected.clear()
        self.refresh_status()

    def _set_category(self, category: str) -> None:
        self._category = category
        self._paint_categories()
        self.rebuild()

    def _paint_categories(self) -> None:
        c = self.colors
        for cat, btn in self.cat_buttons.items():
            if cat == self._category:
                btn.configure(
                    fg_color=c["primary_soft"], text_color=c["primary"],
                    font=(theme.FONT_FAMILY, 11, "bold"),
                )
            else:
                btn.configure(
                    fg_color="transparent", text_color=c["text_muted"],
                    font=(theme.FONT_FAMILY, 11),
                )

    # ------------------------------------------------------------------
    def _choose_dir(self) -> None:
        initial = self.path_var.get() or str(Path.home())
        chosen = filedialog.askdirectory(initialdir=initial, title="选择保存目录", parent=self)
        if chosen:
            self.path_var.set(chosen)
            self.host.settings.download_dir = chosen
            self.host.settings.save()

    def _open_dir(self) -> None:
        from core.paths import open_in_explorer

        path = Path(self.path_var.get() or self.host.settings.download_dir)
        path.mkdir(parents=True, exist_ok=True)
        open_in_explorer(path)

    def _open_repo(self) -> None:
        """打开选中项的项目主页；没选就打开当前列表里的第一个。"""
        apps = self.selected_apps()
        if not apps:
            if not self.cards:
                return
            apps = [next(iter(self.cards.values())).app]
        url = apps[0].homepage
        if url:
            webbrowser.open(url)

    def _start(self) -> None:
        self.host.settings.download_dir = self.path_var.get().strip()
        self.host.settings.save()
        apps = self.selected_apps()
        if not apps:
            messagebox.showinfo("提示", "请先勾选要下载的软件。", parent=self)
            return
        self.host.enqueue_apps(apps, "zh")

    # ------------------------------------------------------------------
    def selected_apps(self):
        return [self.cards[aid].app for aid in self._selected if aid in self.cards]

    def card_for(self, app_id: str):
        return self.cards.get(app_id)

    def refresh_status(self) -> None:
        try:
            self.sel_label.configure(text=f"已选 {len(self._selected)} 个")
        except Exception:  # noqa: BLE001
            pass

        apps = self.selected_apps()
        tips = []
        if any(a.kind == "portable" for a in apps):
            tips.append("绿色版无需安装")
        if any(a.kind == "archive" for a in apps):
            tips.append("源码包解压后按 README 安装")
        try:
            self.hint.configure(text=" · ".join(tips) if tips else "共 %d 个自研应用" % len(OWN_APPS))
        except Exception:  # noqa: BLE001
            pass

    def set_global_speed(self, bps: float) -> None:
        try:
            self.speed_label.configure(text=f"↓ {human_speed(bps)}" if bps > 0 else "")
        except Exception:  # noqa: BLE001
            pass
