# services/searxng — SearXNG privacy metasearch

The stack's web-search backend; queried by the
[local-deep-researcher](../local-deep-researcher/) agent and by n8n
workflows.

## Containers

| Container | Role | Image var |
|---|---|---|
| `searxng` | SearXNG metasearch | `SEARXNG_IMAGE` |

## Subfolders

- **`config/`** — bind-mounted to `/etc/searxng` at runtime.
  - `settings.yml` — **live config**. Hand-edited; includes local
    customizations (rate-limit `disabled: true` markers on the Brave
    engines, custom format / engine list). Edit this file and restart
    `searxng` to apply.

## See also

- [`docs/services/searxng.md`](../../docs/services/searxng.md) — full service docs (engines, ports, throttling).
