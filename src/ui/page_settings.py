"""设置页。"""
from __future__ import annotations

import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core import update
from core.paths import APP_VERSION, data_root, is_frozen, open_in_explorer

from . import theme, widgets

CONN_OPTIONS = ["4", "8", "16", "32"]


class SettingsPage(ctk.CTkFrame):
    def __init__(self, master, host) -> None:
        super().__init__(master, fg_color="transparent")
        self.host = host
        self.colors = host.colors

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()

    # ------------------------------------------------------------------
    def _build_header(self) -> None:
        c = self.colors
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=26, pady=(20, 8))
        ctk.CTkLabel(
            head, text="设置", anchor="w",
            font=(theme.FONT_FAMILY, 19, "bold"), text_color=c["text"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            head, text="修改后立即生效，部分选项在下次下载时应用",
            anchor="w", font=(theme.FONT_FAMILY, 11), text_color=c["text_muted"],
        ).pack(anchor="w", pady=(2, 0))

    def _build_body(self) -> None:
        c = self.colors
        self.scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=c["border"],
            scrollbar_button_hover_color=c["border_strong"],
        )
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 16))
        self.scroll.grid_columnconfigure(0, weight=1)

        self._section("下载", 0)
        self._path_row(1)
        self._conn_row(2)
        self._p2p_row(3)

        self._section("安装", 4)
        self._switch_row(5, "下载完成后自动静默安装",
                         "无需手动点击，安装过程在后台完成", "auto_install")
        self._switch_row(6, "安装完成后自动启动软件",
                         "仅对常见路径的软件生效", "auto_launch")
        self._switch_row(7, "安装成功后删除安装包",
                         "节省磁盘空间", "delete_after_install")

        self._section("高级", 8)
        self._catalog_row(9)
        self._tools_row(10)

        self._section("关于", 11)
        self._about_row(12)

    # -- 组件 -------------------------------------------------------------
    def _card(self, row: int) -> ctk.CTkFrame:
        c = self.colors
        frame = ctk.CTkFrame(
            self.scroll, fg_color=c["surface"], corner_radius=14,
            border_width=1, border_color=c["border"],
        )
        frame.grid(row=row, column=0, sticky="ew", padx=6, pady=(0, 10))
        frame.grid_columnconfigure(1, weight=1)
        return frame

    def _section(self, title: str, row: int) -> None:
        ctk.CTkLabel(
            self.scroll, text=title, anchor="w",
            font=(theme.FONT_FAMILY, 11, "bold"), text_color=self.colors["text_faint"],
        ).grid(row=row, column=0, sticky="w", padx=10, pady=(6, 6))

    def _label_pair(self, parent, row: int, title: str, desc: str) -> None:
        c = self.colors
        ctk.CTkLabel(
            parent, text=title, anchor="w",
            font=(theme.FONT_FAMILY, 12), text_color=c["text"],
        ).grid(row=row, column=0, sticky="w", padx=(16, 12), pady=(12, 0))
        if desc:
            ctk.CTkLabel(
                parent, text=desc, anchor="w",
                font=(theme.FONT_FAMILY, 10), text_color=c["text_faint"],
            ).grid(row=row + 1, column=0, sticky="w", padx=(16, 12), pady=(0, 12))

    def _path_row(self, row: int) -> None:
        c = self.colors
        card = self._card(row)
        self._label_pair(card, 0, "默认下载目录", "")

        holder = ctk.CTkFrame(card, fg_color="transparent")
        holder.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=12)
        holder.grid_columnconfigure(0, weight=1)

        self.dir_var = ctk.StringVar(value=self.host.settings.download_dir)
        entry = ctk.CTkEntry(
            holder, textvariable=self.dir_var, height=34, corner_radius=9,
            fg_color=c["surface_alt"], border_color=c["border"],
            text_color=c["text"], font=(theme.FONT_FAMILY, 11),
        )
        entry.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            holder, text="浏览", width=58, height=34, corner_radius=9,
            fg_color=c["surface_alt"], hover_color=c["track"], text_color=c["text"],
            font=(theme.FONT_FAMILY, 11), command=self._choose_dir,
        ).grid(row=0, column=1, padx=(8, 0))

    def _conn_row(self, row: int) -> None:
        c = self.colors
        card = self._card(row)
        self._label_pair(card, 0, "单文件并发连接数",
                         "数值越大分片越多，服务器支持 Range 时提速明显")

        self.conn_menu = ctk.CTkOptionMenu(
            card, values=CONN_OPTIONS, width=88, height=34, corner_radius=9,
            fg_color=c["surface_alt"], button_color=c["surface_alt"],
            button_hover_color=c["track"], text_color=c["text"],
            dropdown_fg_color=c["surface"], dropdown_text_color=c["text"],
            dropdown_hover_color=c["surface_alt"],
            font=(theme.FONT_FAMILY, 11), dropdown_font=(theme.FONT_FAMILY, 11),
            command=self._on_conn,
        )
        self.conn_menu.set(str(self.host.settings.max_connections))
        self.conn_menu.grid(row=0, column=1, sticky="e", padx=(0, 16), pady=(12, 12))

    def _p2p_row(self, row: int) -> None:
        c = self.colors
        card = self._card(row)
        self._label_pair(card, 0, "启用 P2P（BitTorrent / DHT）",
                         "磁力链与种子下载必需；关闭后仅支持直链")

        self.p2p_var = ctk.BooleanVar(value=self.host.settings.p2p_enabled)
        ctk.CTkCheckBox(
            card, text="", width=24, height=24, checkbox_width=22, checkbox_height=22,
            variable=self.p2p_var, corner_radius=6,
            fg_color=c["primary"], hover_color=c["primary_hover"],
            border_color=c["border_strong"], command=self._on_p2p,
        ).grid(row=0, column=1, sticky="e", padx=(0, 16))

    def _switch_row(self, row: int, title: str, desc: str, attr: str) -> None:
        c = self.colors
        card = self._card(row)
        self._label_pair(card, 0, title, desc)

        var = ctk.BooleanVar(value=getattr(self.host.settings, attr))
        ctk.CTkCheckBox(
            card, text="", width=24, height=24, checkbox_width=22, checkbox_height=22,
            variable=var, corner_radius=6,
            fg_color=c["primary"], hover_color=c["primary_hover"],
            border_color=c["border_strong"],
            command=lambda a=attr, v=var: self._on_flag(a, v),
        ).grid(row=0, column=1, sticky="e", padx=(0, 16))
        setattr(self, f"var_{attr}", var)

    def _catalog_row(self, row: int) -> None:
        c = self.colors
        card = self._card(row)
        self._label_pair(card, 0, "软件清单更新地址",
                         "留空则不更新。填入 JSON 地址可在线修复失效链接")

        holder = ctk.CTkFrame(card, fg_color="transparent")
        holder.grid(row=0, column=1, sticky="ew", padx=(0, 16), pady=12)
        holder.grid_columnconfigure(0, weight=1)

        self.catalog_var = ctk.StringVar(value=self.host.settings.catalog_url)
        ctk.CTkEntry(
            holder, textvariable=self.catalog_var, height=34, corner_radius=9,
            fg_color=c["surface_alt"], border_color=c["border"],
            text_color=c["text"], font=(theme.FONT_FAMILY, 11),
            placeholder_text="https://example.com/catalog.json",
        ).grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            holder, text="更新", width=58, height=34, corner_radius=9,
            fg_color=c["surface_alt"], hover_color=c["track"], text_color=c["text"],
            font=(theme.FONT_FAMILY, 11), command=self._update_catalog,
        ).grid(row=0, column=1, padx=(8, 0))

    def _tools_row(self, row: int) -> None:
        c = self.colors
        card = self._card(row)
        self._label_pair(card, 0, "配置文件与内核", "")

        holder = ctk.CTkFrame(card, fg_color="transparent")
        holder.grid(row=0, column=1, sticky="e", padx=(0, 16), pady=12)

        for text, cmd in (
            ("打开数据目录", lambda: open_in_explorer(data_root())),
            ("导出清单", self._export_catalog),
        ):
            ctk.CTkButton(
                holder, text=text, width=96, height=32, corner_radius=9,
                fg_color=c["surface_alt"], hover_color=c["track"], text_color=c["text"],
                font=(theme.FONT_FAMILY, 11), command=cmd,
            ).pack(side="left", padx=(8, 0))

    def _about_row(self, row: int) -> None:
        c = self.colors
        card = self._card(row)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.grid(row=0, column=0, columnspan=2, sticky="ew", padx=16, pady=14)

        head = ctk.CTkFrame(inner, fg_color="transparent")
        head.pack(fill="x")

        ctk.CTkLabel(
            head, text=f"SwiftGet · 极速软件下载器  v{APP_VERSION}",
            anchor="w", font=(theme.FONT_FAMILY, 12, "bold"), text_color=c["text"],
        ).pack(side="left")

        self.update_btn = ctk.CTkButton(
            head, text="检查更新", width=84, height=26,
            font=(theme.FONT_FAMILY, 10),
            fg_color=c["surface"],
            hover_color=c["track"],
            text_color=c["text"], border_width=1, border_color=c["border"],
            command=self._on_check_update,
        )
        self.update_btn.pack(side="right")
        self._updating = False

        ctk.CTkLabel(
            inner,
            text=("开源软件，基于 Python + CustomTkinter 构建，下载内核为 aria2。\n"
                  "所有下载均直接来自软件官方或公开镜像地址，不经过任何中转服务器；\n"
                  "P2P 模式下你的客户端会与 BitTorrent 网络中的其他节点交换数据。"),
            anchor="w", justify="left",
            font=(theme.FONT_FAMILY, 10), text_color=c["text_muted"],
        ).pack(anchor="w", pady=(6, 0))

    # -- 自更新 -----------------------------------------------------------
    def _on_check_update(self) -> None:
        if self._updating:
            return
        self._updating = True
        self._set_update_btn("检查中…", state="disabled")

        def worker() -> None:
            try:
                info = update.check_update()
            except Exception as exc:  # noqa: BLE001
                info = {"ok": False, "error": str(exc)}
            self.host.post(lambda: self._update_checked(info))

        threading.Thread(target=worker, daemon=True).start()

    def _set_update_btn(self, text: str, state: str = "normal") -> None:
        try:
            self.update_btn.configure(text=text, state=state)
        except Exception:  # noqa: BLE001
            pass

    def _update_checked(self, info: dict) -> None:
        self._updating = False
        self._set_update_btn("检查更新")

        if not info.get("ok"):
            messagebox.showwarning(
                "检查更新",
                f"没能连上 GitHub：{info.get('error') or '未知原因'}\n"
                f"当前版本 v{APP_VERSION}。稍后再试，或直接到发布页看。",
                parent=self,
            )
            webbrowser.open(update.RELEASES_PAGE)
            return

        if not info.get("has_update"):
            messagebox.showinfo(
                "检查更新", f"已是最新版本 v{APP_VERSION}。", parent=self,
            )
            return

        latest = info.get("latest") or "?"
        notes = (info.get("notes") or "").strip()
        if notes:
            notes = notes[:500] + ("…" if len(notes) > 500 else "")
        msg = f"发现新版本 v{latest}（当前 v{APP_VERSION}）。\n\n"
        if notes:
            msg += notes + "\n\n"
        msg += "现在下载并更新吗？更新时程序会关掉，替换完成后自动重新打开。"

        if not messagebox.askyesno("发现新版本", msg, parent=self):
            return

        if not is_frozen():
            messagebox.showinfo(
                "检查更新",
                f"新版本 v{latest} 可用。\n源码运行模式不能自己替换，"
                "请到发布页下载绿色版。",
                parent=self,
            )
            webbrowser.open(info.get("page") or update.RELEASES_PAGE)
            return

        self._start_download(info)

    def _start_download(self, info: dict) -> None:
        self._updating = True
        self._set_update_btn("0%", state="disabled")
        urls = update.asset_urls(info.get("asset_url") or "")
        dest = data_root() / f"SwiftGet-{info.get('latest')}.exe"

        def progress(got: int, total: int) -> None:
            pct = f"{round(got * 100 / total)}%" if total else "下载中"
            self.host.post(lambda: self._set_update_btn(pct, state="disabled"))

        def worker() -> None:
            try:
                path = update.download(urls, dest, progress)
            except Exception as exc:  # noqa: BLE001
                self.host.post(lambda: self._download_failed(exc, info))
                return
            self.host.post(lambda: self._download_done(path, info))

        threading.Thread(target=worker, daemon=True).start()

    def _download_failed(self, exc: Exception, info: dict) -> None:
        self._updating = False
        self._set_update_btn("检查更新")
        if messagebox.askyesno(
            "更新失败",
            f"下载新版本失败：{exc}\n\n要打开发布页手动下载吗？",
            parent=self,
        ):
            webbrowser.open(info.get("page") or update.RELEASES_PAGE)

    def _download_done(self, path: Path, info: dict) -> None:
        self._updating = False
        self._set_update_btn("检查更新")
        size = path.stat().st_size / 1024 / 1024 if path.exists() else 0
        if not messagebox.askyesno(
            "下载完成",
            f"新版本 v{info.get('latest')} 已下载（{size:.1f} MB）。\n\n"
            "点「是」立即替换并重启，程序会自动关掉再打开。",
            parent=self,
        ):
            return
        result = update.apply_update(path)
        if not result.get("ok"):
            messagebox.showerror("更新失败", str(result.get("error")), parent=self)
            return
        # 让 bat 拿到文件锁：先关窗，进程退出
        self.host.after(200, self.host.destroy)

    # -- 回调 -------------------------------------------------------------
    def _persist(self) -> None:
        self.host.settings.save()

    def _choose_dir(self) -> None:
        chosen = filedialog.askdirectory(
            initialdir=self.dir_var.get() or str(Path.home()),
            title="选择下载目录", parent=self,
        )
        if chosen:
            self.dir_var.set(chosen)
            self.host.settings.download_dir = chosen
            self._persist()

    def _on_conn(self, value: str) -> None:
        try:
            n = int(value)
        except ValueError:
            return
        self.host.settings.max_connections = n
        self.host.settings.split = n
        self.host.engine.options.max_connections = n
        self.host.engine.options.split = n
        self._persist()

    def _on_p2p(self) -> None:
        enabled = bool(self.p2p_var.get())
        self.host.settings.p2p_enabled = enabled
        self._persist()
        if not enabled and self.host.engine.running:
            if messagebox.askyesno(
                "需要重启下载引擎",
                "切换 P2P 开关需要重启下载引擎，正在进行的任务会中断。\n是否立即重启？",
                parent=self,
            ):
                import threading

                from core.aria2 import Aria2Options

                opts = Aria2Options(
                    max_connections=self.host.settings.max_connections,
                    split=self.host.settings.split,
                    p2p_enabled=enabled,
                    bt_port=self.host.settings.bt_port,
                )

                def worker() -> None:
                    try:
                        self.host.engine.restart(opts)
                    except Exception:  # noqa: BLE001
                        pass

                threading.Thread(target=worker, daemon=True).start()

    def _on_flag(self, attr: str, var) -> None:
        setattr(self.host.settings, attr, bool(var.get()))
        self._persist()

    def _update_catalog(self) -> None:
        url = self.catalog_var.get().strip()
        self.host.settings.catalog_url = url
        self._persist()
        if not url:
            messagebox.showinfo("提示", "未填写地址，已关闭自动更新。", parent=self)
            return

        def done(count: int) -> None:
            def notify() -> None:
                if count < 0:
                    messagebox.showerror("更新失败", "无法获取清单，请检查地址或网络。", parent=self)
                else:
                    messagebox.showinfo(
                        "更新完成",
                        f"清单已更新，新增 {count} 个软件。",
                        parent=self,
                    )
                    self.host.apps_page.rebuild()

            self.host.post(notify)

        self.host.catalog.update_async(url, done)

    def _export_catalog(self) -> None:
        try:
            path = self.host.catalog.export_local()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("导出失败", str(exc), parent=self)
            return
        messagebox.showinfo("已导出", f"清单已写入：\n{path}", parent=self)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        try:
            self.dir_var.set(self.host.settings.download_dir)
            self.conn_menu.set(str(self.host.settings.max_connections))
            self.catalog_var.set(self.host.settings.catalog_url)
        except Exception:  # noqa: BLE001
            pass
