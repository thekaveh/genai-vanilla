---
category-fit: data
generated: 2026-05-19
license: RSALv2
name: Redis Stack (redis-stack-server)
referenced-by: [redis]
slug: redis-stack
type: external-service
upstream: https://redis.io/docs/latest/operate/oss_and_stack/stack-with-enterprise/
---

# Redis Stack (redis-stack-server)

## Headline
Drop-in replacement for the base `redis:7-alpine` image that bundles RediSearch, RedisJSON, RedisBloom, and RedisTimeSeries — unlocks vector search, native JSON storage, probabilistic dedup, and time-series metrics on the existing Redis instance.

## Problem it solves
The stack uses Redis only as a key-value cache/queue today, leaving advanced workloads (embedding caches, semantic-response caches, BullMQ JSON payloads, agent tool-call dedup, request-rate time-series) to roll their own structures on top of plain strings. Redis Stack ships the four canonical modules in one image, so consumers gain `FT.SEARCH`, `JSON.*`, `BF.*`, and `TS.*` commands without operating a second datastore.

## Stack wiring sketch
- Replace `REDIS_IMAGE` default in `services/redis/service.yml` from `redis:7.2.14-alpine` to `redis/redis-stack-server:7.4` behind a new `REDIS_VARIANT` toggle (`oss | stack`).
- backend → redis (Stack) via `FT.SEARCH` for lightweight semantic-cache lookups (avoid a full Weaviate hop for short-TTL queries).
- weaviate ↔ redis (Stack) — Redis Stack's vector index is NOT a Weaviate replacement, but it's a fast L1 cache for embeddings (`SET emb:<sha> <vec>` with `FT.SEARCH` over a HNSW index).
- n8n → redis (Stack) via the JSON.* commands for richer queue payloads than the current Bull encoding.
- hermes → redis (Stack) via RedisBloom `BF.EXISTS` for tool-call dedup.

## Effort
small — Image swap + version bump; all existing consumers (kong, n8n, backend, litellm, open-webui, jupyterhub) continue to work because Redis Stack is wire-compatible with vanilla Redis. The work is one env var, one manifest note, and one CHANGELOG entry.

## Risks & open questions
- Image is ~10× larger than `redis:7.2.14-alpine` (250 MB vs 30 MB); justify the gain.
- License: Redis Stack uses the Redis Source Available License v2 (RSALv2) since Redis 7.4 — fine for self-hosting, blocks redistribution-as-a-service.
- Existing `--appendonly yes` flag continues to work; module-specific persistence (FT indices) needs a brief audit.
- AGPLv3 of some bundled modules vs RSALv2 of others — confirm before adoption.

## Why now (and why not sooner)
The stack already runs Weaviate for heavy vector search, but several emerging use-cases (embedding cache for the doc-processor, semantic-cache for LiteLLM responses, agent-tool-call dedup) want sub-millisecond latency that Weaviate doesn't deliver. Adding Redis Stack costs one image swap and keeps every existing consumer working unchanged.

## Upstream evidence
- https://redis.io/docs/latest/operate/oss_and_stack/stack-with-enterprise/
- https://hub.docker.com/r/redis/redis-stack-server
- https://redis.io/docs/latest/develop/interact/search-and-query/
