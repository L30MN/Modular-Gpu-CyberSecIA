# Migration

This document covers two kinds of migration:

1. **Local: moving Open WebUI data onto a persistent volume** (done once).
2. **Remote: swapping the GPU inference provider** (the recurring goal).

---

## 1. Local — migrate to a persistent Docker volume

### Why

If Open WebUI runs without a mounted volume, all its data (account, knowledge
base, vector DB, config) lives in the container's ephemeral writable layer. It
survives a restart but is **destroyed** by `docker rm`, a recreate, or an image
update. Moving the data onto a named volume makes it durable.

### Safe procedure (no destructive step until verified)

Prerequisite: a verified backup on the host (see `BACKUP.md`).

```powershell
# 1. Set the current container aside as a fallback (not deleted)
docker stop open-webui
docker rename open-webui open-webui-old

# 2. Create a new container WITH a named volume
docker run -d --name open-webui -p 3000:8080 `
  -v open-webui:/app/backend/data `
  --add-host=host.docker.internal:host-gateway `
  --restart always `
  ghcr.io/open-webui/open-webui:main

# 3. Restore the backup into the new volume
docker exec open-webui rm -rf /app/backend/data/uploads /app/backend/data/vector_db
docker stop open-webui
docker cp "<backup>\webui.db"     open-webui:/app/backend/data/webui.db
docker cp "<backup>\webui.db-wal" open-webui:/app/backend/data/webui.db-wal
docker cp "<backup>\webui.db-shm" open-webui:/app/backend/data/webui.db-shm
docker cp "<backup>\uploads"      open-webui:/app/backend/data/uploads
docker cp "<backup>\vector_db"    open-webui:/app/backend/data/vector_db
docker start open-webui
```

(PowerShell uses a backtick `` ` `` for line continuation. Run each `docker cp`
on one line if you prefer.)

### Verify

- `docker volume ls` lists the `open-webui` volume.
- `localhost:3000` asks to **log in** with the existing account (not create a new
  one).
- The knowledge base still contains all documents.

### Clean up

Once verified, remove the fallback: `docker rm open-webui-old`.

---

## 2. Remote — swap the GPU inference provider

The architecture connects Open WebUI to the inference server through an
**OpenAI-compatible API**. Switching provider (Oracle Cloud → Vast.ai → …) means
changing only the endpoint and key — the local knowledge base, vector DB, and
embeddings are untouched because embeddings run locally on CPU.

To switch:

1. Bring up the inference server (e.g. vLLM) on the new GPU host.
2. Expose its OpenAI-compatible endpoint securely (SSH tunnel / authenticated).
3. In Open WebUI → Admin → Settings → Connections, update the OpenAI API base URL
   and key to point at the new host.
4. Select the model and test.

No data migration is required. See `SECURITY.md` for exposing the endpoint
safely.
