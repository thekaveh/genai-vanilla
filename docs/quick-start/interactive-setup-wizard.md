# Interactive Setup Wizard

The GenAI Vanilla Stack includes an interactive setup wizard that guides you through configuring all services step by step. It launches automatically when you run `./start.sh` with no arguments.

## Quick Start

```bash
./start.sh
```

That's it. The wizard handles everything from there.

## How It Works

### 1. Service Configuration

The wizard presents each configurable service one at a time, showing all available SOURCE options with contextual hints:

- **Container options** (CPU / GPU) for Docker-based deployment
- **Localhost options** for using locally installed services
- **External / API options** for remote or cloud-based services
- **Disabled** to skip a service entirely

The current `.env` value is pre-selected as the default for each service, so pressing Enter keeps your existing configuration.

### 2. Stack Options

After service configuration, the wizard prompts for:

- **Base port** for all services (default: 63000)
- **Cold start** option to remove volumes and rebuild from scratch
- **Hosts file configuration** to enable friendly URLs like `chat.localhost` and `n8n.localhost`

### 3. Pre-Launch Summary

Before launching, a configuration summary table shows:

- Every service with its selected source and endpoint URL
- Hosted endpoints (e.g., `chat.localhost:63002`) if hosts file entries are configured
- Status indicators (on, local, GPU, API, off)

You confirm to launch, or cancel to exit without changes.

## Navigation

| Key | Action |
|-----|--------|
| `Up/Down` | Navigate between options |
| `Enter` | Select the highlighted option |
| `Escape` | Restart the wizard from the beginning |
| `Ctrl+C` | Quit the wizard |

## Progress Tracking

A progress bar at the top of each screen shows how far you are through the configuration process. It starts at 0% and reaches 100% after all steps (services + stack options) are completed.

## When to Use the Wizard vs CLI Flags

| Scenario | Approach |
|----------|----------|
| First time setting up the stack | Wizard (`./start.sh`) |
| Exploring available service options | Wizard |
| Changing one or two services | CLI flags (`./start.sh --llm-provider-source ollama-localhost`) |
| CI/CD or scripted deployments | CLI flags or `.env` file |
| Repeating a previous configuration | CLI flags (copy from wizard's command preview) |

## Relationship to .env and CLI Flags

The wizard reads your current `.env` values as defaults and produces the same `--*-source` overrides that CLI flags would. After confirmation, these overrides are applied to `.env` and the stack launches normally.

- **Wizard selections are persistent** in `.env` and carry over to future runs
- **CLI flags always skip the wizard** and apply directly
- **Any flag** (including `--cold`, `--base-port`, etc.) skips the wizard

## Requirements

The wizard requires the `InquirerPy` Python package, which is included in the project's dependencies. If not installed, `./start.sh` silently falls back to using `.env` defaults without the wizard.

## Configurable Services

The wizard automatically discovers all configurable services from `service-configs.yml`. Currently these include:

| Service | Options |
|---------|---------|
| LLM Provider (Ollama) | container-cpu, container-gpu, localhost, external, api, disabled |
| ComfyUI | container-cpu, container-gpu, localhost, external, disabled |
| Weaviate | container, localhost, disabled |
| Multi2Vec CLIP | container-cpu, container-gpu, disabled |
| Neo4j Graph DB | container, localhost, disabled |
| STT Provider (Parakeet) | container-gpu, localhost, disabled |
| TTS Provider (XTTS) | container-gpu, localhost, disabled |
| Document Processor (Docling) | container-gpu, localhost, disabled |
| OpenClaw | container, localhost, disabled |
| n8n | container, disabled |
| SearxNG | container, disabled |
| JupyterHub | container, disabled |

New services added to `service-configs.yml` are automatically picked up by the wizard.

## Dependency Validation

The wizard validates service dependencies in real time. For example, if you enable n8n but disable Weaviate (which n8n requires), the wizard warns you and offers to either enable the dependency or disable the dependent service.

## Hosts File Setup

The hosts file configuration step enables friendly URLs routed through Kong API Gateway:

| Option | Behavior |
|--------|----------|
| **Default** | Checks `/etc/hosts` for required entries, warns if missing |
| **Setup hosts now** | Adds entries to `/etc/hosts` (requires `sudo`) |
| **Skip** | No hosts check, use `localhost:PORT` URLs only |

When hosts are configured, the pre-launch summary table shows both the direct `localhost:PORT` URL and the friendly `service.localhost:KONG_PORT` URL for applicable services.
