# services/weaviate — Weaviate vector DB family

Three containers, two named volumes.

## Containers

| Container | Role | Image var |
|---|---|---|
| `weaviate` | Vector database (port `WEAVIATE_PORT`) | `WEAVIATE_IMAGE` |
| `weaviate-init` | One-shot alpine sidecar — provisions collections + writes `/shared/weaviate-config.env` (entrypoint `/scripts/init-weaviate.sh`) | `WEAVIATE_INIT_IMAGE` |
| `multi2vec-clip` | CLIP transformer service for multimodal vectorization (active iff `MULTI2VEC_CLIP_SOURCE != disabled`) | `MULTI2VEC_CLIP_IMAGE` |

## Subfolders

- `init/scripts/` — bind-mounted into `weaviate-init` at `/scripts`. Also bind-mounted into `weaviate` as a read-only convenience.

## CLIP toggle

`multi2vec-clip` is profile-gated: the wizard's CLIP source defaults to `disabled`. When enabled (`MULTI2VEC_CLIP_SOURCE=container-cpu` or `container-gpu`), the container starts and weaviate-init wires the relevant `text2vec-*` / `multi2vec-clip` collection vectorizers; otherwise weaviate-init falls back to `text2vec-openai` via the LiteLLM-routed embedding.
