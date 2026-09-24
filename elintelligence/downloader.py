from __future__ import annotations

from pathlib import Path
from typing import Callable
import requests


def download_file(url: str, destination: Path, progress: Callable[[int], None] | None = None) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    headers = {"User-Agent": "ELintelligence-Windows/1.0"}
    with requests.get(url, stream=True, timeout=(30, 120), allow_redirects=True, headers=headers) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", "0") or 0)
        done = 0
        with partial.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                fh.write(chunk)
                done += len(chunk)
                if progress and total > 0:
                    progress(min(100, int(done * 100 / total)))
    partial.replace(destination)
    if progress:
        progress(100)
    return destination
