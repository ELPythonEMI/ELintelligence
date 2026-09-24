# Contributing to ELintelligence

Thanks for contributing.

## Before opening an issue

Please include:

- Windows version
- ELintelligence version / commit
- Python version if running from source
- selected llama.cpp backend (CPU / Vulkan / custom)
- selected GGUF model
- exact error message or log excerpt
- steps to reproduce

Do not attach API keys, private documents, chat history or populated RAG indexes.

## Pull requests

1. Fork the repository.
2. Create a feature/fix branch.
3. Keep changes focused and readable.
4. Run a syntax check before submitting:

```bat
python -m compileall -q elintelligence main.py
```

5. Describe what changed and how it was tested.

## Scope

Useful contributions include:

- Windows UI/UX improvements
- RAG quality and citation accuracy
- llama.cpp runtime compatibility
- local model management
- privacy/security improvements
- documentation

Please avoid adding mandatory cloud services or paid APIs to core functionality.
