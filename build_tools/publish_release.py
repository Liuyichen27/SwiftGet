"""创建 GitHub Release 并上传 exe 附件（网络不稳定，带重试）。

用法：
    GIT_TOKEN=ghp_xxx python build_tools/publish_release.py
"""

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

OWNER = "Liuyichen27"
REPO = "SwiftGet"
TAG = "v1.0.0"
TITLE = "SwiftGet 1.0.0"
ASSET = os.path.join("dist", "SwiftGet.exe")
BODY_FILE = os.path.join("docs", "RELEASE-v1.0.0.md")

TOKEN = os.environ.get("GIT_TOKEN")
if not TOKEN:
    sys.exit("缺少 GIT_TOKEN 环境变量")

for var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
    os.environ.pop(var, None)

API = f"https://api.github.com/repos/{OWNER}/{REPO}"
UPLOAD = f"https://uploads.github.com/repos/{OWNER}/{REPO}"

CTX = ssl.create_default_context()
# 这台机器的证书吊销检查偶尔连不上，放宽到仅校验证书链
CTX.check_hostname = True


def call(url, method="GET", data=None, ctype="application/json", tries=25, delay=6):
    last = None
    for i in range(1, tries + 1):
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {TOKEN}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "SwiftGet-publisher")
        if data is not None:
            req.add_header("Content-Type", ctype)
        try:
            with urllib.request.urlopen(req, timeout=120, context=CTX) as r:
                return json.loads(r.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            payload = e.read().decode("utf-8", "replace")
            # 422 = 已存在，交给调用方处理；其他 4xx 直接报错，不必重试
            if e.code in (401, 403, 404, 422):
                raise RuntimeError(f"HTTP {e.code}: {payload[:400]}")
            last = f"HTTP {e.code}: {payload[:200]}"
        except Exception as e:  # 网络层错误，重试
            last = f"{type(e).__name__}: {e}"
        print(f"  [{i}/{tries}] 失败：{last}，{delay}s 后重试", flush=True)
        time.sleep(delay)
    raise RuntimeError(f"重试 {tries} 次仍未成功：{last}")


def main():
    with open(BODY_FILE, encoding="utf-8") as f:
        body = f.read()

    print("1/2 创建 Release …", flush=True)
    try:
        rel = call(
            f"{API}/releases",
            "POST",
            json.dumps({"tag_name": TAG, "name": TITLE, "body": body,
                        "target_commitish": "main", "draft": False,
                        "prerelease": False}).encode("utf-8"),
        )
        print(f"    已创建：{rel['html_url']}", flush=True)
    except RuntimeError as e:
        if "422" not in str(e):
            raise
        print("    Release 已存在，复用", flush=True)
        rel = call(f"{API}/releases/tags/{TAG}")

    rid = rel["id"]
    name = os.path.basename(ASSET)
    size = os.path.getsize(ASSET)
    print(f"2/2 上传 {name}（{size / 1048576:.1f} MB）…", flush=True)

    existing = call(f"{API}/releases/{rid}/assets")
    for a in existing:
        if a["name"] == name:
            print(f"    已存在同名附件，先删除 id={a['id']}", flush=True)
            call(f"{API}/assets/{a['id']}", "DELETE")

    with open(ASSET, "rb") as f:
        blob = f.read()

    asset = call(
        f"{UPLOAD}/releases/{rid}/assets?name={name}",
        "POST",
        blob,
        ctype="application/octet-stream",
        tries=40,
    )
    print(f"    上传完成：{asset['browser_download_url']}", flush=True)
    print("    大小：", asset["size"], flush=True)
    print("OK", rel["html_url"], flush=True)


if __name__ == "__main__":
    main()
