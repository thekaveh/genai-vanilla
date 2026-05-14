# services/kong — Kong API Gateway

DB-less Kong in front of every public-facing service in the stack. The
single user-visible URL surface — `KONG_HTTP_PORT` (default `63002`) —
routes to backend, comfyui, hermes, jupyterhub, n8n, open-web-ui,
searxng, and the supabase family (api, auth, meta, realtime, storage,
studio).

## Containers

| Container | Role | Image var |
|---|---|---|
| `kong-api-gateway` | DB-less Kong proxy, dynamic config from `volumes/api/kong-dynamic.yml` | `KONG_API_GATEWAY_IMAGE` |

## Where the routes live

The route + upstream definitions are **not** in this folder — they live
in the stack-wide `volumes/api/kong-dynamic.yml`, bind-mounted into the
container at `/home/kong/kong.yml:ro`. Edit there to add a route, then
restart kong-api-gateway. The upstream container names referenced from
that file must match the `container_name:` values in each service's
compose fragment.

Kong is intentionally the **last** service in the root
`docker-compose.yml` include order — it depends on every upstream it
routes to.

## See also

- [`docs/services/kong.md`](../../docs/services/kong.md) — full route table, dashboard credentials, TLS notes.
- `volumes/api/kong-dynamic.yml` — the live route config.
