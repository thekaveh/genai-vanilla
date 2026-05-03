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

See the canonical port table at [Ports and Routes](../deployment/ports-and-routes.md).

## Configuration

Configure this service through `.env`, the interactive wizard, or CLI flags where available. Prefer SOURCE variables and documented env vars over direct `docker-compose.yml` edits.

```bash
REDIS_SOURCE=<option>
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

For general startup and routing issues, see [Troubleshooting](../quick-start/troubleshooting.md).
