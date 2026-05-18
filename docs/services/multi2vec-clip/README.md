# Multi2Vec CLIP

**Port:** internal
**SOURCE variable:** `MULTI2VEC_CLIP_SOURCE`
**SOURCE options:** container-cpu, container-gpu, disabled

## Overview

Optional Weaviate vectorizer module for multimodal/image embeddings.

## Access

| Path | URL | Notes |
|---|---|---|
| Direct | internal container endpoint | Works when the service is enabled in container mode and the port is exposed. |
| Kong | — | Requires `./start.sh --setup-hosts`; only available for services with Kong routes. |

See the canonical port table at [Ports and Routes](../../deployment/ports-and-routes.md).

## Configuration

Configure this service through `.env`, the interactive wizard, or CLI flags where available. Prefer SOURCE variables and documented env vars over direct `docker-compose.yml` edits.

```bash
MULTI2VEC_CLIP_SOURCE=<option>
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

> Auto-generated section — the **Current** subsections are derived from `services/multi2vec-clip/service.yml`. Re-run `python -m bootstrapper.docs.regen multi2vec-clip` after manifest changes.

### Current — Upstream (this service depends on)

_No upstream dependencies._

### Current — Downstream (services that depend on this)

_No downstream consumers._

### Architecture diagram

![multi2vec-clip architecture](./architecture.svg)

[Open the interactive HTML diagram](./architecture.html) for a full-screen view.

### Future — Missing pair integrations

_No high-confidence opportunities identified._

### Future — Candidate new services

_No high-confidence opportunities identified._

### Future — Unused features in this service

_No high-confidence opportunities identified._
