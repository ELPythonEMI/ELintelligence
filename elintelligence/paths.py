from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "ELintelligence"


def portable_root() -> Path:
    """Directory che contiene EXE o sorgenti. In modalità USB tutto resta qui."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def is_portable() -> bool:
    return (portable_root() / "PORTABLE.flag").exists() or os.environ.get("ELINTELLIGENCE_PORTABLE") == "1"


def app_data_dir() -> Path:
    if is_portable():
        path = portable_root() / "data"
    else:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def models_dir() -> Path:
    path = app_data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def runtime_dir(backend: str) -> Path:
    path = app_data_dir() / "runtime" / backend.lower()
    path.mkdir(parents=True, exist_ok=True)
    return path


def documents_dir() -> Path:
    path = app_data_dir() / "documents"
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_file() -> Path:
    return app_data_dir() / "settings.json"


def chat_file() -> Path:
    return app_data_dir() / "chat.json"


def rag_file() -> Path:
    return app_data_dir() / "rag_index.json"


def resource_path(relative: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative
    return Path(__file__).resolve().parent.parent / relative
