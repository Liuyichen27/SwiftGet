"""aria2 下载引擎封装。

aria2 同时提供两种加速能力：

* **多线程分片（HTTP/HTTPS）**：把单文件切成 N 段并发下载，服务器支持 Range 时
  可显著提升单链路速度。
* **BitTorrent / P2P**：磁力链、种子文件，通过 DHT + Peer Exchange 从多个节点
  并行拉取，节点越多越快。

引擎以 aria2c 子进程 + JSON-RPC 方式工作：Windows 用内置的 aria2c.exe，
Linux 用系统装的 aria2（apt install aria2），两边参数完全一致。
"""
from __future__ import annotations

import json
import os
import secrets
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from . import plat
from .paths import APP_VERSION, ensure_aria2

CREATE_NO_WINDOW = plat.CREATE_NO_WINDOW
DETACHED = 0x00000008

# 报给下载源的 UA：Linux 版就别装成 Windows 了，个别源会按 UA 给不同文件
_UA_OS = ("Windows NT 10.0; Win64; x64" if plat.IS_WIN
          else "X11; Linux x86_64" if plat.IS_LINUX else "Macintosh; Intel Mac OS X 10_15_7")
UA = f"Mozilla/5.0 ({_UA_OS}) SwiftGet/{APP_VERSION}"


class Aria2Error(RuntimeError):
    pass


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@dataclass
class Aria2Options:
    max_connections: int = 16
    split: int = 16
    p2p_enabled: bool = True
    bt_port: int = 6881


class Aria2Engine:
    """aria2c 生命周期与 RPC 客户端。"""

    def __init__(self, options: Aria2Options | None = None) -> None:
        self.options = options or Aria2Options()
        self.port = _free_port()
        self.secret = secrets.token_urlsafe(16)
        self.endpoint = f"http://127.0.0.1:{self.port}/jsonrpc"
        self.proc: subprocess.Popen[bytes] | None = None
        self.session = requests.Session()
        self.session.trust_env = False  # 避免系统代理干扰本机 RPC
        self._lock = threading.Lock()
        self._log_path = plat.data_home() / "SwiftGet" / "aria2.log" if not plat.IS_WIN \
            else Path(os.environ.get("TEMP", ".")) / "swiftget_aria2.log"
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass

    # -- 生命周期 ---------------------------------------------------------
    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, timeout: float = 12.0) -> None:
        with self._lock:
            if self.running:
                return
            exe = ensure_aria2()
            if not exe.exists() or (not plat.IS_WIN and not plat.has(exe.name)):
                if plat.IS_WIN:
                    raise Aria2Error("缺少 aria2c 内核文件，请重新安装程序。")
                raise Aria2Error(
                    "没找到 aria2c 下载内核。装上就行：\n"
                    "  Debian / Ubuntu:  sudo apt install aria2\n"
                    "  Fedora:           sudo dnf install aria2\n"
                    "  Arch:             sudo pacman -S aria2"
                )

            opts = self.options
            args = [
                str(exe),
                "--enable-rpc=true",
                "--rpc-listen-all=false",
                f"--rpc-listen-port={self.port}",
                f"--rpc-secret={self.secret}",
                "--rpc-allow-origin-all=false",
                # 分片加速
                f"--max-connection-per-server={max(1, opts.max_connections)}",
                f"--split={max(1, opts.split)}",
                "--min-split-size=1M",
                "--max-concurrent-downloads=4",
                "--file-allocation=none",
                "--continue=true",
                "--auto-file-renaming=false",
                "--allow-overwrite=true",
                "--remote-time=true",
                "--content-disposition-default-utf8=true",
                # 网络
                "--connect-timeout=20",
                "--timeout=30",
                "--max-tries=5",
                "--retry-wait=3",
                # 禁用 IPv6：部分网络环境下 IPv6 路由不可达会让任务直接失败，
                # 强制走 IPv4 更稳（绝大多数下载源都支持 IPv4）
                "--disable-ipv6=true",
                "--async-dns=true",
                f"--user-agent={UA}",
                # 日志静默
                "--console-log-level=warn",
                "--summary-interval=0",
                "--download-result=hide",
                "--quiet=true",
            ]
            if opts.p2p_enabled:
                args += [
                    "--enable-dht=true",
                    "--dht-listen-port=6881-6999",
                    "--bt-enable-lpd=true",
                    "--enable-peer-exchange=true",
                    "--bt-max-peers=80",
                    "--bt-save-metadata=true",
                    "--seed-time=0",
                    "--follow-torrent=mem",
                    "--listen-port=6881-6999",
                ]
            else:
                args += ["--enable-dht=false", "--bt-enable-lpd=false"]

            log = open(self._log_path, "ab")
            creationflags = plat.creation_flags()
            self.proc = subprocess.Popen(
                args, stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                creationflags=creationflags,
            )

        deadline = time.time() + timeout
        last_err: Exception | None = None
        while time.time() < deadline:
            try:
                self.call("getVersion")
                return
            except Exception as exc:  # noqa: BLE001
                last_err = exc
                time.sleep(0.25)
        self.stop()
        raise Aria2Error(f"下载引擎启动失败：{last_err}")

    def stop(self) -> None:
        with self._lock:
            proc = self.proc
            self.proc = None
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        except OSError:
            pass

    def restart(self, options: Aria2Options | None = None) -> None:
        self.stop()
        if options is not None:
            self.options = options
        self.port = _free_port()
        self.endpoint = f"http://127.0.0.1:{self.port}/jsonrpc"
        self.session = requests.Session()
        self.session.trust_env = False
        self.start()

    # -- RPC --------------------------------------------------------------
    def call(self, method: str, params: list[Any] | None = None, timeout: float = 10.0) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "id": "swiftget",
            "method": f"aria2.{method}",
            "params": [f"token:{self.secret}", *(params or [])],
        }
        r = self.session.post(self.endpoint, json=payload, timeout=timeout)
        data = r.json()
        if "error" in data:
            raise Aria2Error(data["error"].get("message", "未知错误"))
        return data.get("result")

    def version(self) -> str:
        return self.call("getVersion").get("version", "?")

    # -- 添加任务 ---------------------------------------------------------
    def add_uri(
        self,
        url: str,
        out: str,
        directory: str | Path,
        headers: list[str] | None = None,
    ) -> str:
        opts: dict[str, Any] = {
            "dir": str(directory),
            "out": out,
            "split": str(max(1, self.options.split)),
            "max-connection-per-server": str(max(1, self.options.max_connections)),
            "min-split-size": "1M",
            "continue": "true",
        }
        if headers:
            opts["header"] = headers
        return self.call("addUri", [[url], opts])

    def add_magnet(self, uri: str, directory: str | Path) -> str:
        return self.call(
            "addUri",
            [[uri], {"dir": str(directory), "seed-time": "0", "bt-save-metadata": "true"}],
        )

    def add_torrent(self, torrent_path: str | Path, directory: str | Path) -> str:
        import base64

        raw = Path(torrent_path).read_bytes()
        b64 = base64.b64encode(raw).decode()
        return self.call("addTorrent", [b64, [], {"dir": str(directory), "seed-time": "0"}])

    # -- 状态 -------------------------------------------------------------
    _STATUS_KEYS = [
        "gid", "status", "totalLength", "completedLength", "downloadSpeed",
        "uploadSpeed", "connections", "numSeeders", "seeder", "errorMessage",
        "files", "dir", "followedBy", "infoHash",
    ]

    def tell(self, gid: str) -> dict[str, Any]:
        try:
            return self.call("tellStatus", [gid, self._STATUS_KEYS], timeout=5)
        except Exception:  # noqa: BLE001
            return {}

    def tell_active(self) -> list[dict[str, Any]]:
        try:
            return self.call("tellActive", [self._STATUS_KEYS], timeout=5) or []
        except Exception:  # noqa: BLE001
            return []

    def tell_waiting(self, offset: int = 0, total: int = 100) -> list[dict[str, Any]]:
        try:
            return self.call("tellWaiting", [offset, total, self._STATUS_KEYS], timeout=5) or []
        except Exception:  # noqa: BLE001
            return []

    def tell_stopped(self, offset: int = 0, total: int = 100) -> list[dict[str, Any]]:
        try:
            return self.call("tellStopped", [offset, total, self._STATUS_KEYS], timeout=5) or []
        except Exception:  # noqa: BLE001
            return []

    def all_statuses(self) -> list[dict[str, Any]]:
        return self.tell_active() + self.tell_waiting() + self.tell_stopped()

    def global_stat(self) -> dict[str, str]:
        try:
            return self.call("getGlobalStat", timeout=5) or {}
        except Exception:  # noqa: BLE001
            return {}

    # -- 控制 -------------------------------------------------------------
    def pause(self, gid: str) -> Any:
        return self.call("pause", [gid])

    def unpause(self, gid: str) -> Any:
        return self.call("unpause", [gid])

    def remove(self, gid: str) -> Any:
        try:
            self.call("forceRemove", [gid])
        except Aria2Error:
            self.call("remove", [gid])
        return None

    def purge_download_result(self) -> None:
        try:
            self.call("purgeDownloadResult")
        except Exception:  # noqa: BLE001
            pass

    def set_global_options(self, opts: dict[str, str]) -> Any:
        return self.call("changeGlobalOption", [opts])

    def tail_log(self, lines: int = 40) -> str:
        try:
            content = self._log_path.read_text(encoding="utf-8", errors="replace")
            return "\n".join(content.splitlines()[-lines:])
        except OSError:
            return ""


def human_size(num: float) -> str:
    if num <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    value = float(num)
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024
        idx += 1
    if idx == 0:
        return f"{int(value)} {units[idx]}"
    return f"{value:.1f} {units[idx]}"


def human_speed(bps: float) -> str:
    if bps <= 0:
        return "—"
    return f"{human_size(bps)}/s"


def human_eta(seconds: float) -> str:
    if seconds <= 0 or seconds != seconds or seconds > 86400 * 7:
        return "—"
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds} 秒"
    if seconds < 3600:
        return f"{seconds // 60} 分 {seconds % 60} 秒"
    return f"{seconds // 3600} 时 {(seconds % 3600) // 60} 分"
