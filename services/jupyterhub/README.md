# services/jupyterhub — JupyterHub data-science notebooks

Multi-user JupyterHub bundled with starter notebooks that exercise the
stack's LLM / vector / graph backends.

## Containers

| Container | Role | Image var |
|---|---|---|
| `jupyterhub` | JupyterHub + lab + bundled notebooks | `JUPYTERHUB_IMAGE` (used as `BASE_IMAGE` in `build/Dockerfile`) |

## Subfolders

- **`build/`** — Dockerfile, `requirements.txt`, and the bundled
  `notebooks/` directory (mounted read-only at `/home/jovyan/notebooks`).
  The Dockerfile installs LangMem / LiteLLM / Weaviate / Neo4j Python
  clients on top of the upstream `jupyter/datascience-notebook` image. See
  `build/README.md` for the notebook list.

## See also

- [`docs/services/jupyterhub.md`](../../docs/services/jupyterhub.md) — full service docs (auth, login URL, notebook tour).
