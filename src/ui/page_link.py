"""链接 / P2P 加速页。

支持三类输入：
* ``http(s)://`` 直链 —— 多线程分片加速
* ``magnet:?xt=urn:btih:...`` 磁力链 —— DHT + Peer Exchange P2P 加速
* ``.torrent`` 种子文件
"""
from __future__ import annotations

import time
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from core.aria2 import human_size, human_speed

from . import theme, widgets


class LinkPage(ctk.CTkFrame):
    def __init__(self, master, host) -> None:
        super().__init__(master, fg_color="transparent")
        self.host = host
        self.colors = host.colors
        self.tasks: dict[str, dict] = {}
        self._last_sync = 0.0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_input()
        self._build_list()

    # ------------------------------------------------------------------
    def _build_header(self) -> None:
        c = self.colors
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=26, pady=(20, 8))

        ctk.CTkLabel(
            head, text="链接 / P2P 加速", anchor="w",
            font=(theme.FONT_FAMILY, 19, "bold"), text_color=c["text"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            head,
            text="直链走多线程分片加速；磁力链与种子走 BitTorrent 网络，节点越多越快",
            anchor="w", font=(theme.FONT_FAMILY, 11), text_color=c["text_muted"],
        ).pack(anchor="w", pady=(2, 0))

    def _build_input(self) -> None:
        c = self.colors
        card = ctk.CTkFrame(
            self, fg_color=c["surface"], corner_radius=14,
            border_width=1, border_color=c["border"],
        )
        card.grid(row=1, column=0, sticky="ew", padx=24, pady=(4, 10))
        card.grid_columnconfigure(0, weight=1)

        self.textbox = ctk.CTkTextbox(
            card, height=104, corner_radius=10,
            fg_color=c["surface_alt"], border_width=1, border_color=c["border"],
            text_color=c["text"], font=(theme.FONT_FAMILY, 11),
            wrap="none",
        )
        self.textbox.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 0))
        self.textbox.insert("1.0", "")
        self._add_placeholder()

        bar = ctk.CTkFrame(card, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=14, pady=12)
        bar.grid_columnconfigure(2, weight=1)

        ctk.CTkButton(
            bar, text="选择种子文件", width=104, height=34, corner_radius=9,
            fg_color=c["surface_alt"], hover_color=c["track"], text_color=c["text"],
            font=(theme.FONT_FAMILY, 11), command=self._pick_torrent,
        ).grid(row=0, column=0)

        mode = "P2P 已启用" if self.host.settings.p2p_enabled else "P2P 已关闭"
        self.mode_label = ctk.CTkLabel(
            bar, text=f"· {mode} · {self.host.settings.max_connections} 线程并发",
            anchor="w", font=(theme.FONT_FAMILY, 10), text_color=c["text_faint"],
        )
        self.mode_label.grid(row=0, column=1, padx=(10, 0), sticky="w")

        self.start_btn = widgets.PillButton(
            bar, c, text="开始下载", width=108, command=self._start,
        )
        self.start_btn.grid(row=0, column=3, sticky="e")

    def _build_list(self) -> None:
        c = self.colors
        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 14))
        wrapper.grid_columnconfigure(0, weight=1)
        wrapper.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(wrapper, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top, text="任务列表", anchor="w",
            font=(theme.FONT_FAMILY, 12, "bold"), text_color=c["text"],
        ).grid(row=0, column=0, sticky="w")

        self.clear_btn = ctk.CTkButton(
            top, text="清除已完成", width=82, height=26, corner_radius=8,
            fg_color="transparent", hover_color=c["surface_alt"],
            text_color=c["text_muted"], border_width=1, border_color=c["border_strong"],
            font=(theme.FONT_FAMILY, 10), command=self._clear_finished,
        )
        self.clear_btn.grid(row=0, column=1, sticky="e")

        self.list_frame = ctk.CTkScrollableFrame(
            wrapper, fg_color="transparent",
            scrollbar_button_color=c["border"],
            scrollbar_button_hover_color=c["border_strong"],
        )
        self.list_frame.grid(row=1, column=0, sticky="nsew")
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.empty_hint = ctk.CTkLabel(
            self.list_frame,
            text="还没有任务。粘贴链接或磁力链后点击「开始下载」。",
            font=(theme.FONT_FAMILY, 11), text_color=c["text_faint"],
        )
        self.empty_hint.grid(row=0, column=0, pady=40)

    # ------------------------------------------------------------------
    def _add_placeholder(self) -> None:
        """输入提示由 label 承担，避免 placeholder 干扰取值。"""
        c = self.colors
        self.hint = ctk.CTkLabel(
            self.textbox.master,
            text="  在此粘贴：https://… 或 magnet:?xt=urn:btih:…（每行一个）",
            font=(theme.FONT_FAMILY, 10), text_color=c["text_faint"], anchor="w",
        )
        self.hint.place(in_=self.textbox, x=8, y=8)
        self.textbox.bind("<Key>", self._hide_hint, add="+")
        self.textbox.bind("<FocusIn>", self._hide_hint, add="+")

    def _hide_hint(self, _event=None) -> None:
        try:
            self.hint.place_forget()
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    def _pick_torrent(self) -> None:
        path = filedialog.askopenfilename(
            title="选择种子文件",
            filetypes=[("BitTorrent 种子", "*.torrent"), ("所有文件", "*.*")],
            parent=self,
        )
        if path:
            self._hide_hint()
            current = self.textbox.get("1.0", "end").strip()
            prefix = current + "\n" if current else ""
            self.textbox.delete("1.0", "end")
            self.textbox.insert("1.0", f"{prefix}{path}")

    def _start(self) -> None:
        raw = self.textbox.get("1.0", "end").strip()
        items = [line.strip() for line in raw.splitlines() if line.strip()]
        if not items:
            messagebox.showinfo("提示", "请先粘贴下载链接或磁力链。", parent=self)
            return
        if not self.host.ensure_engine():
            return

        target = self.host.settings.download_path
        added = 0
        for item in items:
            try:
                if item.lower().startswith("magnet:"):
                    gid = self.host.engine.add_magnet(item, target)
                    title = "磁力任务"
                    kind = "P2P"
                elif item.lower().endswith(".torrent") and Path(item).exists():
                    gid = self.host.engine.add_torrent(item, target)
                    title = Path(item).name
                    kind = "P2P"
                else:
                    name = item.split("?")[0].rstrip("/").split("/")[-1] or "download.bin"
                    gid = self.host.engine.add_uri(item, name, target)
                    title = name
                    kind = "直链"
                self._add_task(gid, title, kind)
                added += 1
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror("添加失败", f"{item[:60]}…\n\n{exc}", parent=self)

        if added:
            self.textbox.delete("1.0", "end")
            self.empty_hint.grid_remove()

    def _add_task(self, gid: str, title: str, kind: str) -> None:
        row = widgets.TaskRow(self.list_frame, self.colors, title, kind)
        count = len(self.tasks)
        row.grid(row=count, column=0, sticky="ew", pady=(0, 8), padx=2)
        self.tasks[gid] = {
            "row": row, "gid": gid, "title": title, "kind": kind,
            "total": 0, "done": 0, "speed": 0.0, "state": "active",
            "started": time.time(),
        }

    # ------------------------------------------------------------------
    def sync_statuses(self) -> None:
        """由主窗口的轮询循环调用，刷新所有任务行。"""
        if not self.tasks:
            return
        now = time.time()
        if now - self._last_sync < 0.5:
            return
        self._last_sync = now

        try:
            statuses = {}
            for item in (self.host.engine.tell_active()
                         + self.host.engine.tell_waiting()
                         + self.host.engine.tell_stopped()):
                gid = item.get("gid")
                if gid:
                    statuses[gid] = item
        except Exception:  # noqa: BLE001
            return

        for gid, task in list(self.tasks.items()):
            st = statuses.get(gid) or self.host.engine.tell(gid)
            row: widgets.TaskRow = task["row"]
            if not st:
                continue
            followed = st.get("followedBy")
            if followed:
                new_gid = followed[0]
                self.tasks[new_gid] = task
                task["gid"] = new_gid
                self.tasks.pop(gid, None)
                continue

            total = int(st.get("totalLength") or 0)
            done = int(st.get("completedLength") or 0)
            speed = float(st.get("downloadSpeed") or 0)
            status = st.get("status", "")
            task.update(total=total, done=done, speed=speed, state=status)

            frac = (done / total) if total else 0.0
            seeders = st.get("numSeeders")
            conns = st.get("connections")

            if status == "error":
                row.update_state(0, st.get("errorMessage") or "下载失败", error=True)
                continue
            if status == "complete":
                name = Path((st.get("files") or [{}])[0].get("path", "")).name
                row.update_state(1.0, f"已完成 · {human_size(total or done)} · {name}", done=True)
                continue
            if status == "paused":
                row.update_state(frac, f"已暂停 · {human_size(done)} / {human_size(total)}")
                continue

            info = f"{human_size(done)} / {human_size(total) if total else '—'} · {human_speed(speed)}"
            if seeders and int(seeders) > 0:
                info += f" · {seeders} 节点"
            elif conns and int(conns) > 1:
                info += f" · {conns} 线程"
            row.update_state(frac, info)

    def _clear_finished(self) -> None:
        for gid, task in list(self.tasks.items()):
            if task["state"] in ("complete", "error"):
                try:
                    task["row"].destroy()
                except Exception:  # noqa: BLE001
                    pass
                self.tasks.pop(gid, None)
        for idx, task in enumerate(self.tasks.values()):
            try:
                task["row"].grid(row=idx, column=0, sticky="ew", pady=(0, 8), padx=2)
            except Exception:  # noqa: BLE001
                pass
        if not self.tasks:
            self.empty_hint.grid()
