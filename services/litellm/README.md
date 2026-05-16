# services/litellm — LiteLLM gateway family

Three containers, two init tiers, one always-on gateway.

## Containers

| Container | Role | Image var |
|---|---|---|
| `llm-catalog-init` | Init tier 0 — UPSERTs the curated model catalog (`bootstrapper/utils/llm_catalog.py`) into `public.llms` and applies wizard model selections | built from `./catalog-init/` |
| `litellm-init` | Init tier 1 — queries `public.llms WHERE active = true` and renders `volumes/litellm/config.yaml` with per-provider routing rules | built from `./init/` |
| `litellm` | The gateway proxy — receives requests at `:4000/v1` and routes to providers per the rendered config | `LITELLM_IMAGE` |

`llm-catalog-init` must complete before `litellm-init`, which must complete before `litellm` starts.

## Subfolders

- `init/scripts/` — bind-mounted into `litellm-init`; entrypoint is `/scripts/init.py`. Renders `volumes/litellm/config.yaml`.
- `catalog-init/scripts/` — bind-mounted into `llm-catalog-init`; entrypoint is `/scripts/sync-catalog.py`. Reads `bootstrapper/utils/llm_catalog.py` (via the `../../bootstrapper/utils:/catalog:ro` cross-folder mount) and UPSERTs into `public.llms`.

## Cross-hierarchy bind mounts (intentional)

The fragment reaches into `../../bootstrapper/utils/` (catalog source) and `../../volumes/litellm/` (runtime-rendered config). Both are stack-wide locations owned by the bootstrapper, not service-local data.

## Access

| Surface | URL |
|---|---|
| Admin dashboard (Kong alias) | `http://litellm.localhost:${KONG_HTTP_PORT}/ui/` — root path 302-redirects here. Requires `./start.sh --setup-hosts`. |
| Admin dashboard (direct port) | `http://localhost:${LITELLM_PORT}/ui/` (default `:63030`) — equivalent; the proxy root on the direct port serves Swagger UI rather than redirecting. |
| Proxy API | `http://localhost:${LITELLM_PORT}/v1/*` or `http://litellm.localhost:${KONG_HTTP_PORT}/v1/*` |
| In-network DNS | `http://litellm:4000` — sibling containers (backend, open-web-ui, jupyterhub, local-deep-researcher, hermes, weaviate) call this |

**Dashboard login**: username `${LITELLM_UI_USERNAME}` (defaults to
`admin`); password = `${LITELLM_MASTER_KEY}` (the same auto-generated
`sk-…` value used as the API Bearer token). Recover with
`grep '^LITELLM_MASTER_KEY=' .env | cut -d= -f2-`. Both env vars must
be set explicitly on the container — modern LiteLLM retired the
"master key alone authenticates the UI" fallback.

The Kong route is always-on (no toggle). Routing is defined in
`bootstrapper/utils/kong_config_generator.py::generate_litellm_service()`.
`preserve_host: True` on the route makes LiteLLM see the browser's
real Host header so login redirects use the correct hostname.

## See also

- [`docs/services/litellm.md`](../../docs/services/litellm.md) — full service docs.
