import concurrent.futures as cf

import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

CANDIDATES = {
    "qq.1": "https://dldir1.qq.com/qqfile/qq/QQNT/Windows/QQ_9.9.17_250317_x64_01.exe",
    "qq.2": "https://dldir1.qq.com/qqfile/qq/PCQQ9.7.23/QQ9.7.23.29392.exe",
    "ding.1": "https://dtapp-pub.dingtalk.com/dingtalk-desktop/win_installer/Release/DingTalk_v7.6.5.41222.exe",
    "vlc.hw": "https://mirrors.huaweicloud.com/vlc/3.0.21/win64/vlc-3.0.21-win64.exe",
    "vlc.ustc": "https://mirrors.ustc.edu.cn/videolan-ftp/vlc/3.0.21/win64/vlc-3.0.21-win64.exe",
    "vlc.get": "https://get.videolan.org/vlc/3.0.21/win64/vlc-3.0.21-win64.exe",
    "7z.hw": "https://mirrors.huaweicloud.com/7zip/24.09/7z2409-x64.exe",
    "npp.ghp": "https://ghfast.top/https://github.com/notepad-plus-plus/notepad-plus-plus/releases/download/v8.7.1/npp.8.7.1.Installer.x64.exe",
    "hr.1": "https://down5.huorong.cn/hrswcksingle.exe",
    "hr.2": "https://down.huorong.cn/hrswcksingle.exe",
    "wps.1": "https://package.wpscdn.cn/wps/download/ep/WPS_Setup.exe",
    "thunder": "https://down.sandai.net/thunder11/XunLeiSetup12.1.7.2650.exe",
}


def probe(item):
    key, url = item
    try:
        r = requests.get(
            url,
            headers={"User-Agent": UA, "Range": "bytes=0-0"},
            stream=True,
            timeout=15,
            allow_redirects=True,
        )
        h = r.headers
        r.close()
        return f"{key:<10} {r.status_code} ct={h.get('Content-Type', '')[:28]:<28} cr={h.get('Content-Range', '')[:30]}"
    except Exception as exc:  # noqa: BLE001
        return f"{key:<10} ERR {type(exc).__name__}"


with cf.ThreadPoolExecutor(max_workers=12) as ex:
    for line in ex.map(probe, CANDIDATES.items()):
        print(line)
