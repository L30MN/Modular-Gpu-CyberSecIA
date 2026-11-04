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
<host-ip>:<external-port> -> 11434/tcp
```

The endpoint is then `http://<host-ip>:<external-port>`.

### 3. Fix the Ollama bind address (important gotcha)

> ⚠️ **Security warning.** Setting `OLLAMA_HOST=0.0.0.0` together with Vast's public
> port mapping exposes Ollama to the **public internet with no authentication** —
> anyone who finds the address can use the rented GPU. This was done only as a quick
> throwaway test on an obscure address. For real use, do **not** expose the port:
> use an **SSH tunnel** instead and keep Ollama on `localhost`, so only your machine
> can reach it (see `SECURITY.md`). The steps below describe the insecure test path;
> the tunnel is the intended setup.

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

Then confirm from your own browser: `http://<host-ip>:<external-port>` should show
`Ollama is running`.

### 4. Connect Open WebUI (local)

- Admin Panel → Settings → Connections → Ollama API.
- Keep the existing local entry (`host.docker.internal:11434`, used for
  embeddings). **Add** the remote endpoint `http://<host-ip>:<external-port>`.
- Refresh/verify — the connection turns green.

### 5. Test

- New chat → select the remote model (`qwen3.5:35b`).
- First message is slow: the 22 GB model loads into VRAM (cold start, ~30–90 s).
  After that, responses are fast.
- Attach a knowledge collection with `#` and ask a question to confirm RAG works
  end-to-end.

## Secure access via SSH tunnel (the intended setup)

This replaces the insecure public-port path above. The remote Ollama stays on
`localhost`; an SSH tunnel is the only way in, authenticated by your SSH key
(served from the Bitwarden SSH agent).

**Prerequisites:** the SSH public key is on the Vast account *before* the instance
is created. In the instance config, leave `OLLAMA_MODEL` empty and do **not** set
`OLLAMA_HOST` (Ollama stays on localhost).

**1. Pull the model manually** (on the instance, via the Vast terminal):

```bash
ollama pull <model>          # e.g. a candidate to test; see model testing below
```

**2. Open the tunnel** from the local machine (PowerShell). Vast shows the SSH
host and port in the instance's "SSH" panel.

```bash
ssh -p <ssh-port> -N -L 127.0.0.1:11435:localhost:11434 root@<host-ip>
```

- `-L 127.0.0.1:11435:localhost:11434` forwards local port **11435** to the
  remote's `localhost:11434` (Ollama). Local **11435**, not 11434, avoids a clash
  with the local embeddings Ollama.
- `-N` holds the tunnel open without running a remote command. Leave the window
  open while you work; closing it closes the tunnel.
- Bitwarden prompts to approve using the key.

**3. Point Open WebUI at the tunnel** (one-time): Admin → Settings → Connections →
Ollama API → add `http://host.docker.internal:11435`. This address is **fixed**:
only the tunnel command changes per instance (new `<host-ip>`/`<ssh-port>`), not
the Open WebUI config.

> **Docker reachability note (verify live):** Open WebUI runs in Docker and reaches
> the host via `host.docker.internal`. A tunnel bound to `127.0.0.1` may not be
> reachable from the container. If the connection does not turn green, re-open the
> tunnel binding to all interfaces (`-L 0.0.0.0:11435:localhost:11434`) and add a
> Windows Firewall block on inbound `11435` for the Public profile, as done for
> ports 3000 and 11434.

## Testing a model's tool calling

Before committing to a model, verify it actually emits function calls (the failure
that hit `dolphin3:8b`). Use a trivial, side-effect-free tool.

**1. Create the tool:** Workspace → Tools → "+", paste `tools/example_tool.py`
(in this repo), save.

**2. Enable it** on a test model/agent (model editor → Tools → tick it).

**3. Ask a question only the tool can answer**, e.g.:

```
Qual è lo stato del lab "alpha"?
```

- **Works:** the model calls `get_lab_status("alpha")` and reports the tool's
  canned answer (you see the tool run in the response).
- **Fails:** the model invents an answer or ignores the tool → it is not reliable
  for agents; try another candidate.

Repeat for each candidate (e.g. Hermes 4, a Qwen-27B abliterated build) and keep
the one that calls tools reliably. Only then set it as `OLLAMA_MODEL` for future
instances.

### Chosen model (verified)

`huihui_ai/qwen2.5-abliterate:32b` — an uncensored (abliterated) Qwen2.5 32B,
~19 GB, fits a 24–32 GB GPU. Verified on an RTX 4080S:

- **Tool calling works** — the abliteration did not break function calling. The
  model called the test tool and used its real output.
- **Uncensored** — did not refuse offensive-security analysis.
- **Coherent** and follows the system prompt (language, step-by-step method),
  unlike small models.

For future instances, set `OLLAMA_MODEL=huihui_ai/qwen2.5-abliterate:32b` so it is
pulled on startup, and attach workspace tools at the **model level** (not per-chat,
which does not persist) so agents always have their tools.

## Automation (one-command launch)

Two scripts in `scripts/` plus a saved Vast template remove the manual setup.

**Vast template** (saved once, selected every time):

- Base: the official **Ollama** template, disk ~50 GB.
- Environment variable `OLLAMA_MODEL=huihui_ai/qwen2.5-abliterate:32b` — the template
  pulls the model on boot. The value is **case-sensitive**: it must be lowercase,
  exactly as shown, or the pull fails.
- Do **not** set `OLLAMA_HOST`: Ollama stays on `localhost`, reachable only through
  the SSH tunnel.
- Leave the template's own defaults (`PORTAL_CONFIG`, `DATA_DIRECTORY`, etc.) untouched.
- The SSH key lives on the Vast **account**, not the template, and must be present
  before renting.
- Optional: paste `scripts/vast-provision.sh` into the template's **On-start Script**
  field. With `OLLAMA_MODEL` already set the model is pulled regardless; the script
  only adds a readiness wait and a verification (`ollama list`). `ollama pull` is
  idempotent, so running both does no harm.

**`scripts/vast-provision.sh`** (remote): waits for Ollama, pulls `OLLAMA_MODEL`
(default `huihui_ai/qwen2.5-abliterate:32b`), prints `ollama list`. For the On-start
field or a manual `bash vast-provision.sh` on the instance.

**`scripts/open-tunnel.ps1`** (local, Windows/PowerShell): opens the SSH tunnel and
forwards local **11435** to the instance's `localhost:11434`. Only this command
changes per instance (new IP / SSH port); the Open WebUI endpoint stays fixed at
`http://host.docker.internal:11435`.

```powershell
.\open-tunnel.ps1 -HostIp <host-ip> -SshPort <ssh-port>
```

It binds `0.0.0.0:11435` by default so the Open WebUI Docker container can reach it,
which **requires** the Windows Firewall block on inbound 11435 (Public profile);
`-BindAddress 127.0.0.1` is the firewall-independent alternative. It uses the SSH
agent (Bitwarden prompts for the key), keeps the tunnel alive
(`ServerAliveInterval`), and fails fast if 11435 is already in use
(`ExitOnForwardFailure`). First run may need, once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

**Per-session flow:**

1. Vast → Templates → select the saved template → pick a GPU → Rent (model pulled
   automatically).
2. Local PC: `.\open-tunnel.ps1 -HostIp <ip> -SshPort <port>`.
3. Open WebUI → select `qwen2.5-abliterate:32b` → work.
4. Done: close the tunnel window and **destroy** the instance.

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
- **Automation:** done — see the "Automation" section above (saved Vast template +
  `scripts/vast-provision.sh` + `scripts/open-tunnel.ps1`).
