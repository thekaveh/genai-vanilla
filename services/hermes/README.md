# services/hermes — Hermes Agent family

Two containers, one named volume.

## Containers

| Container | Role | Image var |
|---|---|---|
| `hermes` | Nous Research Hermes Agent — programmable agent runtime over LiteLLM | `HERMES_IMAGE` |
| `hermes-init` | One-shot alpine sidecar — renders `/opt/data/config.yaml` from a template based on which sibling services are active | `HERMES_INIT_IMAGE` (alpine) |

## Subfolders

- `init/scripts/` — bind-mounted into `hermes-init` at `/scripts`. Entrypoint is `/scripts/init-hermes.sh`.
- `init/templates/` — bind-mounted into `hermes-init` at `/templates`. `config.yaml.tmpl` is rendered by `init-hermes.sh` with env-var substitution, gracefully omitting blocks when a backing service is disabled.

## Routing

| Route | Surface |
|---|---|
| API | `http://localhost:${HERMES_API_PORT}` |
| Dashboard | `http://localhost:${HERMES_DASHBOARD_PORT}` |
| Kong | `http://hermes.localhost:${KONG_HTTP_PORT}` (after `--setup-hosts`) |
| LiteLLM model | `hermes-agent` (registered by `services/litellm/init/scripts/init.py` when `HERMES_SOURCE != disabled`) |

## See also

- [`docs/services/hermes.md`](../../docs/services/hermes.md) — full service docs.
