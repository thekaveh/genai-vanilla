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
| `LLM_PROVIDER_SOURCE` | `ollama-container-cpu` | `ollama-container-cpu`, `ollama-container-gpu`, `ollama-localhost`, `ollama-external`, `api`, `disabled` | User-facing | Main LLM provider mode. |
| `COMFYUI_SOURCE` | `container-cpu` | `container-cpu`, `container-gpu`, `localhost`, `external`, `disabled` | User-facing | Image generation service. |
| `WEAVIATE_SOURCE` | `container` | `container`, `localhost`, `disabled` | User-facing | Vector database. |
| `N8N_SOURCE` | `container` | `container`, `disabled` | User-facing | Workflow automation. |
| `SEARXNG_SOURCE` | `container` | `container`, `disabled` | User-facing | Privacy metasearch. |
| `OPENCLAW_SOURCE` | `disabled` | `container`, `localhost`, `disabled` | User-facing | AI messaging agent. |
| `STT_PROVIDER_SOURCE` | `disabled` | `parakeet-container-gpu`, `parakeet-localhost`, `disabled` | User-facing optional | Speech-to-text provider. |
| `TTS_PROVIDER_SOURCE` | `disabled` | `xtts-container-gpu`, `xtts-localhost`, `disabled` | User-facing optional | Text-to-speech provider. |
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
| `OLLAMA_PULL_SOURCE` | `container` | `container`, `disabled` | Auto-managed init | Pulls configured Ollama models when container Ollama is enabled. |
| `WEAVIATE_INIT_SOURCE` | `container` | `container`, `disabled` | Auto-managed init | Initializes Weaviate schemas/config. |
| `COMFYUI_INIT_SOURCE` | `container` | `container`, `disabled` | Auto-managed init | Initializes ComfyUI assets/config. |
| `N8N_INIT_SOURCE` | `container` | `container`, `disabled` | Auto-managed init | Initializes/imports n8n workflows. |
| `OPENCLAW_INIT_SOURCE` | `container` | `container`, `disabled` | Auto-managed init | Initializes OpenClaw config where applicable. |
| `SUPABASE_DB_INIT_SOURCE` | `container` | `container`, `disabled` | Auto-managed init | Initializes Supabase database state. |

### Services Supporting Localhost

These services can run on your host machine instead of in containers:

| Service | SOURCE Variable | Localhost Option | Benefits |
|---------|----------------|------------------|----------|
| **Ollama** | `LLM_PROVIDER_SOURCE` | `ollama-localhost` | Faster, uses existing models, less memory |
| **ComfyUI** | `COMFYUI_SOURCE` | `localhost` | Direct access, custom setups, faster |
| **Weaviate** | `WEAVIATE_SOURCE` | `localhost` | Custom configuration, performance |
| **Neo4j** | `NEO4J_GRAPH_DB_SOURCE` | `localhost` | Use an existing graph database |
| **OpenClaw** | `OPENCLAW_SOURCE` | `localhost` | Native performance, existing config |
| **STT Provider** | `STT_PROVIDER_SOURCE` | `parakeet-localhost` | Use a host speech-to-text service |
| **TTS Provider** | `TTS_PROVIDER_SOURCE` | `xtts-localhost` | Use a host text-to-speech service |
| **Document Processor** | `DOC_PROCESSOR_SOURCE` | `docling-localhost` | Use a host Docling service |

### Container-Only or Stack-Managed Services

Container-only and stack-managed services should normally be left at their defaults unless you are intentionally reducing the stack or debugging a specific component. Init service SOURCE variables are usually managed by the startup flow and should not be the first knob users change.

### Feature Flags (Non-SOURCE)

Some features within services are controlled by feature flags rather than SOURCE variables:

| Feature | Variable | Options | Notes |
|---------|----------|---------|-------|
| **LangMem Memory** | `LANGMEM_ENABLED` | `true`, `false` | Persistent conversation memory embedded in the Backend service. |

## Detailed SOURCE Configurations

### LLM_PROVIDER_SOURCE (Ollama)

#### `ollama-container-cpu` (Default)
```bash
LLM_PROVIDER_SOURCE=ollama-container-cpu
```
- **Use case**: Default setup, no local Ollama required
- **Pros**: No setup needed, works everywhere
- **Cons**: Higher memory usage, slower model loading
- **Requirements**: None

#### `ollama-container-gpu`
```bash
LLM_PROVIDER_SOURCE=ollama-container-gpu
```
- **Use case**: GPU acceleration in container
- **Pros**: GPU acceleration, no local setup
- **Cons**: Requires NVIDIA GPU + Docker GPU support
- **Requirements**: NVIDIA Container Toolkit

#### `ollama-localhost`
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

#### `ollama-external`
```bash
LLM_PROVIDER_SOURCE=ollama-external
LLM_PROVIDER_EXTERNAL_URL=https://your-ollama-api.example
```
- **Use case**: Remote Ollama instance
- **Pros**: Shared resources, cloud deployment
- **Cons**: Network dependency, latency
- **Requirements**: External Ollama API endpoint

#### `api`
```bash
LLM_PROVIDER_SOURCE=api
```
- **Use case**: Cloud LLM APIs configured in Open WebUI or another consuming application
- **Pros**: No local Ollama resources, access to managed providers
- **Cons**: API costs, internet dependency, provider-specific setup
- **Requirements**: Configure provider credentials in the consuming application. This mode disables the container Ollama service; it is not the same as `ollama-external`. Use `LLM_PROVIDER_EXTERNAL_URL` only with `LLM_PROVIDER_SOURCE=ollama-external`.

#### `disabled`
```bash
LLM_PROVIDER_SOURCE=disabled
```
- **Use case**: No LLM services needed
- **Pros**: Minimal resource usage
- **Cons**: No AI chat capabilities
- **Requirements**: None

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
- **Requirements**: ComfyUI running locally at `COMFYUI_LOCALHOST_URL` (default `http://host.docker.internal:8000`; override if your installation uses another port such as 8188)

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
# COMFYUI_LOCALHOST_URL=http://host.docker.internal:8188
```

#### `external`
```bash
COMFYUI_SOURCE=external
COMFYUI_EXTERNAL_URL=https://your-comfyui-api.example
```
- **Use case**: Remote ComfyUI instance
- **Pros**: Shared GPU resources
- **Cons**: Network dependency
- **Requirements**: External ComfyUI API

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

The default stack also enables the optional CLIP vectorizer service:

```bash
MULTI2VEC_CLIP_SOURCE=container-cpu
WEAVIATE_ENABLE_MODULES=text2vec-ollama,text2vec-openai,multi2vec-clip,generative-ollama,generative-openai
CLIP_INFERENCE_API=http://multi2vec-clip:8080
```

If `MULTI2VEC_CLIP_SOURCE=disabled`, remove `multi2vec-clip` from `WEAVIATE_ENABLE_MODULES` and set `CLIP_INFERENCE_API=` so Weaviate does not advertise a disabled inference endpoint.

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
# OPENCLAW_LOCALHOST_URL=http://host.docker.internal:18789
```

#### `disabled` (Default)
```bash
OPENCLAW_SOURCE=disabled
```
- **Use case**: No AI agent needed
- **Pros**: Saves resources
- **Cons**: No messaging integration
- **Requirements**: None

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
./start.sh --llm-provider-source api \
          --comfyui-source disabled \
          --weaviate-source disabled \
          --n8n-source disabled \
          --searxng-source disabled
```

Benefits:
- Minimal resource usage
- Cloud-powered AI
- Fast startup
- Basic chat functionality

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
- **Open WebUI** → Depends on available LLM (Ollama or API)
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
curl http://localhost:11434/api/tags  # Ollama
curl http://localhost:8000/           # ComfyUI default localhost URL
curl http://localhost:8188/           # ComfyUI if you overrode COMFYUI_LOCALHOST_URL to 8188

# Check service logs
docker logs genai-backend -f
```

**Port conflicts**:
```bash
# Use different base port
./start.sh --base-port 64000

# Check port usage
lsof -i :63015
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

# Test service connectivity
docker exec genai-backend curl http://genai-ollama:11434/api/tags
docker exec genai-kong-api-gateway curl http://genai-comfyui:18188/

# Monitor resource usage
docker stats
```

For more troubleshooting help, see [../quick-start/troubleshooting.md](../quick-start/troubleshooting.md).