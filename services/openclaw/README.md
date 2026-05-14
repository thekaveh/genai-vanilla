# services/openclaw — OpenClaw MCP-gateway family

Two containers, two named volumes.

## Containers

| Container | Role | Image var |
|---|---|---|
| `openclaw-gateway` | OpenClaw MCP gateway — exposes stack services as MCP tools to Claude / Hermes / external agents | `OPENCLAW_GATEWAY_IMAGE` |
| `openclaw-init` | One-shot init — wires service endpoints into the gateway config | `OPENCLAW_INIT_IMAGE` (alpine) |

## Named volumes (2)

- `openclaw-config` — gateway rendered config, persisted across restarts
- `openclaw-workspace` — sandboxed workspace for tool calls that need a writable directory

## Source variants

`OPENCLAW_SOURCE` defaults to `container`; `disabled` skips the gateway entirely. The init sidecar always runs when the gateway runs and adapts the config to whichever sibling services are active (parakeet, hermes, comfyui, …).

## See also

- [`docs/services/openclaw.md`](../../docs/services/openclaw.md) — full service docs.
