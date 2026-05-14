# services/local-deep-researcher — LangGraph research agent

Local-only deep-research agent built on LangGraph; iterates web search ↔
LLM-summarise loops via SearXNG and the LiteLLM gateway.

## Containers

| Container | Role | Image var |
|---|---|---|
| `local-deep-researcher` | LangGraph CLI / FastAPI wrapper around the research loop | `LOCAL_DEEP_RESEARCHER_IMAGE` (used as `BASE_IMAGE` in `build/Dockerfile`) |

## Subfolders

- **`build/`** — Dockerfile + `requirements.txt` + entrypoint scripts. At
  container **startup** (not build time), `build/scripts/docker-entrypoint.sh`
  clones the upstream `local-deep-researcher` repo into the named volume
  `local-deep-researcher-repo` (on subsequent restarts it tries `git pull
  --ff-only` and falls back to a re-clone if that fails). The agent code
  is therefore editable without rebuilding the image. First startup takes
  ~2–5 min because of the clone + `uv pip install`; subsequent restarts
  are fast (the volume persists). The Dockerfile itself only stages an
  empty target dir.

## See also

- [`docs/services/local-deep-researcher.md`](../../docs/services/local-deep-researcher.md) — full service docs.
- [`services/searxng/`](../searxng/) — the search backend the agent calls.
