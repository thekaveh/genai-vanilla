# ComfyUI

**Port:** 63018
**SOURCE variable:** `COMFYUI_SOURCE`
**SOURCE options:** container-cpu, container-gpu, localhost, external, disabled

## Overview

Image generation workflow UI/API. Container mode exposes the stack port; localhost/external modes route dependent services to configured URLs.

## Access

| Path | URL | Notes |
|---|---|---|
| Direct | http://localhost:63018 | Works when the service is enabled in container mode and the port is exposed. |
| Kong | http://comfyui.localhost:63002 | Requires `./start.sh --setup-hosts`; only available for services with Kong routes. |

See the canonical port table at [Ports and Routes](../../deployment/ports-and-routes.md).

## Configuration

Configure this service through `.env`, the interactive wizard, or CLI flags where available. Prefer SOURCE variables and documented env vars over direct `docker-compose.yml` edits.

```bash
COMFYUI_SOURCE=<option>
```

Use `./start.sh` for the guided wizard, or pass a targeted flag for scripted changes when the CLI exposes one.

## Dependencies and integration

The service participates in the Docker Compose network and may be consumed by the Backend API, Open WebUI, JupyterHub, n8n, Weaviate, or init containers depending on which SOURCE modes are enabled.

If a dependency is disabled, adaptive services should degrade where supported. Some implementation-level dependency cleanup is tracked separately as bootstrapper work and is outside this documentation pass.

## Troubleshooting

```bash
# Check service status
docker compose ps

# Check logs; replace SERVICE with the compose service name when needed
docker compose logs -f SERVICE
```

For general startup and routing issues, see [Troubleshooting](../../quick-start/troubleshooting.md).

## Dependencies & Integrations

> Auto-generated section — the **Current** subsections are derived from `services/comfyui/service.yml`. Re-run `python -m bootstrapper.docs.regen comfyui` after manifest changes.

### Current — Upstream (this service depends on)

| Service | Type | Mechanism | Failure mode |
|---|---|---|---|
| supabase | required | `http://supabase:<port>` | _unspecified_ |
| litellm | required | `http://litellm:<port>` | _unspecified_ |
| ollama | required | `http://ollama:<port>` | _unspecified_ |
| comfyui | adaptive | `COMFYUI_HOST_URL=${COMFYUI_ENDPOINT}` | _unspecified_ |

### Current — Downstream (services that depend on this)

| Service | Type | Mechanism |
|---|---|---|
| kong | required | kong declares comfyui in depends_on.required |
| hermes | adaptive | hermes adapts_to comfyui |
| hermes | optional | hermes lists comfyui as optional dep |
| jupyterhub | adaptive | jupyterhub adapts_to comfyui |
| jupyterhub | optional | jupyterhub lists comfyui as optional dep |

### Architecture diagram

![comfyui architecture](./architecture.svg)

[Open the interactive HTML diagram](./architecture.html) for a full-screen view.

### Future — Missing pair integrations

_No high-confidence opportunities identified._

### Future — Candidate new services

_No high-confidence opportunities identified._

### Future — Unused features in this service

_No high-confidence opportunities identified._
