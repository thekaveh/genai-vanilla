# Ports and Routes

> ⚠️ **STALE (as of 3.0.0 — 2026-05-15):** the table below still reflects the pre-3.0.0 hand-edited port layout. Topology v1 (3.0.0) computes ports from a per-category slot allocator in `bootstrapper/services/topology.py`, so individual offsets have shifted. Until this page is regenerated against topology v1, treat **`.env.example`** at the repo root and the **README "Web interfaces" table** as the authoritative sources; the Kong-alias list in `docs/services/kong.md` is also up to date.

This table is the canonical documentation reference for default service ports and Kong routes.

Ports are derived from `BASE_PORT` in `.env`. The default `BASE_PORT` is `63000`, so a service with offset `+17` is exposed on `63017`. You can move the whole stack by editing `BASE_PORT` or running `./start.sh --base-port <port>`.

Kong hostnames require hosts-file setup with `./start.sh --setup-hosts`. Direct `localhost:PORT` URLs work without hosts-file changes when the corresponding service is enabled and running in container mode. Each Kong alias also works when the underlying source is set to `*-localhost` — Kong proxies through `host.docker.internal` to the user's host machine.

| Component | Env var | Offset | Default port | Direct URL | Kong URL | Notes |
|---|---:|---:|---:|---|---|---|
| Supabase PostgreSQL | `SUPABASE_DB_PORT` | +0 | 63000 | `localhost:63000` | — | PostgreSQL connection port, not a browser UI. |
| Redis | `REDIS_PORT` | +1 | 63001 | `localhost:63001` | — | Redis connection port. |
| Kong HTTP Gateway | `KONG_HTTP_PORT` | +2 | 63002 | `http://localhost:63002` | — | Base gateway port for friendly host routes. |
| Kong HTTPS Gateway | `KONG_HTTPS_PORT` | +3 | 63003 | `https://localhost:63003` | — | HTTPS gateway listener when configured. |
| Supabase Meta | `SUPABASE_META_PORT` | +4 | 63004 | `http://localhost:63004` | — | Internal/admin metadata API. |
| Supabase Storage | `SUPABASE_STORAGE_PORT` | +5 | 63005 | `http://localhost:63005` | — | S3-compatible storage API. |
| Supabase Auth | `SUPABASE_AUTH_PORT` | +6 | 63006 | `http://localhost:63006` | — | GoTrue auth API. |
| Supabase REST API | `SUPABASE_API_PORT` | +7 | 63007 | `http://localhost:63007` | `http://api.localhost:63002` | Requires hosts setup for Kong hostname. |
| Supabase Realtime | `SUPABASE_REALTIME_PORT` | +8 | 63008 | `http://localhost:63008` | — | WebSocket/realtime service. |
| Supabase Studio | `SUPABASE_STUDIO_PORT` | +9 | 63009 | `http://localhost:63009` | `http://localhost:63002` | Admin UI; Kong may expose it through the gateway root depending on generated route config. |
| Neo4j Bolt | `GRAPH_DB_PORT` | +10 | 63010 | `bolt://localhost:63010` | — | Graph database Bolt protocol. |
| Neo4j Browser | `GRAPH_DB_DASHBOARD_PORT` | +11 | 63011 | `http://localhost:63011` | — | Neo4j browser/dashboard. |
| LiteLLM Gateway | `LITELLM_PORT` | +12 | 63012 | `http://localhost:63012` | `http://litellm.localhost:63002` | Always-on OpenAI-compatible front door for every LLM provider. Container Ollama is now an internal-only upstream (no host port). Same alias exposes the admin dashboard (`/ui/`), proxy API (`/v1/*`), and usage telemetry (`/spend/*`) — Kong routes the entire surface, not just the dashboard. |
| Local Deep Researcher | `LOCAL_DEEP_RESEARCHER_PORT` | +13 | 63013 | `http://localhost:63013` | — | Research/orchestration service. |
| SearxNG | `SEARXNG_PORT` | +14 | 63014 | `http://localhost:63014` | `http://search.localhost:63002` | Kong hostname requires hosts setup. |
| Open WebUI | `OPEN_WEB_UI_PORT` | +15 | 63015 | `http://localhost:63015` | `http://chat.localhost:63002` | Main chat UI. |
| Backend API | `BACKEND_PORT` | +16 | 63016 | `http://localhost:63016` | `http://api.localhost:63002` | Always-on adaptive core service. |
| n8n | `N8N_PORT` | +17 | 63017 | `http://localhost:63017` | `http://n8n.localhost:63002` | Workflow automation UI/API. |
| ComfyUI | `COMFYUI_PORT` | +18 | 63018 | `http://localhost:63018` | `http://comfyui.localhost:63002` | Container mode direct URL; localhost/external modes route to configured URL. |
| Weaviate HTTP | `WEAVIATE_PORT` | +19 | 63019 | `http://localhost:63019` | — | Vector database REST endpoint. |
| Weaviate gRPC | `WEAVIATE_GRPC_PORT` | +20 | 63020 | `localhost:63020` | — | Vector database gRPC endpoint. |
| Document Processor / Docling | `DOC_PROCESSOR_PORT` | +21 | 63021 | `http://localhost:63021` | — | Optional document processing service. |
| STT Provider (wizard slot) | `STT_PROVIDER_PORT` | +22 | 63022 | `http://localhost:63022` | — | Wizard display slot. Bootstrapper rewrites it to match the active source — `SPEACHES_PORT` for Speaches, this slot for Parakeet, or the port inside `*_LOCALHOST_URL` for host-side variants. |
| TTS Provider (wizard slot) | `TTS_PROVIDER_PORT` | +23 | 63023 | `http://localhost:63023` | — | Wizard display slot. Bootstrapper rewrites it to `SPEACHES_PORT` (Speaches), `CHATTERBOX_PORT` (Chatterbox), or the URL-port for `chatterbox-localhost`. |
| OpenClaw Gateway | `OPENCLAW_GATEWAY_PORT` | +24 | 63024 | `http://localhost:63024` | `http://openclaw.localhost:63002` | Optional AI agent gateway. |
| OpenClaw Bridge | `OPENCLAW_BRIDGE_PORT` | +25 | 63025 | `http://localhost:63025` | — | Optional bridge service. |
| Speaches (TTS+STT) | `SPEACHES_PORT` | +26 | 63026 | `http://localhost:63026` | — | Unified TTS+STT — Kokoro/Piper voices + Faster-Whisper transcription. Runs when either `TTS_PROVIDER_SOURCE` or `STT_PROVIDER_SOURCE` selects a `speaches-*` value. |
| Chatterbox TTS | `CHATTERBOX_PORT` | +27 | 63027 | `http://localhost:63027` | — | Voice-cloning TTS (Resemble AI Chatterbox). Runs when `TTS_PROVIDER_SOURCE=chatterbox-container-gpu`. |
| Hermes Agent API | `HERMES_API_PORT` | +28 | 63028 | `http://localhost:63028` | — | OpenAI-compatible API. Bearer token in `HERMES_API_KEY`. |
| Hermes Agent Dashboard | `HERMES_DASHBOARD_PORT` | +29 | 63029 | `http://localhost:63029` | `http://hermes.localhost:63002` | Web admin UI (skills, sessions, model config). |
| MinIO S3 API | `MINIO_PORT` | +30 | 63030 | `http://localhost:63030` | — | S3-compatible object storage API. |
| MinIO Console | `MINIO_CONSOLE_PORT` | +31 | 63031 | `http://localhost:63031` | `http://minio.localhost:63002` | MinIO admin console UI. Login `minioadmin` / `${MINIO_ROOT_PASSWORD}`. The S3 API at port 63030 is deliberately NOT aliased — S3 clients use full URLs with explicit ports anyway. |
| JupyterHub | `JUPYTERHUB_PORT` | +48 | 63048 | `http://localhost:63048` | `http://jupyter.localhost:63002` | Data science notebook environment. |

## Hosts-file routes

Run this once if you want friendly hostnames:

```bash
./start.sh --setup-hosts
```

Current documented Kong hostnames:

- `api.localhost`
- `chat.localhost`
- `comfyui.localhost`
- `hermes.localhost`
- `jupyter.localhost`
- `n8n.localhost`
- `openclaw.localhost`
- `search.localhost`

## Advanced overrides

`BASE_PORT` is the preferred normal mechanism for moving the whole stack. Individual `*_PORT` variables are advanced overrides and should be changed carefully because docs, gateway routes, and dependent services need to stay aligned.
