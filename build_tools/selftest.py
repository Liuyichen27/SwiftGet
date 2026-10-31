# -*- coding: utf-8 -*-
"""SwiftGet 功能自测（无需交互）。"""
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

PASS = []
FAIL = []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), name, detail)


# ---------- 1. 纯逻辑 ----------
from core.aria2 import human_size, human_speed, human_eta

check("human_size", human_size(0) == "0 B" and human_size(1536) == "1.5 KB"
      and human_size(5 * 1024 * 1024) == "5.0 MB")
check("human_speed", human_speed(0) == "—" and human_speed(1024) == "1.0 KB/s")
check("human_eta", human_eta(59) == "59 秒" and human_eta(125) == "2 分 5 秒"
      and human_eta(float("nan")) == "—")

from core.update import ver_tuple, asset_urls

check("ver_tuple", ver_tuple("v1.2.1") == (1, 2, 1)
      and ver_tuple("1.10.2") == (1, 10, 2)
      and ver_tuple("") == (0, 0, 0))
check("asset_urls", asset_urls("") [0].startswith("https://github.com/")
      and asset_urls("https://gh-proxy.com/x") == ["https://gh-proxy.com/x"])

from core.catalog import AppEntry, Source, Catalog

app = AppEntry(
    id="t", name="Test App", vendor="v", category="c", desc="d",
    color="#000", sources=[Source("https://a/b.exe", "官方")],
    size_label="", installer="msi", silent_args=["/qn"],
)
check("install_command_msi",
      app.install_command("C:/x.msi") == ["msiexec", "/i", "C:/x.msi", "/qn", "/norestart"])
check("suggested_filename", app.suggested_filename() == "Test_App_setup.msi")

vlc = next(a for a in __import__("core.catalog", fromlist=["BUILTIN"]).BUILTIN if a.id == "vlc")
check("vlc_lang_args", vlc.install_command("v.exe", "zh") == ["v.exe", "/L=2052", "/S"])

# settings 原子读写
from core.settings import Settings

s = Settings()
s.download_dir = tempfile.gettempdir()
s.max_connections = 8
s.save()
s2 = Settings.load()
check("settings_roundtrip", s2.max_connections == 8 and s2.download_dir == s.download_dir)

# catalog 覆盖合并
cat = Catalog()
cat._apply({"apps": [{"id": "chrome", "name": "Chrome 改名", "sources": [
    {"url": "https://example.com/x.msi", "label": "镜像"}]}]})
ch = cat.get("chrome")
check("catalog_override",
      ch.name == "Chrome 改名" and ch.sources[0].url == "https://example.com/x.msi"
      and ch.installer == "msi")
exp_path = Path(cat.export_local())
check("catalog_export_roundtrip", exp_path.exists())
exp_path.unlink(missing_ok=True)   # 自测产物，删掉以免污染运行时清单覆盖

# installer 校验
from core.installer import verify_installer

tmpd = Path(tempfile.mkdtemp())
pe = tmpd / "fake.exe"
pe.write_bytes(b"MZ" + b"\x00" * 200_000)
ok, msg = verify_installer(pe)
check("verify_pe", ok and msg == "OK")
bad = tmpd / "bad.exe"
bad.write_bytes(b"<html>" + b"\x00" * 200_000)
ok, msg = verify_installer(bad)
check("verify_bad_pe", not ok)
z = tmpd / "src.zip"
import os as _os
import zipfile

with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
    # 随机字节防止 deflate 把体积压到 2KB 门槛以下
    zf.writestr("a.bin", _os.urandom(4096))
ok, msg = verify_installer(z, "archive")
check("verify_zip", ok)

# ---------- 2. 多源预检（7-Zip：官方 302 到 GitHub，镜像应可用） ----------
from core.catalog import BUILTIN, probe_source

seven = next(a for a in BUILTIN if a.id == "7zip")
mirror_ok, _ = probe_source(seven.sources[1].url, timeout=8)
check("7zip_mirror_probe", mirror_ok, seven.sources[1].url)

# ---------- 3. aria2 引擎真实下载 ----------
from core.aria2 import Aria2Engine, Aria2Options

eng = Aria2Engine(Aria2Options(p2p_enabled=False))
try:
    eng.start(timeout=15)
    check("aria2_start", True, eng.version())
    out = tmpd / "dl"
    out.mkdir(exist_ok=True)
    url = seven.sources[1].url   # gh-proxy 加速镜像，当前网络可达
    gid = eng.add_uri(url, "7z2409-x64.exe", out)
    deadline = time.time() + 120
    final = ""
    while time.time() < deadline:
        st = eng.tell(gid)
        if not st:
            time.sleep(0.5)
            continue
        fb = st.get("followedBy")
        if fb:
            gid = fb[0]
            continue
        if st.get("status") == "complete":
            final = "complete"
            break
        if st.get("status") == "error":
            final = st.get("errorMessage", "err")
            break
        time.sleep(0.5)
    f = out / "7z2409-x64.exe"
    check("aria2_real_download", final == "complete" and f.exists()
          and f.stat().st_size > 1_000_000, f"{final} size={f.stat().st_size if f.exists() else 0}")
    ok, msg = verify_installer(f)
    check("downloaded_file_verify", ok)
except Exception as e:  # noqa: BLE001
    check("aria2_engine", False, repr(e))
finally:
    eng.stop()

print()
print(f"== {len(PASS)} passed, {len(FAIL)} failed ==")
if FAIL:
    print("FAILED:", FAIL)
sys.exit(1 if FAIL else 0)
