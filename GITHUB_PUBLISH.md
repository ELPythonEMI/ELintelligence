# Pubblicazione su GitHub

Repository consigliato:

`https://github.com/ELPythonEMI/ELintelligence`

## Primo push

Dalla cartella del progetto:

```bat
git init
git branch -M main
git add .
git status
git commit -m "Initial public release: ELintelligence 1.1.1"
git remote add origin https://github.com/ELPythonEMI/ELintelligence.git
git push -u origin main
```

Prima del commit controlla sempre `git status`: non devono comparire modelli GGUF, cartelle `data`, `runtime`, `documents`, chiavi o file personali.

## Release binaria

L'EXE compilato non va necessariamente committato nel repository. È preferibile pubblicarlo come **GitHub Release** insieme a checksum/versione.

## Topic suggeriti

`local-ai`, `llama-cpp`, `rag`, `gguf`, `windows`, `python`, `pyside6`, `offline-ai`, `local-llm`, `privacy`

## Descrizione repository suggerita

`Local-first Windows AI assistant with GGUF models, RAG Pro, verifiable citations and optional web search.`

## Slogan

`Local AI. Your data. Your control.`
