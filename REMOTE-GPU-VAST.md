# Remote GPU Deployment — Vast.ai (first successful run)

This documents the first working end-to-end deployment: a disposable GPU rented
on Vast.ai runs the chat LLM, while the local machine keeps Open WebUI, the
knowledge base, and the embeddings. It doubles as a reusable runbook.

## Result

- GPU: 1× RTX 4080S (32 GB VRAM), rented on Vast.ai, ~$0.40/hr.
- Model: `qwen3.5:35b` (~22 GB) served by Ollama on the remote GPU.
- Local Open WebUI connected to the remote Ollama endpoint.
- RAG verified: a PHP SQL-injection snippet was analysed correctly, with the
  model **citing the right OWASP WSTG source files** (SQL injection + MySQL),
  proving local embeddings + remote model work together.
- The model answered the offensive-security question without refusing.

## Steps

### 1. Rent the GPU

- Filter for the target card (24 GB+ VRAM), high reliability (>99%), on-demand.
- Select the **Ollama** template (not the Open WebUI one — the UI stays local).
- Set disk ~50 GB. Rent.
- Note: the template auto-pulls a default model on first boot. This costs
  bandwidth (~$0.23 for a 22 GB model at ~$10/TB).

### 2. Find the Ollama port

On the instance card, open the port mapping (click the IP). Ollama's internal
port `11434` is mapped to an external port, e.g.:

```
70.48.44.13:50500 -> 11434/tcp
```

The endpoint is then `http://<ip>:<external-port>` (here `http://70.48.44.13:50500`).

### 3. Fix the Ollama bind address (important gotcha)

By default the Vast Ollama template starts `ollama serve` bound to `localhost`,
so the external port refuses connections (`ERR_CONNECTION_REFUSED`). Ollama's
listen address is set via the `OLLAMA_HOST` environment variable.

Open the instance's Jupyter terminal and patch the supervisor startup script so
the change survives restarts:

```bash
sed -i '/^ollama serve/i export OLLAMA_HOST=0.0.0.0:11434' /opt/supervisor-scripts/ollama.sh
grep -n OLLAMA_HOST /opt/supervisor-scripts/ollama.sh   # verify
supervisorctl restart ollama
sleep 3 && curl -s http://localhost:11434                # "Ollama is running"
```

Then confirm from your own browser: `http://<ip>:<external-port>` should show
`Ollama is running`.

### 4. Connect Open WebUI (local)

- Admin Panel → Settings → Connections → Ollama API.
- Keep the existing local entry (`host.docker.internal:11434`, used for
  embeddings). **Add** the remote endpoint `http://<ip>:<external-port>`.
- Refresh/verify — the connection turns green.

### 5. Test

- New chat → select the remote model (`qwen3.5:35b`).
- First message is slow: the 22 GB model loads into VRAM (cold start, ~30–90 s).
  After that, responses are fast.
- Attach a knowledge collection with `#` and ask a question to confirm RAG works
  end-to-end.

## Cost notes

- Billed per hour only while the instance is **running** (GPU + disk).
- A **stopped** instance still bills storage (on this host ~$1/day). To pay $0,
  **destroy** the instance when done — the model is re-pulled next time.
- Model re-download costs bandwidth (~$0.23 per 22 GB pull).
- First-run total for setup + testing was ~$0.50 (model download + ~37 min
  runtime while configuring).

## Open items

- **Security:** the Ollama port is currently exposed to the public internet with
  no auth. Next step is an **SSH tunnel** so the endpoint is reachable only from
  the local machine. The SSH key must be added to the Vast account *before*
  creating the instance.
- **Changing endpoint:** every new instance gets a new IP and port, so the Open
  WebUI connection URL must be updated each time. An SSH tunnel fixes this too:
  Open WebUI points at a fixed local address, and only the tunnel command changes
  per instance.
- **Automation:** fold the `OLLAMA_HOST` fix and model pull into a startup script
  so a fresh instance is ready with one command.
