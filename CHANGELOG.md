# ELintelligence GitHub Clean 1.1.3

- README repositioned around the project mission: local AI for modest/non-high-end Windows PCs.
- Large centered project logo added to the README header.
- Added a dedicated “Built for modest hardware” section explaining quantized GGUF, CPU/Vulkan, small-model presets and low-resource RAG fallbacks.
- Removed Python `__pycache__` / bytecode artifacts from the public package.

# Changelog

## 1.1.1 — GitHub / portable-ready

- Clean public-repository layout.
- Windows-only Python/PySide6 desktop application.
- Local GGUF inference through llama.cpp.
- RAG Pro: BM25 + optional BGE-M3 embeddings.
- PDF page-aware citations and source excerpts.
- Clickable web and RAG sources.
- Incremental folder indexing.
- Direct web search plus optional Brave Search.
- Compact/resizable controls and local chat streaming.
- Portable USB mode supported through `PORTABLE.flag`.
- Runtime, models, indexes, histories and secrets are excluded from the public repository.
