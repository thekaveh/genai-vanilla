# SOURCE Configuration Guide

This guide explains the SOURCE-based configuration system that makes the GenAI Vanilla Stack flexible and modular.

## Interactive Setup Wizard

The easiest way to configure SOURCE variables is the **interactive setup wizard**. Run `./start.sh` with no arguments to launch it. The wizard walks you through each service, shows available options with contextual hints, and validates dependencies in real time. See the [Interactive Setup Wizard Guide](../quick-start/interactive-setup-wizard.md) for details.

## Understanding SOURCE Variables

SOURCE variables control how each service is deployed - whether in a Docker container, using a localhost installation, connecting to an external service, or disabling the service entirely.

## Service SOURCE Support Matrix

This matrix lists every `*_SOURCE` variable currently exposed in `.env.example`. Detailed prose below focuses on the most common user-facing services; init/internal rows are included here so operators can understand what appears in `.env`.

| SOURCE variable | Default | Options | Category | Notes |
|---|---|---|---|---|
| `LLM_PROVIDER_SOURCE` | `ollama-container-cpu` | `ollama-container-cpu`, `ollama-container-gpu`, `ollama-localhost`, `none` | User-facing | Local Ollama upstream behind LiteLLM. Use `none` for cloud-only operation. |
| `CLOUD_OPENAI_SOURCE` | `disabled` | `enabled`, `disabled` | User-facing | Toggles OpenAI as a LiteLLM upstream. Requires `OPENAI_API_KEY`. |
| `CLOUD_ANTHROPIC_SOURCE` | `disabled` | `enabled`, `disabled` | User-facing | Toggles Anthropic as a LiteLLM upstream. Requires `ANTHROPIC_API_KEY`. |
| `CLOUD_OPENROUTER_SOURCE` | `disabled` | `enabled`, `disabled` | User-facing | Toggles OpenRouter as a LiteLLM upstream. Requires `OPENROUTER_API_KEY`. |
| `LITELLM_SOURCE` | `container` | `container` | Infrastructure / always-on | LiteLLM gateway. Always on; not user-disableable. |
| `COMFYUI_SOURCE` | `container-cpu` | `container-cpu`, `container-gpu`, `localhost`, `disabled` | User-facing | Image generation service. |
| `PROMETHEUS_SOURCE` | `disabled` | `container`, `disabled` | User-facing optional | Observability scraper + TSDB. Bundles node-exporter and cAdvisor; gates postgres-exporter / redis-exporter sidecars. |
| `GRAFANA_SOURCE` | `disabled` | `container`, `disabled` | User-facing optional | Observability dashboards + unified alerting. Pre-provisions the Prometheus datasource and 7 starter dashboards. |
| `WEAVIATE_SOURCE` | `container` | `container`, `localhost`, `disabled` | User-facing | Vector database. |
| `MINIO_SOURCE` | `container` | `container`, `disabled` | User-facing | S3-compatible artifact-tier object storage. |
| `N8N_SOURCE` | `container` | `container`, `disabled` | User-facing | Workflow automation. |
| `SEARXNG_SOURCE` | `container` | `container`, `disabled` | User-facing | Privacy metasearch. |
| `OPENCLAW_SOURCE` | `disabled` | `container`, `localhost`, `disabled` | User-facing | AI messaging agent. |
| `HERMES_SOURCE` | `container` | `container`, `localhost`, `disabled` | User-facing | Programmable AI agent runtime (Nous Research). Routes reasoning through LiteLLM and appears as the `hermes-agent` model to every consumer. |
| `STT_PROVIDER_SOURCE` | `speaches-container-cpu` | `speaches-container-cpu`, `speaches-container-gpu`, `parakeet-container-gpu`, `parakeet-localhost`, `whisper-cpp-localhost`, `disabled` | User-facing optional | Speech-to-text provider. Speaches is the CPU-friendly default; Parakeet remains for SOTA NVIDIA; whisper.cpp is the best Apple Silicon native option. |
| `TTS_PROVIDER_SOURCE` | `speaches-container-cpu` | `speaches-container-cpu`, `speaches-container-gpu`, `chatterbox-container-gpu`, `chatterbox-localhost`, `disabled` | User-facing optional | Text-to-speech provider. Speaches serves Kokoro/Piper voices; Chatterbox adds 5-sec zero-shot voice cloning. |
| `DOC_PROCESSOR_SOURCE` | `disabled` | `docling-container-gpu`, `docling-localhost`, `disabled` | User-facing optional | Document processing provider. |
| `JUPYTERHUB_SOURCE` | `container` | `container`, `disabled` | User-facing optional | Data science notebooks; adaptive integrations. |
| `MULTI2VEC_CLIP_SOURCE` | `container-cpu` | `container-cpu`, `container-gpu`, `disabled` | User-facing optional | Multimodal Weaviate vectorizer. |
| `LOCAL_DEEP_RESEARCHER_SOURCE` | `container` | `container`, `disabled` | User-facing optional | Local research/orchestration service. |
| `OPEN_WEB_UI_SOURCE` | `container` | `container`, `disabled` | Adaptive application | Main chat UI; adapts to LLM provider. |
| `BACKEND_SOURCE` | `container` | `container` | Adaptive core | Always-on Backend API; not disableable in this remediation track. |
| `REDIS_SOURCE` | `container` | `container` | Infrastructure | Cache/session/queue service. |
| `KONG_API_GATEWAY_SOURCE` | `container` | `container` | Infrastructure | API gateway and friendly host routing. |
| `NEO4J_GRAPH_DB_SOURCE` | `container` | `container`, `localhost`, `disabled` | Infrastructure / user-facing data | Graph database. |
| `SUPABASE_DB_SOURCE` | `container` | `container` | Infrastructure | PostgreSQL database. |
| `SUPABASE_META_SOURCE` | `container` | `container`, `disabled` | Infrastructure | Supabase metadata service. |
| `SUPABASE_STORAGE_SOURCE` | `container` | `container`, `disabled` | Infrastructure | Supabase storage service. |
| `SUPABASE_AUTH_SOURCE` | `container` | `container`, `disabled` | Infrastructure | Supabase auth service. |
| `SUPABASE_API_SOURCE` | `container` | `container`, `disabled` | Infrastructure | Supabase REST API. |
| `SUPABASE_REALTIME_SOURCE` | `container` | `container`, `disabled` | Infrastructure | Supabase realtime service. |
| `SUPABASE_STUDIO_SOURCE` | `container` | `container`, `disabled` | Infrastructure UI | Supabase admin UI. |
| `WEAVIATE_INIT_SOURCE` | `container` | `container`, `disabled` | Auto-managed init | Initializes Weaviate schemas/config. |
| `MINIO_INIT_SOURCE` | `container` | `container`, `disabled` | Auto-managed init | Initializes MinIO buckets, IAM policies, and service accounts. |
| `COMFYUI_INIT_SOURCE` | `container` | `container`, `disabled` | Auto-managed init | Initializes ComfyUI assets/config. |
| `N8N_INIT_SOURCE` | `container` | `container`, `disabled` | Auto-managed init | Initializes/imports n8n workflows. |
| `OPENCLAW_INIT_SOURCE` | `container` | `container`, `disabled` | Auto-managed init | Initializes OpenClaw config where applicable. |
| `HERMES_INIT_SOURCE` | `container` | `container`, `disabled` | Auto-managed init | Renders `/opt/data/config.yaml` for Hermes from environment (model, TTS, STT, ComfyUI host override). |
| `SUPABASE_DB_INIT_SOURCE` | `container` | `container`, `disabled` | Auto-managed init | Initializes Supabase database state. |

> The `litellm-init` and `llm-catalog-init` containers are mandatory and have no SOURCE toggle — they always run when the stack starts. `litellm-init` provisions the dedicated `litellm` Postgres database and renders `volumes/litellm/config.yaml` from `public.llms`; `llm-catalog-init` UPSERTs the curated catalog and the wizard's `*_USER_MODELS` selections into `public.llms`.

### Services Supporting Localhost

These services can run on your host machine instead of in containers:

| Service | SOURCE Variable | Localhost Option | Benefits |
|---------|----------------|------------------|----------|
| **Ollama** (LiteLLM upstream) | `LLM_PROVIDER_SOURCE` | `ollama-localhost` | Faster, uses existing models, less memory. LiteLLM still fronts the upstream. |
| **ComfyUI** | `COMFYUI_SOURCE` | `localhost` | Direct access, custom setups, faster |
| **Weaviate** | `WEAVIATE_SOURCE` | `localhost` | Custom configuration, performance |
| **Neo4j** | `NEO4J_GRAPH_DB_SOURCE` | `localhost` | Use an existing graph database |
| **OpenClaw** | `OPENCLAW_SOURCE` | `localhost` | Native performance, existing config |
| **Hermes Agent** | `HERMES_SOURCE` | `localhost` | Operate your real machine (shell, browser, microphone); host-installed Hermes |
| **STT Provider** | `STT_PROVIDER_SOURCE` | `parakeet-localhost`, `whisper-cpp-localhost` | Run STT natively (best on Apple Silicon — Metal+ANE for whisper.cpp, MLX for Parakeet) |
| **TTS Provider** | `TTS_PROVIDER_SOURCE` | `chatterbox-localhost` | Run Chatterbox voice cloning natively (macOS MPS / Linux) |
| **Document Processor** | `DOC_PROCESSOR_SOURCE` | `docling-localhost` | Use a host Docling service |

### Container-Only or Stack-Managed Services

Container-only and stack-managed services should normally be left at their defaults unless you are intentionally reducing the stack or debugging a specific component. Init service SOURCE variables are usually managed by the startup flow and should not be the first knob users change.

### Feature Flags (Non-SOURCE)

Some features within services are controlled by feature flags rather than SOURCE variables:

| Feature | Variable | Options | Notes |
|---------|----------|---------|-------|
| **LangMem Memory** | `LANGMEM_ENABLED` | `true`, `false` | Persistent conversation memory embedded in the Backend service. |

### Wizard Model Selections (Non-SOURCE)

The interactive wizard's per-provider multiselects persist as comma-separated env vars in `.env`. Two init containers consume them:

- **`llm-catalog-init`** registers every entry in `public.llms` (the single source of truth for what LiteLLM exposes).
- **`ollama-pull`** pre-pulls Ollama models (container sources only).

| Variable | Set by | Default | Notes |
|---|---|---|---|
| `OLLAMA_USER_MODELS` | Single unified Ollama models multiselect (source-aware; localhost/external rows are badged `[pulled]` / `[library]`). | Default-active baseline (qwen3.6:latest, qwen3-embedding:0.6b, nomic-embed-text). | Registered in `public.llms` for every Ollama source. Pulled by `ollama-pull` only for container sources. |
| `OLLAMA_CUSTOM_MODELS` | Ollama "additional models to pull" free-text step. | Empty. | Comma-separated. Pulled by `ollama-pull` for container sources only. |
| `OPENAI_USER_MODELS` | OpenAI multiselect (live `/v1/models` fetch). | Curated default-active intersection (gpt-5, gpt-5-mini, text-embedding-3-large) when key valid. | Requires `OPENAI_API_KEY`. |
| `ANTHROPIC_USER_MODELS` | Anthropic multiselect (live `/v1/models` fetch). | Curated default-active intersection (claude-opus-4-7, claude-sonnet-4-6) when key valid. | Requires `ANTHROPIC_API_KEY`. |
| `OPENROUTER_USER_MODELS` | OpenRouter multiselect (live `/api/v1/models` fetch). | `openrouter/auto` when reachable. | Requires `OPENROUTER_API_KEY`. |

## Detailed SOURCE Configurations

### LLM access (LiteLLM gateway + Ollama upstream + cloud toggles)

LLM access in this stack is split between **LiteLLM** (the always-on OpenAI-compatible gateway every consumer reads) and four configurable upstreams behind it: an Ollama engine plus three cloud providers. See [LiteLLM Gateway](../../services/litellm/README.md) for the consumer-facing surface; the variables below pick what LiteLLM forwards to.

#### `LLM_PROVIDER_SOURCE` — Ollama upstream (single-select)

##### `ollama-container-cpu` (Default)
```bash
LLM_PROVIDER_SOURCE=ollama-container-cpu
```
- **Use case**: Default setup, no local Ollama required
- **Pros**: No setup needed, works everywhere
- **Cons**: Higher memory usage, slower model loading
- **Requirements**: None

##### `ollama-container-gpu`
```bash
LLM_PROVIDER_SOURCE=ollama-container-gpu
```
- **Use case**: GPU acceleration in container
- **Pros**: GPU acceleration, no local setup
- **Cons**: Requires NVIDIA GPU + Docker GPU support
- **Requirements**: NVIDIA Container Toolkit

##### `ollama-localhost`
```bash
LLM_PROVIDER_SOURCE=ollama-localhost
```
- **Use case**: Use existing Ollama installation
- **Pros**: Faster startup, reuse models, less container memory
- **Cons**: Requires local Ollama setup
- **Requirements**: Ollama installed and running locally

Setup for localhost:
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve &

# Pull required models
ollama pull qwen3.6:latest
ollama pull qwen3-embedding:0.6b
```

##### `none`
```bash
LLM_PROVIDER_SOURCE=none
```
- **Use case**: Cloud-only operation (no local Ollama engine)
- **Pros**: Minimal local resource usage; LiteLLM forwards everything to enabled cloud providers
- **Cons**: API costs, internet dependency
- **Requirements**: At least one of `CLOUD_OPENAI_SOURCE`, `CLOUD_ANTHROPIC_SOURCE`, `CLOUD_OPENROUTER_SOURCE` must be `enabled`. The bootstrapper refuses to start when `LLM_PROVIDER_SOURCE=none` AND every cloud source is `disabled`.

The legacy values `LLM_PROVIDER_SOURCE=api` and `LLM_PROVIDER_SOURCE=disabled` have been removed — use `none` together with the per-provider cloud toggles below instead.

#### `CLOUD_OPENAI_SOURCE` / `CLOUD_ANTHROPIC_SOURCE` / `CLOUD_OPENROUTER_SOURCE` (multi-toggle)

Each cloud provider is an independent `enabled` / `disabled` switch — turn on as many as you want simultaneously. Consumers request model IDs against `LITELLM_BASE_URL`; LiteLLM routes per-provider based on `public.llms` rows that `llm-catalog-init` activates from the rules below.

```bash
CLOUD_OPENAI_SOURCE=enabled          # requires OPENAI_API_KEY
CLOUD_ANTHROPIC_SOURCE=enabled       # requires ANTHROPIC_API_KEY
CLOUD_OPENROUTER_SOURCE=enabled      # requires OPENROUTER_API_KEY
```

#### Per-provider activation rules (run by `llm-catalog-init` on every `docker compose up`)

| Provider state | `*_USER_MODELS` env var | Existing active rows in `public.llms` | Result |
|---|---|---|---|
| `disabled` OR no API key | (any) | (any) | All rows for that provider deactivated. |
| `enabled` + key | non-empty CSV | (any) | Activate exactly those rows; deactivate everything else for the provider. |
| `enabled` + key | empty | ≥ 1 | **Keep existing actives** — wizard / hand edits survive re-runs. |
| `enabled` + key | empty | 0 | Activate the curated `default_active=True` set (gpt-5 + gpt-5-mini + text-embedding-3-large for OpenAI, etc.) so the provider is usable out of the box. |

**Bootstrapper safety net** — `source_validator.enforce_runtime_invariants()` flips `CLOUD_*_SOURCE=enabled` back to `disabled` when the matching API key is empty and prints a warning. This protects against the "looks ready in .env, errors at first request" failure mode.

- **Use case**: Mix-and-match local + cloud, or run cloud-only with `LLM_PROVIDER_SOURCE=none`
- **Pros**: One URL/key for every consumer; provider failover and spend logging handled by LiteLLM
- **Cons**: API costs and per-provider quota considerations
- **Requirements**: The provider's API key must be present in `.env`

### COMFYUI_SOURCE

#### `container-cpu` (Default)
```bash
COMFYUI_SOURCE=container-cpu
```
- **Use case**: Default image generation
- **Pros**: Works everywhere, automatic model download
- **Cons**: Slow generation, high memory usage
- **Requirements**: None

#### `container-gpu`
```bash
COMFYUI_SOURCE=container-gpu
```
- **Use case**: Fast image generation
- **Pros**: GPU acceleration, fast generation
- **Cons**: Requires NVIDIA GPU
- **Requirements**: NVIDIA Container Toolkit

#### `localhost`
```bash
COMFYUI_SOURCE=localhost
```
- **Use case**: Existing ComfyUI installation
- **Pros**: Custom workflows, existing setups
- **Cons**: Manual setup required
- **Requirements**: ComfyUI running locally on the port given by `COMFYUI_LOCALHOST_PORT` (default `8000`; override to e.g. `8188` if your installation uses another port). The URL is derived as `http://host.docker.internal:${COMFYUI_LOCALHOST_PORT}` at compose-render time.

Setup for localhost:
```bash
# Clone ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# Install dependencies
pip install -r requirements.txt

# Start ComfyUI on the stack default localhost port
python main.py --port 8000

# If your local ComfyUI uses the common native/default port 8188 instead, set:
# COMFYUI_LOCALHOST_PORT=8188
# (URL is derived as http://host.docker.internal:8188 at compose-render time.)
```

#### `disabled`
```bash
COMFYUI_SOURCE=disabled
```
- **Use case**: No image generation needed
- **Pros**: Saves resources
- **Cons**: No image generation
- **Requirements**: None

### WEAVIATE_SOURCE

#### `container` (Default)
```bash
WEAVIATE_SOURCE=container
WEAVIATE_URL=http://weaviate:8080
```
- **Use case**: Standard vector database
- **Pros**: Easy setup, automatic configuration
- **Cons**: Container resource usage
- **Requirements**: None

The default stack also enables the optional CLIP vectorizer service. Text vectorization talks to LiteLLM via the `text2vec-openai` module — the OpenAI-compatible URL points at `LITELLM_BASE_URL` and `OPENAI_APIKEY` is set to `LITELLM_MASTER_KEY`. There is no longer a separate `text2vec-ollama` module entry.

```bash
MULTI2VEC_CLIP_SOURCE=container-cpu
WEAVIATE_ENABLE_MODULES=text2vec-openai,multi2vec-clip,generative-openai
CLIP_INFERENCE_API=http://multi2vec-clip:8080
```

If `MULTI2VEC_CLIP_SOURCE=disabled`, remove `multi2vec-clip` from `WEAVIATE_ENABLE_MODULES` (leaving `text2vec-openai,generative-openai`) and set `CLIP_INFERENCE_API=` so Weaviate does not advertise a disabled inference endpoint.

#### `localhost`
```bash
WEAVIATE_SOURCE=localhost
```
- **Use case**: Custom Weaviate setup
- **Pros**: Custom configuration, performance tuning
- **Cons**: Manual setup and maintenance
- **Requirements**: Weaviate running locally

#### `disabled`
```bash
WEAVIATE_SOURCE=disabled
```
- **Use case**: No vector search needed
- **Pros**: Reduced resource usage
- **Cons**: No semantic search capabilities
- **Requirements**: None

### MINIO_SOURCE

#### `container` (Default)
```bash
MINIO_SOURCE=container
MINIO_ENDPOINT=http://minio:9000
MINIO_PUBLIC_ENDPOINT=http://localhost:63017
```
- **Use case**: S3-compatible artifact-tier object storage (ComfyUI outputs, Backend blobs, n8n files, JupyterHub datasets, Doc Processor output)
- **Pros**: Five pre-provisioned buckets with scoped service-account credentials; complements Supabase Storage; admin console at `http://localhost:63018`
- **Cons**: Container resource usage
- **Requirements**: None

Consumer code is not auto-wired in the current release — credentials and bucket names are in `.env` so each consumer integration can opt in via env-only changes in a follow-up PR.

#### `disabled`
```bash
MINIO_SOURCE=disabled
```
- **Use case**: No artifact-tier object storage needed
- **Pros**: Saves resources; consumers fall back to Supabase Storage / local volumes
- **Cons**: No S3-compatible artifact surface available
- **Requirements**: None

### OPENCLAW_SOURCE

#### `container`
```bash
OPENCLAW_SOURCE=container
```
- **Use case**: Run OpenClaw agent in Docker
- **Pros**: Easy setup, isolated environment
- **Cons**: Container resource usage
- **Requirements**: None

#### `localhost`
```bash
OPENCLAW_SOURCE=localhost
```
- **Use case**: Use existing OpenClaw installation
- **Pros**: Native performance, persistent config
- **Cons**: Manual setup required
- **Requirements**: Node.js 22+, `npm install -g openclaw`, running `openclaw gateway`

Setup for localhost:
```bash
# Install OpenClaw
npm install -g openclaw

# Run onboarding
openclaw onboard

# Start the gateway on the stack default localhost port
openclaw gateway --port 63024

# If your local OpenClaw uses its native/default port 18789 instead, set:
# OPENCLAW_LOCALHOST_PORT=18789
# (URL is derived as http://host.docker.internal:18789 at compose-render time.)
```

#### `disabled` (Default)
```bash
OPENCLAW_SOURCE=disabled
```
- **Use case**: No AI agent needed
- **Pros**: Saves resources
- **Cons**: No messaging integration
- **Requirements**: None

### HERMES_SOURCE

The programmable AI agent runtime by Nous Research. Hermes reasons over the LiteLLM gateway and exposes an OpenAI-compatible API; `litellm-init` auto-registers `hermes-agent` as a model in the gateway when `HERMES_SOURCE != disabled`, so Open WebUI / n8n / backend / jupyterhub / openclaw all see Hermes for free.

See [Hermes Agent](../../services/hermes/README.md) for the full service doc.

#### `container` (Default)
```bash
HERMES_SOURCE=container
```
- **Use case**: Run Hermes as a stack service consumed by Open WebUI, n8n, OpenClaw, etc.
- **Pros**: Easy setup, isolated environment, available to every consumer without per-service wiring
- **Cons**: ~2–4 GB RAM, ~5.66 GB image on disk, no GPU required
- **Requirements**: `HERMES_DEFAULT_MODEL` must reference a model with ≥64K context window (stock Ollama defaults to 4096 — pull with `--ctx-size 65536` or use a cloud model)

#### `localhost`
```bash
HERMES_SOURCE=localhost
```
- **Use case**: Hermes operates your real dev machine — read/write your real files, drive your real browser, use a real microphone for voice mode
- **Pros**: Native shell/browser/audio access; bigger context budget; React/Ink TUI as a daily-driver
- **Cons**: Manual install per host; consumers still reach it via the same `HERMES_ENDPOINT` (auto-set to `http://host.docker.internal:<port>`)
- **Requirements**: Host-installed Hermes (`curl -fsSL https://hermes-agent.nousresearch.com/install.sh | sh`), then `hermes gateway run`

Setup for localhost:
```bash
# Install Hermes on the host
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | sh

# Start the gateway on the stack default localhost port
hermes gateway run

# If your local Hermes uses a different port, set:
# HERMES_LOCALHOST_PORT=<your-port>
# (URL is derived as http://host.docker.internal:<your-port> at compose-render time.)
```

#### `disabled`
```bash
HERMES_SOURCE=disabled
```
- **Use case**: No agent runtime needed; consumers see only direct LLM models in the LiteLLM dropdown
- **Pros**: Saves ~5.66 GB image disk and 2–4 GB RAM
- **Cons**: No agent loop, skills, voice, or programmable behaviour
- **Requirements**: None — `litellm-init` automatically omits the `hermes-agent` row from the model_list when disabled

### RAY_SOURCE

Ray is the stack's distributed-compute substrate (head + worker containers, `infra` category). Consumers reach it via `RAY_ADDRESS` set per source by the bootstrapper's `_generate_ray_config()` hook. See [Ray service README](../../services/ray/README.md) for the full configuration reference.

#### `disabled` (Default)
```bash
RAY_SOURCE=disabled
```
- **Use case**: No distributed compute needed; Backend's `/api/ray/*` returns 503 and JupyterHub notebooks calling `ray.init()` error cleanly
- **Pros**: Zero footprint
- **Cons**: No parallel job submission
- **Requirements**: None

#### `ray-container-cpu`
```bash
RAY_SOURCE=ray-container-cpu
RAY_WORKER_COUNT=2   # number of ray-worker replicas; 0 = head-only
```
- **Use case**: Default container deployment; suitable for dev machines without GPU passthrough
- **Pros**: Head + N workers, dashboard at `ray.localhost`, REST job-submission API, client server reachable from host Python via `ray://localhost:${RAY_CLIENT_PORT}`
- **Cons**: CPU-only — slow for heavy ML workloads. `shm_size: 4gb` required (compose handles this; rootless Docker may not honor it)
- **Requirements**: ~2-3 GB image disk + ~1 GB RAM per worker

#### `ray-container-gpu`
```bash
RAY_SOURCE=ray-container-gpu
RAY_WORKER_COUNT=2
```
- **Use case**: GPU-accelerated parallel work (multi-host Linux primarily — Mac Docker has no GPU passthrough)
- **Pros**: NVIDIA-runtime workers, same API surface as CPU mode
- **Cons**: Requires NVIDIA Container Toolkit on host. Image is ~5.9 GB
- **Requirements**: NVIDIA GPU + Container Toolkit installed on host

### PROMETHEUS_SOURCE

Prometheus is the stack's metrics scraper + TSDB, bundled with `node-exporter` (host metrics) and `cAdvisor` (container metrics) as one co-lifecycled family. The bootstrapper's `_generate_prometheus_config()` hook also scales the `postgres-exporter` (in `services/supabase/`) and `redis-exporter` (in `services/redis/`) sidecars from this same source. See [Prometheus service README](../../services/prometheus/README.md) for scrape targets and configuration details.

#### `disabled` (Default)
```bash
PROMETHEUS_SOURCE=disabled
```
- **Use case**: Cold-start fast, no observability overhead
- **Pros**: Zero footprint
- **Cons**: No metrics — Grafana shows "datasource unreachable" if also `container`
- **Requirements**: None

#### `container`
```bash
PROMETHEUS_SOURCE=container
PROMETHEUS_RETENTION_DAYS=7   # 1..365 — wizard prompts inline on the source step
```
- **Use case**: Stack-wide observability — scrapes Kong, LiteLLM, Weaviate, n8n, JupyterHub, MinIO, Backend, Hermes, plus the postgres/redis sidecars and cAdvisor/node-exporter
- **Pros**: 14 pre-configured scrape jobs, recording-rules folder ready to extend, Kong-aliased UI at `prometheus.localhost`
- **Cons**: cAdvisor polls every container every 5s and node-exporter polls `/proc` continuously — non-trivial overhead on a laptop
- **Requirements**: ~500 MB image disk + retention-day-dependent disk for the TSDB volume

### GRAFANA_SOURCE

Grafana is the user-facing dashboards + unified alerting UI on top of Prometheus. The Prometheus datasource is pre-provisioned (URL interpolated from `${PROMETHEUS_ENDPOINT}` at boot) plus 7 starter dashboards (stack overview, LiteLLM, Kong, Postgres+Redis, containers+host, n8n, app-tier). See [Grafana service README](../../services/grafana/README.md) for the dashboard catalog and admin-password lifecycle.

#### `disabled` (Default)
```bash
GRAFANA_SOURCE=disabled
```
- **Use case**: Cold-start fast; no UI overhead. Useful even when Prometheus is `container` if you only want raw metrics via Prom's own UI
- **Pros**: Zero footprint
- **Cons**: No dashboards
- **Requirements**: None

#### `container`
```bash
GRAFANA_SOURCE=container
GRAFANA_ADMIN_USERNAME=admin    # override only if you want a different login
GRAFANA_ADMIN_PASSWORD=...       # auto-generated on first bootstrap; persisted to .env
```
- **Use case**: User-facing observability — 7 dashboards in the "GenAI Vanilla" folder, unified alerting enabled (no rules pre-provisioned), Kong-aliased UI at `grafana.localhost`
- **Pros**: Admin login + datasource provisioning happen automatically; sign-up disabled; anonymous-read off by default
- **Cons**: When `PROMETHEUS_SOURCE=disabled`, every panel shows "datasource unreachable" — pair with `--prometheus-source container` for a working setup
- **Requirements**: ~300 MB image disk + small named volume for SQLite

### SPARK_SOURCE

Spark is a standalone Apache Spark cluster (master + N workers + history server + dedicated `spark-connect` gRPC sidecar + one-shot `spark-init`) sitting in the `data` band. It exposes a Spark Connect endpoint on `:15002` via the sidecar for in-stack thin clients (currently Zeppelin's Spark interpreter wires to it; JupyterHub + Backend wiring is a future spec). Spark master URL (`spark://spark-master:7077`) and the Spark Connect URL (`sc://spark-connect:15002`) are baked into the Zeppelin interpreter env at compose-render time. See [Spark service README](../../services/spark/README.md) for the cluster topology and Spark Connect details.

#### `disabled` (Default)
```bash
SPARK_SOURCE=disabled
```
- **Use case**: No Spark workloads; saves ~3 GB image disk + per-worker RAM
- **Pros**: Zero footprint; Zeppelin is also gated off (Zeppelin without Spark errors out at start)
- **Cons**: No batch / SQL / DataFrame compute; LLM operators in Airflow that import `pyspark` will fail
- **Requirements**: None

#### `container`
```bash
SPARK_SOURCE=container
SPARK_WORKER_COUNT=2     # number of spark-worker replicas; 1..8 — wizard prompts inline
```
- **Use case**: Local Spark cluster for batch / SQL / DataFrame jobs and Spark Connect clients
- **Pros**: Master + N workers + history server, Kong-aliased UIs at `spark.localhost` + `spark-history.localhost`, Spark Connect on `:15002`
- **Cons**: Each worker reserves CPU + RAM (defaults to 1 core / 1 GB); heavy on laptops above 2 workers
- **Containers**: `spark-master`, `spark-worker-1..N`, `spark-history`, `spark-connect` (gRPC Connect sidecar), `spark-init` (one-shot — creates the spark-history MinIO bucket)
- **Requirements**: ~3 GB image disk + ~1 GB RAM per worker

### ZEPPELIN_SOURCE

Zeppelin is the Spark-first notebook UI. The Spark interpreter is pre-configured against the in-cluster master + Spark Connect; the JDBC interpreter ships with Supabase Postgres credentials in env vars but requires a one-time UI-driven `postgres` profile setup (see [Zeppelin service README](../../services/zeppelin/README.md) §4). **Hard-gated on Spark** — `ZEPPELIN_SOURCE=container` with `SPARK_SOURCE=disabled` errors out at bootstrap.

#### `disabled` (Default)
```bash
ZEPPELIN_SOURCE=disabled
```
- **Use case**: No notebook UI for Spark; saves ~1.5 GB image disk
- **Pros**: Zero footprint
- **Cons**: No Spark notebook authoring (Jupyter notebooks can still drive Spark Connect though)
- **Requirements**: None

#### `container`
```bash
ZEPPELIN_SOURCE=container
SPARK_SOURCE=container   # REQUIRED — Zeppelin hard-fails without Spark
```
- **Use case**: Web-based notebook authoring against the in-cluster Spark master
- **Pros**: Pre-configured Spark interpreter (master RPC + Spark Connect gRPC + MinIO S3A), Kong-aliased UI at `zeppelin.localhost`, persists notebooks to a named volume. JDBC interpreter ships with credentials in env but needs a one-time UI setup.
- **Cons**: Adds ~1.5 GB image disk + ~512 MB RAM
- **Containers**: `zeppelin`
- **Requirements**: `SPARK_SOURCE=container`

### AIRFLOW_SOURCE

Airflow is a code-defined DAG orchestrator running LocalExecutor (no Celery / Redis broker — the metadata DB is Supabase Postgres). The image bundles `apache-airflow-providers-openai` (LiteLLM-wired) — LangChain support runs via `langchain-openai` + `PythonOperator`; there is no `apache-airflow-providers-langchain` package on PyPI. `airflow-init` seeds Connection objects per sibling source: `postgres_supabase`, `litellm_default`, and `redis_default` (always-on — required deps and locked-source services), `spark_default` (gated on `SPARK_SOURCE=container`), `minio_default` (gated on `MINIO_SOURCE=container`), `weaviate_default` (gated on `WEAVIATE_SOURCE=container`), `neo4j_default` (gated on `NEO4J_GRAPH_DB_SOURCE=container`). See [Airflow service README](../../services/airflow/README.md) §4 for the full seeded Connections matrix and the example DAG.

#### `disabled` (Default)
```bash
AIRFLOW_SOURCE=disabled
```
- **Use case**: No orchestrated workflows; saves ~2 GB image disk + Postgres metadata schema
- **Pros**: Zero footprint
- **Cons**: No scheduled DAGs; no Hermes → Airflow trigger pattern
- **Requirements**: None

#### `container`
```bash
AIRFLOW_SOURCE=container
# Username is hardcoded `admin` — there is no AIRFLOW_ADMIN_USERNAME knob.
AIRFLOW_ADMIN_PASSWORD=...              # auto-generated on first bootstrap; persisted to .env
AIRFLOW_FERNET_KEY=...                  # auto-generated; encrypts Connections + Variables at rest
AIRFLOW_SECRET_KEY=...                  # auto-generated; AIRFLOW__API__SECRET_KEY signs inter-process payloads (DagFileProcessor→scheduler RPC, deferrable triggers, multi-scheduler JWTs) in Airflow 3.x
AIRFLOW_DB_USER=airflow                 # Postgres role on supabase-db
AIRFLOW_DB_PASSWORD=...                 # auto-generated
```
- **Use case**: Scheduled / triggered DAG runs (ETL, model fine-tunes, scheduled LLM evals) with first-class LiteLLM-wired LLM operators
- **Pros**: LocalExecutor (no broker), Supabase Postgres metadata DB, Kong-aliased UI at `airflow.localhost`, REST API under the same alias at `/api/v2/`, 7 Connections auto-seeded (`postgres_supabase` / `litellm_default` / `redis_default` always; `spark_default` / `minio_default` / `weaviate_default` / `neo4j_default` gated on the matching sibling being `container`-sourced)
- **Cons**: ~2 GB image disk + ~1.5 GB RAM for the webserver + scheduler + dag-processor combo
- **Containers**: `airflow-init` (one-shot), `airflow-webserver`, `airflow-scheduler`, `airflow-dag-processor` (Airflow 3.x REQUIRES a standalone DAG processor — the scheduler no longer parses DAGs in-process)
- **Requirements**: Supabase Postgres reachable (always-on)

## Configuration Patterns

### Development Setup
Best for local development with minimal resources:

```bash
./start.sh --llm-provider-source ollama-localhost \
          --comfyui-source localhost \
          --weaviate-source container \
          --n8n-source disabled \
          --searxng-source disabled
```

Benefits:
- Lower memory usage
- Faster AI inference
- Reduced container count
- Easy debugging

### Production Setup
Best for production with full features:

```bash
./start.sh --llm-provider-source ollama-container-gpu \
          --comfyui-source container-gpu \
          --weaviate-source container \
          --n8n-source container \
          --searxng-source container
```

Benefits:
- GPU acceleration
- All features enabled
- Consistent environment
- Scalable architecture

### Minimal Setup
Best for testing or resource-constrained environments:

```bash
./start.sh --llm-provider-source none \
          --cloud-openai-source enabled \
          --comfyui-source disabled \
          --weaviate-source disabled \
          --n8n-source disabled \
          --searxng-source disabled
```

Benefits:
- Minimal resource usage (no local Ollama)
- Cloud-powered AI through LiteLLM
- Fast startup
- Basic chat functionality

Make sure `OPENAI_API_KEY` (or whichever cloud key matches your enabled `CLOUD_*_SOURCE`) is set in `.env`.

### Mixed Setup
Combine different approaches for optimal performance:

```bash
./start.sh --llm-provider-source ollama-localhost \  # Local for speed
          --comfyui-source container-gpu \           # Container for GPU
          --weaviate-source container \              # Container for ease
          --n8n-source container \                   # Full workflow features
          --searxng-source disabled                  # Skip if not needed
```

## Environment File vs CLI Overrides

### Using .env File
Persistent configuration for regular use:

```bash
# Edit .env file
BASE_PORT=63000
LLM_PROVIDER_SOURCE=ollama-localhost
COMFYUI_SOURCE=container-gpu
N8N_SOURCE=container

# Start with file configuration
./start.sh
```

`BASE_PORT` is the preferred way to move the whole stack to another port range. Individual `*_PORT` variables are advanced overrides; normal users should change `BASE_PORT` manually or run `./start.sh --base-port <port>`.

### Using CLI Overrides
Temporary configuration for testing:

```bash
# Override without changing .env
./start.sh --llm-provider-source ollama-localhost --comfyui-source disabled

# Next run uses .env settings again
./start.sh
```

## Service Dependencies

Understanding which services depend on others:

### Core Dependencies
- **Open WebUI / Backend / n8n / JupyterHub / Local Deep Researcher / OpenClaw** → All read `LITELLM_BASE_URL` + `LITELLM_API_KEY` for LLM access. LiteLLM is always-on; the actual upstream is whatever `LLM_PROVIDER_SOURCE` and the `CLOUD_*_SOURCE` toggles select.
- **Backend API** → Depends on database services (PostgreSQL, Redis)
- **n8n workflows** → Often use Weaviate for vector operations

### Optional Dependencies
- **ComfyUI** → Independent, can be disabled without affecting other services
- **SearxNG** → Independent privacy search
- **Weaviate** → Optional unless needed for semantic search

## Performance Considerations

### Memory Usage by Configuration

**High Memory** (12GB+ recommended):
- All services containerized
- GPU services enabled
- Large models loaded

**Medium Memory** (8GB recommended):
- Mix of localhost and container
- Some services disabled
- Smaller models

**Low Memory** (4GB minimum):
- API-based LLM
- Most services disabled
- Minimal container footprint

### CPU Usage

**CPU Intensive**:
- Container-based AI services
- Multiple simultaneous AI tasks
- All services enabled

**CPU Efficient**:
- Localhost AI services
- GPU-accelerated containers
- Selective service enabling

## Troubleshooting SOURCE Configurations

### Common Issues

**Service won't start with localhost SOURCE**:
```bash
# Check if service is running locally
curl http://localhost:11434/api/tags  # Ollama (LiteLLM upstream when LLM_PROVIDER_SOURCE=ollama-localhost)
curl http://localhost:63030/health/liveliness  # LiteLLM gateway (always-on)
curl http://localhost:8000/           # ComfyUI default localhost URL
curl http://localhost:8188/           # ComfyUI if you overrode COMFYUI_LOCALHOST_PORT to 8188

# Check service logs
docker logs genai-backend -f
```

**Port conflicts**:
```bash
# Use different base port
./start.sh --base-port 64000

# Check port usage (Open WebUI default; substitute your conflicting port)
lsof -i :63082
```

**Kong routing not working**:
```bash
# Kong config is dynamically generated at every startup — to debug routes,
# inspect the generator + the KONG_* env vars it consumes:
cat bootstrapper/utils/kong_config_generator.py
env | grep ^KONG_

# Verify hosts file
./start.sh --setup-hosts
```

### Debug Commands

```bash
# Check active SOURCE values
env | grep -E "(OLLAMA|COMFYUI|N8N|WEAVIATE)_SOURCE"

# Test service connectivity (LLM goes via LiteLLM, not Ollama directly)
docker exec genai-backend curl http://genai-litellm:4000/health/liveliness
docker exec genai-litellm curl http://genai-ollama:11434/api/tags
docker exec genai-kong-api-gateway curl http://genai-comfyui:18188/

# Monitor resource usage
docker stats
```

For more troubleshooting help, see [../quick-start/troubleshooting.md](../quick-start/troubleshooting.md).