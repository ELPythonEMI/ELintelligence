from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from .paths import chat_file


@dataclass
class ChatMessage:
    role: str
    text: str
    sources: list[dict] | None = None


class ChatStore:
    def load(self) -> list[ChatMessage]:
        path = chat_file()
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return [ChatMessage(**item) for item in raw if isinstance(item, dict)]
        except Exception:
            return []

    def save(self, items: list[ChatMessage]) -> None:
        trimmed = items[-40:]
        chat_file().write_text(
            json.dumps([asdict(x) for x in trimmed], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def clear(self) -> None:
        try:
            chat_file().unlink(missing_ok=True)
        except Exception:
            pass
