# n8n

**Port:** 63017
**SOURCE variable:** `N8N_SOURCE`
**SOURCE options:** container, disabled

## Overview

Workflow automation service with optional initialization/import support.

## Access

| Path | URL | Notes |
|---|---|---|
| Direct | http://localhost:63017 | Works when the service is enabled in container mode and the port is exposed. |
| Kong | http://n8n.localhost:63002 | Requires `./start.sh --setup-hosts`; only available for services with Kong routes. |

See the canonical port table at [Ports and Routes](../../deployment/ports-and-routes.md).

## Configuration

Configure this service through `.env`, the interactive wizard, or CLI flags where available. Prefer SOURCE variables and documented env vars over direct `docker-compose.yml` edits.

```bash
N8N_SOURCE=<option>
```

Use `./start.sh` for the guided wizard, or pass a targeted flag for scripted changes when the CLI exposes one.

## Troubleshooting

```bash
# Check service status
docker compose ps

# Check logs; replace SERVICE with the compose service name when needed
docker compose logs -f SERVICE
```

For general startup and routing issues, see [Troubleshooting](../../quick-start/troubleshooting.md).

## Dependencies & Integrations

> Auto-generated section — the **Current** subsections are derived from `services/n8n/service.yml`'s `data_flow.calls` field (and inverse passes). Re-run `python -m bootstrapper.docs.regen n8n` after manifest changes.

### Current — Upstream (this service calls)

| Service | Category |
|---|---|
| minio | data |
| supabase | data |
| weaviate | data |
| litellm | llm |
| comfyui | media |
| doc-processor | media |
| searxng | media |
| stt-provider | media |
| tts-provider | media |
| hermes | agents |

### Current — Downstream (services that call this)

| Service | Category |
|---|---|
| kong | infra |
| openclaw | agents |
| backend | apps |

### Architecture diagram

![n8n architecture](./architecture.svg)

[Open the interactive HTML diagram](./architecture.html) for a full-screen view.

### Future — Missing pair integrations

_No high-confidence opportunities identified._

### Future — Candidate new services

_No high-confidence opportunities identified._

### Future — Unused features in this service

_No high-confidence opportunities identified._
