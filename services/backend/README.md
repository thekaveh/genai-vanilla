# services/backend — FastAPI Backend (always-on adaptive)

The stack's first-party API gateway. FastAPI under uvicorn, fronted by
Kong on `KONG_URL`. Adapts at start-up to whichever
LLM / STT / TTS / vector / graph backends the wizard configured.

## Containers

| Container | Role | Image var |
|---|---|---|
| `backend` | FastAPI app (LangMem, Weaviate-vector, Neo4j, n8n, ComfyUI, Hermes, LiteLLM clients) | `BACKEND_IMAGE` |

`BACKEND_SOURCE` is single-valued (`container`) — the backend is a
core stack service, not source-selectable. `BACKEND_SCALE` is auto-managed.

## Subfolders

- **`app/`** — Dockerfile + the FastAPI project itself (nested
  `app/app/` holds the Python source; the outer `app/` is the build
  context). `app/configure-backend.sh` is the entrypoint shim that
  resolves runtime endpoints from `.env` before launching uvicorn.

## See also

- [`docs/services/backend.md`](../../docs/services/backend.md) — full service docs.
