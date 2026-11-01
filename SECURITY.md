# Security

This project is self-hosted and privacy-first. Two areas matter: **keeping
secrets and data out of the repository**, and **hardening the remote GPU**.

## 1. Secrets and data must never enter the repository

The public repository contains only infrastructure code and documentation.

**Never commit:**

- `.env` (real configuration and secrets) — only `.env.example` is committed.
- API keys, tokens, passwords, SSH private keys, TLS certificates.
- The Open WebUI database (`webui.db`), the vector database (`vector_db/`),
  uploaded files (`uploads/`), or any backup (`_backups/`).
- The knowledge-base contents themselves.

These are all excluded by `.gitignore`. Before the first commit, confirm nothing
sensitive is staged:

```bash
git status
```

If a secret is ever committed by accident, treat it as compromised: rotate the
key, and remove it from history (do not just delete it in a new commit).

### Handling secrets

- Keep real values in `.env` (ignored by Git) or in a password manager
  (e.g. Bitwarden).
- Share only `.env.example`, which lists variable names with no values.
- Generate strong secrets, e.g.:

  ```bash
  openssl rand -hex 32
  ```

## 2. Hardening the remote GPU

The remote inference server must not be exposed openly to the Internet.

- **SSH with key authentication only.** Disable password login. Use a dedicated
  key pair; keep the private key off the repository and off shared machines.
- **Firewall.** Allow only the ports you need. Do not leave the inference API or
  any admin port open to the world.
- **Do not publish the inference endpoint directly.** Prefer an **SSH tunnel**
  from the local machine to the GPU host, so the API is reachable only through
  the tunnel, not from the public Internet.
- **Authenticate the API.** If the OpenAI-compatible endpoint must be reachable,
  require an API key and serve it over HTTPS.
- **Separate networks.** Keep the local infrastructure and the remote host
  logically separated; the GPU host should not have standing access to the local
  network.

### Local Ollama note

To let the Docker container reach Ollama, Ollama is set to listen on all
interfaces (`OLLAMA_HOST=0.0.0.0`). This also makes it reachable from other
devices on the local network. On a trusted home network the risk is low; to
close it, add a firewall rule blocking inbound connections to port `11434` from
outside the machine. The Docker container still reaches Ollama through Docker's
internal gateway.

## 3. Principle

Treat the remote GPU as untrusted and disposable. Nothing irreplaceable lives on
it; everything valuable lives locally and is backed up.
