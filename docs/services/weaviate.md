# Weaviate

**Port:** 63019 / 63020
**SOURCE variable:** `WEAVIATE_SOURCE`
**SOURCE options:** container, localhost, disabled

## Overview

Vector database used for semantic search, RAG, embeddings, n8n workflows, Backend features, and notebooks.

## Access

| Path | URL | Notes |
|---|---|---|
| Direct | http://localhost:63019 | Works when the service is enabled in container mode and the port is exposed. |
| Kong | — | Requires `./start.sh --setup-hosts`; only available for services with Kong routes. |

See the canonical port table at [Ports and Routes](../deployment/ports-and-routes.md).

## Configuration

Configure this service through `.env`, the interactive wizard, or CLI flags where available. Prefer SOURCE variables and documented env vars over direct `docker-compose.yml` edits.

```bash
WEAVIATE_SOURCE=<option>
WEAVIATE_URL=http://weaviate:8080
```

Use `./start.sh` for the guided wizard, or pass a targeted flag for scripted changes when the CLI exposes one.

### Multi2Vec CLIP module

The default stack keeps the multimodal CLIP vectorizer enabled:

```bash
MULTI2VEC_CLIP_SOURCE=container-cpu
WEAVIATE_ENABLE_MODULES=text2vec-ollama,text2vec-openai,multi2vec-clip,generative-ollama,generative-openai
CLIP_INFERENCE_API=http://multi2vec-clip:8080
```

If you disable the CLIP provider, remove `multi2vec-clip` from `WEAVIATE_ENABLE_MODULES` and leave `CLIP_INFERENCE_API` blank:

```bash
MULTI2VEC_CLIP_SOURCE=disabled
WEAVIATE_ENABLE_MODULES=text2vec-ollama,text2vec-openai,generative-ollama,generative-openai
CLIP_INFERENCE_API=
```

## Dependencies and integration

The service participates in the Docker Compose network and may be consumed by the Backend API, Open WebUI, JupyterHub, n8n, or init containers depending on which SOURCE modes are enabled.

Optional consumers should use `WEAVIATE_URL` and perform feature-level readiness checks instead of requiring the Weaviate container as a hard Compose startup dependency. This lets n8n, JupyterHub, and other adaptive services still start when Weaviate is disabled, localhost-backed, or externalized.

## Troubleshooting

```bash
# Check service status
docker compose ps

# Check logs; replace SERVICE with the compose service name when needed
docker compose logs -f SERVICE
```

For general startup and routing issues, see [Troubleshooting](../quick-start/troubleshooting.md).
