# services/ollama — Ollama local-LLM family

Two containers, one named volume.

## Containers

| Container | Role | Image var |
|---|---|---|
| `ollama` | Ollama server (port `OLLAMA_PORT`) | `OLLAMA_IMAGE` |
| `ollama-pull` | One-shot sidecar — `ollama pull` for every model in `OLLAMA_USER_MODELS` + `OLLAMA_CUSTOM_MODELS` before any consumer container starts | `OLLAMA_IMAGE` (same image, different entrypoint) |

## Subfolders

- `pull/scripts/` — bind-mounted into `ollama-pull` at `/scripts`. Entrypoint is `/scripts/pull.sh`.

`ollama-pull` is sequenced ahead of `litellm-init` (tier 1 of the init order) so the LiteLLM model_list builds against a registry of already-downloaded models.

## Source variants

`OLLAMA_SOURCE` selects: `container-cpu`, `container-gpu`, `external` (point at an existing host or remote Ollama via `OLLAMA_EXTERNAL_URL`), `disabled`. The `external` variant skips the `ollama` container and routes through `OLLAMA_ENDPOINT` resolved to your URL.

## See also

- [`docs/services/ollama.md`](../../docs/services/ollama.md) — full service docs.
