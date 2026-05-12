# GenAI Vanilla Stack

A flexible, modular GenAI project boilerplate with customizable services.

[![Architecture Diagram](./docs/diagrams/architecture.svg)](./docs/diagrams/architecture.html)

For the richer static architecture view, open [`docs/diagrams/architecture.html`](./docs/diagrams/architecture.html).

## Quick Start

### First-time setup

```bash
# 1. Clone the repository
git clone <your-repository-url> && cd genai-vanilla

# 2. Start with the interactive setup wizard (no configuration needed)
./start.sh

# 3. Wait ~5 minutes for AI models to download, then access:
# Open WebUI (Chat):     http://localhost:63015
# n8n (Workflows):       http://localhost:63017
# Supabase Studio:       http://localhost:63009
# SearxNG (Search):      http://localhost:63014
# ComfyUI:               http://localhost:63018
# JupyterHub (IDE):      http://localhost:63048
#
# Optional Kong host routes after ./start.sh --setup-hosts:
# Chat:                  http://chat.localhost:63002
# n8n:                   http://n8n.localhost:63002
# ComfyUI:               http://comfyui.localhost:63002

# Default credentials:
# Supabase Studio: admin@example.com / changeme123
# n8n:             admin@example.com / changeme123
```

The default configuration runs the full stack on CPU: chat UI, workflow automation, vector database, and privacy search.

### Common option combinations

```bash
# Local AI services (faster, less memory)
./start.sh --llm-provider-source ollama-localhost --comfyui-source localhost

# GPU acceleration
./start.sh --llm-provider-source ollama-container-gpu --comfyui-source container-gpu --stt-provider-source speaches-container-gpu

# Pick a different STT engine (Speaches is the default)
./start.sh --stt-provider-source parakeet-container-gpu   # SOTA NVIDIA (CC-BY-4.0)
./start.sh --stt-provider-source whisper-cpp-localhost    # Best on macOS — Metal + Core ML
./start.sh --stt-provider-source parakeet-localhost       # Parakeet-MLX (macOS) or native Linux

# Pick a different TTS engine (Speaches is the default)
./start.sh --tts-provider-source chatterbox-container-gpu  # Voice cloning, NVIDIA
./start.sh --tts-provider-source chatterbox-localhost      # Voice cloning, macOS MPS / Linux

# Minimal setup (chat only)
./start.sh --n8n-source disabled --searxng-source disabled --weaviate-source disabled

# Cloud-only LLMs (no local Ollama; LiteLLM gateway routes to cloud providers)
# The bootstrapper auto-disables a cloud provider whose API key is empty,
# so pass --openai-api-key on the command line OR set OPENAI_API_KEY in .env first.
./start.sh --llm-provider-source none --cloud-openai-source enabled --openai-api-key sk-... --comfyui-source disabled
```

### Troubleshooting

- **Port conflicts?** → `./start.sh --base-port 64000`
- **Out of memory?** → Increase Docker memory to 10GB+
- **Can't access *.localhost?** → Run `./start.sh --setup-hosts`
- **Want fresh start?** → `./stop.sh --cold && ./start.sh --cold`

### Interactive setup wizard

Running `./start.sh` with no arguments launches an interactive setup wizard that walks through configuring every service step by step:

- Step-by-step service configuration with descriptions and contextual hints (GPU requirements, localhost options, etc.)
- LLM cluster spliced immediately after the LLM Engine step: single unified Ollama models multiselect (source-aware — localhost/external rows are badged `[pulled]` / `[library]`) + a free-text "additional models to pull" step → OpenAI / Anthropic / OpenRouter key + multiselect pairs (live `/v1/models` fetch), keeping engine + local + cloud adjacent in the wizard flow
- Live `ollama.com/library` scrape (a few hundred entries; exact count depends on the upstream catalog at fetch time) for both container and host-side Ollama sources
- Real-time command preview showing the equivalent CLI command as you make selections
- Dependency validation that warns if you enable a service without its required dependencies
- Pre-launch summary table with all endpoints and access URLs before starting
- Color-coded streaming logs once the stack launches, with the full session (wizard warnings + launch phase) tee'd to `/tmp/genai-vanilla-launch-<YYYYMMDDTHHMMSS>.log`
- Keyboard shortcuts: `Esc` returns to the previous step, `Space` toggles multiselect rows, `Ctrl+Q` quits

The wizard covers all configurable services, base port selection, cold start option, and hosts file setup. After reviewing the configuration summary, confirm to launch the stack.

> For users who prefer CLI flags, all options remain available. See [Command Line Interface](#41-command-line-interface) or the [Interactive Setup Wizard Guide](docs/quick-start/interactive-setup-wizard.md).

## Table of contents

- [Overview](#1-overview)
- [Getting Started](#2-getting-started)
- [Core Services](#3-core-services)
- [Usage Guide](#4-usage-guide)
- [Advanced Configuration](#5-advanced-configuration)
- [Development](#6-development)
- [Troubleshooting](#7-troubleshooting)
- [Documentation](#documentation)

## 1. Overview

### 1.1 What is GenAI Vanilla Stack?

GenAI Vanilla Stack is a customizable multi-service architecture for AI applications, featuring:

- **Dynamic service configuration**: SOURCE-based deployment with CLI overrides
- **Kong gateway**: auto-generated routes based on active services
- **Cross-platform support**: Python-based bootstrapping works on all OS
- **Flexible deployment**: mix containerized, localhost, and external services
- **GPU support**: container variants with NVIDIA GPU access for inference services
- **Core services**: Supabase ecosystem, Neo4j, Redis, LiteLLM gateway (always-on, fronts Ollama + cloud LLM providers), FastAPI backend, Kong Gateway

### 1.2 Key features

- **API gateway (Kong)**: centralized API management with dynamic routing
- **Real-time data sync**: live database notifications via Supabase Realtime
- **Flexible service sources**: switch between container, localhost, external, and cloud variants
- **Modular architecture**: choose service combinations via SOURCE variables
- **Environment-based config**: configuration through environment variables
- **Cross-platform Python scripts**: consistent behavior across Windows, macOS, Linux

### 1.3 Architecture overview

The canonical architecture diagram is the rich static artifact at [`docs/diagrams/architecture.html`](docs/diagrams/architecture.html), with a static SVG preview at [`docs/diagrams/architecture.svg`](docs/diagrams/architecture.svg).

The diagram summarizes the default stack around Kong, Open WebUI, the always-on Backend API, the always-on LiteLLM gateway (fronting Ollama and any enabled cloud LLM providers), Supabase/PostgreSQL, Redis, Neo4j, Weaviate, n8n, ComfyUI, JupyterHub, SearxNG, and optional OpenClaw/STT/TTS/document-processing services. It is intentionally maintained as a static generated artifact for now rather than a Mermaid source.

## 2. Getting Started

### 2.1 Getting started summary

- **New to the stack?** → Use containers with `./start.sh` for the easiest experience
- **Have local Ollama?** → Use `./start.sh --llm-provider-source ollama-localhost` for better performance (LiteLLM still fronts the upstream)
- **Have NVIDIA GPU?** → Use `./start.sh --comfyui-source container-gpu` for image generation acceleration
- **Need cloud APIs?** → Use `./start.sh --llm-provider-source none --cloud-openai-source enabled` (or the matching `--cloud-anthropic-source` / `--cloud-openrouter-source` flag) — LiteLLM routes to whichever providers are enabled
- **Limited resources?** → Disable services with `--n8n-source disabled --searxng-source disabled`

The SOURCE-based configuration system controls how each service is deployed.

### 2.2 Prerequisites

- **Docker & Docker Compose** — container orchestration
- **Python 3.10+** — for start/stop scripts
- **8GB+ RAM** allocated to Docker (12GB recommended)
- **10GB+ disk space** for Docker volumes

**Install UV (recommended)** for Python dependency management:
```bash
pip install uv
```

### 2.2 Installation

#### Quick install (recommended)
```bash
git clone <repository-url>
cd genai-vanilla
./start.sh
```

#### Custom configuration
```bash
# Edit configuration before starting
cp .env.example .env
# Edit .env to customize SOURCE variables
./start.sh
```

### 2.3 SOURCE system

The stack uses **SOURCE variables** to control how services are deployed.

**LLM access (always through LiteLLM):**
- **LiteLLM gateway** — always-on; every consumer reads `LITELLM_BASE_URL` + `LITELLM_API_KEY`
- **Ollama upstream** (`LLM_PROVIDER_SOURCE=ollama-container-cpu|ollama-container-gpu|ollama-localhost|ollama-external|none`) — what LiteLLM forwards to for local inference
- **Cloud upstreams** (`CLOUD_OPENAI_SOURCE`, `CLOUD_ANTHROPIC_SOURCE`, `CLOUD_OPENROUTER_SOURCE`) — independent `enabled`/`disabled` toggles; each requires the matching API key

**Other services that support localhost:**
- **ComfyUI** (`COMFYUI_SOURCE=localhost`) — use local ComfyUI via `COMFYUI_LOCALHOST_URL` (default `http://host.docker.internal:8000`; override if your installation uses another port such as 8188)
- **Weaviate** (`WEAVIATE_SOURCE=localhost`) — use local Weaviate instance
- **OpenClaw** (`OPENCLAW_SOURCE=localhost`) — use local OpenClaw installation

**Container-only services:**
- **n8n** (`N8N_SOURCE=container|disabled`) — workflow automation
- **SearxNG** (`SEARXNG_SOURCE=container|disabled`) — privacy search
- **Open WebUI** (`OPEN_WEB_UI_SOURCE=container|disabled`) — chat interface
- **Backend API** (`BACKEND_SOURCE=container`) — always-on adaptive FastAPI backend
- **JupyterHub** (`JUPYTERHUB_SOURCE=container|disabled`) — data science IDE

## 3. Core Services

### 3.1 Service overview

| Service | Direct URL | Kong URL | Purpose | Auth required |
|---------|------------|----------|---------|---------------|
| **Open WebUI** | http://localhost:63015 | http://chat.localhost:63002 | AI chat interface | Create account |
| **n8n** | http://localhost:63017 | http://n8n.localhost:63002 | Workflow automation | admin@example.com |
| **Supabase Studio** | http://localhost:63009 | http://localhost:63002 | Database management | admin@example.com |
| **ComfyUI** | http://localhost:63018 | http://comfyui.localhost:63002 | Image generation | None |
| **SearxNG** | http://localhost:63014 | http://search.localhost:63002 | Privacy search | None |
| **JupyterHub** | http://localhost:63048 | http://jupyter.localhost:63002 | Data science IDE | Token (optional) |
| **Neo4j Browser** | http://localhost:63011 | — | Graph database | neo4j / password |
| **Backend API** | http://localhost:63016 | http://api.localhost:63002 | REST API | API key |
| **LiteLLM Gateway** | http://localhost:63012 | — | OpenAI-compatible LLM front door (Ollama + cloud) | `LITELLM_API_KEY` |
| **Audio (TTS + STT)** | http://localhost:63026 | — | Default install: Speaches serves both `/v1/audio/speech` (Kokoro/Piper) and `/v1/audio/transcriptions` (Faster-Whisper) on one port. Engine-specific overrides — Parakeet on `:63022`, Chatterbox on `:63027`, host-side variants on `*_LOCALHOST_URL`. See [docs/services/tts-provider.md](docs/services/tts-provider.md) and [docs/services/stt-provider.md](docs/services/stt-provider.md). | None |
| **Docling Processor** | http://localhost:63021 | — | Document processing | None |
| **OpenClaw Agent** | http://localhost:63024 | http://openclaw.localhost:63002 | AI agent (messaging) | Token (optional) |

### 3.2 Database layer
- **PostgreSQL (Supabase)** — primary database with auth, storage, realtime
- **Neo4j** — graph database for relationships and graph queries
- **Weaviate** — vector database for embeddings and semantic search
- **Redis** — cache and message queue

### 3.3 AI services
- **LiteLLM Gateway** — always-on OpenAI-compatible front door for every LLM provider in the stack (one URL, one key)
- **Ollama** — local LLM inference engine behind LiteLLM (supports CPU/GPU/localhost/external/none)
- **ComfyUI** — image generation with workflows
- **STT layer** — pluggable speech-to-text: Speaches (default, Faster-Whisper inside, CPU-friendly), NVIDIA Parakeet-TDT (SOTA EN/EU), whisper.cpp localhost (best on Apple Silicon)
- **TTS layer** — pluggable text-to-speech: Speaches (default, Kokoro + Piper voices), Chatterbox (voice cloning, MIT-licensed)
- **Docling** — document processing with table extraction (IBM Docling, GPU-accelerated)
- **OpenClaw** — AI agent for messaging platforms (WhatsApp, Telegram, Discord), file management, and task automation
- **Deep Researcher** — research assistant
- **LangMem** — persistent conversation memory with automated fact extraction, semantic recall, and consolidation (embedded in Backend)

## 4. Usage Guide

### 4.1 Command line interface

```bash
# Interactive wizard (recommended for first-time setup)
./start.sh                    # Launches step-by-step configuration wizard

# Direct commands (skip wizard)
./start.sh --llm-provider-source ollama-localhost  # Any flag skips wizard
./start.sh --help            # Show all options
./stop.sh                    # Stop services, keep data
./stop.sh --cold             # Stop and remove all data

# Port and network
./start.sh --base-port 64000  # Custom port range
./start.sh --setup-hosts      # Configure *.localhost domains

# SOURCE overrides (temporary)
./start.sh --llm-provider-source ollama-localhost
./start.sh --comfyui-source container-gpu
./start.sh --stt-provider-source whisper-cpp-localhost  # Best on Apple Silicon
./start.sh --tts-provider-source chatterbox-localhost   # Voice cloning, native
./start.sh --doc-processor-source docling-container-gpu # Enable document processing
./start.sh --openclaw-source container                 # Enable OpenClaw agent
./start.sh --n8n-source disabled

# Combined examples
./start.sh --cold --base-port 55666 --llm-provider-source ollama-localhost

# Cloud provider keys + models (skip the wizard for cloud config)
./start.sh \
  --cloud-openai-source enabled --openai-api-key sk-... \
  --openai-models "gpt-5,gpt-5-mini,text-embedding-3-large"

# Multi-provider cloud setup
./start.sh \
  --cloud-openai-source enabled --openai-api-key sk-... --openai-models gpt-5 \
  --cloud-anthropic-source enabled --anthropic-api-key sk-ant-... --anthropic-models "claude-opus-4-7,claude-sonnet-4-6" \
  --cloud-openrouter-source enabled --openrouter-api-key sk-or-... --openrouter-models openrouter/auto

# Ollama model selection (CLI parity with the wizard's multiselects)
./start.sh \
  --llm-provider-source ollama-container-cpu \
  --ollama-models "qwen3.6:latest,nomic-embed-text" \
  --ollama-custom-models "mistral:7b,phi4:latest"
```

`*_USER_MODELS` env vars persist across runs, so you only need to pass the model flags once unless you want to change the active set. Cloud-provider key/source flags also imply `--cloud-X-source enabled` when paired with `--X-api-key`.

#### Stop script options

```bash
# Basic stop commands
./stop.sh                    # Stop services, keep data
./stop.sh --cold             # Stop and remove all data (destructive)
./stop.sh --clean-hosts      # Remove *.localhost entries from hosts file
./stop.sh --help             # Show all options

# The --cold option removes all Docker volumes (data loss).
# Use with caution — all database data will be permanently deleted.
```

### 4.2 Service access patterns

**Direct access:**
- Most services accessible directly via `http://localhost:PORT`
- Suitable for development and debugging

**Kong gateway routing:**
- Services with `*.localhost` URLs route through Kong
- Provides centralized authentication and rate limiting
- Requires hosts file setup: `./start.sh --setup-hosts`

## 5. Advanced Configuration

### 5.1 Custom deployments

See [docs/deployment/source-configuration.md](docs/deployment/source-configuration.md) for detailed SOURCE configuration guides.

### 5.2 GPU setup

For NVIDIA GPU acceleration, set the relevant SOURCE variables to a `*-container-gpu` variant (e.g., `LLM_PROVIDER_SOURCE=ollama-container-gpu`, `COMFYUI_SOURCE=container-gpu`, `STT_PROVIDER_SOURCE=speaches-container-gpu` or `parakeet-container-gpu`, `TTS_PROVIDER_SOURCE=speaches-container-gpu` or `chatterbox-container-gpu`). See [docs/deployment/source-configuration.md](docs/deployment/source-configuration.md) for the full list of GPU variants per service.

### 5.3 Using as infrastructure foundation

GenAI Vanilla can be used as a git submodule to provide infrastructure for your projects:

```bash
# Add as submodule in your project
git submodule add <repository-url> infra

# Configure and start
cd infra
cp .env.example .env
# Edit .env: Set PROJECT_NAME=myproject
./start.sh

# Access from your application
# - Docker network: myproject-network
# - Kong gateway: http://localhost:63002
# - Direct ports: derived from BASE_PORT, default http://localhost:63000+
```

**Capabilities:**
- Infrastructure code separated from application code
- Upstream updates can be pulled while maintaining local settings
- Project-specific environment configurations
- Standard git workflow for contributing changes upstream
- Multiple isolated instances with separate Docker resources

**Integration patterns:**
1. **Docker network** — connect your services to `${PROJECT_NAME}-network`
2. **Kong gateway** — use Kong as single entry point (port 63002)
3. **Direct access** — access services via exposed ports

See [docs/deployment/submodule-usage.md](docs/deployment/submodule-usage.md) for the complete guide including:
- Detailed setup instructions
- Integration patterns with code examples
- Contributing back to genai-vanilla
- Troubleshooting submodule issues

## 6. Development

### 6.1 Project structure
```
genai-vanilla/
├── bootstrapper/              # Python startup, SOURCE parsing, port/Kong generation, wizard
├── backend/                   # Always-on FastAPI backend service
├── docs/                      # User, service, deployment, diagram, and planning docs
├── supabase/                  # Supabase service configuration
├── graph-db/                  # Neo4j configuration/init assets
├── jupyterhub/                # JupyterHub image, notebooks, and requirements
├── n8n/ + n8n-init/           # Workflow automation service and init/import assets
├── open-webui/ + open-webui-init/ # Chat UI service and initialization assets
├── ollama-pull/               # Model-pull init container assets
├── comfyui-init/              # ComfyUI initialization assets
├── weaviate-init/             # Weaviate schema/config initialization assets
├── searxng/                   # Search service configuration
├── local-deep-researcher/     # Local research/orchestration service
├── doc-processor/             # Docling document processor service
├── stt-provider/              # Speech-to-text providers (Parakeet GPU/MLX, whisper.cpp host notes)
├── tts-provider/              # Text-to-speech providers (Chatterbox localhost setup)
├── docker-compose.yml         # Main compose file
├── .env.example               # Configuration template
├── start.sh                   # Start script
└── stop.sh                    # Stop script
```

### 6.2 Adding services

New services are declared in `bootstrapper/service-configs.yml` (under `source_configurable` or `adaptive_services`) and wired into `docker-compose.yml`. The bootstrapper computes ports, generates Kong routes, and adapts dependent services automatically.

## 7. Troubleshooting

### 7.1 Common issues

**Port conflicts:**
```bash
./start.sh --base-port 64000  # Use different port range
lsof -i :63015               # Check what's using port
```

**Memory issues:**
```bash
# Increase Docker memory in Docker Desktop
# Settings → Resources → Memory (set to 10-12GB)
```

**Service health:**
```bash
docker compose ps              # Check service status
docker logs genai-litellm -f   # Check LLM gateway logs
docker logs genai-ollama -f    # Check Ollama upstream logs (if enabled)
```

### 7.2 Detailed troubleshooting

For longer-form troubleshooting guides, see [docs/quick-start/troubleshooting.md](docs/quick-start/troubleshooting.md).

## Documentation

- [Documentation index](docs/README.md)
- [Quick Start guides](docs/quick-start/) — installation and first-run
- [Service documentation](docs/services/) — individual service guides
- [Ports and Routes](docs/deployment/ports-and-routes.md) — canonical ports, direct URLs, and Kong routes
- [Deployment guides](docs/deployment/) — deployment options, ports, routes, and configuration
- [ROADMAP.md](docs/ROADMAP.md) — future development plans
- [CHANGELOG.md](docs/CHANGELOG.md) — release history

## Contributing

Contributions welcome. Open a PR or an issue to propose changes.

## License

[MIT License](LICENSE)

## Support

- Check the [documentation](docs/README.md)
- Report issues on [GitHub Issues](https://github.com/thekaveh/genai-vanilla/issues)
- Ask questions in [GitHub Discussions](https://github.com/thekaveh/genai-vanilla/discussions)
