"""通用界面组件。"""
from __future__ import annotations

from typing import Callable

import customtkinter as ctk

from . import theme


def bind_recursive(widget, sequence: str, callback: Callable) -> None:
    """把事件递归绑定到控件及其全部子控件，实现整块可点击。"""
    widget.bind(sequence, callback)
    for child in widget.winfo_children():
        bind_recursive(child, sequence, callback)


class AppCard(ctk.CTkFrame):
    """软件选择卡片：整卡可点击切换选中，下载时在卡片内展示进度。"""

    CARD_WIDTH = 296

    def __init__(
        self,
        master,
        app,
        colors: dict[str, str],
        on_toggle: Callable[["AppCard"], None],
        desc_wrap: int = 200,
        **kwargs,
    ) -> None:
        super().__init__(
            master,
            width=self.CARD_WIDTH,
            height=kwargs.pop("card_height", 132),
            corner_radius=theme._RADIUS,
            fg_color=colors["surface"],
            border_width=1,
            border_color=colors["border"],
            **kwargs,
        )
        self.app = app
        self.colors = colors
        self.on_toggle = on_toggle
        self.selected = False
        self._hover = False
        self._state_busy = False
        self.grid_propagate(False)

        self.grid_columnconfigure(1, weight=1)

        # 品牌色方块图标
        self.icon = ctk.CTkLabel(
            self,
            text=app.name[:1].upper(),
            width=40,
            height=40,
            corner_radius=10,
            fg_color=app.color,
            text_color="#FFFFFF",
            font=(theme.FONT_FAMILY, 17, "bold"),
        )
        self.icon.grid(row=0, column=0, padx=(16, 12), pady=(16, 0), sticky="nw")

        self.title = ctk.CTkLabel(
            self,
            text=app.name,
            anchor="w",
            font=(theme.FONT_FAMILY, 13, "bold"),
            text_color=colors["text"],
        )
        self.title.grid(row=0, column=1, padx=(0, 8), pady=(18, 0), sticky="new")

        self.check = ctk.CTkLabel(
            self,
            text="",
            width=20,
            height=20,
            corner_radius=6,
            fg_color=colors["surface"],
            border_width=1,
            border_color=colors["border_strong"],
            text_color="#FFFFFF",
            font=(theme.FONT_FAMILY, 11, "bold"),
        )
        self.check.grid(row=0, column=2, padx=(0, 16), pady=(18, 0), sticky="ne")

        self.desc = ctk.CTkLabel(
            self,
            text=app.desc,
            anchor="w",
            justify="left",
            wraplength=desc_wrap,
            font=(theme.FONT_FAMILY, 11),
            text_color=colors["text_muted"],
        )
        self.desc.grid(row=1, column=0, columnspan=3, padx=16, pady=(10, 0), sticky="w")

        self.meta = ctk.CTkLabel(
            self,
            text=self._meta_text(),
            anchor="w",
            font=(theme.FONT_FAMILY, 10),
            text_color=colors["text_faint"],
        )
        self.meta.grid(row=2, column=0, columnspan=3, padx=16, pady=(6, 0), sticky="w")

        # 命令行工具把用法直接印在卡片上（内容来自 core/own_apps.py 的源码），
        # 免得用户下完源码包还得解压翻 README 才知道怎么跑。
        self.usage = None
        if getattr(app, "usage", ""):
            self.usage = ctk.CTkLabel(
                self,
                text=app.usage,
                anchor="w",
                justify="left",
                wraplength=desc_wrap,
                font=("Consolas", 10),
                text_color=colors["text_faint"],
            )
            self.usage.grid(row=3, column=0, columnspan=3, padx=16, pady=(4, 0), sticky="w")

        # 进度条浮在卡片底部，不参与布局，避免卡片高度跳动
        self.progress = ctk.CTkProgressBar(
            self,
            height=4,
            corner_radius=2,
            progress_color=colors["primary"],
            fg_color=colors["track"],
        )
        self.progress.set(0)

        bind_recursive(self, "<Button-1>", self._click)
        bind_recursive(self, "<Enter>", self._enter)
        bind_recursive(self, "<Leave>", self._leave)

    # -- 外观 -------------------------------------------------------------
    def _meta_text(self) -> str:
        parts = []
        if self.app.size_label:
            parts.append(self.app.size_label)
        if not self.app.silent_ok:
            parts.append("需手动确认安装")
        elif self.app.supports_language:
            parts.append("可选语言")
        if len(self.app.sources) > 1:
            parts.append(f"{len(self.app.sources)} 个下载源")
        return " · ".join(parts)

    def _paint(self) -> None:
        c = self.colors
        if self.selected:
            self.configure(fg_color=c["selection"], border_color=c["primary"])
            self.check.configure(
                text="✓", fg_color=c["primary"], border_color=c["primary"]
            )
        elif self._hover:
            self.configure(fg_color=c["surface_alt"], border_color=c["border_strong"])
            self.check.configure(
                text="", fg_color=c["surface"], border_color=c["border_strong"]
            )
        else:
            self.configure(fg_color=c["surface"], border_color=c["border"])
            self.check.configure(
                text="", fg_color=c["surface"], border_color=c["border_strong"]
            )

    # -- 事件 -------------------------------------------------------------
    def _click(self, _event=None) -> None:
        if self._state_busy:
            return
        self.on_toggle(self)

    def _enter(self, _event=None) -> None:
        self._hover = True
        self._paint()

    def _leave(self, _event=None) -> None:
        # 指针在子控件之间移动也会触发 Leave，用坐标判断是否真的离开
        try:
            x, y = self.winfo_pointerxy()
            widget = self.winfo_containing(x, y)
            if widget is not None:
                parent = widget
                while parent is not None:
                    if parent is self:
                        return
                    parent = parent.master
        except Exception:  # noqa: BLE001
            pass
        self._hover = False
        self._paint()

    # -- 状态 -------------------------------------------------------------
    def set_selected(self, value: bool) -> None:
        self.selected = value
        self._paint()

    def set_busy(self, busy: bool) -> None:
        self._state_busy = busy

    def show_progress(self, fraction: float, text: str) -> None:
        self._show_bar(fraction, self.colors["primary"])
        self.meta.configure(text=text, text_color=self.colors["primary"])

    def show_done(self, text: str = "已完成") -> None:
        self._show_bar(1.0, self.colors["success"])
        self.meta.configure(text=text, text_color=self.colors["success"])

    def show_error(self, text: str) -> None:
        self._show_bar(1.0, self.colors["danger"])
        self.meta.configure(text=text, text_color=self.colors["danger"])

    def _show_bar(self, fraction: float, color: str) -> None:
        if not self.progress.winfo_ismapped():
            # customtkinter 组件的尺寸必须在构造时指定，place 只能给位置
            self.progress.place(relx=0.03, rely=1.0, y=-8, relwidth=0.94, anchor="sw")
        self.progress.configure(progress_color=color)
        self.progress.set(max(0.0, min(1.0, fraction)))

    def reset_progress(self) -> None:
        self.progress.place_forget()
        self.meta.configure(text=self._meta_text(), text_color=self.colors["text_faint"])


class PillButton(ctk.CTkButton):
    """胶囊按钮样式统一入口。"""

    def __init__(self, master, colors: dict[str, str], primary: bool = True, **kwargs):
        if primary:
            fg, hover, text = colors["primary"], colors["primary_hover"], "#FFFFFF"
        else:
            fg, hover, text = colors["surface"], colors["surface_alt"], colors["text"]
        kwargs.setdefault("corner_radius", 10)
        kwargs.setdefault("height", 38)
        kwargs.setdefault("font", (theme.FONT_FAMILY, 12, "bold" if primary else "normal"))
        kwargs.setdefault("border_width", 0 if primary else 1)
        if not primary:
            kwargs.setdefault("border_color", colors["border_strong"])
        super().__init__(master, fg_color=fg, hover_color=hover, text_color=text, **kwargs)


class SegmentedTabs(ctk.CTkFrame):
    """顶部页签：轻量下划线风格。"""

    def __init__(self, master, colors: dict[str, str], items: list[str], command=None):
        super().__init__(master, fg_color="transparent")
        self.colors = colors
        self.command = command
        self.buttons: list[ctk.CTkButton] = []
        self.active = 0
        for idx, label in enumerate(items):
            btn = ctk.CTkButton(
                self,
                text=label,
                width=0,
                height=32,
                corner_radius=8,
                fg_color="transparent",
                hover_color=colors["surface_alt"],
                text_color=colors["text_muted"],
                font=(theme.FONT_FAMILY, 12),
                command=lambda i=idx: self.select(i),
            )
            btn.pack(side="left", padx=(0, 4))
            self.buttons.append(btn)
        self.select(0, notify=False)

    def select(self, index: int, notify: bool = True) -> None:
        self.active = index
        for i, btn in enumerate(self.buttons):
            if i == index:
                btn.configure(
                    fg_color=self.colors["primary_soft"],
                    text_color=self.colors["primary"],
                    font=(theme.FONT_FAMILY, 12, "bold"),
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=self.colors["text_muted"],
                    font=(theme.FONT_FAMILY, 12),
                )
        if notify and self.command:
            self.command(index)


class TaskRow(ctk.CTkFrame):
    """加速下载页的任务行。"""

    def __init__(self, master, colors: dict[str, str], title: str, kind: str = "直链"):
        super().__init__(master, fg_color=colors["surface"], corner_radius=12,
                         border_width=1, border_color=colors["border"])
        self.colors = colors
        self.grid_columnconfigure(0, weight=1)

        self.name = ctk.CTkLabel(
            self, text=title, anchor="w",
            font=(theme.FONT_FAMILY, 12, "bold"), text_color=colors["text"],
        )
        self.name.grid(row=0, column=0, padx=(14, 8), pady=(10, 0), sticky="ew")

        self.tag = ctk.CTkLabel(
            self, text=kind, width=48, height=20, corner_radius=6,
            fg_color=colors["primary_soft"], text_color=colors["primary"],
            font=(theme.FONT_FAMILY, 10, "bold"),
        )
        self.tag.grid(row=0, column=1, padx=(0, 14), pady=(10, 0))

        self.bar = ctk.CTkProgressBar(
            self, height=5, corner_radius=3,
            progress_color=colors["primary"], fg_color=colors["track"],
        )
        self.bar.set(0)
        self.bar.grid(row=1, column=0, columnspan=2, padx=14, pady=(8, 0), sticky="ew")

        self.info = ctk.CTkLabel(
            self, text="等待中", anchor="w",
            font=(theme.FONT_FAMILY, 10), text_color=colors["text_muted"],
        )
        self.info.grid(row=2, column=0, columnspan=2, padx=14, pady=(4, 10), sticky="ew")

    def update_state(self, fraction: float, text: str, done: bool = False, error: bool = False):
        self.bar.set(max(0.0, min(1.0, fraction)))
        self.info.configure(text=text)
        if error:
            self.bar.configure(progress_color=self.colors["danger"])
            self.info.configure(text_color=self.colors["danger"])
        elif done:
            self.bar.configure(progress_color=self.colors["success"])
            self.info.configure(text_color=self.colors["success"])
