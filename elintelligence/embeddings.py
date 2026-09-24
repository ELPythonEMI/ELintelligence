from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests

from .downloader import download_file
from .paths import app_data_dir, models_dir


EMBEDDING_MODEL_NAME = "BGE-M3 Q4_K_M"
EMBEDDING_MODEL_FILE = "bge-m3-Q4_K_M.gguf"
EMBEDDING_MODEL_URL = (
    "https://huggingface.co/lm-kit/bge-m3-gguf/resolve/main/"
    "bge-m3-Q4_K_M.gguf?download=true"
)
EMBEDDING_MODEL_APPROX_MB = 438


def embedding_model_path() -> Path:
    return models_dir() / EMBEDDING_MODEL_FILE


def embedding_model_installed() -> bool:
    path = embedding_model_path()
    return path.is_file() and path.stat().st_size > 50 * 1024 * 1024


def download_embedding_model(progress: Callable[[int], None] | None = None) -> Path:
    return download_file(EMBEDDING_MODEL_URL, embedding_model_path(), progress)


@dataclass(frozen=True)
class EmbeddingConfig:
    server_exe: Path
    backend: str
    gpu_layers: int
    threads: int
    port: int
    model: Path = embedding_model_path()


class EmbeddingSession:
    """Small temporary llama-server dedicated to dense embeddings.

    The process is started only while indexing/searching and is stopped again
    afterwards. This keeps the feature independent from Python ML frameworks and
    reuses the llama.cpp runtime already installed by ELintelligence.
    """

    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config
        self.process: subprocess.Popen | None = None
        self._log_handle = None
        self.session = requests.Session()

    def __enter__(self) -> "EmbeddingSession":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    def start(self, status: Callable[[str], None] | None = None) -> None:
        status = status or (lambda _x: None)
        if self.process is not None and self.process.poll() is None:
            return
        if not self.config.server_exe.is_file():
            raise FileNotFoundError(f"llama-server.exe non trovato: {self.config.server_exe}")
        if not self.config.model.is_file():
            raise FileNotFoundError(
                "Modello embeddings RAG Pro non installato. Premi 'RAG Pro' per scaricarlo."
            )

        args = [
            str(self.config.server_exe),
            "-m", str(self.config.model),
            "--embedding",
            "--pooling", "mean",
            "-c", "2048",
            "-b", "2048",
            "-ub", "2048",
            "-t", str(max(1, self.config.threads)),
            "--host", "127.0.0.1",
            "--port", str(self.config.port),
            "--no-webui",
            "--n-gpu-layers", "0" if self.config.backend == "cpu" else str(self.config.gpu_layers),
        ]
        log_path = app_data_dir() / "rag-embedding-server.log"
        self._log_handle = log_path.open("a", encoding="utf-8", errors="ignore")
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        status("Caricamento modello embeddings RAG Pro…")
        self.process = subprocess.Popen(
            args,
            cwd=str(self.config.server_exe.parent),
            stdout=self._log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )

        deadline = time.time() + 150
        health = f"http://127.0.0.1:{self.config.port}/health"
        last_error = ""
        while time.time() < deadline:
            if self.process.poll() is not None:
                self.stop()
                raise RuntimeError(f"Server embeddings terminato durante il caricamento. Log: {log_path}")
            try:
                response = self.session.get(health, timeout=2)
                if response.status_code == 200:
                    status("RAG Pro pronto")
                    return
                last_error = response.text[:250]
            except Exception as exc:
                last_error = str(exc)
            time.sleep(0.4)
        self.stop()
        raise TimeoutError(f"Timeout caricamento embeddings. {last_error}")

    def stop(self) -> None:
        process = self.process
        self.process = None
        if process is not None and process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=3)
            except Exception:
                try:
                    process.kill()
                except Exception:
                    pass
        if self._log_handle is not None:
            try:
                self._log_handle.close()
            except Exception:
                pass
            self._log_handle = None

    def embed_many(
        self,
        texts: list[str],
        status: Callable[[str], None] | None = None,
        batch_size: int = 8,
    ) -> list[list[float]]:
        if not texts:
            return []
        if self.process is None or self.process.poll() is not None:
            self.start(status)
        status = status or (lambda _x: None)
        url = f"http://127.0.0.1:{self.config.port}/v1/embeddings"
        output: list[list[float]] = []
        total = len(texts)
        for start in range(0, total, max(1, batch_size)):
            batch = texts[start:start + batch_size]
            status(f"Embeddings {min(start + len(batch), total)}/{total}…")
            response = self.session.post(
                url,
                json={
                    "input": batch,
                    "model": self.config.model.name,
                    "encoding_format": "float",
                },
                timeout=(15, 300),
            )
            response.raise_for_status()
            data = response.json()
            rows = data.get("data") if isinstance(data, dict) else None
            if not isinstance(rows, list):
                raise RuntimeError("Risposta embeddings non valida")
            rows = sorted(rows, key=lambda item: int(item.get("index", 0)))
            vectors = [item.get("embedding") for item in rows]
            if len(vectors) != len(batch) or any(not isinstance(v, list) for v in vectors):
                raise RuntimeError("Numero di embeddings restituiti non valido")
            output.extend([[float(x) for x in vector] for vector in vectors])
        return output
