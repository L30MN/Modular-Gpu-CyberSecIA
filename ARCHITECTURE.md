# Architecture

## Goal

Separate the **permanent infrastructure** from the **computational power**:

```
┌─────────────────── Local machine (permanent) ───────────────────┐
│                                                                  │
│   Open WebUI  (Docker, persistent volume)                        │
│     ├── Chat interface                                           │
│     ├── Knowledge base + collections                             │
│     ├── Vector database (embeddings)                             │
│     └── Configuration, prompts, workflows                        │
│                                                                  │
│   Ollama (local)  →  nomic-embed-text   [EMBEDDINGS, CPU]        │
│                                                                  │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                │  OpenAI-compatible API
                                │  (one endpoint + key to change)
                                │
                  ┌─────────────┴──────────────┐
                  │   Remote GPU (disposable)   │
                  │   vLLM  →  large chat LLM    │
                  │   Oracle A10 / Vast.ai 4090  │
                  └──────────────────────────────┘
```

### Key design decisions

1. **Embeddings stay local, on CPU.**
   RAG retrieval requires that every query be embedded with the *same* model
   that built the vector database. If embeddings ran on the remote GPU, the
   knowledge base would depend on that GPU being online, and swapping providers
   could break compatibility. `nomic-embed-text` is tiny (~274 MB) and runs fine
   on CPU, so it stays local. The remote GPU only runs the large chat model.

2. **OpenAI-compatible API as the integration contract.**
   Open WebUI talks to the remote inference server through the OpenAI-compatible
   API (`OPENAI_API_BASE_URL` + key). Both vLLM and Ollama expose this interface,
   so changing GPU provider means changing one endpoint — no rebuild.

3. **vLLM preferred on the GPU side.**
   For A10 / RTX 4090 class GPUs, vLLM gives higher throughput and better memory
   management than Ollama, and is natively OpenAI-compatible. Ollama remains a
   valid simpler fallback.

4. **All project state lives locally.**
   The GPU is stateless and disposable. Everything worth keeping — data, config,
   knowledge base — is on the local machine and backed up.

## Environment audit (2026-11-01)

### Current state

| Component | State |
|---|---|
| Docker | 29.9.2 + Compose v5.6.1 |
| Open WebUI | image `open-webui:main`, container on port 3000 |
| Startup | manual `docker run` (no compose file) |
| Ollama | 0.40.13 (host) |
| Models | `dolphin3:8b` (chat), `nomic-embed-text` (embedding) |
| Active embedding | Ollama → `nomic-embed-text` via `host.docker.internal:11434` |
| RAG | OWASP WSTG loaded (168 Markdown files); Top K = 3; hybrid search OFF |
| Remote backend | not yet configured (`OPENAI_API_BASE_URL` empty) |

### Problems identified

1. **No data persistence (critical).**
   `docker volume ls` is empty and the container has no mounts. All data lives in
   the container's ephemeral writable layer. It survives a restart but is
   **destroyed** by `docker rm`, a recreate, or an image update. Fixed by
   migrating to a named volume (see `MIGRATION.md`).

2. **No `docker-compose.yml`.**
   The container was started by hand, so the deployment is not reproducible or
   version-controllable.

3. **Weak RAG retrieval.**
   Top K = 3 and hybrid search disabled cause relevant chunks to be missed on
   specific queries. Tuning deferred (not blocking the infrastructure work).

### Components to keep (working)

- Docker + Open WebUI — do not reinstall.
- Ollama + both models.
- Local CPU embedding pipeline — already matches the target architecture.

## Lessons learned during setup

- **Ollama must listen on all interfaces** for the Docker container to reach it:
  set `OLLAMA_HOST=0.0.0.0` on the host, then restart Ollama.
- **A corrupted embedding model** loads into memory but hangs forever on
  inference, with no error. Symptom: `/api/embed` never returns. Fix:
  `ollama rm nomic-embed-text && ollama pull nomic-embed-text`.
- **Raw STIX JSON (e.g. MITRE `enterprise-attack.json`) is a poor RAG source.**
  It is built for machines, full of IDs and UUIDs. Convert to small, readable
  Markdown files (one per technique) for good retrieval quality.
- **Always verify the cited source.** If an answer has no citation, the model
  answered from memory and may be wrong.
