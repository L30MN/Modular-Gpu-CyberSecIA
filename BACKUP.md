# Backup & Restore

Open WebUI stores everything it generates inside the container at
`/app/backend/data`. Until that directory is on a persistent volume, it is
**ephemeral** — a safety backup to the host disk protects against data loss.

> **Source files vs generated data.** Your Markdown source documents on disk are
> the *ingredients*. The *cooked meal* — embeddings (vector DB), collections,
> account, and configuration — exists only inside the container. A backup saves
> the cooked meal too, so you don't have to re-index everything from scratch.

## What lives in `/app/backend/data`

| Item | Keep? | Why |
|---|---|---|
| `webui.db` (+ `-wal`, `-shm`) | ✅ | SQLite DB: account, collections, config |
| `vector_db/` | ✅ | The embeddings (vector database) |
| `uploads/` | ✅ | Uploaded source files |
| `cache/` | ❌ | Re-downloadable model files; contains symlinks |

## Backup (Windows / PowerShell)

Create the destination, then copy each item **except `cache`** (the `cache`
folder contains symlinks that fail to copy on Windows without elevated
privileges — and it is not needed).

```powershell
$dst = "C:\AI\SecurityKB\_backups\webui-data-$(Get-Date -Format yyyy-MM-dd)"
New-Item -ItemType Directory -Force -Path $dst | Out-Null

docker cp open-webui:/app/backend/data/webui.db      "$dst\webui.db"
docker cp open-webui:/app/backend/data/webui.db-wal  "$dst\webui.db-wal"
docker cp open-webui:/app/backend/data/webui.db-shm  "$dst\webui.db-shm"
docker cp open-webui:/app/backend/data/uploads       "$dst\uploads"
docker cp open-webui:/app/backend/data/vector_db     "$dst\vector_db"
```

`docker cp` is read-only on the container side: it copies out and changes
nothing inside the container.

### Verify

```powershell
Get-ChildItem $dst
```

Expect `uploads`, `vector_db`, and `webui.db` (~350 MB) plus the two small WAL
files. If those are present, the backup is complete.

## Restore (outline)

Restoring copies the backed-up data back into a fresh Open WebUI container that
**has a persistent volume mounted**. With the volume mounted at
`/app/backend/data`:

```powershell
docker cp "<backup>\webui.db"     open-webui:/app/backend/data/webui.db
docker cp "<backup>\webui.db-wal" open-webui:/app/backend/data/webui.db-wal
docker cp "<backup>\webui.db-shm" open-webui:/app/backend/data/webui.db-shm
docker cp "<backup>\uploads"      open-webui:/app/backend/data/
docker cp "<backup>\vector_db"    open-webui:/app/backend/data/
docker restart open-webui
```

The `cache/` folder is intentionally not restored; Open WebUI re-downloads those
models on first use.

## Notes

- Keep backups **outside** any Git repository — they contain your knowledge base
  and account data. See `SECURITY.md`.
- The embedding model and vector dimensions must match on restore. If you ever
  change the embedding model, the vector database must be rebuilt.
