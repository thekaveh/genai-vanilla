# OpenClaw AI Agent Service

Open-source AI agent for messaging platforms with web-based administration dashboard.

## Overview

The OpenClaw service provides an AI-powered agent that connects to messaging apps:

- **Messaging Integration**: WhatsApp, Telegram, Discord, Slack, iMessage, and more
- **File Management**: Read, create, and manage files in a dedicated workspace
- **Calendar Management**: Schedule events and manage calendars
- **GitHub Monitoring**: Monitor repositories, issues, and pull requests
- **Command Execution**: Execute commands via messaging interface
- **Web Dashboard**: Browser-based admin panel for configuration and approvals
- **Multi-Provider LLM**: Supports Ollama, Anthropic, OpenAI, and many more

## Architecture

OpenClaw runs as a single gateway process that:

- Serves the web dashboard on port 18789
- Manages messaging platform connections (bridge) on port 18790
- Stores configuration in `~/.openclaw/` directory
- Stores workspace files in `~/.openclaw/workspace/`

The gateway connects to LLM providers (Ollama, Anthropic, OpenAI) for AI capabilities and to messaging platforms (WhatsApp, Telegram, etc.) for user interaction.

**Container Mode Initialization**: When running in container mode, an `openclaw-init` container runs first to:
- Set correct volume permissions (uid 1000/node) on config and workspace volumes
- Pre-configure the gateway for non-loopback binding (`gateway.controlUi.dangerouslyAllowHostHeaderOriginFallback`)

The gateway container starts with `--bind lan` to listen on all interfaces (required for Docker networking).

## Quick Start

### Container Mode (Docker)

**Step 1: Configure source**

Edit `.env`:
```bash
OPENCLAW_SOURCE=container
```

**Step 2: Start the stack**
```bash
./start.sh
```

Or use CLI override:
```bash
./start.sh --openclaw-source container
```

**Step 3: Access the dashboard**

Open `http://localhost:63024` or `http://openclaw.localhost:63002` (via Kong).

**Step 4: Run onboarding**
```bash
docker exec -it genai-openclaw-gateway openclaw onboard
```

**Note:**
- OpenClaw is **disabled by default** - you must explicitly enable it
- First run requires onboarding to configure messaging channels and LLM provider

### Localhost Mode (Native)

**Step 1: Install OpenClaw**
```bash
# Requires Node.js 22+
npm install -g openclaw
```

**Step 2: Run onboarding**
```bash
openclaw onboard --install-daemon
```

**Step 3: Start the gateway**
```bash
openclaw gateway --port 18789
```

**Step 4: Start the stack with OpenClaw localhost**
```bash
./start.sh --openclaw-source localhost
```

Or edit `.env`:
```bash
OPENCLAW_SOURCE=localhost
```

### Disable OpenClaw

```bash
OPENCLAW_SOURCE=disabled
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENCLAW_SOURCE` | Service source (container, localhost, disabled) | `disabled` |
| `OPENCLAW_IMAGE` | Docker image | `ghcr.io/openclaw/openclaw:latest` |
| `OPENCLAW_GATEWAY_PORT` | Gateway HTTP port (base_port + 24) | `63024` |
| `OPENCLAW_BRIDGE_PORT` | Bridge port (base_port + 25) | `63025` |
| `OPENCLAW_GATEWAY_TOKEN` | Optional token for securing gateway API | `` |
| `OPENCLAW_SCALE` | Container replicas (set by bootstrapper) | `0` |

### LLM API Keys (Optional Overrides)

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENCLAW_ANTHROPIC_API_KEY` | Anthropic API key for OpenClaw | Falls back to stack-wide key |
| `OPENCLAW_OPENAI_API_KEY` | OpenAI API key for OpenClaw | Falls back to stack-wide `OPENAI_API_KEY` |

### Localhost-Specific

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENCLAW_LOCALHOST_URL` | Local service URL | `http://host.docker.internal:63024` |

## LLM Configuration

OpenClaw automatically inherits the stack's LLM provider configuration:

- **Ollama**: Connects to the stack's Ollama endpoint automatically. The `OLLAMA_API_KEY` is set to `"ollama-local"` which activates the Ollama provider in OpenClaw.
- **Anthropic**: Set `OPENCLAW_ANTHROPIC_API_KEY` in `.env`, or OpenClaw uses the stack-wide key if available.
- **OpenAI**: Set `OPENCLAW_OPENAI_API_KEY` in `.env`, or falls back to stack-wide `OPENAI_API_KEY`.

**Provider Priority**: OpenClaw uses providers in this order: Anthropic > OpenAI > Ollama. If you want to force Ollama usage, ensure no Anthropic/OpenAI keys are set.

**Important**: When connecting to the stack's Ollama, OpenClaw uses the native Ollama API (not `/v1`). Do not add `/v1` to the Ollama URL.

## Web Dashboard

The OpenClaw gateway includes a built-in web dashboard for administration:

- **Direct access**: `http://localhost:63024`
- **Via Kong**: `http://openclaw.localhost:63002`

The dashboard provides:
- Chat interface for interacting with the agent
- Configuration management
- Execution approvals
- Channel status monitoring

**Security**: The dashboard is an admin surface. If `OPENCLAW_GATEWAY_TOKEN` is set, you'll need to provide the token to access the dashboard.

## Interactive CLI Usage

Run OpenClaw CLI commands inside the container:

```bash
# Run onboarding
docker exec -it genai-openclaw-gateway openclaw onboard

# Configure settings
docker exec -it genai-openclaw-gateway openclaw config set models.providers.ollama.baseUrl "http://ollama:11434"

# Check health
docker exec -it genai-openclaw-gateway openclaw doctor

# View gateway status
docker exec -it genai-openclaw-gateway openclaw gateway probe
```

Or use docker compose run for one-off commands:
```bash
docker compose run --rm openclaw-gateway openclaw config get gateway.auth.token
```

## Health Check

```bash
# Direct health check
curl http://localhost:63024/healthz

# Deep health check (requires token)
docker exec genai-openclaw-gateway node dist/index.js health --token "$OPENCLAW_GATEWAY_TOKEN"
```

## Source Modes

### container

Runs OpenClaw gateway in a Docker container.

**Best for**: Standard deployment, messaging app integrations

**Resources**: ~2GB RAM minimum

**Setup**: Automatic via docker-compose

### localhost

Connects to OpenClaw running natively on the host machine.

**Best for**: Development, custom configurations, persistent settings

**Resources**: Node.js 22+, npm

**Setup**: Manual - `npm install -g openclaw`, then `openclaw gateway`

### disabled

No OpenClaw agent (default).

**Best for**: When messaging agent functionality is not needed

**Impact**: No messaging platform integration available

## Dependencies

### Required

- None (OpenClaw is optional for all services)

### Optional (LLM Providers)

- **Ollama**: Local LLM inference (auto-configured when available)
- **Anthropic API**: Cloud LLM (requires API key)
- **OpenAI API**: Cloud LLM (requires API key)

## Troubleshooting

### Permission Denied on Startup

**Problem**: `EACCES: permission denied, open '/home/node/.openclaw/openclaw.json'`

**Solution**:
1. The `openclaw-init` container should fix this automatically on startup
2. If it persists, manually fix: `docker run --rm -v genai-openclaw-config:/data alpine chown -R 1000:1000 /data`
3. Restart the gateway: `docker restart genai-openclaw-gateway`

### Gateway Won't Start

**Problem**: OpenClaw container fails to start

**Solution**:
1. Check logs: `docker logs genai-openclaw-gateway`
2. Verify image is available: `docker pull ghcr.io/openclaw/openclaw:latest`
3. Ensure ports 63024/63025 are not in use
4. Check Docker has sufficient memory (2GB+ recommended)

### Can't Connect to Ollama

**Problem**: OpenClaw doesn't see Ollama models

**Solution**:
1. Verify Ollama is running: `curl http://localhost:63012/api/tags`
2. Check the Ollama endpoint is configured correctly
3. Run inside container: `docker exec genai-openclaw-gateway openclaw config get models.providers.ollama`
4. Ensure `OLLAMA_API_KEY` is set (any value activates the provider)

### Dashboard Not Loading

**Problem**: Web dashboard returns errors

**Solution**:
1. Check health endpoint: `curl http://localhost:63024/healthz`
2. Wait for startup (20s start period)
3. If using Kong, verify hosts file: `./start.sh --setup-hosts`
4. Check if `OPENCLAW_GATEWAY_TOKEN` is required

### Port Already in Use

**Problem**: Port 63024 or 63025 is occupied

**Solution**:
```bash
# Use different base port
./start.sh --base-port 64000

# Or check what's using the port
lsof -i :63024
```

## References

- [OpenClaw Documentation](https://docs.openclaw.ai/)
- [OpenClaw Docker Guide](https://docs.openclaw.ai/install/docker)
- [OpenClaw Ollama Integration](https://docs.openclaw.ai/providers/ollama)
- [OpenClaw GitHub Repository](https://github.com/openclaw/openclaw)
