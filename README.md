# Modular Remote GPU AI Infrastructure

A self-hosted, privacy-first AI assistant for cybersecurity study (pentesting,
OWASP, MITRE ATT&CK, CWE/CAPEC) built around a **modular architecture**: the
infrastructure (chat UI, knowledge base, RAG, vector database) lives permanently
on a local machine, while **GPU compute is a swappable, disposable resource**
reached over a standardized API.

The guiding principle: *the GPU is an engine you can swap, not the place where
the project lives.*

> **About this project.** This is my first end-to-end project. I have been studying
> cybersecurity and AI for roughly two months, and I am building it in the open to
> learn: documenting every decision and every dead end rather than hiding the rough
> edges. Expect the perspective of a beginner trying to do things properly, not that
> of a seasoned professional — feedback is welcome.

## Why this design

Running large language models needs a powerful GPU. Renting one in the cloud is
cheap and flexible — but you don't want your data, your knowledge base, or your
configuration trapped on a rented machine that you destroy at the end of the day.

So this project splits the two concerns:

| Concern | Where it lives | Why |
|---|---|---|
| UI, knowledge base, RAG, vector DB, config | **Local machine (permanent)** | Your data and setup, always yours |
| LLM inference (the heavy GPU work) | **Remote GPU (disposable)** | Rent power on demand, swap providers freely |
| Embeddings (RAG indexing) | **Local machine, CPU** | Keeps RAG independent of the GPU |

Swapping GPU provider (Oracle Cloud → Vast.ai → anything else) means changing
**one API endpoint**, not rebuilding the project.

## Stack

- **Open WebUI** — chat interface + knowledge base + RAG orchestration (Docker)
- **Ollama** (local) — serves the embedding model on CPU
- **nomic-embed-text** — embedding model (small, CPU-friendly, stays local)
- **Remote inference server** — **Ollama** serves the large chat LLM on a rented GPU (vLLM is the documented upgrade path — see `ARCHITECTURE.md`)
- **OpenAI-compatible API** — the standardized interface between Open WebUI and the remote GPU

> **On the hardware and model choices (cost vs. power).** In this build I use a
> rented **RTX 4080S (~$0.40/hr on Vast.ai)** and the model
> **`huihui_ai/qwen2.5-abliterate:32b`** (~19 GB). That is a deliberate choice: I
> looked for the most *efficient* setup — the best result for the least money —
> not the most powerful one. The whole point of the modular design is that this is
> not a ceiling. With no budget limit, the exact same project runs unchanged on far
> stronger GPUs (A100, H100, …) and much larger models — you only change the remote
> endpoint and the model name, nothing else in the architecture. Pick the GPU and
> model that fit your budget; the infrastructure stays the same.

## Current status

- [x] Local stack working (Open WebUI + Ollama + embeddings)
- [x] RAG verified end-to-end (OWASP WSTG knowledge base, 168 Markdown files)
- [x] Environment audit completed — see `ARCHITECTURE.md`
- [x] Safety backup of all persistent data — see `BACKUP.md`
- [x] Migrated Open WebUI to a persistent Docker volume — see `MIGRATION.md`
- [x] Reproducible `docker-compose.yml` + `.env.example`
- [x] First remote GPU deployment on Vast.ai, connected and tested — see `REMOTE-GPU-VAST.md`
- [x] Knowledge base expanded: OWASP + MITRE ATT&CK, CWE and CAPEC converted to Markdown (`scripts/`)
- [x] First agent: "Pentest Mentor" (system prompt + knowledge collections)
- [x] Secure remote access via SSH tunnel (Ollama stays on localhost, reached only through the tunnel)
- [x] Chose and verified an uncensored, tool-calling model: `huihui_ai/qwen2.5-abliterate:32b` — abliteration kept function calling; verified end-to-end on the Pentest Mentor (tool call + RAG + step-by-step methodology, in Italian)
- [x] Automate remote setup: saved Vast template + provisioning script + SSH-tunnel script (`scripts/`) — see `REMOTE-GPU-VAST.md`
- [ ] Build specialised agents with tool calling + an SSH "run-in-VM" executor tool
- [ ] Set up an isolated vulnerable lab (red team + blue team) for practice
- [ ] Optional: revisit Oracle Cloud (A10) if GPU quota is unlocked

> **On the autonomous agents (scope).** This project refers to AI agents that call
> tools, and to a three-layer design in which an agent would *run* offensive tools
> (scans and the like) against isolated lab machines on its own. That
> autonomous-execution part is **intentionally not included in this version** — it is
> a defined next phase, not something left out by accident. It appears here because
> choosing the model forced the question: an uncensored model is only useful for this
> if it can still call tools reliably, so that capability had to be verified (see
> `REMOTE-GPU-VAST.md`). I will publish that part **separately**, once I have
> successfully and safely automated an AI-driven attack inside a lab. The design is
> described in `ARCHITECTURE.md`.

## Documentation

| File | Contents |
|---|---|
| `README.md` | This overview |
| `ARCHITECTURE.md` | Design, audit findings, and technical decisions |
| `INSTALLATION.md` | Local setup from scratch |
| `MIGRATION.md` | Moving inference between GPU providers |
| `REMOTE-GPU-VAST.md` | Runbook + record of the first Vast.ai GPU deployment |
| `BACKUP.md` | Backup and restore of persistent data |
| `SECURITY.md` | Secrets handling, network hardening, `.gitignore` rules |
| `docker-compose.yml` | Reproducible local deployment |
| `.env.example` | Configuration template (no secrets) |
| `scripts/` | Knowledge-base conversion scripts (+ their `README.md`) |
| `prompts/` | Agent system prompts (in Italian by design — see `prompts/README.md`) |
| `LICENSE` | MIT license |

## A note on data and privacy

This repository contains **only** infrastructure code and documentation. It must
never contain the knowledge-base contents, the vector database, the Open WebUI
database, API keys, or any credentials. See `SECURITY.md`.
