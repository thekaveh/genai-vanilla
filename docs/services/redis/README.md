# Redis

**Port:** 63001
**SOURCE variable:** `REDIS_SOURCE`
**SOURCE options:** container

## Overview

Core cache/queue/session infrastructure service used by multiple stack components.

## Access

| Path | URL | Notes |
|---|---|---|
| Direct | localhost:63001 | Works when the service is enabled in container mode and the port is exposed. |
| Kong | — | Requires `./start.sh --setup-hosts`; only available for services with Kong routes. |

See the canonical port table at [Ports and Routes](../../deployment/ports-and-routes.md).

## Configuration

Configure this service through `.env`, the interactive wizard, or CLI flags where available. Prefer SOURCE variables and documented env vars over direct `docker-compose.yml` edits.

```bash
REDIS_SOURCE=<option>
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

> Auto-generated section — the **Current** subsections are derived from `services/redis/service.yml`. Re-run `python -m bootstrapper.docs.regen redis` after manifest changes.

### Current — Upstream (this service depends on)

| Service | Type | Mechanism | Failure mode |
|---|---|---|---|
| supabase | required | `http://supabase:<port>` | _unspecified_ |

### Current — Downstream (services that depend on this)

| Service | Type | Mechanism |
|---|---|---|
| kong | required | kong declares redis in depends_on.required |
| litellm | required | litellm declares redis in depends_on.required |
| searxng | required | searxng declares redis in depends_on.required |
| n8n | required | n8n declares redis in depends_on.required |
| backend | required | backend declares redis in depends_on.required |
| jupyterhub | required | jupyterhub declares redis in depends_on.required |
| open-webui | required | open-webui declares redis in depends_on.required |

### Architecture diagram

![redis architecture](./architecture.svg)

[Open the interactive HTML diagram](./architecture.html) for a full-screen view.

### Future — Missing pair integrations

_No high-confidence opportunities identified._

### Future — Candidate new services

_No high-confidence opportunities identified._

### Future — Unused features in this service

_No high-confidence opportunities identified._
