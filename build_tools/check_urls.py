"""批量预检软件下载源可用性。仅开发期使用。"""
import concurrent.futures as cf
import sys

import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

CANDIDATES = {
    "chrome.msi": "https://dl.google.com/dl/chrome/install/googlechromestandaloneenterprise64.msi",
    "chrome.exe": "https://dl.google.com/chrome/install/ChromeStandaloneSetup64.exe",
    "huorong.a": "https://down5.huorong.cn/hrswcksingle.exe",
    "huorong.b": "https://download.huorong.cn/hrswcksingle.exe",
    "huorong.c": "https://down5.huorong.cn/hrss/hrs_setup.exe",
    "huorong.d": "https://www.huorong.cn/down",
    "360.a": "https://down.360safe.com/inst.exe",
    "360.b": "https://down.360safe.com/setup.exe",
    "7zip.a": "https://www.7-zip.org/a/7z2409-x64.exe",
    "7zip.b": "https://www.7-zip.org/a/7z2501-x64.exe",
    "7zip.c": "https://sparanoid.com/lab/7z/7z2408-x64.exe",
    "vlc.a": "https://mirrors.tuna.tsinghua.edu.cn/videolan-ftp/vlc/3.0.21/win64/vlc-3.0.21-win64.exe",
    "vlc.b": "https://get.videolan.org/vlc/3.0.21/win64/vlc-3.0.21-win64.exe",
    "wechat.a": "https://dldir1.qq.com/weixin/Windows/WeChatSetup.exe",
    "qq.a": "https://dldir1.qq.com/qqfile/qq/QQNT/Windows/QQ_9.9.19_250610_x64_01.exe",
    "everything.a": "https://www.voidtools.com/Everything-1.4.1.1026.x64-Setup.exe",
    "notepadpp.a": "https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.7.1/npp.8.7.1.Installer.x64.exe",
    "bandizip.a": "https://dl.bandisoft.com/bandizip.std/BANDIZIP-SETUP-STD-X64.EXE",
    "dingtalk.a": "https://dtapp-pub.dingtalk.com/dingtalk-desktop/win_installer/Release/DingTalk_v7.8.2.412240121.exe",
    "wps.a": "https://package.wpscdn.cn/wps/download/ep/WPS_Setup_18710.exe",
    "netease.a": "https://d1.music.126.net/dmusic/cloudmusicsetup2.10.13.202675.exe",
    "thunder.a": "https://down.sandai.net/thunder11/XunLeiSetup12.1.7.2650.exe",
}


def probe(item):
    name, url = item
    try:
        r = requests.get(
            url, headers={"User-Agent": UA, "Range": "bytes=0-0"},
            stream=True, timeout=18, allow_redirects=True,
        )
        code = r.status_code
        ctype = r.headers.get("Content-Type", "")
        crange = r.headers.get("Content-Range", "")
        clen = r.headers.get("Content-Length", "")
        r.close()
        return name, code, ctype[:40], crange, clen
    except Exception as exc:  # noqa: BLE001
        return name, "ERR", type(exc).__name__, "", ""


def main():
    with cf.ThreadPoolExecutor(max_workers=10) as pool:
        results = list(pool.map(probe, CANDIDATES.items()))
    ok = 0
    for name, code, ctype, crange, clen in results:
        flag = "OK " if code in (200, 206) else "-- "
        if code in (200, 206):
            ok += 1
        print(f"{flag}{name:<14} {code}  ct={ctype}  range={crange}  len={clen}")
    print(f"\n{ok}/{len(results)} reachable")


if __name__ == "__main__":
    sys.exit(main())
