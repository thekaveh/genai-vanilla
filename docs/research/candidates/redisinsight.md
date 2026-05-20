---
slug: redisinsight
name: RedisInsight
type: external-service
category-fit: data
generated: 2026-05-19
upstream: https://github.com/RedisInsight/RedisInsight
license: SSPL-1.0
referenced-by: [redis]
---

# RedisInsight

## Headline
Official self-hostable Redis GUI for browsing keys, inspecting streams, profiling commands, and debugging the half-dozen stack services that share the redis instance.

## Problem it solves
Today the only way to inspect Redis state across the stack — kong's rate-limit cache, n8n's BullMQ queues, open-webui's websocket store on db=2, jupyterhub's session store on db=3, the litellm cache, the backend's session keys — is `redis-cli` inside the container. There's no view of stream lag, BullMQ stuck jobs, or a slow-command profile across consumers. RedisInsight surfaces all of this in one web UI and adds bulk operations + a CLI workbench with auto-complete.

## Stack wiring sketch
- redisinsight → redis via `REDIS_HOST=redis` + `REDIS_PASSWORD=${REDIS_PASSWORD}` (single connection, browses all DB indices).
- kong → redisinsight via a new `redisinsight.localhost` alias (Kong route, `preserve_host: true`).
- backend → redisinsight only indirectly (operators inspecting backend's session keys via the GUI).

## Effort
small — One container, one Kong alias, one SOURCE variant (`container | disabled`); image is `redis/redisinsight:latest`, default port 5540, healthcheck on `/api/health`.

## Risks & open questions
- License is SSPL-1.0 (Server Side Public License), not OSI-approved — needs a note in the SOURCE description and probably defaults to `disabled` in the wizard.
- No built-in auth in the OSS image; must sit behind Kong with a basic-auth plugin or be marked dev-only.
- v2 stores its own config in a volume — small but worth a named volume entry.

## Why now (and why not sooner)
Eight stack services now write to Redis on five different DB indices. Debugging "why is n8n's BullMQ stuck?" or "what's eating Kong's rate-limit memory?" requires per-service `redis-cli` sessions today. A single GUI cuts the loop from minutes to seconds and makes Redis observable in the same way Supabase Studio makes Postgres observable.

## Upstream evidence
- https://github.com/RedisInsight/RedisInsight
- https://redis.io/docs/latest/operate/redisinsight/
- https://hub.docker.com/r/redis/redisinsight
