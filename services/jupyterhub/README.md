# JupyterHub - Data Science IDE

**Port:** 63081
**Category:** Application Tier
**Dependencies:** PostgreSQL, Redis, LiteLLM (gateway to Ollama / cloud LLMs), Weaviate, Neo4j

---

## 1. Overview

JupyterHub provides an interactive Jupyter Lab environment pre-configured with access to all GenAI Vanilla Stack services. It's designed for data scientists and AI engineers to experiment, prototype, and develop AI applications.

## 2. Quick Start

### 2.1 Access JupyterHub

```bash
# Start the stack (JupyterHub enabled by default)
./start.sh

# Access at: http://localhost:63081
```

### 2.2 Disable JupyterHub

```bash
# Temporarily disable
./start.sh --jupyterhub-source disabled

# Permanently disable (edit .env)
JUPYTERHUB_SOURCE=disabled
```

## 3. Features

- **Pre-installed AI Libraries**: OpenAI SDK (pointed at LiteLLM), LangChain, LlamaIndex, Transformers
- **Database Clients**: Weaviate, Neo4j, PostgreSQL, Redis, Supabase
- **Sample Notebooks**: 7 ready-to-use notebooks demonstrating service integration
- **Persistent Storage**: All notebooks saved in Docker volumes
- **Environment Variables**: Auto-configured connections to all services

## 4. Configuration

### 4.1 Environment Variables (`.env`)

```bash
JUPYTERHUB_SOURCE=container     # Options: container, disabled
# Using python-3.11 tag for stable builds and Docker cache optimization
# Note: :latest tag causes rebuilds every time (5-10 min). Use specific version for caching.
JUPYTERHUB_IMAGE=jupyter/datascience-notebook:python-3.11
JUPYTERHUB_PORT=63081
JUPYTERHUB_TOKEN=               # Optional: authentication token
```

> **Performance Tip**: The `python-3.11` tag provides stable Docker layer caching, reducing rebuild times from 8-10 minutes to 5-10 seconds on subsequent starts. Using `:latest` forces Docker to check for updates and rebuild layers every time.

### 4.2 Authentication

- **No token set**: Auto-generated token shown in logs
- **Custom token**: Set `JUPYTERHUB_TOKEN` in `.env`
- **View token**: `docker logs genai-jupyterhub | grep token`

## 5. Sample Notebooks

| Notebook | Description |
|----------|-------------|
| `00_environment_check.ipynb` | Verify all service connections |
| `01_litellm_basics.ipynb` | LLM inference via the LiteLLM gateway (Ollama upstream) |
| `02_langchain_rag.ipynb` | RAG pipeline with Weaviate |
| `03_neo4j_graphs.ipynb` | Knowledge graph queries |
| `04_supabase_data.ipynb` | Database and storage operations |
| `05_comfyui_images.ipynb` | AI image generation |
| `06_n8n_workflows.ipynb` | Workflow automation |
| `07_ray_cluster.ipynb` | Distributed compute on the Ray cluster |

## 6. Service Integration Examples

### 6.1 Connect to the LLM gateway (LiteLLM)

Every notebook talks to LiteLLM via the OpenAI-compatible API — never to Ollama directly. The container has `OPENAI_API_BASE` and `OPENAI_API_KEY` pre-set from `LITELLM_BASE_URL` and `LITELLM_API_KEY` (which equals `LITELLM_MASTER_KEY`).

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("OPENAI_API_BASE"),  # e.g. http://litellm:4000/v1
    api_key=os.getenv("OPENAI_API_KEY"),    # equals $LITELLM_API_KEY
)

response = client.chat.completions.create(
    model="ollama/qwen3.6:latest",  # or "gpt-4o", "claude-sonnet-4-6", etc.
    messages=[{"role": "user", "content": "Hello!"}],
)
print(response.choices[0].message.content)
```

LangChain users should reach for `ChatOpenAI` / `OpenAIEmbeddings` against the same env vars:

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="ollama/qwen3.6:latest")  # picks up OPENAI_API_BASE / OPENAI_API_KEY
```

### 6.2 Connect to Weaviate (Vector DB)

```python
import os
import weaviate

client = weaviate.connect_to_custom(
    http_host=os.getenv("WEAVIATE_URL").replace("http://", "").split(":")[0],
    http_port=8080
)
```

### 6.3 Connect to Neo4j (Graph DB)

```python
import os
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD"))
)
```

## 7. Data Persistence

- **Work Directory**: `/home/jovyan/work` - Persisted in `jupyterhub-data` volume
- **Sample Notebooks**: `/home/jovyan/notebooks` - Read-only, copy to `work/` to modify
- **Shared Config**: `/shared` - Weaviate configuration (read-only)

## 8. Custom Packages

### 8.1 Temporary Installation

```bash
!pip install package-name
```

### 8.2 Permanent Installation

1. Edit `services/jupyterhub/build/requirements.txt`
2. Rebuild: `docker compose build jupyterhub`
3. Restart: `./stop.sh && ./start.sh`

## 9. Troubleshooting

### 9.1 Cannot Access JupyterHub

**Check if running:**
```bash
docker ps | grep jupyterhub
```

**View logs:**
```bash
docker logs genai-jupyterhub
```

### 9.2 Token Not Working

**Get current token:**
```bash
docker logs genai-jupyterhub | grep "token="
```

**Set permanent token:**
```bash
# In .env
JUPYTERHUB_TOKEN=my-secret-token
```

### 9.3 Port Already in Use

```bash
# In .env
JUPYTERHUB_PORT=64048  # Use different port
```

### 9.4 Out of Memory

Increase Docker memory:
- Docker Desktop → Settings → Resources → Memory
- Recommended: 8GB+ for data science workloads

## 10. Advanced Configuration

### 10.1 GPU-aware workflows

JupyterHub itself is configured through `.env` and the stack startup flow. Prefer enabling GPU-backed upstream services through their SOURCE variables, for example `LLM_PROVIDER_SOURCE=ollama-container-gpu`, `COMFYUI_SOURCE=container-gpu`, or `MULTI2VEC_CLIP_SOURCE=container-gpu`.

Avoid direct `docker-compose.yml` edits for normal operation; local compose edits are unsupported experiments and can be overwritten or invalidated by future stack changes.

### 10.2 Multi-user Setup

For authentication, create `jupyterhub_config.py`:

```python
c.JupyterHub.authenticator_class = 'firstuseauthenticator.FirstUseAuthenticator'
```

## 11. Architecture

JupyterHub runs inside the Docker Compose network and receives environment variables for the services that are enabled. It reaches LLMs through the always-on LiteLLM gateway (`LITELLM_BASE_URL` / `LITELLM_API_KEY`, also exported as `OPENAI_API_BASE` / `OPENAI_API_KEY`) and connects directly to Weaviate, Neo4j, PostgreSQL/Supabase, Redis, ComfyUI, n8n, STT/TTS, and document-processing services when those services are available.

For the current high-level stack diagram, see [Architecture Diagram](../../docs/diagrams/architecture.svg).

## 12. Resources

- [Jupyter Lab Documentation](https://jupyterlab.readthedocs.io/)
- [JupyterHub Documentation](https://jupyterhub.readthedocs.io/)
- [Sample Notebooks](./build/notebooks/)
- [GenAI Stack Docs](../../README.md)

## 13. Support

- **Logs**: `docker logs genai-jupyterhub`
- **Issues**: [GitHub Issues](https://github.com/thekaveh/genai-vanilla/issues)
- **Docs**: [Full Documentation](../../README.md)

## 14. Dependencies & Integrations

> Auto-generated section — the **Current** subsections are derived from `services/jupyterhub/service.yml`'s `data_flow.calls` field (and inverse passes). Re-run `python -m bootstrapper.docs.regen jupyterhub` after manifest changes.

### 14.1 Current — Upstream (this service calls)

| Service | Category |
|---|---|
| ray | infra |
| minio | data |
| neo4j | data |
| supabase | data |
| weaviate | data |
| litellm | llm |
| hermes | agents |

### 14.2 Current — Downstream (services that call this)

| Service | Category |
|---|---|
| kong | infra |

### 14.3 Architecture diagram

![jupyterhub architecture](./architecture.svg)

[Open the interactive HTML diagram](./architecture.html) for a full-screen view.

### 14.4 Future — Missing pair integrations

- **jupyterhub ↔ minio** — *Why:* notebooks need durable artifact storage (datasets, model weights, parquet shards) instead of an isolated Docker volume. *Mechanism:* inject `AWS_S3_ENDPOINT_URL=http://minio:9000` plus `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` and pre-install `s3fs`/`boto3` so `pd.read_parquet("s3://...")` works. *Effort:* small. *Confidence:* high.
- **jupyterhub ↔ backend** — *Why:* the FastAPI backend already aggregates LiteLLM, Weaviate, Neo4j, ComfyUI, and Hermes so notebooks should reuse it instead of hand-rolling per-upstream clients. *Mechanism:* adaptive env `BACKEND_BASE_URL=http://backend:8000` consumed via `httpx` against `/v1/...` routes. *Effort:* small. *Confidence:* high.
- **jupyterhub ↔ hermes** — *Why:* researchers want to drive the tool-using agent runtime from notebooks (chain prompts, inspect intermediate tool calls) without going through Open WebUI. *Mechanism:* `HERMES_AGENT_MODEL=hermes-agent` env hint plus a sample notebook calling the existing `OPENAI_API_BASE` LiteLLM alias. *Effort:* small. *Confidence:* high.
- **jupyterhub ↔ local-deep-researcher** — *Why:* long LangGraph deep-research runs should be launchable from a notebook and streamable into a dataframe. *Mechanism:* `DEEP_RESEARCHER_BASE_URL=http://local-deep-researcher:2024` plus an SSE client snippet against LangGraph's `/runs/stream`. *Effort:* medium. *Confidence:* medium.
- **jupyterhub ↔ openclaw** — *Why:* unattended notebook jobs (training, sweeps, embeddings) should ping Slack/Discord when they finish. *Mechanism:* inject `OPENCLAW_WEBHOOK_URL=http://openclaw:<port>/webhook/notify` and post JSON from a util helper. *Effort:* small. *Confidence:* medium.

### 14.5 Future — Candidate new services

- **MLflow** ([details](../../docs/research/candidates/mlflow.md)) — *Headline:* self-hosted experiment-tracking, run-history, and model-registry server backed by Supabase Postgres + MinIO artifacts. *Wires into:* jupyterhub, backend, supabase, minio, n8n.
- **Label Studio** ([details](../../docs/research/candidates/label-studio.md)) — *Headline:* multi-user annotation studio for text, image, audio, and document labeling that produces supervised datasets for downstream ingestion. *Wires into:* jupyterhub, backend, weaviate, minio, supabase.

### 14.6 Future — Unused features in this service

- **Real multi-user JupyterHub (DockerSpawner + Authenticator)** — *Why pursue:* today the container is single-user `jupyter/datascience-notebook` despite the service name, so a proper Hub with `DockerSpawner` and `NativeAuthenticator`/OAuth would let multiple humans share the stack. *Effort:* large.
- **Jupyter AI extension wired to LiteLLM** — *Why pursue:* `jupyter-ai` accepts any OpenAI-compatible base URL, so pointing it at `LITELLM_BASE_URL` exposes every gateway model as a first-class `%ai` magic. *Effort:* small.
- **GPU enablement for the notebook container** — *Why pursue:* the image already ships PyTorch + PyG but the manifest exposes no `container-gpu` source, so heavy training falls back to CPU even when the host has a GPU. *Effort:* medium.
- **jupyter-server-proxy for ComfyUI/n8n** — *Why pursue:* the proxy is already in `requirements.txt` but unused; mounting ComfyUI and n8n behind `/proxy/<service>/` would embed those UIs in iframes without leaving the lab. *Effort:* small.
- **Persistent kernel state via ipyparallel** — *Why pursue:* long-running RAG/agent loops lose state on kernel restart; an `ipyparallel` cluster (workers as sidecars) would survive restarts. *Effort:* medium.
