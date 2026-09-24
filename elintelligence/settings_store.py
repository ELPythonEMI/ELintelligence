from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path

from .paths import settings_file


@dataclass
class AppSettings:
    backend: str = "vulkan"  # cpu | vulkan | custom
    custom_server: str = ""
    active_model_id: str = "qwen3-06b"
    custom_model: str = ""
    context_size: int = 4096
    max_tokens: int = 512
    gpu_layers: int = 99
    threads: int = max(2, (os.cpu_count() or 4) - 1)
    port: int = 11435
    web_enabled: bool = False
    web_engine: str = "direct"  # direct | brave
    rag_enabled: bool = False
    sidebar_collapsed: bool = False
    sidebar_width: int = 210
    watched_folders: list[str] = field(default_factory=list)


class SettingsStore:
    def load(self) -> AppSettings:
        path = settings_file()
        if not path.exists():
            return AppSettings()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            defaults = asdict(AppSettings())
            defaults.update({k: v for k, v in raw.items() if k in defaults})
            return AppSettings(**defaults)
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        path = settings_file()
        path.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")
