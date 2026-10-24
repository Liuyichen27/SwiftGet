"""诊断：逐个软件、逐个源跑预检，打印真实失败原因。"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import requests  # noqa: E402

from core.catalog import BUILTIN  # noqa: E402

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def probe(url: str, timeout: float = 10.0):
    try:
        r = requests.get(
            url,
            headers={"User-Agent": UA, "Range": "bytes=0-0"},
            stream=True,
            timeout=timeout,
            allow_redirects=True,
        )
        code = r.status_code
        ctype = r.headers.get("Content-Type", "")
        crange = r.headers.get("Content-Range", "")
        clen = r.headers.get("Content-Length", "")
        r.close()
        return code, ctype, crange, clen, ""
    except Exception as exc:  # noqa: BLE001
        return None, "", "", "", f"{type(exc).__name__}: {exc}"


def main() -> None:
    for app in BUILTIN:
        print(f"\n=== {app.name} ({app.id}) installer={app.installer}")
        for src in app.sources:
            code, ctype, crange, clen, err = probe(src.url)
            if err:
                print(f"  [ERR] {src.label:<12} {src.url[:70]}  -> {err[:80]}")
            else:
                print(f"  [{code}] {src.label:<12} ct={ctype[:30]:<30} "
                      f"cr={crange[:26]:<26} len={clen}")


if __name__ == "__main__":
    main()
