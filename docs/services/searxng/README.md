# SearxNG

**Port:** 63014
**SOURCE variable:** `SEARXNG_SOURCE`
**SOURCE options:** container, disabled

## Overview

Privacy-respecting metasearch service used by research workflows and available through Kong when enabled.

## Access

| Path | URL | Notes |
|---|---|---|
| Direct | http://localhost:63014 | Works when the service is enabled in container mode and the port is exposed. |
| Kong | http://search.localhost:63002 | Requires `./start.sh --setup-hosts`; only available for services with Kong routes. |

See the canonical port table at [Ports and Routes](../../deployment/ports-and-routes.md).

## Configuration

Configure this service through `.env`, the interactive wizard, or CLI flags where available. Prefer SOURCE variables and documented env vars over direct `docker-compose.yml` edits.

```bash
SEARXNG_SOURCE=<option>
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

> Auto-generated section — the **Current** subsections are derived from `services/searxng/service.yml`'s `data_flow.calls` field (and inverse passes). Re-run `python -m bootstrapper.docs.regen searxng` after manifest changes.

### Current — Upstream (this service calls)

_No upstream calls._

### Current — Downstream (services that call this)

| Service | Category |
|---|---|
| kong | infra |
| hermes | agents |
| n8n | agents |
| local-deep-researcher | apps |
| open-webui | apps |

### Architecture diagram

![searxng architecture](./architecture.svg)

[Open the interactive HTML diagram](./architecture.html) for a full-screen view.

### Future — Missing pair integrations

_No high-confidence opportunities identified._

### Future — Candidate new services

_No high-confidence opportunities identified._

### Future — Unused features in this service

_No high-confidence opportunities identified._
