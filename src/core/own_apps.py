"""自创应用清单。

这里放的是本项目作者自己写、自己打包的小工具，和「常用软件」那种第三方
安装包不是一回事：

* ``kind="portable"`` —— 绿色版单文件，下载完直接双击运行，不存在安装步骤；
* ``kind="archive"``  —— 源码压缩包，解压后按 README 里的命令装。

因此它们不参与静默安装流程（见 ``ui.app._download_worker``），下载完就结束。

下载源统一走 GitHub Release：官方直链优先，``gh-proxy.com`` 镜像兜底
（国内直连 github.com 的 Release 经常超时，预检会按顺序自动挑选可用的那个）。
"""
from __future__ import annotations

from .catalog import AppEntry, Source

VERSION = "1.0.0"
OWNER = "Liuyichen27"

OWN_CATEGORIES = ["全部", "桌面应用", "命令行工具"]


def _release(repo: str, filename: str) -> list[Source]:
    """官方直链 + 加速镜像，两路都指向同一个 Release 附件。"""
    path = f"{OWNER}/{repo}/releases/download/v{VERSION}/{filename}"
    return [
        Source(f"https://github.com/{path}", "官方"),
        Source(f"https://gh-proxy.com/https://github.com/{path}", "加速镜像"),
    ]


def _e(**kw) -> AppEntry:
    return AppEntry(**kw)


OWN_APPS: list[AppEntry] = [
    _e(
        id="cleanblackboard",
        name="CleanBlackboard - 简黑板",
        vendor="自研 · 桌面应用",
        category="桌面应用",
        desc="双击就能写的白板，不联网、无账号，绿色版",
        color="#2F6BFF",
        sources=_release("clean-blackboard", "CleanBlackboard.exe"),
        size_label="≈13.1 MB · 绿色版",
        kind="portable",
        filename="CleanBlackboard.exe",
        homepage="https://github.com/Liuyichen27/clean-blackboard",
        note="手写、框选、小黑板、导出 PNG 与工程文件，全部离线可用。",
    ),
    _e(
        id="dupfinder",
        name="dupfinder",
        vendor="自研 · 命令行",
        category="命令行工具",
        desc="三级筛选找重复文件，绝不删任何文件",
        color="#12B76A",
        sources=_release("dupfinder", f"dupfinder-{VERSION}.zip"),
        size_label="≈11 KB · 源码包",
        kind="archive",
        filename=f"dupfinder-{VERSION}.zip",
        homepage="https://github.com/Liuyichen27/dupfinder",
        note="解压后 python -m pip install . 即可，零第三方依赖。",
    ),
    _e(
        id="mdcheck",
        name="mdcheck",
        vendor="自研 · 命令行",
        category="命令行工具",
        desc="Markdown检查：链接、代码块、标题",
        color="#7A5AF8",
        sources=_release("mdcheck", f"mdcheck-{VERSION}.zip"),
        size_label="≈11 KB · 源码包",
        kind="archive",
        filename=f"mdcheck-{VERSION}.zip",
        homepage="https://github.com/Liuyichen27/mdcheck",
        note="零依赖；--toc --write 可以原地更新目录。",
    ),
    _e(
        id="autostart",
        name="autostart",
        vendor="自研 · 命令行",
        category="命令行工具",
        desc="看清开机启动项的真实来源，禁用前先备份",
        color="#F79009",
        sources=_release("autostart", f"autostart-{VERSION}.zip"),
        size_label="≈13 KB · 源码包",
        kind="archive",
        filename=f"autostart-{VERSION}.zip",
        homepage="https://github.com/Liuyichen27/autostart",
        note="只支持 Windows，零依赖（winreg）。",
    ),
    _e(
        id="picslim",
        name="picslim",
        vendor="自研 · 命令行",
        category="命令行工具",
        desc="批量压图片体积，按目标体积自适应",
        color="#0EA5E9",
        sources=_release("picslim", f"picslim-{VERSION}.zip"),
        size_label="≈12 KB · 源码包",
        kind="archive",
        filename=f"picslim-{VERSION}.zip",
        homepage="https://github.com/Liuyichen27/picslim",
        note="需要 Pillow；压不动会直说，不偷偷降质量。",
    ),
    _e(
        id="pdftidy",
        name="pdftidy",
        vendor="自研 · 命令行",
        category="命令行工具",
        desc="合并、拆分、提取、旋转、加密的PDF工具箱",
        color="#F04438",
        sources=_release("pdftidy", f"pdftidy-{VERSION}.zip"),
        size_label="≈13 KB · 源码包",
        kind="archive",
        filename=f"pdftidy-{VERSION}.zip",
        homepage="https://github.com/Liuyichen27/pdftidy",
        note="需要 pypdf；默认 AES-256 加密，环境不支持会明说。",
    ),
    _e(
        id="quickhash",
        name="quickhash",
        vendor="自研 · 命令行",
        category="命令行工具",
        desc="算文件哈希、生成校验文件，零依赖",
        color="#667085",
        sources=_release("quickhash", f"quickhash-{VERSION}.zip"),
        size_label="≈11 KB · 源码包",
        kind="archive",
        filename=f"quickhash-{VERSION}.zip",
        homepage="https://github.com/Liuyichen27/quickhash",
        note="纯标准库；能验发行版给的 SHA256SUMS。",
    ),
]


def own_catalog() -> dict[str, AppEntry]:
    return {a.id: a for a in OWN_APPS}


def by_category(category: str) -> list[AppEntry]:
    if category in ("", "全部"):
        return list(OWN_APPS)
    return [a for a in OWN_APPS if a.category == category]
