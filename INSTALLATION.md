# Installation (local setup from scratch)

This sets up the **local, permanent** side of the project: Open WebUI plus a
local Ollama for CPU embeddings. The remote GPU that serves the large chat model
is covered separately in `REMOTE-GPU-VAST.md`.

## Prerequisites

- **Docker** + **Docker Compose**
- **Ollama** installed and running on the host (used for CPU embeddings)
- **Git**
- **Python 3.8+** (only if you want to build the knowledge base; see step 5)
- ~2 GB free disk for the image and the embedding model

## 1. Clone and configure

```bash
git clone https://github.com/LDRDMN/Modular-Gpu-CyberSecIA.git
cd Modular-Gpu-CyberSecIA
cp .env.example .env
```

Open `.env` and set a fixed `WEBUI_SECRET_KEY` (keeps you logged in across
container restarts). Generate one with:

```bash
openssl rand -hex 32
```

## 2. Create the persistent volume

The compose file expects an **external** named volume, so your data (chats,
knowledge base, vector DB) survives a container recreation. Create it once,
before the first start:

```bash
docker volume create open-webui
```

## 3. Start Open WebUI

```bash
docker compose up -d
```

Open http://localhost:3000 and create the admin account (the first user created
becomes the administrator).

## 4. Local embedding model

Pull the embedding model used for RAG (small, runs on CPU):

```bash
ollama pull nomic-embed-text
```

Then in Open WebUI: **Admin → Settings → Documents** set the embedding engine to
**Ollama**, model `nomic-embed-text`, reachable at
`http://host.docker.internal:11434`.

> If Ollama is not reachable from the container, make sure it listens on all
> interfaces (`OLLAMA_HOST=0.0.0.0`) and read the "Local Ollama note" in
> `SECURITY.md` for the firewall caveat.

## 5. Build the knowledge base (optional)

The RAG sources are **not shipped** in this repository (it holds infrastructure
and code only — see "A note on data and privacy" in `README.md`). Each source is
public; download it, convert it to Markdown with the scripts in `scripts/`, then
upload the resulting folder as a Knowledge collection in Open WebUI.

| Source | Where to download | License / attribution |
|---|---|---|
| OWASP WSTG | https://github.com/OWASP/wstg (Markdown) | CC BY-SA 4.0 — © OWASP Foundation |
| MITRE ATT&CK | https://github.com/mitre-attack/attack-stix-data | © The MITRE Corporation — ATT&CK terms of use |
| CWE | https://cwe.mitre.org/data/downloads.html | © The MITRE Corporation |
| CAPEC | https://capec.mitre.org/data/downloads.html | © The MITRE Corporation |

The scripts use only the Python standard library — no `pip install` needed.
Example (MITRE):

```bash
python scripts/mitre_to_md.py <path-to>/enterprise-attack.json <output-dir>
```

See `scripts/README.md` for the exact command of each converter.

## 6. Remote GPU (chat model)

The local stack above does embeddings and RAG. The large chat model runs on a
rented GPU. See `REMOTE-GPU-VAST.md` for renting a GPU, pulling the model, and
connecting Open WebUI through the SSH tunnel.
