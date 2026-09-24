from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

import requests

from .downloader import download_file
from .paths import app_data_dir, runtime_dir


@dataclass(frozen=True)
class EngineConfig:
    server_exe: Path
    model: Path
    backend: str
    context_size: int
    max_tokens: int
    gpu_layers: int
    threads: int
    port: int = 11435

    def signature(self) -> tuple:
        return (
            str(self.server_exe.resolve()),
            str(self.model.resolve()),
            self.backend,
            self.context_size,
            self.gpu_layers,
            self.threads,
            self.port,
        )


class RuntimeInstaller:
    RELEASES_URL = "https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=20"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "User-Agent": "ELintelligence-Windows/1.0",
        })

    @staticmethod
    def installed_server(backend: str) -> Path:
        return runtime_dir(backend) / "llama-server.exe"

    def is_installed(self, backend: str) -> bool:
        return self.installed_server(backend).is_file()

    def install(
        self,
        backend: str,
        status: Callable[[str], None] | None = None,
        progress: Callable[[int], None] | None = None,
    ) -> Path:
        backend = backend.lower()
        if backend not in {"cpu", "vulkan"}:
            raise ValueError("Backend installabile non valido")
        status = status or (lambda _x: None)
        progress = progress or (lambda _x: None)

        status("Cerco una release Windows di llama.cpp…")
        response = self.session.get(self.RELEASES_URL, timeout=(20, 30))
        response.raise_for_status()
        releases = response.json()
        if not isinstance(releases, list):
            raise RuntimeError("Risposta GitHub non valida")

        pattern = re.compile(rf"llama-.*-bin-win-{re.escape(backend)}-x64\.zip$", re.I)
        asset = None
        for release in releases:
            for candidate in release.get("assets", []):
                name = str(candidate.get("name") or "")
                if pattern.match(name):
                    asset = candidate
                    break
            if asset:
                break
        if not asset:
            raise RuntimeError(f"Pacchetto llama.cpp Windows {backend.upper()} x64 non trovato")

        target_dir = runtime_dir(backend)
        target_dir.parent.mkdir(parents=True, exist_ok=True)

        # Download/extract outside the active runtime directory. This prevents
        # partially overwriting a working install if Windows has a DLL locked.
        stage_root = target_dir.parent / f".{backend}-install-stage"
        zip_path = target_dir.parent / f".{backend}-runtime-download.zip"
        shutil.rmtree(stage_root, ignore_errors=True)
        zip_path.unlink(missing_ok=True)
        stage_root.mkdir(parents=True, exist_ok=True)

        status(f"Download {asset['name']}…")
        download_file(str(asset["browser_download_url"]), zip_path, progress)
        status("Estrazione runtime…")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(stage_root)

        servers = list(stage_root.rglob("llama-server.exe"))
        if not servers:
            raise RuntimeError("llama-server.exe non trovato nell'archivio scaricato")
        bin_dir = servers[0].parent

        target_dir.mkdir(parents=True, exist_ok=True)
        status("Aggiornamento runtime locale…")

        # llama-server maps ggml*.dll into memory. After stopping it Windows may
        # need a brief moment to release those file handles, so retry removals.
        def remove_with_retry(path: Path) -> None:
            last_exc: Exception | None = None
            for attempt in range(8):
                try:
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink(missing_ok=True)
                    return
                except PermissionError as exc:
                    last_exc = exc
                    time.sleep(0.35 + attempt * 0.15)
            raise PermissionError(
                f"Windows sta ancora usando '{path.name}'. "
                "Chiudi eventuali llama-server.exe dal Task Manager e riprova. "
                f"Dettaglio: {last_exc}"
            )

        for item in list(target_dir.iterdir()):
            remove_with_retry(item)

        try:
            for item in bin_dir.iterdir():
                dest = target_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dest)
        except PermissionError as exc:
            raise PermissionError(
                "Accesso negato durante la copia delle DLL llama.cpp. "
                "Chiudi llama-server.exe/ELintelligence, verifica che antivirus o Controlled Folder Access "
                f"non stiano bloccando la cartella runtime e riprova. Dettaglio: {exc}"
            ) from exc
        finally:
            shutil.rmtree(stage_root, ignore_errors=True)
            zip_path.unlink(missing_ok=True)
        server = target_dir / "llama-server.exe"
        if not server.is_file():
            raise RuntimeError("Installazione runtime incompleta")
        progress(100)
        status(f"Runtime {backend.upper()} installato")
        return server


class LlamaServer:
    def __init__(self) -> None:
        self.process: subprocess.Popen | None = None
        self._config_sig: tuple | None = None
        self._log_handle = None
        self.session = requests.Session()

    @property
    def running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def stop(self) -> None:
        process = self.process
        self.process = None
        self._config_sig = None
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

    def force_stop_all_windows(self) -> str:
        """Stop the managed server and any orphan llama-server.exe process on Windows."""
        self.stop()
        if os.name != "nt":
            return "Server locale arrestato."
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            result = subprocess.run(
                ["taskkill", "/F", "/T", "/IM", "llama-server.exe"],
                capture_output=True,
                text=True,
                errors="replace",
                creationflags=creationflags,
                timeout=10,
            )
            if result.returncode == 0:
                return "llama-server.exe arrestato forzatamente."
            return "Server locale arrestato. Nessun altro llama-server.exe attivo."
        except Exception as exc:
            return f"Server locale arrestato. taskkill non disponibile: {exc}"

    def ensure_started(self, config: EngineConfig, status: Callable[[str], None] | None = None) -> None:
        status = status or (lambda _x: None)
        sig = config.signature()
        if self.running and sig == self._config_sig:
            return
        self.stop()
        if not config.server_exe.is_file():
            raise FileNotFoundError(f"llama-server.exe non trovato: {config.server_exe}")
        if not config.model.is_file():
            raise FileNotFoundError(f"Modello GGUF non trovato: {config.model}")

        args = [
            str(config.server_exe),
            "-m", str(config.model),
            "-c", str(config.context_size),
            "-t", str(config.threads),
            "--host", "127.0.0.1",
            "--port", str(config.port),
            "--n-gpu-layers", "0" if config.backend == "cpu" else str(config.gpu_layers),
        ]
        log_path = app_data_dir() / "llama-server.log"
        self._log_handle = log_path.open("a", encoding="utf-8", errors="ignore")
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        status("Avvio llama-server e caricamento modello…")
        self.process = subprocess.Popen(
            args,
            cwd=str(config.server_exe.parent),
            stdout=self._log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
        self._config_sig = sig

        deadline = time.time() + 150
        url = f"http://127.0.0.1:{config.port}/health"
        last_error = ""
        while time.time() < deadline:
            if self.process.poll() is not None:
                self.stop()
                raise RuntimeError(f"llama-server si è chiuso durante il caricamento. Log: {log_path}")
            try:
                response = self.session.get(url, timeout=2)
                if response.status_code == 200:
                    status("Modello pronto")
                    return
                last_error = response.text[:300]
            except Exception as exc:
                last_error = str(exc)
            time.sleep(0.5)
        self.stop()
        raise TimeoutError(f"Timeout caricamento modello. {last_error}")

    def _chat_payload(
        self,
        config: EngineConfig,
        messages: list[dict],
        temperature: float,
        stream: bool,
    ) -> dict:
        # Keep desktop chat focused on the final answer. Recent llama.cpp builds
        # may expose model thinking separately in reasoning_content (Qwen3 in
        # particular). Disabling it avoids spending the small local token budget
        # on hidden reasoning and makes the visible answer predictable.
        return {
            "model": config.model.name,
            "messages": messages,
            "stream": stream,
            "max_tokens": config.max_tokens,
            "temperature": temperature,
            "reasoning_effort": "none",
            "reasoning_format": "none",
            "chat_template_kwargs": {"enable_thinking": False},
        }

    @staticmethod
    def _extract_visible_text(event: dict) -> str:
        choices = event.get("choices") or []
        if not choices:
            return ""
        choice = choices[0] or {}
        delta = choice.get("delta") or {}
        content = delta.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        # Compatibility with a few llama.cpp / OpenAI-style variants.
        text = delta.get("text")
        return text if isinstance(text, str) else ""

    def _chat_once(
        self,
        config: EngineConfig,
        messages: list[dict],
        temperature: float,
    ) -> str:
        url = f"http://127.0.0.1:{config.port}/v1/chat/completions"
        payload = self._chat_payload(config, messages, temperature, stream=False)
        response = self.session.post(url, json=payload, timeout=(15, 600))
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = (choices[0] or {}).get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts)
        return ""

    def stream_chat(
        self,
        config: EngineConfig,
        messages: list[dict],
        temperature: float = 0.7,
    ) -> Iterator[str]:
        if not self.running:
            raise RuntimeError("llama-server non è avviato")
        url = f"http://127.0.0.1:{config.port}/v1/chat/completions"
        payload = self._chat_payload(config, messages, temperature, stream=True)
        headers = {"Accept": "text/event-stream", "Content-Type": "application/json"}
        visible_parts: list[str] = []
        with self.session.post(
            url,
            json=payload,
            headers=headers,
            stream=True,
            timeout=(15, 600),
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines(decode_unicode=False):
                if not raw_line:
                    continue
                try:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                except AttributeError:
                    line = str(raw_line).strip()
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                content = self._extract_visible_text(event)
                if content:
                    visible_parts.append(content)
                    yield content

        # Some model/template combinations can finish a streaming request with
        # no visible delta at all. Retry once synchronously instead of leaving
        # the UI with only search sources.
        if not visible_parts:
            fallback = self._chat_once(config, messages, temperature).strip()
            if fallback:
                yield fallback

