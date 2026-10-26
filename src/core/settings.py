"""用户设置持久化。"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .paths import data_root, default_download_dir


@dataclass
class Settings:
    download_dir: str = ""
    language: str = "zh"            # zh | en | system
    theme: str = "light"            # light | dark | system
    auto_install: bool = True       # 下载完成后自动静默安装
    auto_launch: bool = False       # 安装完成后启动软件
    delete_after_install: bool = False
    max_connections: int = 16       # 单服务器最大连接数（分片加速）
    split: int = 16                 # 分片数
    p2p_enabled: bool = True        # 启用 BitTorrent / DHT
    bt_port: int = 6881
    catalog_url: str = ""           # 自定义远程清单地址
    last_selected: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.download_dir:
            self.download_dir = str(default_download_dir())

    @property
    def download_path(self) -> Path:
        p = Path(self.download_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def path(cls) -> Path:
        return data_root() / "settings.json"

    @classmethod
    def load(cls) -> "Settings":
        file = cls.path()
        if not file.exists():
            return cls()
        try:
            raw: dict[str, Any] = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in raw.items() if k in known})

    def save(self) -> None:
        """原子写：先写 .tmp 再 replace。

        直接 write_text 覆盖时，如果写一半崩溃/断电，settings.json 会变成
        半截 JSON，下次启动 load() 解析失败就退回全部默认值——用户的下载
        目录、主题、语言全丢。replace 是原子操作，要么旧的要么新的。
        """
        file = self.path()
        tmp = file.with_suffix(".json.tmp")
        try:
            tmp.write_text(
                json.dumps(asdict(self), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp.replace(file)
        except OSError:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
