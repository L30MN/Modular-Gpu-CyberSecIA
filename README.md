# Modular Remote GPU AI Infrastructure

A self-hosted, privacy-first AI assistant for cybersecurity study (pentesting,
OWASP, MITRE ATT&CK, CWE/CAPEC) built around a **modular architecture**: the
infrastructure (chat UI, knowledge base, RAG, vector database) lives permanently
on a local machine, while **GPU compute is a swappable, disposable resource**
reached over a standardized API.

The guiding principle: *the GPU is an engine you can swap, not the place where
the project lives.*

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
- **Remote inference server** (vLLM or Ollama) — serves the large chat LLM on a rented GPU
- **OpenAI-compatible API** — the standardized interface between Open WebUI and the remote GPU

## Current status

- [x] Local stack working (Open WebUI + Ollama + embeddings)
- [x] RAG verified end-to-end (OWASP WSTG knowledge base, 168 Markdown files)
- [x] Environment audit completed — see `ARCHITECTURE.md`
- [x] Safety backup of all persistent data — see `BACKUP.md`
- [x] Migrated Open WebUI to a persistent Docker volume — see `MIGRATION.md`
- [x] Reproducible `docker-compose.yml` + `.env.example`
- [x] First remote GPU deployment on Vast.ai, connected and tested — see `REMOTE-GPU-VAST.md`
- [ ] Secure the remote endpoint with an SSH tunnel
- [ ] Automate remote setup (startup script) for one-command launch
- [ ] Optional: revisit Oracle Cloud (A10) if GPU quota is unlocked

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

## A note on data and privacy

This repository contains **only** infrastructure code and documentation. It must
never contain the knowledge-base contents, the vector database, the Open WebUI
database, API keys, or any credentials. See `SECURITY.md`.
