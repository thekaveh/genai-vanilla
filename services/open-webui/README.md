# services/open-webui — Open WebUI family

Two containers, one named volume.

## Containers

| Container | Role | Image var |
|---|---|---|
| `open-web-ui` | Chat UI (port `OPEN_WEB_UI_PORT`) | `OPEN_WEB_UI_IMAGE` |
| `open-webui-init` | One-shot init — creates admin user, primes Open WebUI's DB | built from `./init/` |

## Subfolders

- `init/` — Dockerfile + scripts for `open-webui-init`. Build context: `./init`.
- `extras/tools/` — host-editable Python tools bind-mounted into `/app/backend/data/tools` in the running UI. Add a `.py` here and it appears in the Open WebUI Tools section.
- `extras/functions/` — same pattern for functions (filters, pipelines).
- `extras/workflows/` — staging slot for n8n-style workflow JSON (currently NOT mounted into the container; reserved for the workflow integration roadmapped under MinIO+n8n artifact handoff).

## See also

- [`docs/services/open-webui.md`](../../docs/services/open-webui.md) — full service docs.
