# Security policy

## Reporting a vulnerability

Please do not publish sensitive security details, credentials or personal documents in a public issue.

For ordinary bugs that do not expose secrets or user data, open a GitHub issue with a minimal reproduction.

## Secrets

ELintelligence must never commit or bundle:

- API keys
- personal documents
- chat history
- populated RAG indexes
- private model files
- Windows credential-store exports

The repository `.gitignore` blocks the most common generated/sensitive paths, but contributors should still review `git status` before every commit.

## Local service

llama.cpp is started as a local service and should normally bind only to loopback (`127.0.0.1`). Do not expose the local inference server to untrusted networks without understanding the security implications.
