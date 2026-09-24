# Third-party software, services and models

ELintelligence is an independent project. This source repository does **not** vendor model weights, llama.cpp runtime binaries, Python wheels, or user data. Third-party software, services and model weights remain subject to their own licenses and terms.

This file documents the **direct dependencies and exact model repositories referenced by ELintelligence**. Transitive dependencies installed by `pip` retain their own licenses.

## Project license

ELintelligence source code is distributed under **GNU GPL-3.0-only**. See `LICENSE`.

## Python / UI / packaging

- **Python** — Python Software Foundation License (PSF-2.0 family). https://www.python.org/psf/license/
- **PySide6 / Qt for Python** — Qt for Python Community Edition is available under LGPLv3/GPLv3; commercial licensing is also available from Qt. https://doc.qt.io/qtforpython-6/
- **requests** — Apache-2.0. https://github.com/psf/requests
- **Beautiful Soup 4 (`beautifulsoup4`)** — MIT. https://www.crummy.com/software/BeautifulSoup/
- **pypdf** — BSD-3-Clause. https://github.com/py-pdf/pypdf
- **keyring** — MIT. https://github.com/jaraco/keyring
- **PyInstaller** — GPL-2.0 with the PyInstaller bootloader exception, plus Apache-2.0 for certain files. The exception permits distributing executables produced by PyInstaller under the application's license, subject to dependency licenses. https://pyinstaller.org/en/stable/license.html

The GPL-3.0-only license of ELintelligence is compatible with the direct permissive dependencies above and with LGPLv3 components. Third-party libraries remain under their own licenses.

## Local inference runtime

- **llama.cpp** — MIT. https://github.com/ggml-org/llama.cpp

ELintelligence does not include llama.cpp binaries in this source repository. The application may download an official Windows build separately at runtime, or the user may select an existing `llama-server.exe`.

## Model weights referenced by the application

Model weights are **not included** in this repository.

The current preset download URLs point to these exact repositories:

- **Gemma 4 E2B IT QAT — Unsloth GGUF quantization**  
  Repository: `unsloth/gemma-4-E2B-it-qat-GGUF`  
  Repository metadata license: **Apache-2.0**  
  https://huggingface.co/unsloth/gemma-4-E2B-it-qat-GGUF

- **Qwen3 0.6B — ggml-org GGUF quantization**  
  Repository: `ggml-org/Qwen3-0.6B-GGUF`  
  Repository metadata license: **Apache-2.0**  
  https://huggingface.co/ggml-org/Qwen3-0.6B-GGUF

- **BGE-M3 — LM-Kit GGUF quantization**  
  Repository: `lm-kit/bge-m3-gguf`  
  Repository metadata license: **MIT**  
  https://huggingface.co/lm-kit/bge-m3-gguf

Users who replace these presets or redistribute model files must check the license and terms of the **exact model/quantization repository** they use. ELintelligence does not grant rights to third-party model weights.

## Web search providers

- Direct web-search mode accesses public web-search result pages. Use remains subject to the selected provider's current terms, technical restrictions and acceptable-use rules.
- **Brave Search API** support is optional and subject to Brave's API terms and pricing.

Provider terms are separate from open-source software licenses and may change independently of this repository.

## Binary releases

Publishing this **source repository** is different from distributing a prebuilt Windows executable.

A Windows executable produced with PyInstaller can contain Python, Qt/PySide6 and transitive Python dependencies. Before publishing prebuilt binaries, preserve the applicable third-party copyright/license notices and comply with the redistribution conditions of the exact versions bundled in that build.

For Qt/PySide6 in particular, review the LGPLv3/GPLv3 obligations for the distribution method you choose. Keeping the application GPL-3.0-only does not remove the requirement to preserve third-party license notices.

## Trademarks / affiliation

Third-party project, provider and model names are used only to identify compatible software/services/models. ELintelligence is not affiliated with or endorsed by Google, Unsloth, Qwen/Alibaba, BAAI, LM-Kit, Qt, Brave, DuckDuckGo or the llama.cpp project.
