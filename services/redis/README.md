# services/redis — Redis cache & queue

The stack's single Redis instance — cache for Open WebUI, queue backend
for n8n (queue mode), session store for several consumers.

## Containers

| Container | Role | Image var |
|---|---|---|
| `redis` | Redis 7.x | `REDIS_IMAGE` |

`REDIS_SOURCE` is intentionally not a wizard-rendered toggle (Redis is
mandatory). The single named volume `redis-data` persists state.

Redis was the first service carved out of the monolithic
`docker-compose.yml` during the configuration modularization, so its
manifest doubles as a reference template for new services.

## See also

- [`docs/services/redis.md`](../../docs/services/redis.md) — full service docs.
- [`docs/CONTRIBUTING-services.md`](../../docs/CONTRIBUTING-services.md) — how to add a new service folder using this one as a template.
