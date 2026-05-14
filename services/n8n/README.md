# services/n8n — n8n workflow automation family

Three co-lifecycled containers + one named volume in one manifest.

## Containers

| Container | Role | Image var |
|---|---|---|
| `n8n` | Main n8n process (UI + API on `N8N_PORT`) | `N8N_IMAGE` |
| `n8n-worker` | Queue-mode worker (scales with `N8N_WORKER_SCALE`, follows main scale via `service_config.py`) | `N8N_IMAGE` (same image) |
| `n8n-init` | One-shot alpine sidecar — installs community packages, imports workflow templates from `./workflows-stage/` | `N8N_INIT_IMAGE` (alpine) |

## Subfolders

- `init/scripts/` — bind-mounted into `n8n-init` at `/scripts`; entrypoint is `/scripts/init-n8n.sh`.
- `init/config/` — bind-mounted into `n8n-init` at `/config`; holds workflow JSON templates the init script imports.
- `workflows-stage/` — staging area for workflow files that get imported via the init sidecar (visible only to the host operator).

## Recovery note

If `n8n` restart-loops with `Error: Command "start" not found`, the cause is **corrupted state in the `n8n-data` named volume** (typically a half-installed community package shadowed n8n's own `start` subcommand). Surgical fix:

```bash
docker rm -f genai-n8n genai-n8n-init genai-n8n-worker
docker volume rm genai-n8n-data
./start.sh
```

See `docs/services/n8n.md` for the full failure-mode write-up.

## See also

- [`docs/services/n8n.md`](../../docs/services/n8n.md) — full service docs.
