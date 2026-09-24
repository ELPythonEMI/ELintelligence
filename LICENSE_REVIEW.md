# License review — 2026-09-24

This project-level review is intended as a practical publication checklist, not legal advice.

## Source repository status

No known direct-license conflict was identified for publishing ELintelligence source under `GPL-3.0-only` with the currently declared direct dependencies.

Verified direct dependency/model license families:

- PySide6 / Qt for Python: LGPLv3 / GPLv3 / commercial options
- requests: Apache-2.0
- Beautiful Soup 4: MIT
- pypdf: BSD-3-Clause
- keyring: MIT
- llama.cpp: MIT
- PyInstaller: GPL-2.0 with bootloader exception (plus Apache-2.0 for some files)
- unsloth/gemma-4-E2B-it-qat-GGUF: Apache-2.0
- ggml-org/Qwen3-0.6B-GGUF: Apache-2.0
- lm-kit/bge-m3-gguf: MIT

## Not included in the source repository

Do not commit:

- GGUF model weights
- llama.cpp runtime binaries
- Python virtual environments / installed wheels
- API keys
- personal documents
- chat history
- populated RAG indexes

## Before publishing a prebuilt EXE

A binary produced with PyInstaller bundles additional third-party components. Re-check the exact dependency set and include the required notices/license texts for the versions shipped. Qt/PySide6 redistribution obligations deserve particular attention.

## Separate issues

Open-source licensing does not automatically resolve:

- trademarks / project naming
- privacy-law obligations
- third-party web-service terms
- model acceptable-use policies, if any
- security/export/compliance requirements in a particular jurisdiction
