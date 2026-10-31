"""Linux 版内置清单。

和 Windows 版是两套东西，不共用：Windows 那套是「exe + 静默安装参数」，
到 Linux 上完全没意义（这里装软件的正经途径是 apt）。所以 Linux 版只收录
**官网只给 deb / 压缩包、系统仓库里又没有**的那类软件，其余交给 apt。

``kind`` 的含义：
* ``deb``     —— 下载完调 apt 装（会弹一次管理员密码框）
* ``tarball`` —— 解压到 ~/.local/opt，自己带启动脚本的绿色包
* ``archive`` —— 源码包，解压看说明自己装（自创的 CLI 工具）
"""
from __future__ import annotations

from .catalog import AppEntry, Source, _e

LINUX_BUILTIN: list[AppEntry] = [
    _e(
        id="chrome",
        name="Google Chrome",
        vendor="Google",
        category="浏览器",
        desc="全球使用最广的浏览器，官网只给 deb",
        color="#4285F4",
        size_label="≈120 MB · deb",
        kind="deb",
        filename="google-chrome-stable_current_amd64.deb",
        homepage="https://www.google.cn/chrome/",
        sources=[
            ("https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb", "官方"),
        ],
        note="官方稳定版 deb，装完会把 Chrome 的 apt 源一起加上，以后跟着系统更新。",
    ),
    _e(
        id="edge",
        name="Microsoft Edge",
        vendor="Microsoft",
        category="浏览器",
        desc="Chromium 内核，能直接用 Chrome 的扩展",
        color="#0AA1DD",
        size_label="≈110 MB · deb",
        kind="deb",
        filename="microsoft-edge-stable_amd64.deb",
        homepage="https://www.microsoft.com/edge",
        sources=[
            ("https://go.microsoft.com/fwlink?linkid=2149051", "官方"),
        ],
        note="官方链接会 302 到最新版 deb，不用关心版本号。",
    ),
    _e(
        id="vscode",
        name="Visual Studio Code",
        vendor="Microsoft",
        category="开发",
        desc="最主流的代码编辑器，插件生态大",
        color="#007ACC",
        size_label="≈100 MB · deb",
        kind="deb",
        filename="code_amd64.deb",
        homepage="https://code.visualstudio.com/",
        sources=[
            ("https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-x64", "官方"),
        ],
        note="官方 stable 通道。要 Insider 版把 build=stable 换成 build=insider。",
    ),
    _e(
        id="firefox",
        name="Firefox",
        vendor="Mozilla",
        category="浏览器",
        desc="独立内核的浏览器，官网压缩包比系统源新",
        color="#FF7139",
        size_label="≈75 MB · tar.xz",
        kind="tarball",
        filename="firefox-latest.tar.xz",
        homepage="https://www.mozilla.org/firefox/",
        sources=[
            ("https://download.mozilla.org/?product=firefox-latest-ssl&os=linux64&lang=zh-CN", "官方 中文"),
        ],
        note="解压即用的绿色版，会装到 ~/.local/opt/firefox，不影响系统自带的那个。",
    ),
    _e(
        id="appimagelauncher",
        name="AppImageLauncher",
        vendor="TheAssassin",
        category="工具",
        desc="双击 AppImage 就能装进应用菜单，不用手动 chmod",
        color="#E95420",
        size_label="≈2 MB · deb",
        kind="deb",
        filename="appimagelauncher_2.2.0_amd64.deb",
        homepage="https://github.com/TheAssassin/AppImageLauncher",
        sources=[
            ("https://github.com/TheAssassin/AppImageLauncher/releases/download/"
             "v2.2.0/appimagelauncher_2.2.0-gha118_amd64.deb", "官方"),
        ],
        note="装了它，以后下到的 .AppImage 双击就能集成，省得每次 chmod +x 再自己建快捷方式。",
    ),
    _e(
        id="cleanblackboard",
        name="CleanBlackboard - 简黑板",
        vendor="自研",
        category="工具",
        desc="双击就能写的白板，不联网、无账号",
        color="#2F6BFF",
        size_label="≈130 KB · deb",
        kind="deb",
        filename="cleanblackboard_1.2.2_all.deb",
        homepage="https://github.com/Liuyichen27/clean-blackboard",
        sources=[
            ("https://github.com/Liuyichen27/clean-blackboard/releases/download/"
             "v1.2.2/cleanblackboard_1.2.2_all.deb", "官方"),
            ("https://gh-proxy.com/https://github.com/Liuyichen27/clean-blackboard/"
             "releases/download/v1.2.2/cleanblackboard_1.2.2_all.deb", "加速镜像"),
        ],
        note="装完在应用菜单里叫「简黑板」，也可以命令行敲 cleanblackboard。\n"
             "依赖会自动装（python3-webview + WebKitGTK），装完跑 cleanblackboard --check 自检。",
        usage="sudo apt install ./cleanblackboard_*.deb  →  cleanblackboard",
    ),
]


def linux_catalog() -> list[AppEntry]:
    return list(LINUX_BUILTIN)
