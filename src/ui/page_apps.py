"""常用软件页：卡片网格 + 路径/语言配置 + 一键静默下载。"""
from __future__ import annotations

from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from core.aria2 import human_speed
from core.catalog import CATEGORIES

from . import theme, widgets

LANG_LABELS = ["简体中文", "English", "跟随系统"]
LANG_VALUES = {"简体中文": "zh", "English": "en", "跟随系统": "system"}


class AppsPage(ctk.CTkFrame):
    COLUMNS = 3

    def __init__(self, master, host) -> None:
        super().__init__(master, fg_color="transparent")
        self.host = host
        self.colors = host.colors
        self.cards: dict[str, widgets.AppCard] = {}
        self._category = "全部"
        self._selected: set[str] = set(self.host.settings.last_selected or [])

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

        title = ctk.CTkLabel(
            head, text="常用软件", anchor="w",
            font=(theme.FONT_FAMILY, 19, "bold"), text_color=c["text"],
        )
        title.grid(row=0, column=0, sticky="w")

        subtitle = ctk.CTkLabel(
            head, text="勾选后一键静默下载并安装，安装过程无需手动点击",
            anchor="w", font=(theme.FONT_FAMILY, 11), text_color=c["text_muted"],
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(2, 0))

        actions = ctk.CTkFrame(head, fg_color="transparent")
        actions.grid(row=0, column=2, rowspan=2, sticky="e")
        self.sel_all_btn = ctk.CTkButton(
            actions, text="全选", width=54, height=28, corner_radius=8,
            fg_color="transparent", hover_color=c["surface_alt"],
            text_color=c["text_muted"], border_width=1, border_color=c["border_strong"],
            font=(theme.FONT_FAMILY, 11), command=self._select_all,
        )
        self.sel_all_btn.pack(side="left", padx=(0, 6))
        self.clear_btn = ctk.CTkButton(
            actions, text="清空", width=54, height=28, corner_radius=8,
            fg_color="transparent", hover_color=c["surface_alt"],
            text_color=c["text_muted"], border_width=1, border_color=c["border_strong"],
            font=(theme.FONT_FAMILY, 11), command=self._clear_all,
        )
        self.clear_btn.pack(side="left")

        # 分类筛选
        self.cat_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.cat_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(6, 0))
        self.cat_buttons: dict[str, ctk.CTkButton] = {}
        for cat in CATEGORIES:
            btn = ctk.CTkButton(
                self.cat_bar, text=cat, width=0, height=26, corner_radius=8,
                fg_color="transparent", hover_color=self.colors["surface_alt"],
                text_color=self.colors["text_muted"], font=(theme.FONT_FAMILY, 11),
                command=lambda c=cat: self._set_category(c),
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
        self.path_entry = ctk.CTkEntry(
            row0, textvariable=self.path_var, height=34, corner_radius=9,
            fg_color=c["surface_alt"], border_color=c["border"],
            text_color=c["text"], font=(theme.FONT_FAMILY, 11),
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=8)

        # ---- 第二行：语言 + 操作 ----
        row1 = ctk.CTkFrame(inner, fg_color="transparent")
        row1.pack(fill="x", pady=(10, 0))

        ctk.CTkLabel(
            row1, text="安装语言", width=52, anchor="w",
            font=(theme.FONT_FAMILY, 11), text_color=c["text_muted"],
        ).pack(side="left")

        self.lang_menu = ctk.CTkOptionMenu(
            row1, values=LANG_LABELS, width=124, height=34, corner_radius=9,
            fg_color=c["surface_alt"], button_color=c["surface_alt"],
            button_hover_color=c["track"], text_color=c["text"],
            dropdown_fg_color=c["surface"], dropdown_text_color=c["text"],
            dropdown_hover_color=c["surface_alt"],
            font=(theme.FONT_FAMILY, 11), dropdown_font=(theme.FONT_FAMILY, 11),
            command=lambda _v: self.refresh_status(),
        )
        self.lang_menu.set("简体中文")
        self.lang_menu.pack(side="left", padx=(0, 10))

        self.lang_hint = ctk.CTkLabel(
            row1, text="", anchor="w",
            font=(theme.FONT_FAMILY, 10), text_color=c["text_faint"],
        )
        self.lang_hint.pack(side="left")

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
    # 卡片构建
    # ------------------------------------------------------------------
    def rebuild(self) -> None:
        self._selected = {i for i in self._selected if self.host.catalog.get(i)}
        for widget in self.scroll.winfo_children():
            widget.destroy()
        self.cards.clear()

        apps = self.host.catalog.by_category(self._category)
        for idx, app in enumerate(apps):
            card = widgets.AppCard(
                self.scroll, app, self.colors, self._toggle_card,
            )
            row, col = divmod(idx, self.COLUMNS)
            card.grid(row=row, column=col, padx=7, pady=7, sticky="new")
            self.cards[app.id] = card
            if app.id in self._selected:
                card.set_selected(True)

        self._restore_job_cards()
        self.refresh_status()

    def _restore_job_cards(self) -> None:
        """重建卡片后把进行中任务的引用与进度重新挂回去。"""
        for job in getattr(self.host, "jobs", {}).values():
            card = self.cards.get(job.app.id)
            job.card = card
            if card is None:
                continue
            try:
                if job.state == "error":
                    card.show_error(job.message or "出错")
                elif job.state == "finished":
                    card.show_done(job.install_result or "已完成")
                elif job.state in ("downloading", "verifying", "installing"):
                    frac = (job.done / job.total) if job.total else 0.0
                    card.show_progress(frac, job.message or "下载中…")
            except Exception:  # noqa: BLE001
                pass

    def card_for(self, app_id: str):
        return self.cards.get(app_id)

    def selected_cards(self) -> list[widgets.AppCard]:
        return [c for aid, c in self.cards.items() if aid in self._selected]

    def selected_apps(self):
        return [c.app for c in self.selected_cards()]

    # ------------------------------------------------------------------
    # 交互
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

    def _choose_dir(self) -> None:
        initial = self.path_var.get() or str(Path.home())
        chosen = filedialog.askdirectory(initialdir=initial, title="选择下载目录", parent=self)
        if chosen:
            self.path_var.set(chosen)
            self.host.settings.download_dir = chosen
            self.host.settings.save()

    def _open_dir(self) -> None:
        from core.paths import open_in_explorer

        path = Path(self.path_var.get() or self.host.settings.download_dir)
        path.mkdir(parents=True, exist_ok=True)
        open_in_explorer(path)

    def _start(self) -> None:
        self.host.settings.download_dir = self.path_var.get().strip()
        self.host.settings.save()
        lang = LANG_VALUES.get(self.lang_menu.get(), "zh")
        apps = self.selected_apps()
        if not apps:
            from tkinter import messagebox

            messagebox.showinfo("提示", "请先勾选要下载的软件。", parent=self)
            return
        self.host.enqueue_apps(apps, lang)

    # ------------------------------------------------------------------
    # 状态刷新
    # ------------------------------------------------------------------
    def refresh_status(self) -> None:
        count = len(self._selected)
        try:
            self.sel_label.configure(text=f"已选 {count} 个")
        except Exception:  # noqa: BLE001
            pass

        apps = self.selected_apps()
        manual = [a for a in apps if not a.silent_ok]
        if manual:
            hint = f"{len(manual)} 个软件安装时需手动确认"
        elif apps and not any(a.supports_language for a in apps):
            hint = "所选安装包不区分语言"
        elif any(a.supports_language for a in apps):
            hint = "部分软件支持指定语言"
        else:
            hint = ""
        try:
            self.lang_hint.configure(text=hint)
        except Exception:  # noqa: BLE001
            pass

    def set_global_speed(self, bps: float) -> None:
        try:
            if bps > 0:
                self.speed_label.configure(text=f"↓ {human_speed(bps)}")
            else:
                self.speed_label.configure(text="")
        except Exception:  # noqa: BLE001
            pass
