"""引擎联调测试：真实下载一个小文件，验证 aria2 分片下载链路。"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from core.aria2 import Aria2Engine, Aria2Options, human_size, human_speed  # noqa: E402
from core.catalog import probe_source  # noqa: E402

TARGET_DIR = ROOT / "build_tools" / "_test_dl"
URL = "https://www.voidtools.com/Everything-1.4.1.1026.x64-Setup.exe"
NAME = "Everything_test.exe"


def main() -> int:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    for old in TARGET_DIR.glob("*"):
        old.unlink()

    print("[1] 预检源…")
    ok, size = probe_source(URL)
    print(f"    reachable={ok} size={human_size(size)}")
    if not ok:
        print("源不可用，测试终止")
        return 2

    print("[2] 启动 aria2 引擎…")
    engine = Aria2Engine(Aria2Options(max_connections=16, split=16, p2p_enabled=True))
    t0 = time.time()
    engine.start()
    print(f"    版本 {engine.version()} 端口 {engine.port} 用时 {time.time()-t0:.2f}s")

    print("[3] 提交下载任务…")
    gid = engine.add_uri(URL, NAME, TARGET_DIR)
    print(f"    gid={gid}")

    print("[4] 跟踪进度…")
    last = 0.0
    deadline = time.time() + 180
    peak_speed = 0.0
    max_conns = 0
    while time.time() < deadline:
        st = engine.tell(gid)
        if not st:
            time.sleep(0.5)
            continue
        status = st.get("status")
        total = int(st.get("totalLength") or 0)
        done = int(st.get("completedLength") or 0)
        speed = float(st.get("downloadSpeed") or 0)
        conns = int(st.get("connections") or 0)
        peak_speed = max(peak_speed, speed)
        max_conns = max(max_conns, conns)
        if time.time() - last > 0.8:
            last = time.time()
            frac = (done / total * 100) if total else 0
            print(f"    {status:<9} {frac:5.1f}%  {human_size(done)}/{human_size(total)}  "
                  f"{human_speed(speed)}  conns={conns}")
        if status == "complete":
            break
        if status == "error":
            print("    错误:", st.get("errorMessage"))
            engine.stop()
            return 3
        time.sleep(0.25)

    print("[5] 结果")
    files = engine.tell(gid).get("files") or []
    path = Path(files[0]["path"]) if files else TARGET_DIR / NAME
    exists = path.exists()
    fsize = path.stat().st_size if exists else 0
    print(f"    文件: {path}")
    print(f"    存在={exists} 大小={human_size(fsize)}")
    print(f"    峰值速度={human_speed(peak_speed)} 最大并发连接={max_conns}")

    engine.stop()
    print("    aria2 已停止")

    if exists and fsize > 1_000_000:
        print("\n✅ 下载链路验证通过")
        return 0
    print("\n❌ 文件异常")
    return 1


if __name__ == "__main__":
    sys.exit(main())
