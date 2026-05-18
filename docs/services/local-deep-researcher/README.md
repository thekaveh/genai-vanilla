# Local Deep Researcher

**Port:** 63013
**SOURCE variable:** `LOCAL_DEEP_RESEARCHER_SOURCE`
**SOURCE options:** container, disabled

## Overview

Optional local research/orchestration service for multi-step web/research flows.

## Access

| Path | URL | Notes |
|---|---|---|
| Direct | http://localhost:63013 | Works when the service is enabled in container mode and the port is exposed. |
| Kong | — | Requires `./start.sh --setup-hosts`; only available for services with Kong routes. |

See the canonical port table at [Ports and Routes](../../deployment/ports-and-routes.md).

## Configuration

Configure this service through `.env`, the interactive wizard, or CLI flags where available. Prefer SOURCE variables and documented env vars over direct `docker-compose.yml` edits.

```bash
LOCAL_DEEP_RESEARCHER_SOURCE=<option>
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

> Auto-generated section — the **Current** subsections are derived from `services/local-deep-researcher/service.yml`. Re-run `python -m bootstrapper.docs.regen local-deep-researcher` after manifest changes.

### Current — Upstream (this service depends on)

| Service | Type | Mechanism | Failure mode |
|---|---|---|---|
| supabase | required | `http://supabase:<port>` | _unspecified_ |
| weaviate | optional | `(optional — wired conditionally; see manifest)` | _unspecified_ |
| litellm | required | `http://litellm:<port>` | _unspecified_ |
| chatterbox | optional | `(optional — wired conditionally; see manifest)` | _unspecified_ |
| docling | optional | `(optional — wired conditionally; see manifest)` | _unspecified_ |
| parakeet | optional | `(optional — wired conditionally; see manifest)` | _unspecified_ |
| searxng | required | `http://searxng:<port>` | _unspecified_ |
| searxng | optional | `(optional — wired conditionally; see manifest)` | _unspecified_ |
| speaches | optional | `(optional — wired conditionally; see manifest)` | _unspecified_ |
| n8n | optional | `(optional — wired conditionally; see manifest)` | _unspecified_ |

### Current — Downstream (services that depend on this)

| Service | Type | Mechanism |
|---|---|---|
| kong | required | kong declares local-deep-researcher in depends_on.required |
| open-webui | optional | open-webui lists local-deep-researcher as optional dep |

### Architecture diagram

![local-deep-researcher architecture](./architecture.svg)

[Open the interactive HTML diagram](./architecture.html) for a full-screen view.

### Future — Missing pair integrations

_No high-confidence opportunities identified._

### Future — Candidate new services

_No high-confidence opportunities identified._

### Future — Unused features in this service

_No high-confidence opportunities identified._
