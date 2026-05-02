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

Before launching, a configuration summary inside the same anchored info-box shows:

- Every service with its selected source, alias (when hosts are configured), and direct port
- Hosted endpoints (e.g., `chat.localhost:63002`) if hosts file entries are configured
- Color-coded source choices (container = green, localhost / external / cloud = cyan, off = slate)

You confirm to launch (the **Launch the stack with this configuration?** step is the wizard's final question), or cancel to exit without changes.

### 4. Streaming Logs

After confirmation, the wizard tears down its Rich Live region and a Textual application (`bootstrapper/ui/log_stream_app.py`) takes over the screen:

- The same stylized info-box stays **pinned** at the top — it never moves while logs flow
- Below it, a bordered **Streaming Logs** panel with mouse-wheel scrollback inside the panel itself
- `docker compose` build / up / port-verify / `logs -f` output streams into the panel with original ANSI colors preserved (`Text.from_ansi`)
- Press `Ctrl+C` or `q` to detach. The stack keeps running — `docker compose logs -f <service>` will resume streaming any time

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

The TUI uses three Python libraries — all included in `bootstrapper/pyproject.toml`:

- **rich** — drives the wizard's anchored info-box (alternate-screen `Live` region) and the styled log lines.
- **readchar** — single-keystroke reader for the wizard's select / number widgets.
- **textual** — owns the post-confirm streaming phase (pinned info-box + bordered `RichLog` widget).

Python ≥ 3.9 is required. The wizard automatically falls back to non-interactive (.env defaults + CLI flags) when `stdin` isn't a TTY, when the terminal is too small, or when the user passes `--no-tui`. In that mode `./start.sh` runs the legacy linear flow with passthrough docker output.

## Brand Customization

The metadata on the pinned info-box's border (brand name, tagline, version, author, license, repo URL) is overridable via `BRAND_*` environment variables. Defaults are the GenAI Vanilla project's identity; forks can rebrand the wizard by editing the `BRAND_*` block in `.env`:

```
BRAND_NAME=GenAI Vanilla
BRAND_TAGLINE=AI Development Suite
BRAND_VERSION=
BRAND_AUTHOR=Kaveh Razavi
BRAND_LICENSE=Apache License 2.0
BRAND_REPO_URL=github.com/thekaveh/genai-vanilla
```

Empty values fall back to the canonical defaults (encoded in `bootstrapper/ui/state.py::AppState`). See `.env.example` for the latest documented block.

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
