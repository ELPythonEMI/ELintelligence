<p align="center">
  <img src="assets/icon.png" alt="ELintelligence logo" width="180">
</p>

<h1 align="center">ELintelligence</h1>

<p align="center"><strong>Local AI. Your data. Your control.</strong></p>

ELintelligence is a local-first AI assistant for Windows designed with a specific goal: **make useful local AI accessible on modest and non-high-end PCs**, not only on expensive AI workstations.

It uses Python, PySide6 and llama.cpp to run compatible quantized GGUF models locally, supports document RAG with verifiable citations, and can optionally use web search without requiring a paid AI subscription.

The project favors efficient configurations, smaller quantized models, CPU/Vulkan execution and graceful fallbacks so users can choose a balance between speed, memory usage and response quality.


## Built for modest hardware

ELintelligence was created for people who want to experiment with and use local AI **without needing a top-tier GPU or a high-end workstation**.

The application is designed around practical resource-saving choices:

- quantized **GGUF** models instead of full-precision weights
- small-model presets such as **Qwen3 0.6B** for low-memory systems
- optional higher-quality models when the hardware can handle them
- **CPU** inference for maximum compatibility
- **Vulkan** acceleration on supported GPUs without requiring CUDA
- configurable context size, token limit, thread count and GPU layers
- BM25-only RAG fallback when semantic embeddings would use too many resources
- optional BGE-M3 embeddings rather than a mandatory second model
- no mandatory cloud inference or paid token API

Hardware requirements still depend on the model you select. A very small quantized model can run on considerably weaker hardware than a multi-billion-parameter model, so ELintelligence exposes model/runtime choices instead of assuming one hardware profile fits everyone.

## Highlights

- **Local GGUF inference** through `llama-server.exe`
- **Gemma / Qwen presets** plus custom GGUF import
- **RAG Pro** with BM25 + optional local BGE-M3 embeddings
- **PDF page citations** such as `D1 · manual.pdf · page 12`
- **Clickable web and document sources**
- **Folder indexing** with incremental refresh
- **Direct web search** without an API key, plus optional Brave Search
- **Streaming responses** from the local model
- **CPU / Vulkan** runtime support, with custom llama.cpp runtime selection
- **Portable USB mode** that can keep models, runtime, RAG index and settings beside the executable
- Cyberpunk-style Windows UI

## Privacy model

By default, model inference and RAG processing are local.

```text
Prompt / local documents
        ↓
ELintelligence
        ↓
llama.cpp on localhost
        ↓
Local GGUF model
```

When web search is enabled, the search query is sent to the selected search provider. Local documents and the final LLM inference do not need to be sent to a cloud AI provider.

## Requirements

- Windows 10 or Windows 11 x64
- Python 3.12 recommended for development
- Internet connection only for downloads and optional web search
- Enough RAM/VRAM for the selected GGUF model

## Quick start from source

```bat
git clone https://github.com/ELPythonEMI/ELintelligence.git
cd ELintelligence
RUN_DEV.bat
```

`RUN_DEV.bat` creates a virtual environment and installs the Python dependencies automatically.

Or manually:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

## Build the Windows executable

```bat
BUILD_EXE.bat
```

Default output:

```text
dist\ELintelligence\ELintelligence.exe
```

To build a one-file executable you can run the PowerShell build script with `-OneFile`.

## Portable / USB build

```bat
BUILD_USB_PORTABLE.bat
```

The script creates `USB_READY` containing the executable, a `PORTABLE.flag` and an empty `data` folder. When `PORTABLE.flag` is present, ELintelligence keeps its runtime data beside the executable instead of using `%LOCALAPPDATA%`.

If you already have a local installation and want to copy its data to the portable folder, use:

```bat
MIGRA_DA_PC_A_USB.bat
```

## RAG Pro

ELintelligence can index:

- PDF
- TXT
- Markdown
- HTML
- CSV
- LOG

PDF files are indexed page by page. When a response uses a PDF chunk, the UI can show a citation such as:

```text
D1 · technical_manual.pdf · page 12
```

The source can include the retrieved excerpt and can be opened from the interface.

### Hybrid retrieval

RAG Pro combines lexical retrieval with optional semantic embeddings:

1. BM25 finds keyword/technical matches.
2. BGE-M3 can generate embeddings locally through llama.cpp.
3. Scores are combined and filtered.
4. Only the most relevant chunks are sent to the chat model.
5. The UI shows sources that were actually cited whenever possible.

If the embedding model is not installed, RAG automatically falls back to BM25.

## Models

Model files are **not included in this repository**. ELintelligence can download supported presets or use your own GGUF file.

Current presets include:

- Gemma 4 E2B IT QAT (GGUF)
- Qwen3 0.6B (GGUF)
- BGE-M3 (optional embedding model for RAG Pro)

The current preset repositories are Apache-2.0 for the Gemma 4 and Qwen3 GGUF downloads, and MIT for the BGE-M3 GGUF download. Model files are not included here; always review the exact repository terms before redistributing weights. See `THIRD_PARTY.md`.

## Repository safety

Do **not** commit runtime data or personal content. The included `.gitignore` excludes common sensitive/generated files, including:

```text
PORTABLE.flag
data/
models/
runtime/
documents/
*.gguf
rag_index.json
chat.json
settings.json
.env*
```

Never commit API keys, personal documents, chat history or a populated RAG index.

## Project structure

```text
ELintelligence/
├── assets/              # icon and UI assets
├── elintelligence/      # application source
├── scripts/             # build / run / portable helpers
├── main.py
├── requirements.txt
├── pyproject.toml
├── BUILD_EXE.bat
├── BUILD_USB_PORTABLE.bat
├── RUN_DEV.bat
├── LICENSE
├── THIRD_PARTY.md
└── README.md
```

## License

ELintelligence source code is released under **GNU GPL-3.0-only**. See `LICENSE`.

Third-party software and model weights remain under their own licenses. See `THIRD_PARTY.md`.

### Binary releases and third-party notices

This repository does not contain prebuilt third-party runtimes or model weights. If you publish a Windows executable built with PyInstaller, review and preserve the license notices for the exact Python/Qt packages bundled in that release. See `THIRD_PARTY.md`.

## Disclaimer

ELintelligence is an independent open-source project and is not affiliated with Google, Qwen/Alibaba, BAAI, DuckDuckGo, Brave or the llama.cpp project.

AI-generated output can be incomplete or incorrect. For important information, verify the answer against the cited original source.

## Contributing

Bug reports, feature requests and pull requests are welcome. See `CONTRIBUTING.md`.
