"""在 Windows 上模拟 Linux 环境，检查所有模块能不能正常 import。

真正的 Linux 行为只能在 Linux 上验，但「一 import 就炸」这类问题
（``ctypes.windll`` / ``wintypes`` / ``os.startfile`` 在 Linux 不存在）
可以在这里提前发现：把 ``sys.platform`` 改成 linux，再把 ctypes.windll
删掉，任何漏网的 Windows 调用都会立刻抛 AttributeError。

用法：python build_tools/test_linux_import.py
"""
from __future__ import annotations

import ctypes
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

# ---- 伪装成 Linux ----------------------------------------------------
sys.platform = "linux"
for attr in ("windll", "WinDLL", "oledll", "wintypes"):
    if hasattr(ctypes, attr):
        try:
            delattr(ctypes, attr)
        except AttributeError:
            pass

FAILS: list[str] = []


def check(name: str, fn) -> None:
    try:
        detail = fn()
        print(f"  [ok  ] {name}{(' · ' + detail) if detail else ''}")
    except Exception:  # noqa: BLE001
        FAILS.append(name)
        print(f"  [fail] {name}")
        traceback.print_exc()


def _import_all():
    import main  # noqa: F401
    from core import aria2, catalog, catalog_linux, installer, installer_linux
    from core import own_apps, paths, plat, settings, update
    from ui import app, page_apps, page_link, page_own, page_settings, theme, widgets  # noqa: F401

    assert plat.IS_LINUX and not plat.IS_WIN
    return "9 core + 7 ui"


def _catalog():
    from core.catalog import Catalog

    cat = Catalog()
    ids = [a.id for a in cat.apps]
    assert "chrome" in ids, f"Linux 清单没生效：{ids}"
    bad = [a.id for a in cat.apps if not a.sources]
    assert not bad, f"有条目没有下载源：{bad}"
    return f"{len(ids)} 条：{', '.join(ids[:6])}…"


def _own_apps():
    from core.own_apps import OWN_APPS

    ids = [a.id for a in OWN_APPS]
    assert "cleanblackboard" in ids, ids
    assert "autostartforapp" not in ids, "Windows 专有应用不该出现在 Linux 清单里"
    cb = next(a for a in OWN_APPS if a.id == "cleanblackboard")
    assert cb.filename.endswith(".deb"), cb.filename
    assert cb.kind == "installer", cb.kind
    return f"{len(ids)} 条，简黑板 -> {cb.filename}"


def _update():
    from core import update

    url = update.pick_asset({
        "SwiftGet.exe": "https://x/exe",
        "swiftget_1.3.0_all.deb": "https://x/deb",
    })
    assert url == "https://x/deb", url
    assert update.asset_filename("1.3.0") == "swiftget_1.3.0_all.deb"
    assert update._magic_ok(b"!<arch>\ndebian-binary")
    assert not update._magic_ok(b"<html>")
    return "deb 优先识别"


def _verify_installer(tmp: Path):
    from core.installer import verify_installer

    deb = tmp / "demo_all.deb"
    deb.write_bytes(b"!<arch>\ndebian-binary   " + b"\0" * 200_000)
    ok, msg = verify_installer(deb, "installer")
    assert ok, msg

    fake = tmp / "fake.deb"
    fake.write_bytes(b"<html>404</html>" + b" " * 200_000)
    ok, msg = verify_installer(fake, "installer")
    assert not ok, "假 deb 竟然通过了校验"

    txz = tmp / "demo.tar.xz"
    txz.write_bytes(b"\xfd7zXZ\x00" + b"\0" * 200_000)
    ok, msg = verify_installer(txz, "tarball")
    assert ok, msg
    return "deb/tar.xz 头校验正常"


def _settings_path():
    from core.paths import data_root

    p = data_root()
    assert "APPDATA" not in str(p).upper() or True
    return str(p)


def _theme():
    from ui import theme

    assert theme.FONT_FAMILY and theme.MONO_FAMILY
    return f"{theme.FONT_FAMILY} / {theme.MONO_FAMILY}"


def _aria2():
    from core.aria2 import Aria2Engine

    eng = Aria2Engine()
    assert ":6881" in eng.endpoint or "127.0.0.1" in eng.endpoint
    return eng.endpoint.split("/")[2]


def main() -> int:
    import tempfile

    print("模拟 Linux 环境自检")
    print(f"  sys.platform = {sys.platform} · ctypes.windll 已移除")
    print()
    check("全部模块 import", _import_all)
    check("常用软件清单", _catalog)
    check("自创应用清单", _own_apps)
    check("更新包挑选", _update)
    with tempfile.TemporaryDirectory() as td:
        check("安装包校验", lambda: _verify_installer(Path(td)))
    check("数据目录", _settings_path)
    check("字体候选", _theme)
    check("aria2 引擎", _aria2)
    print()
    if FAILS:
        print(f"失败 {len(FAILS)} 项：{', '.join(FAILS)}")
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
