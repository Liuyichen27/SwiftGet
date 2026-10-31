"""Linux 上的「安装」动作。

Windows 那套是 exe + 静默参数（msiexec /S /qn），到 Linux 完全不适用。
这里按包类型分三条路：

* ``.deb``      —— 用 apt 装，走 pkexec（桌面环境弹密码框）或免密 sudo
* ``.tar.xz``   —— 解压到 ``~/.local/opt/<id>``，在 ``~/.local/bin`` 建启动软链
* ``.AppImage`` —— chmod +x 后挪到 ``~/.local/bin``

刻意不做的事：不碰 ``/usr/local``、不动系统目录、不静默装系统包。
用户要装的东西都落在自己的家目录下，卸载就是删文件夹。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
from pathlib import Path

from . import plat
from .installer import InstallResult


def _run(cmd: list[str], timeout: int = 900) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, f"找不到命令：{cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "命令超时"
    except Exception as e:  # noqa: BLE001
        return -1, f"{type(e).__name__}: {e}"
    out = (p.stdout or "") + "\n" + (p.stderr or "")
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    return p.returncode, (lines[-1] if lines else "")


def install_deb(path: Path) -> InstallResult:
    """用 apt 装本地 deb。apt 会把依赖一起解决，比 dpkg -i 省心。"""
    if not plat.has("apt") and not plat.has("apt-get"):
        return InstallResult(
            False, -1,
            "这个发行版没有 apt。Debian/Ubuntu 才能自动装 deb，"
            "其它发行版请手动解压 deb 或用系统自带的包管理器。",
        )

    base = ["install", "-y", str(path)]
    attempts: list[tuple[list[str], str]] = []
    if plat.has("pkexec"):
        attempts.append((["pkexec", "apt"], "pkexec"))
    if plat.has("sudo"):
        attempts.append((["sudo", "-n", "apt"], "sudo -n"))   # -n：没配免密就直接失败，不卡在终端

    if not attempts:
        return InstallResult(False, -1, f"没有 pkexec / sudo，请手动：sudo apt install {path}")

    last = ""
    for prefix, label in attempts:
        code, tail = _run(prefix + base)
        if code == 0:
            return InstallResult(True, 0, "安装完成")
        # 126/127 或明确说没授权，说明这条提权路走不通，换下一条
        low = tail.lower()
        if code in (126, 127) or "not authorized" in low or "no password" in low:
            last = f"{label} 未获授权"
            continue
        return InstallResult(False, code, tail or f"apt 返回 {code}")

    return InstallResult(
        False, -1,
        f"{last or '提权失败'}。请手动执行：sudo apt install {path}",
    )


def _safe_extract(tar_path: Path, dest: Path) -> str | None:
    """解压，返回错误信息（None 表示成功）。顺手挡掉目录穿越。"""
    try:
        with tarfile.open(tar_path) as tf:
            for m in tf.getmembers():
                p = Path(m.name)
                if p.is_absolute() or ".." in p.parts:
                    return "压缩包里有越界路径，已中止（可能不是官方包）"
                if m.issym() or m.islnk():
                    target = Path(m.linkname)
                    if target.is_absolute() or ".." in target.parts:
                        return "压缩包里有可疑软链，已中止"
            # Python 3.12+ 有 filter 参数，老版本忽略
            try:
                tf.extractall(dest, filter="data")
            except TypeError:
                tf.extractall(dest)
    except Exception as e:  # noqa: BLE001
        return f"解压失败：{type(e).__name__}: {e}"
    return None


def _pick_executable(base: Path, app_id: str) -> Path | None:
    """在解压出来的目录里找那个该跑的程序。"""
    # 1) 同名文件最靠谱：firefox/firefox、firefox/firefox-bin
    for name in (app_id, f"{app_id}-bin"):
        direct = base / name
        if direct.is_file() and os.access(direct, os.X_OK):
            return direct
    # 2) 顶层任意可执行文件
    for p in sorted(base.iterdir()):
        if p.is_file() and os.access(p, os.X_OK):
            return p
    # 3) 再往下找一层（很多包是 foo/bin/foo）
    for p in sorted(base.rglob("*")):
        if p.is_file() and p.name in (app_id, f"{app_id}-bin") and os.access(p, os.X_OK):
            return p
    return None


def extract_tarball(path: Path, app_id: str, app_name: str) -> InstallResult:
    """解压到 ~/.local/opt/<id>，并在 ~/.local/bin 建一个同名启动软链。"""
    root = plat.data_home() / "opt"
    dest = root / app_id
    try:
        root.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return InstallResult(False, -1, f"创建目录失败：{e}")

    err = _safe_extract(path, dest)
    if err:
        return InstallResult(False, -1, err)

    # 顶层只有一个目录时往里退一层（tar 通常包了一层 foo-x.y.z/）
    items = list(dest.iterdir())
    base = items[0] if len(items) == 1 and items[0].is_dir() else dest

    exe = _pick_executable(base, app_id)
    if exe is None:
        return InstallResult(
            True, 0,
            f"已解压到 {dest}（没找到可执行文件，包里的启动方式可能不叫 {app_id}）",
        )

    bin_dir = Path.home() / ".local" / "bin"
    link = bin_dir / app_id
    try:
        bin_dir.mkdir(parents=True, exist_ok=True)
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(exe)
    except OSError as e:
        return InstallResult(True, 0, f"已解压到 {dest}，但建启动软链失败：{e}")

    hint = f"已装到 {dest}，命令：{app_id}"
    if str(bin_dir) not in os.environ.get("PATH", ""):
        hint += f"\n（{bin_dir} 不在 PATH 里，把 export PATH=\"$HOME/.local/bin:$PATH\" 加进 ~/.bashrc）"
    return InstallResult(True, 0, hint)


def install_appimage(path: Path, app_id: str) -> InstallResult:
    """AppImage 只需要可执行位，然后挪到 ~/.local/bin。"""
    bin_dir = Path.home() / ".local" / "bin"
    try:
        bin_dir.mkdir(parents=True, exist_ok=True)
        target = bin_dir / path.name
        shutil.copy2(path, target)
        target.chmod(0o755)
    except OSError as e:
        return InstallResult(False, -1, f"拷贝失败：{e}")
    return InstallResult(True, 0, f"已装到 {target}，命令行敲 {target.name} 就能跑")


def install(app, path: Path) -> InstallResult:
    """按扩展名分派。app 是 AppEntry（只用 id / name / file_ext）。"""
    ext = (path.suffix or "").lower()
    full = path.name.lower()
    if full.endswith(".appimage") or ext == ".appimage":
        return install_appimage(path, app.id)
    if ext == ".deb":
        return install_deb(path)
    if full.endswith((".tar.xz", ".tar.gz", ".tar.bz2", ".tgz")):
        return extract_tarball(path, app.id, app.name)
    return InstallResult(False, -1, f"不认识这种包：{path.name}")
