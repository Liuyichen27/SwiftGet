"""P2P 链路验证：用公开合法种子连接 DHT 网络，观察 peer 数量。"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from core.aria2 import Aria2Engine, Aria2Options, human_size, human_speed  # noqa: E402

TARGET_DIR = ROOT / "build_tools" / "_test_p2p"

# WebTorrent 官方示例种子（开源电影 Sintel，CC 授权），做种节点稳定
MAGNET = (
    "magnet:?xt=urn:btih:08ada5a7a6183aae1e09d831df6748d566095a10"
    "&dn=Sintel&tr=udp%3A%2F%2Fexplodie.org%3A6969"
    "&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337"
)
WATCH_SECONDS = 75


def main() -> int:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    engine = Aria2Engine(Aria2Options(p2p_enabled=True, max_connections=16))
    print("[1] 启动引擎（含 DHT）…")
    engine.start()
    print(f"    aria2 {engine.version()}  port={engine.port}")

    print("[2] 提交磁力链…")
    gid = engine.add_magnet(MAGNET, TARGET_DIR)
    print(f"    gid={gid}")

    print(f"[3] 观察 {WATCH_SECONDS}s…")
    start = time.time()
    peak_seeders = 0
    peak_speed = 0.0
    got_meta = False
    last_print = 0.0
    current = gid

    while time.time() - start < WATCH_SECONDS:
        st = engine.tell(current)
        if not st:
            time.sleep(1)
            continue

        followed = st.get("followedBy")
        if followed and not got_meta:
            got_meta = True
            current = followed[0]
            print(f"    ✅ 已获取种子元数据，切换 gid={current}")
            continue

        status = st.get("status", "")
        seeders = int(st.get("numSeeders") or 0)
        speed = float(st.get("downloadSpeed") or 0)
        done = int(st.get("completedLength") or 0)
        total = int(st.get("totalLength") or 0)
        peak_seeders = max(peak_seeders, seeders)
        peak_speed = max(peak_speed, speed)

        if time.time() - last_print > 3:
            last_print = time.time()
            print(f"    {status:<9} 节点={seeders:<3} 速度={human_speed(speed):<12} "
                  f"{human_size(done)}/{human_size(total)}")

        if status == "complete":
            print("    下载完成")
            break
        if status == "error":
            print("    错误:", st.get("errorMessage"))
            break
        time.sleep(0.8)

    print("[4] 结论")
    print(f"    元数据获取: {'✅' if got_meta else '❌'}")
    print(f"    最大 peer 节点: {peak_seeders}")
    print(f"    峰值速度: {human_speed(peak_speed)}")

    try:
        engine.remove(current)
    except Exception:
        pass
    engine.stop()

    ok = got_meta or peak_seeders > 0
    print("\n✅ P2P 链路可用" if ok else "\n⚠ P2P 网络在当前环境不可达（不影响本机运行）")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
