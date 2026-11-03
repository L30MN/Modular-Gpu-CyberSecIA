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

## Knowledge base

The RAG knowledge base is built from four public security sources, each kept as a
separate collection of small Markdown files (converted from their machine-readable
originals by the scripts in `scripts/`):

| Collection | Source format | Viewpoint it adds |
|---|---|---|
| **OWASP WSTG** | Markdown | How to *test* a weakness in a web app |
| **CWE** | XML | The *flaw in the code*, with examples and fixes |
| **CAPEC** | STIX JSON | How an attacker *exploits* it (attack pattern) |
| **MITRE ATT&CK** | STIX JSON | Where it fits in a *real-world attack*, and which groups use it |

The collections overlap on purpose: they describe the same topics from different
angles, and cross-reference each other (CAPEC-66 → CWE-89 → OWASP SQL-injection
testing). The embedding model and vector dimensions are fixed; changing the
embedding model would require rebuilding every collection.

## Agents and the execution model

Agents are **not models**. An agent is a configuration — a system prompt, a set of
attached knowledge collections, and a set of callable tools — that *uses* a model.
Agents are defined in Open WebUI (custom models) and therefore live in the **local
persistent layer**, independent of the GPU. One strong tool-calling model on the
GPU can power many specialised agents; swapping the GPU does not touch them.

The model that backs the agents must support **native function calling**
reliably. This is in tension with "uncensored": crude abliterated fine-tunes often
degrade tool-calling. The chosen model must be verified on real tool schemas, not
picked from a ranking.

When an agent acts on a lab, work runs in **three modular layers**:

```
Remote GPU (brain)        decides which tool to call, with which arguments
      │  OpenAI-compatible API
Local PC (orchestration)  Open WebUI runs the tool code (a thin wrapper)
      │  SSH
Lab VM (hands)            the command actually runs here, contained
```

The offensive tooling (nmap, etc.) stays **inside an isolated lab VM**; the tool on
the PC is a thin SSH wrapper that runs the command there and returns the output.
Swapping the lab (VirtualBox today, a cloud VM tomorrow) means changing the SSH
target — the same "change one endpoint" principle as swapping the GPU.

**Safety constraints:** tools act only on lab VMs the user owns or is authorised to
test, on an isolated (host-only / internal) network; early agents propose commands
for manual confirmation rather than executing autonomously. This belongs to a later
phase — the prerequisite is a verified tool-calling model.

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
