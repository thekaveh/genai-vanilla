# SOURCE Configuration Guide

This guide explains the SOURCE-based configuration system that makes the GenAI Vanilla Stack flexible and modular.

## Understanding SOURCE Variables

SOURCE variables control how each service is deployed - whether in a Docker container, using a localhost installation, connecting to an external service, or disabling the service entirely.

## Service SOURCE Support Matrix

### Services Supporting Localhost
These services can run on your host machine instead of in containers:

| Service | SOURCE Variable | Localhost Option | Benefits |
|---------|----------------|------------------|----------|
| **Ollama** | `LLM_PROVIDER_SOURCE` | `ollama-localhost` | Faster, uses existing models, less memory |
| **ComfyUI** | `COMFYUI_SOURCE` | `localhost` | Direct access, custom setups, faster |
| **Weaviate** | `WEAVIATE_SOURCE` | `localhost` | Custom configuration, performance |

### Container-Only Services
These services only run in Docker containers:

| Service | SOURCE Variable | Options | Reason |
|---------|----------------|---------|--------|
| **n8n** | `N8N_SOURCE` | `container`, `disabled` | Complex dependencies |
| **SearxNG** | `SEARXNG_SOURCE` | `container`, `disabled` | Custom config required |
| **Open WebUI** | `OPEN_WEB_UI_SOURCE` | `container`, `disabled` | Integrated environment |
| **Backend API** | `BACKEND_SOURCE` | `container`, `disabled` | Service dependencies |

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
ollama pull qwen2.5:latest
ollama pull mxbai-embed-large
```

#### `ollama-external`
```bash
LLM_PROVIDER_SOURCE=ollama-external
OLLAMA_EXTERNAL_URL=https://your-ollama-api.com
```
- **Use case**: Remote Ollama instance
- **Pros**: Shared resources, cloud deployment
- **Cons**: Network dependency, latency
- **Requirements**: External Ollama API endpoint

#### `api`
```bash
LLM_PROVIDER_SOURCE=api
```
- **Use case**: Cloud LLM APIs (OpenAI, Anthropic, etc.)
- **Pros**: No local resources, access to latest models
- **Cons**: API costs, internet dependency
- **Requirements**: API keys configured in Open WebUI

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
- **Requirements**: ComfyUI running on localhost:8188

Setup for localhost:
```bash
# Clone ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# Install dependencies
pip install -r requirements.txt

# Start ComfyUI
python main.py --port 8188
```

#### `external`
```bash
COMFYUI_SOURCE=external
COMFYUI_EXTERNAL_URL=https://your-comfyui-api.com
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
```
- **Use case**: Standard vector database
- **Pros**: Easy setup, automatic configuration
- **Cons**: Container resource usage
- **Requirements**: None

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
LLM_PROVIDER_SOURCE=ollama-localhost
COMFYUI_SOURCE=container-gpu
N8N_SOURCE=container

# Start with file configuration
./start.sh
```

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
curl http://localhost:8188/           # ComfyUI

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
# Check Kong configuration
cat volumes/api/kong.yml

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