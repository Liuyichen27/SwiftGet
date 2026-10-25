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

VERSION = "1.1.0"
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
        usage="双击 CleanBlackboard.exe 就能写 · Ctrl+S 存工程 / Ctrl+E 导 PNG",
    ),
    _e(
        id="dupfinder",
        name="dupfinder",
        vendor="自研 · 命令行",
        category="命令行工具",
        desc="三级筛选找重复文件，绝不删任何文件",
        color="#12B76A",
        sources=_release("dupfinder", f"dupfinder-{VERSION}.zip"),
        size_label="≈14 KB · 源码包",
        kind="archive",
        filename=f"dupfinder-{VERSION}.zip",
        homepage="https://github.com/Liuyichen27/dupfinder",
        note="三级筛选：按大小分桶 → 头部取样 → 全文哈希，6 万文件几秒扫完。\n只出报告，宁可少报也不误删。",
        usage="pip install .  →  dupfinder D:/照片 D:/备份",
    ),
    _e(
        id="mdcheck",
        name="mdcheck",
        vendor="自研 · 命令行",
        category="命令行工具",
        desc="Markdown检查：链接、代码块、标题",
        color="#7A5AF8",
        sources=_release("mdcheck", f"mdcheck-{VERSION}.zip"),
        size_label="≈14 KB · 源码包",
        kind="archive",
        filename=f"mdcheck-{VERSION}.zip",
        homepage="https://github.com/Liuyichen27/mdcheck",
        note="查七项：代码块未闭合、本地链接/图片失效、标题层级跳跃、多个 H1、\n锚点对不上、空链接。零依赖，--toc --write 原地更新目录。",
        usage="pip install .  →  mdcheck . --toc --write",
    ),
    _e(
        id="autostart",
        name="autostart",
        vendor="自研 · 命令行",
        category="命令行工具",
        desc="看清开机启动项的真实来源，禁用前先备份",
        color="#F79009",
        sources=_release("autostart", f"autostart-{VERSION}.zip"),
        size_label="≈15 KB · 源码包",
        kind="archive",
        filename=f"autostart-{VERSION}.zip",
        homepage="https://github.com/Liuyichen27/autostart",
        note="摊开三处真实来源：HKCU Run、HKLM Run、启动文件夹；\n每条带完整命令，禁用前自动备份，随时还原。仅 Windows，零依赖。",
        usage="pip install .  →  autostart list",
    ),
    _e(
        id="picslim",
        name="picslim",
        vendor="自研 · 命令行",
        category="命令行工具",
        desc="批量压图片体积，按目标体积自适应",
        color="#0EA5E9",
        sources=_release("picslim", f"picslim-{VERSION}.zip"),
        size_label="≈18 KB · 源码包",
        kind="archive",
        filename=f"picslim-{VERSION}.zip",
        homepage="https://github.com/Liuyichen27/picslim",
        note="先降质量，降到下限还超标才缩尺寸；只读原图，结果写到另一个目录，\n绝不覆盖源文件。需要 Pillow。",
        usage="pip install .  →  picslim ./照片 -o ./压缩后 --max-size 500K",
    ),
    _e(
        id="pdftidy",
        name="pdftidy",
        vendor="自研 · 命令行",
        category="命令行工具",
        desc="合并、拆分、提取、旋转、加密的PDF工具箱",
        color="#F04438",
        sources=_release("pdftidy", f"pdftidy-{VERSION}.zip"),
        size_label="≈20 KB · 源码包",
        kind="archive",
        filename=f"pdftidy-{VERSION}.zip",
        homepage="https://github.com/Liuyichen27/pdftidy",
        note="八个子命令覆盖日常操作；默认 AES-256，加密库缺失时退回 RC4-128 并明说。\n不修改源文件。需要 pypdf。",
        usage="pip install .  →  pdftidy merge a.pdf b.pdf -o 合并.pdf",
    ),
    _e(
        id="quickhash",
        name="quickhash",
        vendor="自研 · 命令行",
        category="命令行工具",
        desc="算文件哈希、生成校验文件，零依赖",
        color="#667085",
        sources=_release("quickhash", f"quickhash-{VERSION}.zip"),
        size_label="≈17 KB · 源码包",
        kind="archive",
        filename=f"quickhash-{VERSION}.zip",
        homepage="https://github.com/Liuyichen27/quickhash",
        note="输出格式与 coreutils sha256sum 完全一致，能验发行版的 SHA256SUMS，\n别人也能用 sha256sum -c 验你的。1 MB 流式读取，纯标准库。",
        usage="pip install .  →  quickhash 镜像.iso --save SHA256SUMS",
    ),
]


def own_catalog() -> dict[str, AppEntry]:
    return {a.id: a for a in OWN_APPS}


def by_category(category: str) -> list[AppEntry]:
    if category in ("", "全部"):
        return list(OWN_APPS)
    return [a for a in OWN_APPS if a.category == category]
