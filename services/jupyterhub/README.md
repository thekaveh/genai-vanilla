# services/jupyterhub — JupyterHub DS/ML + LLM workbench

Single-user Jupyter Lab environment bundled with starter notebooks. The
image is now a general-purpose DS/ML environment: it ships PyTorch,
PyTorch Geometric, and PyTorch Lightning alongside the stack's LLM /
vector / graph client libraries. Suitable for running ML training and
inference notebooks in addition to the original LLM/RAG demos.

## Containers

| Container | Role | Image var |
|---|---|---|
| `jupyterhub` | JupyterHub + lab + bundled notebooks | `JUPYTERHUB_IMAGE` (used as `BASE_IMAGE` in `build/Dockerfile`) |

## Subfolders

- **`build/`** — Dockerfile, `requirements.txt`, and the bundled
  `notebooks/` directory (mounted read-only at `/home/jovyan/notebooks`).
  The Dockerfile installs the DS/ML stack (torch, PyG, pytorch-lightning)
  plus LangChain / LiteLLM / Weaviate / Neo4j Python clients on top of the
  upstream `jupyter/datascience-notebook` image. See `build/README.md`
  for the notebook list.

## See also

- [`docs/services/jupyterhub.md`](../../docs/services/jupyterhub.md) — full service docs (auth, login URL, notebook tour).
