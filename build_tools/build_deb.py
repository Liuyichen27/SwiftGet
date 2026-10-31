"""把 SwiftGet 打成 Debian / Ubuntu 可安装的 .deb。

为什么是「源码 + 系统 python3」而不是 PyInstaller 单文件
------------------------------------------------------
PyInstaller 不能交叉编译：Windows 上跑不出一份 Linux 可执行文件，
这台机器也没有可用的 Linux 环境（WSL 只有壳，没装发行版）。所以这里做
`Architecture: all` 的源码包：deb 里放 Python 源码 + 界面资源 + **vendor 的
customtkinter / darkdetect**，运行时用系统的 python3。

vendor 是有意为之：`customtkinter` 没有被 Debian/Ubuntu 打包，如果写成
Depends 就永远装不上；又不能叫用户在 postinst 里 pip install（离线机器直接
卡住）。它俩是纯 Python，塞进包里最省事。`requests / Pillow / packaging /
tkinter` 各大发行版都有，写成 Depends 让 apt 去装。

产物
----
    dist/swiftget_<版本>_all.deb

顺带做完整性自检：重新把 deb 读一遍，校验 ar 结构、control 字段、
data.tar.gz 里的文件清单和权限。

用法
----
    python build_tools/build_deb.py
"""

from __future__ import annotations

import gzip
import hashlib
import io
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"

PKG = "swiftget"
APP_DIR = "/usr/lib/swiftget"
DESKTOP = "swiftget.desktop"
MAINTAINER = "Liuyichen27 <Liuyichen27@users.noreply.github.com>"
HOMEPAGE = "https://github.com/Liuyichen27/SwiftGet"

# aria2 是下载内核，缺了这软件就没法用，必须是硬依赖。
# python3-tk 提供 tkinter（customtkinter 的底座），requests 查清单/预检下载源，
# python3-pil 给 CTkImage 用，python3-packaging 是 customtkinter 的依赖。
DEPENDS = (
    "python3 (>= 3.9), "
    "python3-tk, "
    "python3-requests, "
    "python3-pil, "
    "python3-packaging, "
    "aria2"
)
# 中文字体必需（不然整屏方块）；xdg-utils 用于「打开所在文件夹」；
# pkexec 是装 deb 时的图形授权弹窗
RECOMMENDS = "fonts-noto-cjk, xdg-utils, pkexec | policykit-1"

ICON_SIZES = (512, 256, 128, 64, 48, 32)

# 打进去的纯 Python 依赖（Debian 没有对应包）
VENDOR = ("customtkinter", "darkdetect")

DESKTOP_ENTRY = """[Desktop Entry]
Type=Application
Name=SwiftGet
Name[zh_CN]=极速下载器
GenericName=Download Manager
GenericName[zh_CN]=下载器
Comment=Multi-source downloader: software, links, BT. aria2 powered.
Comment[zh_CN]=多源极速下载器：常用软件、磁力/直链，基于 aria2
Exec=swiftget %U
Icon=swiftget
Terminal=false
Categories=Network;FileTransfer;Utility;
Keywords=download;aria2;bt;magnet;http;
Keywords[zh_CN]=下载;加速;磁力;种子;
StartupWMClass=SwiftGet
StartupNotify=true
"""

LAUNCHER = """#!/bin/sh
# SwiftGet 启动器：真正的内容在 /usr/lib/swiftget
set -e
APP_DIR=/usr/lib/swiftget

if [ ! -f "$APP_DIR/main.py" ]; then
    echo "找不到 $APP_DIR/main.py，安装可能不完整，请重新安装：" >&2
    echo "  sudo apt install --reinstall ./swiftget_*.deb" >&2
    exit 1
fi

if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "SwiftGet 需要 tkinter（python3-tk），现在没装：" >&2
    echo "  sudo apt install python3-tk" >&2
    exit 1
fi

if ! command -v aria2c >/dev/null 2>&1; then
    echo "提示：没找到 aria2c 下载内核，装一下更快也更稳：" >&2
    echo "  sudo apt install aria2" >&2
fi

exec python3 "$APP_DIR/main.py" "$@"
"""

POSTINST = """#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t /usr/share/icons/hicolor || true
fi
exit 0
"""

POSTRM = """#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi
# 用户数据（~/.config/SwiftGet、下载目录）不动，卸载不该带走配置
exit 0
"""


def read_version() -> str:
    text = (ROOT / "src" / "core" / "paths.py").read_text(encoding="utf-8")
    m = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', text, re.M)
    if not m:
        raise SystemExit("src/core/paths.py 里找不到 APP_VERSION")
    return m.group(1)


def control_text(ver: str, installed_kb: int) -> str:
    return f"""Package: {PKG}
Version: {ver}
Section: net
Priority: optional
Architecture: all
Depends: {DEPENDS}
Recommends: {RECOMMENDS}
Installed-Size: {installed_kb}
Maintainer: {MAINTAINER}
Homepage: {HOMEPAGE}
Description: SwiftGet - multi-source downloader powered by aria2
 A desktop downloader for Debian / Ubuntu: a curated app list with mirror
 fallback, plain URL and magnet/BT downloads, multi-connection acceleration
 via aria2, and one-click install of .deb / tarball / AppImage packages.
 .
 SwiftGet：极速下载器。常用软件清单（多源自动挑选可用镜像）、直链与
 磁力/种子下载、aria2 多线程加速，下完能直接装 deb / 解压 tar.xz /
 收好 AppImage。
"""


# ----------------------------------------------------------------------
# tar / ar 构造
# ----------------------------------------------------------------------
def _tar_bytes(entries: list[tuple[str, Path | None, bytes | None, int]]) -> bytes:
    """entries: (归档内路径, 源文件, 内存内容, 模式)。

    所有条目属主都写成 root:root，时间戳用构建时间 —— 这是 Debian 包的规矩。
    """
    buf = io.BytesIO()
    now = int(time.time())
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.GNU_FORMAT) as tf:
        tf.encoding = "utf-8"
        for name, src, data, mode in entries:
            info = tarfile.TarInfo(name)
            info.mtime = now
            info.uid = 0
            info.gid = 0
            info.uname = "root"
            info.gname = "root"
            info.mode = mode
            if name.endswith("/"):
                # 目录必须是 DIRTYPE(b'5')。写成普通文件的话 dpkg 解包时
                # 会去「创建一个叫 usr 的空文件」，随后的 usr/bin 就全失败
                info.type = tarfile.DIRTYPE
                info.size = 0
                tf.addfile(info)
                continue
            if data is None and src is not None:
                data = src.read_bytes()
            payload = data or b""
            info.size = len(payload)
            tf.addfile(info, io.BytesIO(payload))

    raw = buf.getvalue()
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", compresslevel=9, mtime=now) as gz:
        gz.write(raw)
    return out.getvalue()


def _ar_member(name: str, data: bytes, mtime: int) -> bytes:
    # ar 头固定 60 字节：名字 16 / 时间 12 / 属主 6 / 属组 6 / 权限 8 / 大小 10 / 魔数 2
    header = (
        f"{name:<16}{mtime:<12}{0:<6}{0:<6}{'100644':<8}{len(data):<10}`\n"
    ).encode("ascii")
    body = data if len(data) % 2 == 0 else data + b"\n"
    return header + body


def build_ar(*members: tuple[str, bytes]) -> bytes:
    now = int(time.time())
    out = b"!<arch>\n"
    for name, data in members:
        out += _ar_member(name, data, now)
    return out


# ----------------------------------------------------------------------
# 文件树
# ----------------------------------------------------------------------
def _vendor_dir() -> Path:
    """找到要打包的第三方纯 Python 包所在目录。"""
    try:
        import customtkinter

        return Path(customtkinter.__file__).resolve().parent.parent
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"找不到 customtkinter（{exc}）。先装一下：\n"
            f"  {sys.executable} -m pip install customtkinter darkdetect"
        ) from exc


def collect_entries(ver: str, stage: Path) -> tuple[list, list[str]]:
    """返回 (tar 条目表, md5sums 行)。"""
    entries: list[tuple[str, Path | None, bytes | None, int]] = []
    md5: list[str] = []
    seen: set[str] = set()

    def add(path: str, src: Path | None = None, data: bytes | None = None,
            mode: int = 0o644) -> None:
        payload = data if data is not None else (src.read_bytes() if src else b"")
        entries.append((path, None, payload, mode))
        if mode & 0o111 == 0:      # 只对普通文件算 md5
            md5.append(f"{hashlib.md5(payload).hexdigest()}  {path[2:]}")
        parent = str(Path(path).parent).replace("\\", "/")
        while parent not in (".", "/", ""):
            d = f"./{parent.lstrip('./')}/" if not parent.startswith("./") else f"{parent}/"
            if d not in seen:
                seen.add(d)
                entries.insert(len(entries) - 1, (d, None, b"", 0o755))
            parent = str(Path(parent).parent).replace("\\", "/")

    # 1) 程序本体：src 下摊平到 /usr/lib/swiftget
    for f in sorted((ROOT / "src").rglob("*")):
        if not f.is_file():
            continue
        if "__pycache__" in f.parts or f.suffix in (".pyc", ".pyo"):
            continue
        rel = f.relative_to(ROOT / "src").as_posix()
        add(f".{APP_DIR}/{rel}", f)

    # 2) vendor：纯 Python 依赖，Debian 仓库里没有
    site = _vendor_dir()
    for pkg in VENDOR:
        base = site / pkg
        if not base.is_dir():
            raise SystemExit(f"缺少 vendor 包：{base}")
        for f in sorted(base.rglob("*")):
            if not f.is_file() or "__pycache__" in f.parts or f.suffix in (".pyc", ".pyo"):
                continue
            add(f".{APP_DIR}/vendor/{f.relative_to(site).as_posix()}", f)

    # 3) 界面图标
    for name in ("app.png", "app.ico"):
        f = ROOT / "assets" / name
        if f.exists():
            add(f".{APP_DIR}/assets/{name}", f)

    # 4) 文档
    for name in ("README.md", "LICENSE"):
        f = ROOT / name
        if f.exists():
            add(f".{APP_DIR}/{name}", f)

    # 5) 启动器
    add("./usr/bin/swiftget", None, LAUNCHER.encode("utf-8"), 0o755)

    # 6) 桌面入口
    add(f"./usr/share/applications/{DESKTOP}", None, DESKTOP_ENTRY.encode("utf-8"))

    # 7) 图标（多尺寸）
    src_icon = ROOT / "assets" / "app.png"
    for size in ICON_SIZES:
        out = stage / f"icon-{size}.png"
        try:
            from PIL import Image

            with Image.open(src_icon) as im:
                im.convert("RGBA").resize((size, size), Image.LANCZOS).save(out)
        except Exception:
            if size == 256:
                shutil.copy2(src_icon, out)
            else:
                continue
        if out.exists():
            add(f"./usr/share/icons/hicolor/{size}x{size}/apps/swiftget.png", out)

    # 8) 版权与 changelog
    add(f"./usr/share/doc/{PKG}/copyright", None,
        f"SwiftGet {ver}\nMIT License\n{HOMEPAGE}\n".encode("utf-8"))
    add(f"./usr/share/doc/{PKG}/changelog.gz", None,
        gzip.compress(
            f"swiftget ({ver}) unstable; urgency=medium\n\n"
            f"  * Release {ver}: Linux (deb) edition.\n\n"
            f" -- {MAINTAINER}  {time.strftime('%a, %d %b %Y %H:%M:%S +0800')}\n"
            .encode("utf-8"), mtime=0))

    uniq: dict[str, tuple] = {}
    for e in entries:
        uniq[e[0]] = e
    ordered = sorted(uniq.values(), key=lambda e: (e[0].count("/"), e[0]))
    return ordered, md5


def build() -> int:
    ver = read_version()
    stage = Path(tempfile.mkdtemp(prefix="sg_deb_"))
    try:
        # shell 脚本先过一遍 sh -n：少写个 fi 这类低级错，装到别人机器上
        # 就是「装完点不开」，在这里拦住最划算
        sh = shutil.which("sh")
        if sh:
            for label, src in (("启动器", LAUNCHER), ("postinst", POSTINST),
                               ("postrm", POSTRM)):
                f = stage / f"syntax_{label}.sh"
                f.write_text(src, encoding="utf-8", newline="\n")
                r = subprocess.run([sh, "-n", str(f)], capture_output=True, text=True)
                if r.returncode != 0:
                    raise SystemExit(f"{label} 语法错误：{r.stderr.strip()}")
            print(f"[ok] 启动器 / postinst / postrm 语法通过（{Path(sh).name} -n）")

        data_entries, md5_lines = collect_entries(ver, stage)
        data_tar = _tar_bytes(data_entries)

        total_bytes = sum(len(d or b"") for _, _, d, _ in data_entries)
        installed_kb = max(1, (total_bytes + 1023) // 1024)

        ctrl_dir = stage / "ctrl"
        ctrl_dir.mkdir(exist_ok=True)
        (ctrl_dir / "control").write_text(control_text(ver, installed_kb), encoding="utf-8")
        (ctrl_dir / "postinst").write_text(POSTINST, encoding="utf-8")
        (ctrl_dir / "postrm").write_text(POSTRM, encoding="utf-8")
        (ctrl_dir / "md5sums").write_text("\n".join(md5_lines) + "\n", encoding="utf-8")

        ctrl_entries = [
            ("./control", None, (ctrl_dir / "control").read_bytes(), 0o644),
            ("./md5sums", None, (ctrl_dir / "md5sums").read_bytes(), 0o644),
            ("./postinst", None, (ctrl_dir / "postinst").read_bytes(), 0o755),
            ("./postrm", None, (ctrl_dir / "postrm").read_bytes(), 0o755),
        ]
        ctrl_tar = _tar_bytes(ctrl_entries)

        deb = build_ar(
            ("debian-binary", b"2.0\n"),
            ("control.tar.gz", ctrl_tar),
            ("data.tar.gz", data_tar),
        )

        DIST.mkdir(exist_ok=True)
        out = DIST / f"{PKG}_{ver}_all.deb"
        out.write_bytes(deb)
        print(f"打好了：{out}")
        print(f"  大小 {len(deb) / 1024:.1f} KB · 解包后 {installed_kb} KB · "
              f"{len(data_entries)} 个条目")

        return verify(out, ver)
    finally:
        shutil.rmtree(stage, ignore_errors=True)


# ----------------------------------------------------------------------
# 自检：把打好的 deb 读回来验一遍
# ----------------------------------------------------------------------
def _read_ar(blob: bytes) -> list[tuple[str, bytes]]:
    if not blob.startswith(b"!<arch>\n"):
        raise SystemExit("不是 ar 归档")
    out = []
    pos = 8
    while pos + 60 <= len(blob):
        head = blob[pos:pos + 60]
        if head[58:60] != b"`\n":
            raise SystemExit(f"ar 头魔数不对（偏移 {pos}）")
        name = head[0:16].decode("ascii").strip()
        size = int(head[48:58].decode("ascii").strip() or 0)
        pos += 60
        out.append((name, blob[pos:pos + size]))
        pos += size + (size % 2)
    return out


def _untar(blob: bytes) -> list[tuple[str, int, bytes, int, int]]:
    raw = gzip.decompress(blob)
    out = []
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tf:
        for m in tf.getmembers():
            data = tf.extractfile(m).read() if m.isfile() else b""
            out.append((m.name, m.mode, data, m.uid, m.gid))
    return out


def _dir_types(blob: bytes) -> list[tuple[str, bytes]]:
    """列出目录条目及其 type，确认它们真是 DIRTYPE 而不是同名普通文件。"""
    raw = gzip.decompress(blob)
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as tf:
        return [(m.name, m.type) for m in tf.getmembers() if m.isdir()]


def verify(deb: Path, ver: str) -> int:
    print("\n自检：")
    blob = deb.read_bytes()
    members = _read_ar(blob)
    names = [n for n, _ in members]
    ok = True

    def chk(cond: bool, what: str, detail: str = "") -> None:
        nonlocal ok
        print(f"  {'[ok  ]' if cond else '[fail]'} {what}"
              f"{('  — ' + detail) if detail else ''}")
        ok = ok and cond

    chk(names == ["debian-binary", "control.tar.gz", "data.tar.gz"],
        "ar 成员顺序正确", " / ".join(names))
    chk(dict(members)["debian-binary"] == b"2.0\n", "debian-binary 是 2.0")

    ctrl = {n.lstrip("./"): (m, d) for n, m, d, _, _ in _untar(dict(members)["control.tar.gz"])}
    required = {"Package", "Version", "Architecture", "Maintainer", "Description", "Depends"}
    text = ctrl["control"][1].decode("utf-8")
    fields = {ln.split(":", 1)[0] for ln in text.splitlines() if ":" in ln and not ln.startswith(" ")}
    chk(required <= fields, "control 必需字段齐全", f"缺 {required - fields}" if required - fields else "")
    chk(f"Package: {PKG}" in text, "Package 名正确")
    chk(f"Version: {ver}" in text, "版本号与 paths.py 一致", ver)
    chk("Architecture: all" in text, "Architecture: all（纯 Python，不绑架构）")
    chk("aria2" in text, "依赖里带 aria2 下载内核")
    chk(ctrl["postinst"][0] & 0o111 != 0, "postinst 可执行")
    chk(ctrl["postrm"][0] & 0o111 != 0, "postrm 可执行")

    data = _untar(dict(members)["data.tar.gz"])
    paths = {p: (mode, payload) for p, mode, payload, _, _ in data}
    must = [
        f".{APP_DIR}/main.py",
        f".{APP_DIR}/core/plat.py",
        f".{APP_DIR}/core/installer_linux.py",
        f".{APP_DIR}/core/catalog_linux.py",
        f".{APP_DIR}/ui/app.py",
        f".{APP_DIR}/vendor/customtkinter/__init__.py",
        f".{APP_DIR}/vendor/darkdetect/__init__.py",
        f".{APP_DIR}/assets/app.png",
        "./usr/bin/swiftget",
        f"./usr/share/applications/{DESKTOP}",
        "./usr/share/icons/hicolor/256x256/apps/swiftget.png",
    ]
    for p in must:
        chk(p in paths, f"包含 {p}")
    chk(paths["./usr/bin/swiftget"][0] & 0o111 != 0, "启动器可执行")
    chk(paths[f".{APP_DIR}/main.py"][0] == 0o644, "main.py 权限 0644")
    chk(all(uid == 0 and gid == 0 for _, _, _, uid, gid in data), "所有条目属主是 root")
    chk(not [p for p in paths if "__pycache__" in p], "没有混进 __pycache__")
    dirs = _dir_types(dict(members)["data.tar.gz"])
    bad_dirs = [n for n, t in dirs if t != tarfile.DIRTYPE]
    chk(dirs and not bad_dirs, "目录条目类型是 DIRTYPE(5)",
        f"{len(dirs)} 个目录" if not bad_dirs else f"伪装成文件的目录：{bad_dirs[:3]}")
    chk(b"APP_VERSION" in paths.get(f".{APP_DIR}/core/paths.py", (0, b""))[1],
        "源码文件内容完整")

    entries = [p for p in paths if p.startswith(f".{APP_DIR}/")]
    chk(len(entries) > 40, "源码 + vendor 条目数量正常", f"{len(entries)} 项")

    sums = dict(
        (ln.split("  ", 1)[1], ln.split("  ", 1)[0])
        for ln in ctrl["md5sums"][1].decode("utf-8").splitlines() if "  " in ln
    )
    bad = [p for p, h in sums.items()
           if f"./{p}" in paths and hashlib.md5(paths[f"./{p}"][1]).hexdigest() != h]
    chk(not bad, "md5sums 与实际内容一致", f"{len(sums)} 项" if not bad else str(bad[:3]))

    print(f"\n{'自检通过' if ok else '自检失败'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(build())
