from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from .paths import models_dir


@dataclass(frozen=True)
class ModelPreset:
    id: str
    label: str
    url: str
    filename: str
    approx_gb: float
    context: int
    max_tokens: int
    high_memory: bool

    @property
    def path(self) -> Path:
        return models_dir() / self.filename


GEMMA = ModelPreset(
    id="gemma4-e2b",
    label="Gemma 4 E2B IT QAT · UD-Q4_K_XL",
    url=(
        "https://huggingface.co/unsloth/gemma-4-E2B-it-qat-GGUF/resolve/main/"
        "gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf?download=true"
    ),
    filename="gemma-4-E2B-it-qat-UD-Q4_K_XL.gguf",
    approx_gb=2.62,
    context=4096,
    max_tokens=512,
    high_memory=True,
)

QWEN = ModelPreset(
    id="qwen3-06b",
    label="Qwen3 0.6B Lite · Q4_0",
    url=(
        "https://huggingface.co/ggml-org/Qwen3-0.6B-GGUF/resolve/main/"
        "Qwen3-0.6B-Q4_0.gguf?download=true"
    ),
    filename="Qwen3-0.6B-Q4_0.gguf",
    approx_gb=0.43,
    context=4096,
    max_tokens=512,
    high_memory=False,
)

CATALOG = (GEMMA, QWEN)


def preset_by_id(model_id: str | None) -> ModelPreset | None:
    return next((m for m in CATALOG if m.id == model_id), None)
