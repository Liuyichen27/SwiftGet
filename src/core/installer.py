"""静默安装执行器。

安装动作需要管理员权限，但程序本身以普通权限运行，只在真正安装时通过
``ShellExecuteW(verb="runas")`` 触发一次 UAC，避免每次启动都弹窗。
"""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import tempfile
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000

SEE_MASK_NOCLOSEPROCESS = 0x00000040
SEE_MASK_NOASYNC = 0x00000100
SEE_MASK_FLAG_NO_UI = 0x00000400
SEE_MASK_NO_CONSOLE = 0x00008000
SW_HIDE = 0
SW_SHOWNORMAL = 1
ERROR_CANCELLED = 1223
INFINITE = 0xFFFFFFFF


class SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", ctypes.c_ulong),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIcon", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


class ElevationCancelled(RuntimeError):
    """用户在 UAC 弹窗中点了取消。"""


@dataclass
class InstallResult:
    ok: bool
    code: int
    message: str


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:  # noqa: BLE001
        return False


def _run_shellexec(
    exe: str, params: str, cwd: str | None, elevate: bool, show: bool
) -> int:
    sei = SHELLEXECUTEINFOW()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NOASYNC | SEE_MASK_NO_CONSOLE
    sei.lpVerb = "runas" if elevate else "open"
    sei.lpFile = exe
    sei.lpParameters = params or None
    sei.lpDirectory = cwd
    sei.nShow = SW_SHOWNORMAL if show else SW_HIDE

    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei)):
        err = ctypes.get_last_error()
        if err == ERROR_CANCELLED:
            raise ElevationCancelled("已取消管理员授权")
        raise OSError(err, f"无法启动安装程序（错误码 {err}）")

    handle = sei.hProcess
    if not handle:
        return 0
    try:
        ctypes.windll.kernel32.WaitForSingleObject(handle, INFINITE)
        code = wintypes.DWORD()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        return int(code.value)
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def run_silent(
    command: list[str], workdir: str | None = None, silent: bool = True
) -> InstallResult:
    """执行安装命令，自动提权。

    ``silent=True`` 传静默参数并隐藏窗口；``silent=False`` 用于安装器本身
    不支持静默的情况——正常显示安装向导，由用户点几下完成。
    """
    if not command:
        return InstallResult(False, -1, "空的安装命令")

    exe, *args = command
    exe_path = Path(exe)
    resolved = exe
    if exe_path.exists():
        resolved = str(exe_path.resolve())
    else:
        found = shutil.which(exe)
        if found:
            resolved = found

    # 统一用引号包裹带空格的路径
    params = subprocess.list2cmdline(args) if silent else ""
    cwd = workdir or str(Path(resolved).parent)

    try:
        code = _run_shellexec(resolved, params, cwd, elevate=True, show=not silent)
    except ElevationCancelled as exc:
        return InstallResult(False, ERROR_CANCELLED, str(exc))
    except OSError as exc:
        return InstallResult(False, -1, str(exc))

    if code == 0:
        return InstallResult(True, 0, "安装完成")
    if code == 3010:
        return InstallResult(True, code, "安装完成，需要重启系统")
    if code == 1641:
        return InstallResult(True, code, "安装完成，系统正在重启")
    return InstallResult(False, code, f"安装程序返回错误码 {code}")


def launch_after_install(hint_path: str | None = None) -> None:
    """安装完成后静默拉起软件（尽力而为，失败忽略）。"""
    candidates: list[str] = []
    if hint_path:
        candidates.append(hint_path)

    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    la = os.environ.get("LOCALAPPDATA", "")
    candidates += [
        rf"{pf}\Google\Chrome\Application\chrome.exe",
        rf"{pf86}\Google\Chrome\Application\chrome.exe",
        rf"{la}\Google\Chrome\Application\chrome.exe",
        rf"{pf}\Tencent\WeChat\WeChat.exe",
        rf"{pf86}\Tencent\WeChat\WeChat.exe",
        rf"{pf}\7-Zip\7zFM.exe",
        rf"{pf}\Everything\Everything.exe",
        rf"{pf}\Bandizip\Bandizip.exe",
        rf"{pf}\Notepad++\notepad++.exe",
        rf"{pf}\VideoLAN\VLC\vlc.exe",
        rf"{pf86}\VideoLAN\VLC\vlc.exe",
    ]
    for path in candidates:
        if path and Path(path).exists():
            try:
                # 用 ShellExecute 语义启动（等同用户双击）。老代码给 GUI 程序
                # 传 CREATE_NO_WINDOW，某些程序会因为没有控制台/窗口站不对
                # 而启动失败或者起来是空窗口；startfile 不吃这个参数，
                # 也不会让子进程跟着本进程一起退出。
                os.startfile(path)  # noqa: S606
                return
            except OSError:
                continue


def verify_installer(path: str | Path, kind: str = "installer") -> tuple[bool, str]:
    """下载件基础校验：存在、大小合理、文件头正常。

    ``kind`` 决定按什么标准判断——安装包看 PE/MSI 头，源码包看 ZIP 头，
    绿色版单文件仍然看 PE 头（它本身就是个 exe）。
    """
    p = Path(path)
    if not p.exists():
        return False, "文件不存在"
    size = p.stat().st_size
    if kind == "archive":
        # 源码包本来就小，几十 KB 是正常的，门槛放低
        if size < 2 * 1024:
            return False, f"文件过小（{size} 字节），可能下载不完整"
    elif size < 100 * 1024:
        return False, f"文件过小（{size} 字节），可能下载不完整"
    try:
        with p.open("rb") as fh:
            head = fh.read(8)
    except OSError as exc:
        return False, f"无法读取文件：{exc}"

    if kind == "archive":
        if head[:2] != b"PK":
            return False, "不是有效的 ZIP 压缩包"
        return True, "OK"
    if p.suffix.lower() == ".msi":
        if head[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            return False, "MSI 文件头异常，可能已损坏"
        return True, "OK"
    if head[:2] != b"MZ":
        return False, "不是有效的 Windows 可执行文件"
    return True, "OK"


def safe_temp_dir(prefix: str = "swiftget_") -> Path:
    return Path(tempfile.mkdtemp(prefix=prefix))
