# GenAI Vanilla Stack

A flexible, modular GenAI project boilerplate with customizable services.

This project provides a solid foundation for building GenAI applications with a focus on modularity, allowing developers to swap components or connect to external services as needed. It supports both local development and production deployment with GPU acceleration.

![Architecture Diagram](./docs/images/architecture.png)

## 1. Project Overview

GenAI Vanilla Stack is a customizable multi-service architecture for AI applications, featuring:

- **Dynamic Service Configuration**: SOURCE-based deployment with CLI overrides
- **Intelligent Kong Gateway**: Auto-generated routes based on active services  
- **Cross-Platform Support**: Python-based bootstrapping works on all OS
- **Flexible Deployment**: Mix containerized, localhost, and external services
- **Support for GPU acceleration and cloud deployment (AWS ECS compatible)**
- **Core services**: Supabase ecosystem, Neo4j, Redis, Ollama, FastAPI backend, Kong Gateway

## 2. Features

- **2.1. API Gateway (Kong)**: Centralized API management, authentication, and routing for backend services.
- **2.2. Real-time Data Synchronization**: Live database change notifications via Supabase Realtime WebSocket connections.
- **2.3. Flexible Service Configuration**: Switch between containerized services or connect to existing external endpoints by using SOURCE variables in .env.example (e.g., `LLM_PROVIDER_SOURCE=ollama-localhost` for local Ollama).
- **2.4. Modular Service Configuration**: Choose different service combinations via SOURCE variables in .env.example
- **2.5. Cloud Ready**: Designed for seamless deployment to cloud platforms like AWS ECS
- **2.6. Environment-based Configuration**: Easy configuration through environment variables
- **2.7. Explicit Initialization Control**: Uses a dedicated `supabase-db-init` service to manage custom database setup after the base database starts.
- **2.8. Dynamic Kong Configuration**: Intelligent API Gateway configuration that adapts to your SOURCE settings

### 2.8. Dynamic Kong Configuration

The stack now features intelligent Kong API Gateway configuration that adapts to your SOURCE settings:

- **Automatic Route Generation**: Kong routes are dynamically created based on enabled services
- **Health Checking**: Localhost services are checked for availability before routing
- **Adaptive Configuration**: Disabled services automatically have their routes removed
- **No Manual Configuration**: Replaces the old dual kong.yml/kong-local.yml approach

The dynamic configuration is generated at startup by `bootstrapper/utils/kong_config_generator.py` and includes:
- Automatic detection of service availability
- Smart routing for localhost vs container services
- Proper handling of external service URLs
- WebSocket support for real-time services

## 3. Getting Started

### 3.1. Prerequisites

- Docker and Docker Compose
- Python 3.10+ (required for running start/stop scripts)
- UV package manager (optional, for better Python dependency management)

#### 3.1.1. Docker Resource Requirements

This stack requires sufficient resources allocated to your Docker environment:

- **Memory**: At least 8GB, preferably 10-12GB RAM allocated to Docker
- **CPU**: At least 4 cores recommended, especially for running AI models
- **Disk**: At least 10GB of free space for Docker volumes

**For Docker Desktop users:**
- Increase memory allocation in Settings → Resources → Memory
- Increase CPU allocation in Settings → Resources → CPU

**For Colima users:**
```bash
# Start Colima with adequate resources (adjust as needed)
colima start --memory 12 --cpu 6
```

**Important**: After adding the n8n service to the stack, memory requirements have increased. If you experience container crashes with exit code 137 (OOM kill), this indicates insufficient memory allocated to Docker.

### 3.2. Quick Start Configurations

The GenAI Vanilla stack uses a **SOURCE-based configuration system** that provides flexible deployment options through simple environment variable configuration.

#### 🚀 **Option 1: Full Container Setup (Recommended for Beginners)**

**What it does:** Runs all AI services (Ollama, ComfyUI, Weaviate) inside Docker containers with CPU-only processing.

```bash
# 1. Clone and navigate to the repository
git clone <your-repository-url>
cd genai-vanilla

# 2. Use default configuration (already set in .env.example)
# LLM_PROVIDER_SOURCE=ollama-container-cpu
# COMFYUI_SOURCE=container-cpu  
# WEAVIATE_SOURCE=container

# 3. Start the stack
./start.sh

# 4. Access services (after ~5 minutes for AI model downloads)
# - Open WebUI: http://localhost:63015
# - n8n Workflows: http://localhost:63002/n8n/
# - Supabase Studio: http://localhost:63009
```

#### 🏠 **Option 2: Local AI Services Setup**

**What it does:** Uses your local Ollama and ComfyUI installations, with other services in containers.

```bash
# 1. Install Ollama locally first
curl -fsSL https://ollama.com/install.sh | sh

# 2. Start Ollama and pull models
ollama serve
# In another terminal:
ollama pull qwen2.5:latest
ollama pull mxbai-embed-large

# 3. Edit .env.example to use localhost services
cp .env.example .env
# Edit .env and change:
# LLM_PROVIDER_SOURCE=ollama-localhost
# COMFYUI_SOURCE=localhost

# 4. Start the stack
./start.sh

# 5. Benefits: Faster startup, uses your local models, less Docker resource usage
```

#### 🔥 **Option 3: GPU-Accelerated Containers**

**What it does:** Runs AI services in containers with full GPU acceleration (requires NVIDIA GPU + Docker GPU support).

```bash
# 1. Ensure NVIDIA Container Toolkit is installed
# Follow: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

# 2. Edit .env.example for GPU acceleration
cp .env.example .env
# Edit .env and change:
# LLM_PROVIDER_SOURCE=ollama-container-gpu
# COMFYUI_SOURCE=container-gpu

# 3. Start the stack
./start.sh

# 4. Verify GPU usage: docker exec genai-ollama nvidia-smi
```

#### ☁️ **Option 4: Cloud API Setup**

**What it does:** Uses cloud LLM APIs (OpenAI, Anthropic, etc.) instead of local models.

```bash
# 1. Edit .env.example for API configuration
cp .env.example .env
# Edit .env and change:
# LLM_PROVIDER_SOURCE=api
# COMFYUI_SOURCE=disabled

# 2. Start the stack
./start.sh

# 3. Configure API providers in Open WebUI:
# Go to http://localhost:63015 → Settings → Connections
# Add your OpenAI/Anthropic API keys
```

### 3.3. Advanced Configuration

#### Understanding SOURCE Variables

The stack uses these primary SOURCE variables in your `.env` file:

**Services that support localhost SOURCE:**
- ✅ **`LLM_PROVIDER_SOURCE`**: Controls Ollama deployment
  - `ollama-container-cpu` - Docker container, CPU only (default)
  - `ollama-container-gpu` - Docker container with GPU acceleration
  - `ollama-localhost` - Use Ollama running on host machine ✅
  - `api` - Use cloud API providers instead
  - `disabled` - No LLM service

- ✅ **`COMFYUI_SOURCE`**: Controls ComfyUI deployment
  - `container-cpu` - Docker container, CPU only (default)
  - `container-gpu` - Docker container with GPU acceleration
  - `localhost` - Use ComfyUI running on host machine (port 8188) ✅
  - `disabled` - No image generation service

- ✅ **`WEAVIATE_SOURCE`**: Controls vector database
  - `container` - Docker container (default)
  - `localhost` - Use Weaviate on host machine ✅
  - `disabled` - No vector search capabilities

**Services that do NOT support localhost SOURCE (container only):**
- ❌ **`N8N_SOURCE`**: Controls N8N workflow automation
  - `container` - Docker container only
  - `disabled` - No workflow automation

- ❌ **`SEARXNG_SOURCE`**: Controls SearxNG privacy search
  - `container` - Docker container only  
  - `disabled` - No privacy search engine

- ❌ **`OPEN_WEB_UI_SOURCE`**: Controls Open-WebUI chat interface
  - `container` - Docker container only
  - `disabled` - No chat interface

- ❌ **`BACKEND_SOURCE`**: Controls FastAPI backend
  - `container` - Docker container only
  - `disabled` - No backend API

### 3.3.1 Command-Line SOURCE Overrides

The start.sh script now supports direct SOURCE configuration via command-line arguments, allowing you to override .env settings without editing files:

#### Available SOURCE Override Arguments:

**--llm-provider-source** (Options: ollama-container-cpu, ollama-container-gpu, ollama-localhost, ollama-external, api, disabled)
- Controls how LLM services are deployed
- Example: `./start.sh --llm-provider-source ollama-localhost`

**--comfyui-source** (Options: container-cpu, container-gpu, localhost, external, disabled)
- Controls ComfyUI image generation deployment
- Example: `./start.sh --comfyui-source localhost`

**--weaviate-source** (Options: container, localhost, disabled)
- Controls Weaviate vector database deployment
- Example: `./start.sh --weaviate-source localhost`

**--n8n-source** (Options: container, disabled)
- Controls N8N workflow automation deployment
- Example: `./start.sh --n8n-source disabled`

**--searxng-source** (Options: container, disabled)
- Controls SearxNG privacy search engine deployment
- Example: `./start.sh --searxng-source disabled`

#### Common Usage Patterns:

**1. Development with Local AI Services:**
```bash
./start.sh --llm-provider-source ollama-localhost \
          --comfyui-source localhost \
          --weaviate-source container
```

**2. Production with GPU Acceleration:**
```bash
./start.sh --llm-provider-source ollama-container-gpu \
          --comfyui-source container-gpu \
          --base-port 80
```

**3. Lightweight API-Only Setup:**
```bash
./start.sh --llm-provider-source api \
          --comfyui-source disabled \
          --weaviate-source disabled \
          --n8n-source disabled \
          --searxng-source disabled
```

**4. Cold Start with Custom Configuration:**
```bash
./start.sh --cold \
          --base-port 55666 \
          --llm-provider-source ollama-localhost \
          --comfyui-source localhost \
          --setup-hosts
```

**Note:** CLI overrides are temporary and only apply to the current session. The next run without arguments will use values from .env file.

#### Complete Script Reference

```bash
# Basic Operations
./start.sh                    # Start with .env configuration
./start.sh --help            # Show all available options
./start.sh --help-usage      # Show detailed usage examples

# Port and Network Configuration
./start.sh --base-port 64000  # Use custom port range
./start.sh --setup-hosts      # Configure /etc/hosts for *.localhost domains
./start.sh --skip-hosts       # Skip hosts file setup

# Fresh Start Options
./start.sh --cold             # Complete reset: new keys, cleanup, fresh start
./stop.sh --cold              # Stop and remove all data

# Service SOURCE Overrides (temporary, session-only)
./start.sh --llm-provider-source ollama-localhost
./start.sh --comfyui-source localhost  
./start.sh --weaviate-source disabled
./start.sh --n8n-source disabled
./start.sh --searxng-source disabled

# Combined Examples
./start.sh --cold --base-port 55666 --llm-provider-source ollama-localhost
./start.sh --comfyui-source container-gpu --setup-hosts
```

#### Service Dependencies

The stack automatically configures service dependencies based on your SOURCE choices:

- **n8n workflows** → Requires Weaviate for vector operations
- **Open WebUI** → Connects to available LLM and ComfyUI services
- **Backend API** → Integrates with all available AI services
- **Local Deep Researcher** → Uses configured LLM for research tasks

### 3.4. Troubleshooting Quick Start Issues

#### Common Issues and Solutions

**🔍 Port Conflicts**
```bash
# Error: "bind: address already in use"
# Solution: Use different port range
./start.sh --base-port 64000

# Or find what's using the port:
lsof -i :63015  # Check specific port
```

**🐳 Docker Resource Issues**
```bash
# Error: Containers crashing with exit code 137
# Solution: Increase Docker memory allocation
# Docker Desktop: Settings → Resources → Memory (set to 8-12GB)
# Colima: colima start --memory 12 --cpu 6
```

**🧠 AI Model Download Issues**
```bash
# ComfyUI models downloading slowly?
# Check progress:
docker logs genai-comfyui-init -f

# Ollama models not pulling?
# Check Ollama logs:
docker logs genai-ollama -f

# For localhost setup, ensure models are pre-downloaded:
ollama pull qwen2.5:latest
ollama pull mxbai-embed-large
```

**🎨 ComfyUI Model Management**
```bash
# Models are automatically downloaded by comfyui-init service
# This happens for BOTH container and localhost setups
# Check download progress:
docker logs genai-comfyui-init -f

# For localhost ComfyUI, models are still downloaded to ensure consistency
# The init service manages model placement regardless of SOURCE setting
```

**🌐 Service Connectivity Issues**
```bash
# Services showing as unhealthy?
# Check overall status:
docker compose ps

# Check specific service logs:
docker logs genai-[service-name] -f

# Common fix - restart unhealthy services:
docker restart genai-weaviate genai-supabase-studio
```

**⚡ Localhost Service Issues**
```bash
# "Connection refused" when using localhost SOURCE?
# Verify service is running and accessible:
curl http://localhost:11434/api/tags  # For Ollama
curl http://localhost:8188/           # For ComfyUI

# Ensure proper SOURCE configuration in .env:
LLM_PROVIDER_SOURCE=ollama-localhost
COMFYUI_SOURCE=localhost
```


#### Complete Fresh Restart

```bash
# If everything is broken, start fresh:
./stop.sh --cold                    # Remove all data
./start.sh --cold --base-port 64000 # Fresh start with new ports
```

### 3.4.1 Cross-Platform Compatibility

The stack uses Python-based bootstrapping for consistent behavior across platforms:

**Benefits:**
- ✅ Works on Windows, macOS, and Linux
- ✅ Automatic dependency resolution
- ✅ Better error handling and recovery
- ✅ Consistent port management
- ✅ Dynamic configuration generation

**Using UV Package Manager (Recommended):**
```bash
# Install UV for better dependency management
pip install uv

# The start.sh script will automatically detect and use UV
./start.sh  # Automatically uses UV if available
```

**Direct Python Execution:**
```bash
# If shell scripts don't work on your system
python3 bootstrapper/start.py --help
python3 bootstrapper/stop.py --help
```

#### Python Script Issues

If the start/stop scripts fail:
```bash
# 1. Ensure Python 3.10+ is installed
python3 --version

# 2. Install UV for better dependency management (optional)
pip install uv

# 3. Run directly with Python if wrapper fails
python3 bootstrapper/start.py --help
python3 bootstrapper/stop.py --help

# 4. Check for missing Python modules (if running without UV)
pip install pyyaml click rich
```

### 3.5. Manual Docker Compose Commands (Alternative)

You can also use Docker Compose commands directly with the unified configuration:

```bash
# First, make sure all previous services are stopped to avoid port conflicts
docker compose --env-file=.env down --remove-orphans

# Start all services with current SOURCE configuration
docker compose --env-file=.env up

# Build all services
docker compose --env-file=.env build

# Recommended: Use start.sh script for easier SOURCE configuration management
./start.sh  # Uses SOURCE variables from .env file
```

### 3.6. Convenience Scripts Reference

#### start.sh Script Details

The `start.sh` script is now a thin wrapper that calls the Python implementation:
1. Detects if UV is available for better dependency management
2. Calls `bootstrapper/start.py` with all arguments
3. Falls back to system Python if UV is not installed

The Python implementation automatically:
1. Copies `.env.example` to `.env` if needed
2. Generates ALL encryption keys (Supabase, N8N, SearxNG) when needed
3. Configures service scaling based on SOURCE variables
4. Manages port assignments and conflicts
5. Validates service dependencies and auto-resolves conflicts
6. Displays service status and access URLs

```bash
Usage: ./start.sh [options]
Options:
  --base-port PORT   Set base port (default: 63000)
  --cold             Fresh install with new keys  
  --setup-hosts      Configure hosts file
  --skip-hosts       Skip hosts file setup
  --help             Show help message
```
6. Explicitly uses the `.env` file when starting Docker Compose to ensure port settings are applied consistently
7. Starts the appropriate Docker Compose configuration

**First-time Setup:**
When running for the first time, the script will automatically:
- Create the `.env` file from `.env.example`
- Generate all required encryption keys (Supabase JWT, N8N, SearxNG)
- Set all port numbers based on the specified base port

**Cold Start Option:**
Use the `--cold` option to force a complete reset of the environment:
```bash
./start.sh --cold
```
This will:
- Back up your existing `.env` file with a timestamp
- Create a fresh `.env` file from `.env.example`
- Generate new encryption keys for all services
- Set all port numbers based on the specified base port
- Perform comprehensive Docker cleanup (containers, volumes, networks)

**Port Assignment Logic:**
- SUPABASE_DB_PORT = BASE_PORT + 0
- REDIS_PORT = BASE_PORT + 1
- KONG_HTTP_PORT = BASE_PORT + 2
- KONG_HTTPS_PORT = BASE_PORT + 3
- SUPABASE_META_PORT = BASE_PORT + 4
- SUPABASE_STORAGE_PORT = BASE_PORT + 5
- SUPABASE_AUTH_PORT = BASE_PORT + 6
- SUPABASE_API_PORT = BASE_PORT + 7
- SUPABASE_REALTIME_PORT = BASE_PORT + 8
- SUPABASE_STUDIO_PORT = BASE_PORT + 9
- GRAPH_DB_PORT = BASE_PORT + 10
- GRAPH_DB_DASHBOARD_PORT = BASE_PORT + 11
- LLM_PROVIDER_PORT = BASE_PORT + 12
- LOCAL_DEEP_RESEARCHER_PORT = BASE_PORT + 13
- SEARXNG_PORT = BASE_PORT + 14
- OPEN_WEB_UI_PORT = BASE_PORT + 15
- BACKEND_PORT = BASE_PORT + 16
- N8N_PORT = BASE_PORT + 17
- COMFYUI_PORT = BASE_PORT + 18
- WEAVIATE_PORT = BASE_PORT + 19
- WEAVIATE_GRPC_PORT = BASE_PORT + 20

**Troubleshooting Port Issues:**
- If services appear to use inconsistent port numbers despite setting a custom base port, make sure to always use the `--env-file=.env` flag with Docker Compose commands
- The script automatically uses this flag to ensure Docker Compose reads the updated environment variables
- When running Docker Compose manually, always include this flag: `docker compose --env-file=.env ...`

**Troubleshooting Research Integration:**
- Research service health: `curl http://localhost:${BACKEND_PORT}/research/health`
- Check local-deep-researcher status: `docker compose ps local-deep-researcher`
- View research logs: `docker compose logs local-deep-researcher`
- For detailed troubleshooting: See section 15.3 "Deep Researcher Integration"

#### stop.sh

The `stop.sh` script is now a thin wrapper that calls the Python implementation:
1. Detects if UV is available for better dependency management
2. Calls `bootstrapper/stop.py` with all arguments
3. Falls back to system Python if UV is not installed

This script stops the stack and cleans up resources:

```bash
Usage: ./stop.sh [options]
Options:
  --cold             Remove volumes (data will be lost)
  --clean-hosts      Remove GenAI Stack hosts file entries (requires sudo/admin)
  --help             Show this help message
```

The script:
1. Reads SOURCE configuration from .env file
2. Stops all containers for enabled services
3. Removes orphaned containers
4. Preserves data volumes by default

**Cold Stop Option:**
Use the `--cold` option to perform a complete cleanup including volumes:
```bash
./stop.sh --cold
```
This will:
- Stop all containers
- Remove all volumes (all data will be lost)
- Remove orphaned containers

This is useful when you want to start completely fresh, but be careful as all database data will be lost.

**Hosts File Cleanup:**
Use the `--clean-hosts` option to remove subdomain entries from your hosts file:
```bash
sudo ./stop.sh --clean-hosts ./start.sh
```
This will remove all GenAI Stack subdomain entries (n8n.localhost, api.localhost, search.localhost, comfyui.localhost) from your system's hosts file.

---

## 🎉 **Getting Started Summary**

**New to the stack?** → Use **Option 1: Full Container Setup** for the easiest experience  
**Have local Ollama?** → Use **Option 2: Local AI Services** for better performance  
**Have NVIDIA GPU?** → Use **Option 3: GPU-Accelerated** for maximum speed  
**Need cloud APIs?** → Use **Option 4: Cloud API Setup** for OpenAI/Anthropic integration

The SOURCE-based configuration system provides a simple and flexible way to customize your deployment.

**Next Steps After Starting:** Access your services, configure API keys if needed, and explore the workflows in n8n and Open WebUI!

---

## 4. Quick Access Guide

Once the stack is running, you can access services at the following URLs:

### Main Services
- **Supabase Studio**: `http://localhost:${SUPABASE_STUDIO_PORT}` (default: 63009)
- **Neo4j Dashboard**: `http://localhost:${GRAPH_DB_DASHBOARD_PORT}` (default: 63011)
- **SearxNG Privacy Search**: 
  - **Direct**: `http://localhost:${SEARXNG_PORT}` (default: 63014)
  - **Via Kong**: `http://search.localhost:${KONG_HTTP_PORT}/` (default: search.localhost:63002) - ✅ **Subdomain Access**
    - **Setup Required**: Add hosts file entries (see Section 16.2 below)
- **Open-WebUI**: 
  - **Direct**: `http://localhost:${OPEN_WEB_UI_PORT}` (default: 63015)
  - **Via Kong**: `http://chat.localhost:${KONG_HTTP_PORT}/` (default: chat.localhost:63002) - ✅ **Subdomain Access**
    - **Setup Required**: Add hosts file entries (see Section 16.2 below)
- **n8n Workflow Automation**: 
  - **Direct**: `http://localhost:${N8N_PORT}` (default: 63017) - ✅ **Recommended**
  - **Via Kong**: `http://n8n.localhost:${KONG_HTTP_PORT}/` (default: n8n.localhost:63002) - ✅ **Fully Working**
    - **Setup Required**: Add hosts file entries (see Section 16.2 below for detailed instructions)
- **ComfyUI Image Generation**:
  - **Direct**: `http://localhost:${COMFYUI_PORT}` (default: 63018) - ✅ **Authentication Bypassed**
  - **Local (localhost SOURCE configuration)**: `http://localhost:8000`
  - **Via Kong**: `http://comfyui.localhost:${KONG_HTTP_PORT}/` (default: comfyui.localhost:63002) - ✅ **Subdomain Access**
    - **Setup Required**: Add hosts file entries (see Section 16.2 below)

### API Endpoints
- **Backend API**: 
  - **Direct**: `http://localhost:${BACKEND_PORT}` (default: 63016)
  - **Via Kong**: `http://api.localhost:${KONG_HTTP_PORT}/` (default: api.localhost:63002) - ✅ **Subdomain Access**
    - **Setup Required**: Add hosts file entries (see Section 16.2 below)
- **Kong API Gateway**: `http://localhost:${KONG_HTTP_PORT}` (default: 63002)

### Database Services
- **PostgreSQL**: `localhost:${SUPABASE_DB_PORT}` (default: 63000)
- **Neo4j**: `bolt://localhost:${GRAPH_DB_PORT}` (default: 63010)
- **Redis**: `localhost:${REDIS_PORT}` (default: 63001)

## 5. Service Configuration

Services can be configured through SOURCE environment variables in the unified Docker Compose architecture:

### 5.1. Environment Variables

The project uses two environment files:
- `.env` - Contains actual configuration values (not committed to git)
- `.env.example` - Template with the same structure but empty secret values (committed to git)

**Note on Service Naming:**

The service names used in the `docker-compose.yml` files (e.g., `supabase-auth`, `supabase-api`) are mapped to Kong routes through dynamic configuration generation. The Kong gateway routes are automatically generated based on SOURCE values and active services at startup.

### 5.2. Kong API Gateway Configuration

The Kong API Gateway is used for centralized API management, including routing, authentication, plugin management, and WebSocket proxying for real-time services. It is configured dynamically based on SOURCE values.

*   **Dynamic Configuration:** Routes are generated at startup by `bootstrapper/utils/kong_config_generator.py` based on enabled services.
*   **WebSocket Support:** Kong automatically handles HTTP to WebSocket protocol upgrades for services like n8n and Supabase Realtime.
*   **Environment Variables:** The following variables are used by the Kong service and must be set in your `.env` file:
    *   `KONG_HTTP_PORT`: Port for Kong's HTTP listener.
    *   `KONG_HTTPS_PORT`: Port for Kong's HTTPS listener.
    *   `DASHBOARD_USERNAME`: Username for accessing the Kong dashboard (if enabled).
    *   `DASHBOARD_PASSWORD`: Password for accessing the Kong dashboard.

When setting up the project:
1. Copy `.env.example` to `.env`
2. Fill in the required values in `.env`
3. Keep both files in sync when adding new variables

## 6. Authentication and User Management

This stack utilizes Supabase Auth (GoTrue) for user authentication and management, leveraging JSON Web Tokens (JWTs) for secure API access.

### 6.1. Overview

- **Provider:** Supabase Auth (`supabase-auth` service) handles user registration, login, password management, and JWT issuance.
- **Method:** Authentication relies on JWTs signed with a shared secret (`SUPABASE_JWT_SECRET`).
- **Gateway:** The Kong API Gateway (`kong-api-gateway`) acts as the entry point for most API requests, routing them to the appropriate backend services. Authentication policies are dynamically configured based on service requirements. The `key-auth` and `acl` plugins are applied automatically where needed. Authentication is primarily handled by the upstream Supabase services.
- **Clients:** Services like `supabase-studio` and the `backend` API act as clients, obtaining JWTs from `supabase-auth` and including them in requests to other services via Kong.

### 6.2. Key Components and Configuration

- **`supabase-auth` (GoTrue):**
    - Issues JWTs upon successful login/sign-up.
    - Validates JWTs presented to its endpoints.
    - Configured via `GOTRUE_*` environment variables in `docker-compose` files (e.g., `GOTRUE_JWT_SECRET`, `GOTRUE_DISABLE_SIGNUP`, `GOTRUE_MAILER_AUTOCONFIRM`).
    - By default, sign-ups are enabled (`GOTRUE_DISABLE_SIGNUP="false"`) and emails are auto-confirmed (`GOTRUE_MAILER_AUTOCONFIRM="true"`) for local development convenience.
- **`supabase-api` (PostgREST):**
    - Expects a valid JWT in the `Authorization: Bearer <token>` header for most requests.
    - Validates the JWT signature using `PGRST_JWT_SECRET` (shared with `supabase-auth`).
    - Enforces database permissions based on the `role` claim in the JWT (e.g., `anon`, `authenticated`) via PostgreSQL's Row Level Security (RLS).
- **`supabase-storage`:**
    - Uses JWTs passed via Kong to enforce storage access policies defined in the database.
- **`kong-api-gateway`:**
    - Routes authenticated requests to backend services.
    - Currently relies on upstream services for JWT validation. (See note above about commented-out plugins).
- **JWT Keys (`.env` file):**
    - `SUPABASE_JWT_SECRET`: The secret key used to sign and verify all JWTs. Must be consistent across `supabase-auth`, `supabase-api`, and `supabase-storage`.
    - `SUPABASE_ANON_KEY`: A pre-generated, long-lived JWT representing the `anon` (anonymous) role. Used for public access requests.
    - `SUPABASE_SERVICE_KEY`: A pre-generated, long-lived JWT representing the `service_role`. Grants administrative privileges, bypassing RLS. Use with caution.

### 6.3. Setup and Usage

1.  **Generate Keys:** The start.py script automatically generates secure Supabase JWT keys during first run or cold start. This creates secure values for `SUPABASE_JWT_SECRET`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_KEY` and populates them in your `.env` file.
2.  **Client Authentication:** Client applications (like a frontend app interacting with the `backend` service, or the `backend` service itself interacting with Supabase APIs) need to:
    *   Implement a login flow using `supabase-auth` endpoints (e.g., `/auth/v1/token?grant_type=password`).
    *   Store the received JWT securely.
    *   Include the JWT in the `Authorization: Bearer <token>` header for subsequent requests to protected API endpoints via the Kong gateway.
3.  **Anonymous Access:** For requests that should be publicly accessible, use the `SUPABASE_ANON_KEY` in the `Authorization` header. Ensure appropriate RLS policies are set up in the database for the `anon` role.
4.  **Service Role Access:** For backend operations requiring administrative privileges, use the `SUPABASE_SERVICE_KEY` in the `Authorization` header. This key should be handled securely and never exposed to frontend clients.
5.  **User Management via Studio:** You can manage users (invite, delete, etc.) through the Supabase Studio interface (`http://localhost:${SUPABASE_STUDIO_PORT}`), which interacts with the `supabase-auth` service.

## 7. Database Services

### 7.1. Supabase Services

The Supabase services provide a PostgreSQL database with additional capabilities along with a web-based Studio interface for management:

#### 7.1.1. Supabase PostgreSQL Database

The Supabase PostgreSQL database comes with pgvector and PostGIS extensions for vector operations and geospatial functionality.

#### 7.1.2. Supabase Auth Service

The Supabase Auth service (GoTrue) provides user authentication and management:

- **API Endpoint**: Available at http://localhost:${SUPABASE_AUTH_PORT} (configured via `SUPABASE_AUTH_PORT`)
- **JWT Authentication**: Uses a secure JWT token system for authentication
- **Features**: User registration, login, password recovery, email confirmation, and more

#### 7.1.3. Supabase Storage Service

The Supabase Storage service provides a secure file storage and management system:

- **API Endpoint**: Available at http://localhost:${SUPABASE_STORAGE_PORT} (configured via `SUPABASE_STORAGE_PORT`)
- **Features**:
  - File upload and download
  - Public and private buckets
  - Access control via JWT tokens
  - Integration with Supabase Auth for user-specific storage
- **Configuration**:
  - `STORAGE_BACKEND`: File storage backend (default: file)
  - `FILE_SIZE_LIMIT`: Maximum file size in bytes (default: 50MB)
  - `REGION`: Storage region identifier (default: local)
- **Dependencies**: Requires Supabase DB and Auth services

#### 7.1.4. Supabase API Service (PostgREST)

The Supabase API service (PostgREST) provides a RESTful API interface to the PostgreSQL database:

- **API Endpoint**: Available at http://localhost:${SUPABASE_API_PORT} (configured via `SUPABASE_API_PORT`)
- **Auto-generated API**: Automatically generates RESTful endpoints for all tables and views
- **JWT Authentication**: Uses the same JWT tokens as the Auth service for secure access
- **Role-Based Access Control**: Enforces database-level permissions based on JWT claims
- **Dependencies**: Requires both the Supabase DB and Auth services

**API Usage Examples:**

- **List all records**: `GET http://localhost:${SUPABASE_API_PORT}/table_name`
- **Filter records**: `GET http://localhost:${SUPABASE_API_PORT}/table_name?column=value`
- **Create record**: `POST http://localhost:${SUPABASE_API_PORT}/table_name` with JSON body
- **Update record**: `PATCH http://localhost:${SUPABASE_API_PORT}/table_name?id=eq.1` with JSON body
- **Delete record**: `DELETE http://localhost:${SUPABASE_API_PORT}/table_name?id=eq.1`

**Authentication Headers:**

- Anonymous access: `Authorization: Bearer ${SUPABASE_ANON_KEY}`
- Authenticated access: `Authorization: Bearer user_jwt_token`
- Service role access: `Authorization: Bearer ${SUPABASE_SERVICE_KEY}`

**Health Check Endpoint:**

- The API provides a health check endpoint at `/health` that returns a simple "healthy" response
- This endpoint is used by Docker health checks to monitor the service status

**Configuration Options:**

The Supabase API service can be customized using the following environment variables:

- `SUPABASE_API_MAX_ROWS`: Maximum number of rows returned by a request (default: 1000)
- `SUPABASE_API_POOL`: Number of database connections to keep open (default: 10)
- `SUPABASE_API_POOL_TIMEOUT`: Timeout for acquiring a connection from the pool (default: 10)
- `SUPABASE_API_EXTRA_SEARCH_PATH`: Additional schemas to search (default: public,extensions)
- `SUPABASE_API_SERVER_PROXY_URI`: Proxy URI for external access

**Important Note on Environment Variables:**

The Supabase API service uses native PostgREST variables with the `PGRST_` prefix (e.g., `PGRST_DB_URI`, `PGRST_DB_SCHEMA`).

**IMPORTANT**: Before starting the stack for the first time, you must generate a secure JWT secret and auth tokens:

### Automatic Key Generation

All required encryption keys are automatically generated by the Python startup script:
- Supabase JWT keys (JWT_SECRET, ANON_KEY, SERVICE_KEY)
- N8N encryption key (48-character hex)
- SearxNG secret key (64-character hex)

Keys are generated:
- On first run when .env is created
- During cold start (--cold flag)
- When missing keys are detected

The automatic generation process:
1. Generates secure random JWT secrets
2. Creates properly signed JWT tokens for both anonymous and service role access
3. Updates your .env file with all required values

### Manual setup (alternative)

If you prefer to generate the keys manually:

1. Generate a JWT secret:
```bash
# Generate a random 32-character hex string for the JWT secret
openssl rand -hex 32

# Then copy this value to your .env file in the SUPABASE_JWT_SECRET variable
```

2. Generate JWT tokens for authentication using the JWT secret:
   - Go to [jwt.io](https://jwt.io/)
   - In the "PAYLOAD" section, create tokens with the following structure:
   
   For the ANON key (anonymous access):
   ```json
   {
     "iss": "supabase-local",
     "role": "anon",
     "exp": 2147483647
   }
   ```
   
   For the SERVICE key (service role access):
   ```json
   {
     "iss": "supabase-local",
     "role": "service_role",
     "exp": 2147483647
   }
   ```
   
   - In the "VERIFY SIGNATURE" section, enter your JWT secret
   - Copy the generated tokens to your .env file for SUPABASE_ANON_KEY and SUPABASE_SERVICE_KEY variables

#### 7.1.5. Supabase Realtime Service

The Supabase Realtime service provides real-time database change notifications via WebSocket connections:

- **API Endpoint**: Available at http://localhost:${SUPABASE_REALTIME_PORT} (configured via `SUPABASE_REALTIME_PORT`)
- **WebSocket Endpoint**: Available at `ws://localhost:${KONG_HTTP_PORT}/realtime/v1/` (via Kong API Gateway)
- **Features**:
  - Real-time database change notifications via logical replication
  - Presence channels for tracking online users
  - Broadcast messaging between clients
  - Row-Level Security (RLS) enforcement for secure channels
- **Configuration**:
  - Uses logical replication with dedicated replication slot (`supabase_realtime_slot`)
  - JWT authentication using the same tokens as other Supabase services
  - Configurable channel security and access control
- **Dependencies**: Requires Supabase DB, Auth, and API services
- **Integration**: Accessible through Kong API Gateway for centralized routing and policy enforcement

**Usage Examples:**

- **Connect to WebSocket**: `ws://localhost:${KONG_HTTP_PORT}/realtime/v1/websocket`
- **Subscribe to table changes**: Listen for INSERT, UPDATE, DELETE events on specific tables
- **Presence channels**: Track which users are currently online in your application
- **Broadcast messages**: Send real-time messages between connected clients

**Authentication:**
- Use the same JWT tokens as other Supabase services
- Anonymous access: Include `apikey=${SUPABASE_ANON_KEY}` in WebSocket connection
- Authenticated access: Include `apikey=user_jwt_token` in WebSocket connection

#### 7.1.6. Supabase Studio Dashboard

The Supabase Studio provides a modern web-based administration interface for PostgreSQL:

- **Accessible**: Available at http://localhost:${SUPABASE_STUDIO_PORT} (configured via `SUPABASE_STUDIO_PORT`)
- **Database**: The dashboard automatically connects to the PostgreSQL database
- **Features**: Table editor, SQL editor, database structure visualization, real-time connection monitoring, and more
- **Authentication**: Integrated with the Auth service for user management
- **Realtime Integration**: Shows active realtime connections and channel subscriptions

### 7.2. Neo4j Graph Database (neo4j-graph-db)

The Neo4j Graph Database service (`neo4j-graph-db`) provides a robust graph database for storing and querying connected data:

- **Built-in Dashboard Interface**: Available at http://localhost:${GRAPH_DB_DASHBOARD_PORT} (configured via `GRAPH_DB_DASHBOARD_PORT`)
- **First-time Login**:
  1. When you first access the dashboard, you'll see the Neo4j Browser interface
  2. In the connection form, you'll see it's pre-filled with "neo4j://neo4j-graph-db:7687"
  3. **Change the connection URL to**: `neo4j://localhost:${GRAPH_DB_PORT}` or `bolt://localhost:${GRAPH_DB_PORT}`
  4. Connection details:
     - Database: Leave as default (neo4j)
     - Authentication type: Username / Password
     - Username: `neo4j`
     - Password: Value of `GRAPH_DB_PASSWORD` from your `.env` file (default: neo4j_password)
  5. Click "Connect" button

- **Application Connection**: Applications can connect to the database using the Bolt protocol:
  - Bolt URL: `bolt://localhost:${GRAPH_DB_PORT}`
  - Username: `neo4j`
  - Password: Value of `GRAPH_DB_PASSWORD` from your `.env` file
- **Persistent Storage**: Data is stored in a Docker volume for persistence between container restarts

### 7.3. Weaviate Vector Database

Weaviate provides a powerful vector database for semantic search, RAG applications, and AI-driven workflows:

- **GraphQL API**: Available at `http://localhost:${WEAVIATE_PORT}/v1/graphql`
- **REST API**: Available at `http://localhost:${WEAVIATE_PORT}/v1`
- **gRPC API**: Available at `localhost:${WEAVIATE_GRPC_PORT}`
- **Kong Proxy**: Available at `http://vector.localhost:${KONG_HTTP_PORT}/` (requires hosts file setup)

#### 7.3.1. Features

- **Multi-modal Vector Search**: Support for text, images, and other data types
- **Hybrid Search**: Combines vector similarity with keyword search
- **Auto-vectorization**: Automatic embedding generation using Ollama or OpenAI
- **GraphQL Interface**: Powerful query language with built-in playground
- **CLIP Integration**: Image vectorization for visual similarity search
- **Real-time Updates**: Immediate availability of new data for search

#### 7.3.2. Dynamic Embedding Model Configuration

**Automatic Model Discovery**:
The system dynamically discovers and configures embedding models from your database:

1. **weaviate-init Service**: Queries the database for active Ollama embedding models
   ```sql
   SELECT name FROM public.llms WHERE provider = 'ollama' AND active = true AND embeddings > 0 ORDER BY embeddings DESC;
   ```

2. **Dynamic Configuration**: Automatically configures Weaviate to use the discovered model
3. **Fallback Strategy**: Uses `nomic-embed-text` if no active embedding model is found
4. **Runtime Verification**: Start script displays the discovered embedding model during startup

**Default Embedding Model**: `mxbai-embed-large` (configured in database seed data)
- High-quality 334M parameter model from mixedbread.ai
- 1,000-dimensional embeddings
- Superior performance compared to many OpenAI models

**Service Dependencies**:
The Weaviate integration includes proper dependency management:
- `weaviate-init` → Queries database for embedding configuration
- `multi2vec-clip` → Provides CLIP model for image embeddings
- `weaviate` → Depends on both init and CLIP services
- Application services (`backend`, `n8n`, `open-web-ui`) → Wait for Weaviate to be ready

#### 7.3.3. Integration Points

**Ollama Integration**:
- Text vectorization using your dynamically configured Ollama models
- Automatic embedding generation for documents
- Profile-aware configuration (containerized vs local Ollama)
- Model selection managed through database configuration

**Backend Service Integration**:
- Vector storage and retrieval for RAG applications
- Environment variables: `WEAVIATE_URL`, `WEAVIATE_ENABLED`, `WEAVIATE_OLLAMA_EMBEDDING_MODEL`
- REST API endpoints for vector operations
- Dynamic model discovery from shared configuration

**n8n Workflow Integration**:
- Automated document processing and vectorization
- Vector search workflows
- Batch processing capabilities

**ComfyUI Integration**:
- Image embedding storage via CLIP vectorization
- Visual similarity search for generated images
- Multi-modal search combining text and images

#### 7.3.4. Embedding Strategy

The system implements a multi-layered embedding approach:

**Text Embeddings**:
1. **Primary**: Dynamic Ollama model (discovered from database)
2. **Fallback**: OpenAI text2vec (if API key provided)
3. **Default**: `nomic-embed-text` (if no active model configured)

**Image Embeddings**:
1. **Primary**: multi2vec-clip (self-contained CLIP model)
2. **Specialized**: For cross-modal text-image search and visual similarity

**Multimodal Embeddings**:
1. **Primary**: multi2vec-clip for text-image alignment
2. **Text-only fallback**: Dynamic Ollama model for pure text

This approach provides:
- **Flexibility**: Change embedding models via database configuration
- **Performance**: Local processing without external API dependencies
- **Multimodal Capabilities**: CLIP for image and cross-modal tasks
- **Fallback Options**: Graceful degradation if services are unavailable

#### 7.3.5. Profile-Specific Configuration

**Default Profile** (`vector.yml`):
- Uses containerized Ollama at `http://ollama:11434`
- GPU acceleration disabled for CLIP

**AI-Local Profile** (`vector-local.yml`):
- Uses local Ollama at `http://host.docker.internal:11434`
- Requires local Ollama installation

**AI-GPU Profile** (`vector-gpu.yml`):
- Uses GPU-accelerated Ollama
- GPU-enabled CLIP processing for faster image vectorization

#### 7.3.4. Usage Examples

**GraphQL Query (Text Search)**:
```graphql
{
  Get {
    Document(
      nearText: {
        concepts: ["artificial intelligence"]
      }
      limit: 5
    ) {
      title
      content
      _additional {
        distance
      }
    }
  }
}
```

**REST API (Vector Storage)**:
```bash
curl -X POST http://localhost:${WEAVIATE_PORT}/v1/objects \
  -H "Content-Type: application/json" \
  -d '{
    "class": "Document",
    "properties": {
      "title": "AI Research Paper",
      "content": "Latest developments in machine learning..."
    }
  }'
```

#### 7.3.5. Access Points

- **GraphQL Playground**: `http://localhost:${WEAVIATE_PORT}/v1/graphql`
- **REST API Docs**: `http://localhost:${WEAVIATE_PORT}/v1`
- **Kong Proxy**: `http://vector.localhost:${KONG_HTTP_PORT}/v1/graphql`
- **Health Check**: `http://localhost:${WEAVIATE_PORT}/v1/.well-known/ready`

#### 7.3.6. Testing Weaviate Integration

After starting the stack, run these tests to verify Weaviate is working correctly:

**1. Health Check**:
```bash
# Check if Weaviate is ready
curl -s http://localhost:${WEAVIATE_PORT}/v1/.well-known/ready | jq .

# Check Weaviate schema endpoint
curl -s http://localhost:${WEAVIATE_PORT}/v1/schema | jq .
```

**2. Verify Embedding Model Configuration**:
```bash
# Check which embedding model is configured
docker logs genai-weaviate-init 2>&1 | grep "embedding model"

# Check Weaviate configuration and verify Ollama endpoint
docker exec genai-weaviate env | grep OLLAMA_ENDPOINT

# Verify model in containerized Ollama 
docker exec genai-ollama ollama list | grep mxbai-embed-large || echo "Containerized Ollama not running (likely localhost SOURCE configuration)"

# For localhost SOURCE configuration, check local Ollama
curl -s http://localhost:11434/api/tags | jq '.models[] | select(.name | contains("mxbai-embed-large"))' || echo "Local Ollama not available or model not pulled"
```

**3. Create a Test Collection**:

**For Default/GPU Profile** (containerized Ollama):
```bash
curl -X POST http://localhost:${WEAVIATE_PORT}/v1/schema \
  -H "Content-Type: application/json" \
  -d '{
    "class": "TestDocument",
    "vectorizer": "text2vec-ollama",
    "moduleConfig": {
      "text2vec-ollama": {
        "model": "mxbai-embed-large",
        "apiEndpoint": "http://ollama:11434"
      }
    },
    "properties": [
      {
        "name": "title",
        "dataType": ["text"]
      },
      {
        "name": "content", 
        "dataType": ["text"]
      }
    ]
  }'
```

**For AI-Local Profile** (local Ollama):
```bash
curl -X POST http://localhost:${WEAVIATE_PORT}/v1/schema \
  -H "Content-Type: application/json" \
  -d '{
    "class": "TestDocument", 
    "vectorizer": "text2vec-ollama",
    "moduleConfig": {
      "text2vec-ollama": {
        "model": "mxbai-embed-large",
        "apiEndpoint": "http://host.docker.internal:11434"
      }
    },
    "properties": [
      {
        "name": "title",
        "dataType": ["text"]
      },
      {
        "name": "content",
        "dataType": ["text"] 
      }
    ]
  }'
```

**4. Test Text Embedding (Ollama)**:

**For Default/GPU Profiles (Containerized Ollama)**:
```bash
# Create collection with containerized Ollama endpoint
curl -X POST http://localhost:${WEAVIATE_PORT}/v1/schema \
  -H "Content-Type: application/json" \
  -d '{
    "class": "TestDocument",
    "vectorizer": "text2vec-ollama",
    "moduleConfig": {
      "text2vec-ollama": {
        "apiEndpoint": "http://ollama:11434",
        "model": "'${WEAVIATE_OLLAMA_EMBEDDING_MODEL:-nomic-embed-text}'"
      }
    },
    "properties": [
      {
        "name": "title",
        "dataType": ["text"]
      },
      {
        "name": "content", 
        "dataType": ["text"]
      }
    ]
  }'

# Add a document with text embedding
curl -X POST http://localhost:${WEAVIATE_PORT}/v1/objects \
  -H "Content-Type: application/json" \
  -d '{
    "class": "TestDocument",
    "properties": {
      "title": "Introduction to Vector Databases",
      "content": "Vector databases enable semantic search by storing embeddings..."
    }
  }'
```

**For AI-Local Profile (Local Ollama)**:
```bash
# Create collection with local Ollama endpoint
curl -X POST http://localhost:${WEAVIATE_PORT}/v1/schema \
  -H "Content-Type: application/json" \
  -d '{
    "class": "TestDocumentLocal",
    "vectorizer": "text2vec-ollama",
    "moduleConfig": {
      "text2vec-ollama": {
        "apiEndpoint": "http://host.docker.internal:11434",
        "model": "'${WEAVIATE_OLLAMA_EMBEDDING_MODEL:-nomic-embed-text}'"
      }
    },
    "properties": [
      {
        "name": "title",
        "dataType": ["text"]
      },
      {
        "name": "content",
        "dataType": ["text"]
      }
    ]
  }'

# Add a document with text embedding
curl -X POST http://localhost:${WEAVIATE_PORT}/v1/objects \
  -H "Content-Type: application/json" \
  -d '{
    "class": "TestDocumentLocal",
    "properties": {
      "title": "Introduction to Vector Databases (Local)",
      "content": "Vector databases enable semantic search by storing embeddings..."
    }
  }'
```

**5. Test Vector Search**:
```bash
# Search for similar documents (containerized Ollama)
curl -X POST http://localhost:${WEAVIATE_PORT}/v1/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{
      Get {
        TestDocument(
          nearText: {
            concepts: [\"semantic search\"]
          }
          limit: 3
        ) {
          title
          content
          _additional {
            distance
            certainty
          }
        }
      }
    }"
  }' | jq .

# Search for similar documents (localhost SOURCE configuration)
curl -X POST http://localhost:${WEAVIATE_PORT}/v1/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{
      Get {
        TestDocumentLocal(
          nearText: {
            concepts: [\"semantic search\"]
          }
          limit: 3
        ) {
          title
          content
          _additional {
            distance
            certainty
          }
        }
      }
    }"
  }' | jq .
```

**6. Test CLIP Image Embedding**:
```bash
# Create a CLIP collection for multimodal search
curl -X POST http://localhost:${WEAVIATE_PORT}/v1/schema \
  -H "Content-Type: application/json" \
  -d '{
    "class": "MultimodalDoc",
    "vectorizer": "multi2vec-clip",
    "moduleConfig": {
      "multi2vec-clip": {
        "textFields": ["description"],
        "weights": {
          "textFields": [1.0]
        }
      }
    },
    "properties": [
      {
        "name": "description",
        "dataType": ["text"]
      }
    ]
  }'

# Add a document with CLIP vectorization
curl -X POST http://localhost:${WEAVIATE_PORT}/v1/objects \
  -H "Content-Type: application/json" \
  -d '{
    "class": "MultimodalDoc",
    "properties": {
      "description": "A beautiful sunset over the ocean with golden colors"
    }
  }'

# Test CLIP-based search
curl -X POST http://localhost:${WEAVIATE_PORT}/v1/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{
      Get {
        MultimodalDoc(
          nearText: {
            concepts: [\"golden sky\"]
          }
          limit: 3
        ) {
          description
          _additional {
            distance
          }
        }
      }
    }"
  }' | jq .
```

**7. Test Kong Proxy Access**:
```bash
# Access Weaviate through Kong (requires hosts file setup)
curl -s http://vector.localhost:${KONG_HTTP_PORT}/v1/.well-known/ready | jq .
```

**8. Integration Tests**:
```bash
# Test backend connection to Weaviate
curl -s http://localhost:${BACKEND_PORT}/health | jq .

# Check if backend can access Weaviate
docker exec genai-backend sh -c 'curl -s http://weaviate:8080/v1/.well-known/ready'

# Verify n8n can access Weaviate
docker exec genai-n8n sh -c 'curl -s http://weaviate:8080/v1/.well-known/ready'
```

**9. Monitor Resource Usage**:
```bash
# Check Weaviate memory and CPU usage
docker stats genai-weaviate genai-multi2vec-clip --no-stream

# Check logs for any errors
docker logs genai-weaviate 2>&1 | grep -i error
docker logs genai-multi2vec-clip 2>&1 | grep -i error
```

**10. Advanced Testing - Hybrid Search**:
```bash
# Test hybrid search (combining vector and keyword)
curl -X POST http://localhost:${WEAVIATE_PORT}/v1/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{
      Get {
        TestDocument(
          hybrid: {
            query: \"vector database\",
            alpha: 0.75
          }
          limit: 5
        ) {
          title
          content
          _additional {
            score
          }
        }
      }
    }"
  }' | jq .
```

**Expected Results**:
- Health checks should return `200 OK` status
- Embedding model should show `mxbai-embed-large` (or your configured model)
- Collection creation should succeed without errors
- Document insertion should complete successfully
- Vector searches should return relevant results with distance scores
- CLIP service should be running and accessible
- Kong proxy should route requests correctly
- Integration services should connect without issues

**Troubleshooting**:
If any tests fail:
1. Check service logs: `docker logs genai-weaviate`
2. Verify dependencies: `docker compose ps`
3. Check configuration: `docker exec genai-weaviate env | grep -i weaviate`
4. Verify network connectivity: `docker network inspect genai_backend-bridge-network`

## 8. AI Services

### 8.1. Ollama Service

The Ollama service provides a containerized environment for running large language models locally:

- **API Endpoint**: Available at http://localhost:${OLLAMA_PORT}
- **Persistent Storage**: Model files are stored in a Docker volume for persistence between container restarts
- **Multiple Deployment Options**:
  - **Default (Containerized)**: Uses the Ollama container within the stack
  - **Local Ollama**: Connect to an Ollama instance running on your host machine
  - **Production with GPU**: Use NVIDIA GPU acceleration for improved performance

#### 7.1.1. Switching Between Deployment Options

The Ollama service can be deployed in different configurations using separate Docker Compose files:

```bash
# Default: Use the containerized Ollama service (CPU)
docker compose up

# Development with local Ollama (running on your host machine)
# First ensure Ollama is running on your host
./start.sh  # with LLM_PROVIDER_SOURCE=ollama-localhost in .env.example

# Production with NVIDIA GPU support
./start.sh --base-port 64000  # all services containerized
```

#### 7.1.2. Environment-Specific Configuration

The Ollama service is configured for different environments using standalone Docker Compose files:

- **container-cpu SOURCE**: Standard containerized Ollama service (runs on CPU)
- **localhost SOURCE**: Complete stack without an Ollama container, connects directly to a locally running Ollama instance
- **container-gpu SOURCE**: Complete stack with NVIDIA GPU acceleration for the Ollama container

The configuration includes an `ollama-pull` service that automatically downloads required models from the Supabase database. It queries the LLMs table for models where `provider='ollama'` and `active=true`, then pulls each model via the Ollama API. This ensures the necessary models are always available for dependent services.

### 8.2. Local Deep Researcher Service

The Local Deep Researcher service provides an advanced AI-powered research platform built on LangGraph for conducting comprehensive web research tasks:

- **API Endpoint**: Available at http://localhost:${LOCAL_DEEP_RESEARCHER_PORT} (configured via `LOCAL_DEEP_RESEARCHER_PORT`)
- **LangGraph Server**: Runs a LangGraph development server internally on port 2024, exposed via the configured port
- **Database Integration**: Automatically queries the Supabase database to detect and use active LLM models
- **Dynamic Configuration**: Adapts to your preferred LLM setup by reading from the LLMs table
- **Web Research**: Performs multi-source web scraping and research with configurable depth and search backends

#### 7.2.1. Features

- **Intelligent Model Selection**: Automatically detects active Ollama models from the database, with preference for Ollama providers
- **Configurable Research Depth**: Adjustable number of research loops via `LOCAL_DEEP_RESEARCHER_LOOPS` (default: 3)
- **Multiple Search Backends**: Supports DuckDuckGo and other search APIs via `LOCAL_DEEP_RESEARCHER_SEARCH_API`
- **LangGraph Integration**: Built on LangGraph for advanced workflow orchestration and AI agent management
- **Persistent Storage**: Research data and results stored in Docker volumes for persistence between restarts

#### 7.2.2. Configuration

The Local Deep Researcher service is configured through environment variables and database queries:

- **Environment Variables**:
  - `LOCAL_DEEP_RESEARCHER_PORT`: Port to expose the service (default: 63013)
  - `LOCAL_DEEP_RESEARCHER_LOOPS`: Number of research iteration loops (default: 3)
  - `LOCAL_DEEP_RESEARCHER_SEARCH_API`: Search backend to use (default: DuckDuckGo)

- **Database Integration**:
  - Queries `public.llms` table for active content LLMs: `SELECT provider, name FROM public.llms WHERE active = true AND content > 0 ORDER BY content DESC, provider = 'ollama' DESC, name LIMIT 1`
  - Automatically configures runtime settings based on detected models
  - Falls back to llama3.2 if no active models are found

#### 7.2.3. Dependencies and Startup

The Local Deep Researcher service depends on:
- **Supabase Database**: For LLM configuration queries and potential data storage
- **Ollama Service**: For AI model inference (either containerized or local host)
- **Ollama Pull Service**: Ensures required models are available before startup

#### 7.2.4. Different Deployment Configurations

The service adapts to different deployment scenarios:

- **container-cpu SOURCE**: Connects to containerized Ollama service
- **localhost SOURCE**: Connects to local host Ollama instance
- **container-gpu SOURCE**: Connects to GPU-accelerated containerized Ollama

#### 7.2.5. Usage

Once running, the Local Deep Researcher provides:
- **Web Interface**: Accessible via browser for managing research tasks
- **API Endpoints**: RESTful API for programmatic research task submission
- **Research Workflows**: Automated multi-step research processes with web scraping and analysis
- **Result Management**: Persistent storage and retrieval of research findings

### 8.3. SearxNG Privacy Search Service

SearxNG is a privacy-respecting metasearch engine that aggregates results from multiple search engines without tracking users, serving as the primary search backend for the GenAI stack.

#### 7.3.1. Overview

- **API Endpoint**: Available at `http://localhost:${SEARXNG_PORT}` (default: 63014)
- **Kong Gateway**: Accessible via `http://localhost:${KONG_HTTP_PORT}/searxng/`
- **Purpose**: Privacy-focused web search for the GenAI stack
- **Integration**: Serves as a search backend for various services

#### 7.3.2. Features

- **Privacy First**: No user tracking, no profiling, no data retention
- **Multiple Search Engines**: Access to 70+ search engines through unified interface
- **Customizable**: Full control over which engines to use and disable
- **API Access**: JSON API for programmatic searches and automation
- **Fast Performance**: Redis caching for improved response times
- **Rate Limiting**: Built-in protection via Kong Gateway integration

#### 7.3.3. Configuration

The service is configured via `searxng/config/settings.yml` with key settings including:

- **Search Engines**: DuckDuckGo, Wikipedia, GitHub (privacy-focused selection)
- **UI Preferences**: Simple theme with auto color scheme detection
- **API Format Support**: HTML, JSON, CSV, and RSS output formats
- **Rate Limiting**: 60 searches per minute, 1000 per hour via Kong
- **Security**: Redis-backed caching with password authentication

#### 7.3.4. Integration Points

**Local Deep Researcher Integration:**
- Primary search backend for AI-powered research workflows
- Configurable via `LOCAL_DEEP_RESEARCHER_SEARCH_API=searxng`
- Provides privacy-respecting alternative to direct API access

**Backend API Integration:**
- Access privacy-focused search via `/search/privacy?q=your+query`
- JSON API endpoints for programmatic access
- Session tracking and result caching capabilities

**n8n Workflow Integration:**
- SearxNG webhook nodes for automated privacy-respecting searches
- Batch processing capabilities for research automation
- Integration with workflow scheduling and triggers

**Open-WebUI Integration:**
- Research tools can leverage SearxNG for web searches
- Privacy-focused search capabilities in chat interface
- Automatic result formatting and display

#### 7.3.5. API Usage Examples

**Basic Search:**
```bash
curl "http://localhost:${SEARXNG_PORT}/search?q=artificial+intelligence&format=json"
```

**Search with Specific Engines:**
```bash
curl "http://localhost:${SEARXNG_PORT}/search?q=python&engines=duckduckgo,wikipedia&format=json"
```

**Via Kong Gateway:**
```bash
curl "http://localhost:${KONG_HTTP_PORT}/searxng/search?q=machine+learning&format=json"
```

**Health Check:**
```bash
curl "http://localhost:${SEARXNG_PORT}/healthz"
```

#### 7.3.6. Troubleshooting

**Service Not Starting:**
- Check logs: `docker logs genai-searxng`
- Verify Redis is healthy and accessible
- Ensure port 63014 is not in use by other services
- Check SearxNG secret key generation in start.sh

**Search Not Working:**
- Verify enabled engines in `settings.yml` configuration
- Check network connectivity to external search providers
- Review rate limiting settings and current usage
- Test individual search engines for availability

**Integration Issues:**
- Ensure SearxNG is accessible from other containers
- Verify Kong Gateway routing configuration is correct
- Check service dependencies are running and healthy
- Review environment variable configuration

### 8.4. Open Web UI

Open-WebUI is integrated with the Deep Researcher service to provide AI-powered web research capabilities directly within the chat interface. This integration uses Open-WebUI's Tools system to enable seamless research functionality.

**Architecture**:
```
User → Open-WebUI → Research Tool → Deep Researcher (LangGraph) → Web Search
                                           ↓
                                        Ollama LLM
```

- **Accessible**: Available at http://localhost:${OPEN_WEB_UI_PORT} (configured via `OPEN_WEB_UI_PORT`)
- **Model Integration**: Connects to Ollama API endpoint for standard AI chat functionality
- **Database Integration**: Uses the Supabase PostgreSQL database (`DATABASE_URL`) for storing conversations and settings
- **Storage Interaction**: Interacts with the Supabase Storage API (via the Kong API Gateway) for file operations
- **Deep Researcher Integration**: Direct LangGraph API integration for AI research capabilities:
    - **Tools**: AI-invoked research capabilities that models can use automatically
    - **Direct Connection**: Tools connect directly to Deep Researcher service via LangGraph API
    - **Database-driven**: Research uses active models from the `llms` table (qwen3:latest by default)
    - **Two Tool Types**: Basic research tool and enhanced research tool with progress tracking
- **Volume Mounts**: 
    - `open-web-ui-data:/app/backend/data` - Persistent data storage
    - `../open-webui/tools:/app/backend/data/tools` - Research tools directory
- **Generic Image**: Uses standard `dyrnq/open-webui:latest` for reliability and simplicity
- **Dependencies**: Depends on Ollama, Supabase DB, Ollama Pull, Local Deep Researcher, and Supabase Storage services
- **Configuration**:
    - `OLLAMA_BASE_URL`: URL for Ollama API
    - `DATABASE_URL`: PostgreSQL connection string for Supabase
    - `WEBUI_SECRET_KEY`: Secret key for Open Web UI

#### 7.3.1. Enabling Deep Researcher in Open-WebUI

**Prerequisites**:
1. Ensure all services are running:
   ```bash
   docker-compose up -d
   ```

2. Verify Deep Researcher is healthy:
   ```bash
   curl http://localhost:${LOCAL_DEEP_RESEARCHER_PORT}/docs
   ```

3. Ensure Ollama has the required model:
   ```bash
   docker-compose exec ollama ollama pull qwen3:latest
   # Or use an alternative model and update the database
   ```

**Step-by-Step Setup**:

1. **Access Open-WebUI Admin Interface**
   - Navigate to Open-WebUI: `http://localhost:${OPEN_WEB_UI_PORT}`
   - Log in with admin credentials
   - Go to **Admin Panel** → **Tools**

2. **Import Research Tools**
   
   The research tools are automatically mounted from the host filesystem. You have two tools available:

   - **Research Assistant** (`research_tool.py`)
     - Basic research functionality
     - Synchronous results display
     - Best for quick research queries

   - **Research Assistant (Enhanced)** (`research_streaming_tool.py`)
     - Progressive status updates
     - Real-time research progress
     - Best for detailed research tasks

   **Import Method (Copy/Paste)**:
   Since Open-WebUI's file browser shows the container filesystem, use the copy/paste method:

   a. On your host machine, copy the content of the tool file:
   ```bash
   # For basic research tool
   cat open-webui/tools/research_tool.py
   
   # For enhanced research tool  
   cat open-webui/tools/research_streaming_tool.py
   ```

   b. In Open-WebUI admin interface:
   - Go to **Tools** → **Create New Tool**
   - Paste the entire file content
   - Click **"Create Tool"**

3. **Configure Tool Settings**
   
   After importing, configure the tool by clicking on its settings (gear icon):

   **Default Configuration** (Usually no changes needed):
   - `researcher_url`: `http://local-deep-researcher:2024` (auto-configured)
   - `timeout`: 300 seconds
   - `enable_tool`: true

   **Note**: The tools are pre-configured to use the correct Deep Researcher URL. You typically don't need to modify these settings.

4. **Enable Tools for Models**
   - Go to **Admin Panel** → **Models**
   - Select the model you want to use (e.g., your Ollama model)
   - In the **Tools** section, enable:
     - ✅ Research Assistant
     - ✅ Research Assistant (Enhanced) (optional)
   - Save the model configuration

5. **Test the Integration**
   - Start a new chat with the model that has research tools enabled
   - Try these example queries:
     - "Research the latest developments in AI"
     - "What are the current trends in renewable energy?"
     - "Find information about quantum computing applications"

   The tool will automatically activate when it detects research-related queries.

**Do You Need to Restart Open-WebUI?**
- **No**, you don't need to restart when importing tools through the admin interface
- **Yes**, you need to restart when modifying tool Python files directly on disk

#### 7.3.2. How Research Tools Work

1. **Query Detection**: When you ask a research question, Open-WebUI detects it needs to use the research tool
2. **Thread Creation**: The tool creates a new thread in the Deep Researcher LangGraph API
3. **Research Execution**: Deep Researcher performs web searches and analysis using the configured LLM with the correct `research_topic` input format
4. **Result Formatting**: Results are formatted and displayed in the chat interface

**Recent Fixes**:
- **Input Format**: Fixed tools to use `research_topic` input field (required by Deep Researcher) instead of `query`
- **State Management**: Removed conflicting configuration parameters that caused thread state issues
- **Thread Isolation**: Each research session now properly creates isolated threads

#### 7.3.3. Open-WebUI Directory Structure

The `open-webui/` folder contains custom research integrations:

- `tools/` - Research tools for manual import into Open-WebUI
  - `research_tool.py` - Basic research tool with polling and fallback support
  - `research_streaming_tool.py` - Enhanced research tool with progress tracking

#### 7.3.4. Troubleshooting Open-WebUI Research Integration

**Tools Not Showing Up**:

1. Check if tools are mounted:
   ```bash
   docker-compose exec open-web-ui ls -la /app/backend/data/tools/
   ```

2. Verify Deep Researcher connectivity:
   ```bash
   docker-compose exec open-web-ui curl http://local-deep-researcher:2024/docs
   ```

**Research Failing**:

1. Check Deep Researcher logs:
   ```bash
   docker-compose logs local-deep-researcher --tail=50
   ```

2. Verify Ollama model is available:
   ```bash
   docker-compose exec ollama ollama list
   ```

3. Check if the model name in the database matches:
   ```sql
   -- Connect to database and check active LLM
   SELECT name, provider FROM llms WHERE active = true AND content > 0 ORDER BY content DESC;
   ```

**Model Not Found Error**:

If you see "model not found" errors:

1. Pull the required model:
   ```bash
   docker-compose exec ollama ollama pull qwen3:latest
   ```

2. Or update the database to use an available model:
   ```sql
   UPDATE llms SET active = true WHERE name = 'your-available-model' AND provider = 'ollama';
   UPDATE llms SET active = false WHERE name != 'your-available-model';
   ```

#### 7.3.5. Advanced Configuration

**Using Different LLMs**:

The Deep Researcher service dynamically selects the LLM from the database. To change it:

1. Connect to Supabase database
2. Update the `llms` table to activate your preferred model
3. Ensure the model is available in Ollama

**Custom Search Engines**:

Currently supports:
- DuckDuckGo (default)
- Additional engines can be configured in the Deep Researcher service

**Performance Tuning**:

- Adjust `max_loops` in the tool code for search depth
- Modify `timeout` in tool settings for longer research
- Configure `poll_interval` for status update frequency

#### 7.3.6. Security Considerations

- Research tools only have access to public web content
- All requests are routed through the backend service
- No direct internet access from Open-WebUI container
- Results are sanitized before display

#### 7.3.7. Development Guidelines

To modify the research tools:

1. Edit files in `open-webui/tools/`
2. Restart Open-WebUI: `docker-compose restart open-web-ui`
3. Re-import the tool in the admin interface
4. Test thoroughly before deployment

For more details on tool development, see the Open-WebUI official documentation.

### 8.5. Backend API Service

The Backend service provides a FastAPI-based REST API that connects to Supabase PostgreSQL, Neo4j Graph Database, and Ollama for AI model inference. It interacts with Supabase Storage via the Kong API Gateway. Its own API is also exposed through the Kong gateway.

- **API Endpoint (via Kong):** Available at `http://localhost:${KONG_HTTP_PORT}/backend` (or HTTPS equivalent). Kong routes requests starting with `/backend` to this service.
- **Direct API Endpoint (Internal/Testing):** Available at `http://localhost:${BACKEND_PORT}` (configured via `BACKEND_PORT`).
- **API Documentation (via Kong):**
  - Swagger UI: `http://localhost:${KONG_HTTP_PORT}/backend/docs`
  - ReDoc: `http://localhost:${KONG_HTTP_PORT}/backend/redoc`
- **Features**:
  - Connection to Supabase PostgreSQL with pgvector support
  - Authentication via Supabase Auth service
  - Neo4j Graph Database integration for storing and querying connected data
  - DSPy framework for advanced prompt engineering and LLM optimization
  - Integration with Ollama for local AI model inference
  - Support for multiple LLM providers (OpenAI, Groq, etc.)
  - Comprehensive research API integration with Local Deep Researcher
  - Async task management for long-running research operations
  - Session tracking and result persistence
  - Dependency management with uv instead of pip/virtualenv

- **Research API Endpoints**:
  - `POST /research/start` - Start new research session
  - `GET /research/{session_id}/status` - Check research progress
  - `GET /research/{session_id}/result` - Get completed results
  - `POST /research/{session_id}/cancel` - Cancel running research
  - `GET /research/{session_id}/logs` - Get detailed process logs
  - `GET /research/sessions` - List user research history
  - `GET /research/health` - Service health check

#### 7.3.1. Configuration

The backend service is configured via environment variables:

- `KONG_URL`: Base URL for the Kong API Gateway (e.g., `http://kong-api-gateway:8000`). Used for interacting with Supabase services like Storage via the gateway.
- `DATABASE_URL`: PostgreSQL connection string for Supabase (direct connection).
- `OLLAMA_BASE_URL`: URL for Ollama API (direct connection or via host).
- `NEO4J_URI`: Connection URI for Neo4j Graph Database (bolt://neo4j-graph-db:7687) (direct connection).
- `NEO4J_USER`: Username for Neo4j authentication (set via `GRAPH_DB_USER` in .env).
- `NEO4J_PASSWORD`: Password for Neo4j authentication (set via `GRAPH_DB_PASSWORD` in .env).
- `BACKEND_PORT`: Port to expose the API (configured via `BACKEND_PORT`).

#### 7.3.2. Dependencies and Interactions

The backend service interacts with several other services:

**Direct Connections:**
- **Supabase DB:** Connects directly using a PostgreSQL driver and the `DATABASE_URL` for standard database operations.
- **Neo4j Graph DB (neo4j-graph-db):** Connects directly using the Bolt protocol and `NEO4J_URI` for graph operations.
- **Ollama:** Connects directly via HTTP using `OLLAMA_BASE_URL` for AI model inference.

**Connections via Kong API Gateway:**
- **Supabase Storage:** Interacts with the Storage API via Kong using the `KONG_URL` (e.g., `http://kong-api-gateway:8000/storage/v1`) and the `storage3` client library.
- **Supabase Auth & API (PostgREST):** If the backend needs to make HTTP calls to Supabase Auth or the PostgREST API, it **should** use the `KONG_URL` (e.g., `http://kong-api-gateway:8000/auth/v1` or `http://kong-api-gateway:8000/rest/v1`) to route these requests through the gateway. (Note: Current implementation in `main.py` does not show these calls, but explicit environment variables should be added if needed).

**Architectural Rationale:**
- Direct connections are used for non-HTTP protocols (PostgreSQL, Bolt) or for services not typically managed under the central API gateway policies (like Ollama in this setup). The Neo4j service is configured to advertise its service name (`neo4j-graph-db`) for reliable inter-container communication.
- HTTP API interactions with core Supabase services (Auth, API, Storage) are routed through the Kong gateway (`kong-api-gateway`) to leverage centralized routing, potential policy enforcement (authentication, rate limiting - though auth plugins are currently commented out), and a unified access point.

#### 7.3.3. Local Development

For local development outside of Docker:

```bash
# Navigate to app directory
cd backend/app

# Install dependencies using uv
uv pip install -r requirements.txt

# Run the server in development mode
uvicorn main:app --reload
```

### 8.6. ComfyUI Service

ComfyUI is a powerful node-based workflow interface for Stable Diffusion and AI image generation, integrated into the GenAI stack for seamless image generation capabilities.

#### 7.6.1. Features

- **Visual Workflow Editor**: Node-based interface for creating complex image generation workflows
- **Multi-Architecture Support**: CPU-only for development/testing, CUDA acceleration for production
- **Multiple AI Models**: Support for SDXL, SD 1.5, ControlNet, LoRA, and custom models
- **API Integration**: RESTful API for programmatic access and automation
- **WebSocket Support**: Real-time progress updates and workflow monitoring
- **Supabase Integration**: Automatic upload of generated images to Supabase Storage
- **Kong Gateway Routing**: Secure API access through the Kong API Gateway

#### 7.6.2. Configuration

ComfyUI is configured through environment variables in `.env`:

```bash
# ComfyUI Configuration
COMFYUI_PORT=63018
COMFYUI_BASE_URL=http://comfyui:18188  # Updated to bypass authentication
COMFYUI_ARGS=--listen
COMFYUI_AUTO_UPDATE=false
COMFYUI_PLATFORM=linux/amd64
COMFYUI_IMAGE_TAG=v2-cpu-22.04-v0.2.7  # latest-cuda for GPU

# Storage Integration
COMFYUI_UPLOAD_TO_SUPABASE=true
COMFYUI_STORAGE_BUCKET=comfyui-images
```

#### 7.6.2.1. ComfyUI Authentication

The ComfyUI service uses the `ai-dock` Docker image which includes authentication by default.

**Default Credentials:**
When accessing ComfyUI through:
- Direct URL: `http://localhost:55684/`
- Kong Gateway: `http://localhost:55668/comfyui/`

You will be redirected to a login page. Use these credentials:
- **Username**: `user`
- **Password**: `password`

**Disabling Authentication (Optional):**
If you want to disable authentication, you can add these environment variables to the ComfyUI service:

```yaml
environment:
  - WEB_ENABLE_AUTH=false
  - ENABLE_QUICKTUNNEL=false
```

**Alternative Solutions:**
1. Use a different ComfyUI image without authentication
2. Configure a reverse proxy to bypass the authentication layer
3. Use the ComfyUI API directly (bypassing the web UI)

> **🔧 Authentication Fix**: ComfyUI is configured to bypass the ai-dock authentication layer by connecting directly to port 18188 (internal ComfyUI port) instead of port 8188 (Caddy reverse proxy). This eliminates the need for login credentials and provides direct access to the ComfyUI interface.

#### 7.6.3. Deployment Profiles

ComfyUI supports multiple deployment configurations:

**Default Profile (CPU):**
- Uses `ghcr.io/ai-dock/comfyui:v2-cpu-22.04-v0.2.7`
- CPU-only processing (slower but universal compatibility)
- Suitable for development and testing

**AI-GPU Profile (CUDA):**
- Uses `ghcr.io/ai-dock/comfyui:latest-cuda`
- NVIDIA GPU acceleration with CUDA support
- High-performance image generation for production

**AI-Local Profile:**
- Uses local ComfyUI installation on host machine
- CPU-only processing with local Ollama integration
- Connects to host-based Ollama and ComfyUI instances
- Optimized for macOS Apple Silicon (M1/M2/M3/M4) with Metal Performance Shaders

#### 7.6.4. Local ComfyUI Installation (Localhost SOURCE Configuration)

For localhost SOURCE configuration, you'll need to install ComfyUI locally on your host machine. This is particularly beneficial for macOS users with Apple Silicon processors.

**Prerequisites:**
- macOS 12.3 or later (for Apple Silicon optimization)
- Python 3.10+ installed
- Xcode Command Line Tools: `xcode-select --install`

**Installation Steps:**

1. **Clone ComfyUI Repository:**
   ```bash
   git clone https://github.com/comfyanonymous/ComfyUI.git
   cd ComfyUI
   ```

2. **Create Virtual Environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On macOS/Linux
   ```

3. **Install PyTorch for Apple Silicon:**
   ```bash
   # For Apple Silicon (M1/M2/M3/M4) - enables Metal Performance Shaders
   pip3 install --pre torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/nightly/cpu
   ```

4. **Install ComfyUI Dependencies:**
   ```bash
   pip3 install -r requirements.txt
   ```

5. **Start ComfyUI:**
   ```bash
   python3 main.py --listen
   ```

6. **Verify Installation:**
   - ComfyUI should be accessible at `http://localhost:8188`
   - The stack will automatically connect to your local ComfyUI instance

**Model Installation:**
- When you start the GenAI stack with localhost SOURCE configuration, the `comfyui-init` service will automatically download essential models
- Models are stored in the `comfyui-models` Docker volume and shared with your local ComfyUI installation
- You can access models at: `./models/` directory in your ComfyUI installation

**Performance Benefits:**
- **Apple Silicon**: Utilizes Metal Performance Shaders for hardware-accelerated inference
- **Memory Efficiency**: Better memory management on macOS
- **Native Integration**: Seamless integration with macOS system resources

**Using the AI-Local Profile:**
```bash
# Start the stack with local ComfyUI
./start.sh  # with LLM_PROVIDER_SOURCE=ollama-localhost in .env.example

# Or manually with unified configuration
docker compose --env-file=.env up
```

#### 7.6.5. Service Dependencies

ComfyUI depends on several services for full functionality:

- **Database**: `supabase-db-init` (database initialization)
- **AI Models**: `ollama-pull` (model availability)
- **Storage**: `supabase-storage` (image storage)
- **Cache**: `redis` (queue management)

#### 7.6.6. Integration Points

**OpenWebUI Integration:**
- Direct image generation from chat interface
- Seamless workflow integration with conversations
- Generated images automatically stored in Supabase

**Backend API Integration:**
- RESTful endpoints for image generation
- Status monitoring and result retrieval
- Automated image processing pipelines

**n8n Workflow Automation:**
- Automated image generation workflows
- Webhook-based progress notifications
- Batch processing capabilities

#### 7.6.7. API Endpoints

ComfyUI provides several API endpoints accessible through Kong Gateway:

```bash
# Health check
curl http://localhost:${KONG_HTTP_PORT}/comfyui/system_stats

# Submit workflow
curl -X POST http://localhost:${KONG_HTTP_PORT}/comfyui/prompt \
  -H "Content-Type: application/json" \
  -d @workflow.json

# Check generation status
curl http://localhost:${KONG_HTTP_PORT}/comfyui/history/{prompt_id}

# Retrieve generated image
curl http://localhost:${KONG_HTTP_PORT}/comfyui/view?filename={filename}
```

#### 7.6.8. Model Management

ComfyUI uses persistent volumes for model storage:

```
/opt/ComfyUI/models/
├── checkpoints/     # Main AI models (SDXL, SD 1.5, etc.)
├── vae/            # Variational Autoencoders
├── loras/          # LoRA fine-tuned models
├── controlnet/     # ControlNet models
├── upscale_models/ # Upscaling models
└── clip/           # CLIP models
```

#### 7.6.9. Performance Considerations

**CPU Mode (Default/Development):**
- Slower image generation (2-5 minutes per image)
- Lower memory requirements
- Universal compatibility (macOS M-chip, Linux, Windows)

**GPU Mode (Production):**
- Fast image generation (10-30 seconds per image)
- Requires NVIDIA GPU with 8GB+ VRAM
- CUDA 12.5+ support recommended

#### 7.6.10. Integration Examples

**Generate via Backend API:**
```bash
curl -X POST http://localhost:${BACKEND_PORT}/comfyui/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "a beautiful landscape",
    "negative_prompt": "blurry, low quality",
    "width": 512,
    "height": 512,
    "steps": 20
  }'
```

**OpenWebUI Usage:**
1. ComfyUI automatically configured as image generation backend
2. Use image generation features in chat conversations
3. Generated images stored in Supabase Storage with URLs returned

**n8n Workflow Integration:**
1. HTTP Request node to submit workflows to ComfyUI
2. WebSocket or polling for progress monitoring
3. Automated image processing and storage

#### 7.6.11. Troubleshooting

**Service Not Starting:**
- Check GPU drivers and CUDA installation (GPU mode)
- Verify sufficient disk space for models
- Check Docker container logs: `docker logs genai-comfyui`

**Slow Generation:**
- Ensure GPU mode is enabled for production
- Check model loading and VRAM usage
- Verify CUDA acceleration is working

**Integration Issues:**
- Verify service dependencies are healthy
- Check Kong Gateway routing configuration
- Ensure environment variables are correctly set

### 8.7. n8n Workflow Automation Service

n8n is a powerful workflow automation platform that provides advanced orchestration capabilities for the GenAI stack, enabling automated data processing, API integration, and workflow scheduling.

#### 8.7.1. Overview

- **Direct Access**: `http://localhost:${N8N_PORT}` (default: 63017)
- **Kong Gateway**: `http://n8n.localhost:${KONG_HTTP_PORT}/` (requires hosts file setup)
- **Database Integration**: Uses PostgreSQL for workflow storage and execution history
- **Queue System**: Redis-backed queue processing for reliable workflow execution
- **Community Packages**: Pre-installed nodes for ComfyUI, MCP, and other integrations

#### 8.7.2. Workflow Templates

This directory contains ready-to-use n8n workflow templates for the GenAI Vanilla Stack.

**Available Workflows:**

**1. SearxNG Research Workflow (`searxng-research-workflow.json`)**
- **Purpose**: Automated research using SearxNG with AI summarization
- **Webhook**: `/webhook/research`
- **Features**:
  - Searches SearxNG for relevant information
  - Uses AI to summarize and analyze results
  - Returns structured research summaries

#### 8.7.3. Manual Import Instructions

Since modern n8n requires user management, workflows must be imported manually:

**Step 1: Complete n8n Setup**
1. Access n8n at `http://n8n.localhost:55668` or `http://localhost:55683`
2. Complete the initial user setup (email + password)
3. Login to n8n

**Step 2: Set Up Database Credentials**
1. Go to **Credentials** → **Add Credential**
2. Select **PostgreSQL**
3. Configure:
   - **Name**: `Supabase Database`
   - **Host**: `supabase-db`
   - **Port**: `5432`
   - **Database**: `postgres`
   - **User**: `supabase_admin`
   - **Password**: `password` (or your configured password)
   - **SSL**: Disabled

**Step 3: Import Workflows**
1. Go to **Workflows** → **Import from File**
2. Upload `searxng-research-workflow.json`
3. For each workflow:
   - Open the workflow
   - Click on the PostgreSQL node
   - Select the credential you created in Step 2
   - Save the workflow
   - **Activate** the workflow (toggle switch)

**Step 4: Test Webhooks**
- **Research**: `POST http://localhost:55683/webhook/research`

#### 8.7.4. Integration with Open-WebUI

The research workflow is designed to work with the Open-WebUI n8n integration tool:
- `trigger_research()` → calls `/webhook/research`

#### 8.7.5. Community Nodes

The following community nodes are automatically installed:
- `n8n-nodes-comfyui` - ComfyUI integration
- `@ksc1234/n8n-nodes-comfyui-image-to-image` - Image transformations
- `n8n-nodes-mcp` - Model Context Protocol support

## 9. Database Setup Process

The database initialization follows a two-stage process managed by Docker Compose dependencies:

1.  **Base Database Initialization (`supabase-db` service):**
    *   Uses the standard `supabase/postgres` image.
    *   On first start with an empty data volume, this image runs its own internal initialization scripts located within its `/docker-entrypoint-initdb.d/`.
    *   These base scripts handle setting up PostgreSQL, creating the database specified by `POSTGRES_DB`, creating standard Supabase roles (`anon`, `authenticated`, `service_role`), enabling necessary extensions (like `pgcrypto`, `uuid-ossp`), and setting up the basic `auth` and `storage` schemas.
    *   **IMPORTANT**: The `SUPABASE_DB_USER` in your `.env` file must be set to `supabase_admin`. This is required by the base image's internal scripts.

2.  **Custom Post-Initialization (`supabase-db-init` service):**
    *   A dedicated, short-lived service (`supabase-db-init`) using a `postgres:alpine` image (which includes `psql` and `pg_isready`).
    *   This service `depends_on: supabase-db`.
    *   Its entrypoint (`supabase/db/scripts/db-init-runner.sh`) first waits until `supabase-db` is ready to accept connections using `pg_isready`.
    *   Once the database is ready, the runner script executes all `.sql` files found in the `./supabase/db/scripts/` directory (mounted to `/scripts` inside the container) in alphabetical/numerical order.
    *   These custom scripts handle project-specific setup *after* the base Supabase initialization is complete. This includes:
        *   Ensuring required extensions like `vector` and `postgis` are enabled (`01-extensions.sql`).
        *   Ensuring schemas like `auth` and `storage` exist (`02-schemas.sql`).
        *   Creating necessary custom types for Supabase Auth (`03-auth-types.sql`).
        *   Creating custom public tables like `users` and `llms` (`04-public-tables.sql`).
        *   Granting appropriate permissions to standard roles (`05-permissions.sql`).
        *   Creating custom functions like `public.health` (`06-functions.sql`).
        *   Inserting seed data like default LLMs (`07-seed-data.sql`).
    *   All custom SQL scripts use `IF NOT EXISTS` or equivalent idempotent logic to allow safe re-runs if needed (though `db-init` only runs once per `docker compose up`).

3.  **Service Dependencies:**
    *   Most other services (`supabase-meta`, `supabase-auth`, `supabase-api`, `supabase-studio`, `ollama-pull`, `open-web-ui`, `backend`) now have `depends_on: { supabase-db-init: { condition: service_completed_successfully } }`.
    *   This ensures they only start *after* both the base database initialization and all custom post-initialization steps are fully completed.

This approach separates base database setup from custom application setup, improving reliability and maintainability.

## 10. Neo4j Graph Database (neo4j-graph-db) Backup and Restore

### 10.1. Manual Backup

To manually create a graph database backup:

     ```bash
     # Create a backup (will temporarily stop and restart Neo4j)
     docker exec -it ${PROJECT_NAME}-neo4j-graph-db /usr/local/bin/backup.sh
     ```

The backup will be stored in the `/snapshot` directory inside the container, which is mounted to the `./neo4j-graph-db/snapshot/` directory on your host machine.

### 10.2. Manual Restore

To restore from a previous backup:

     ```bash
     # Restore from the latest backup
     docker exec -it ${PROJECT_NAME}-neo4j-graph-db /usr/local/bin/restore.sh
     ```

### 10.3. Important Notes:
- By default, data persists in the Docker volume between restarts
- Automatic restoration at startup is enabled by default for Neo4j. When the container starts, it will automatically restore from the latest backup if one is available
- To disable automatic restore for Neo4j, remove or rename the auto_restore.sh script in the Dockerfile

## 11. Project Structure (Note: Network and Volume names)

The project uses Docker named volumes for data persistence and a custom bridge network for inter-service communication.
- **Network Name:** `backend-bridge-network` (defined in `docker-compose` files)
- **Volume Names:** `supabase-db-data`, `redis-data`, `graph-db-data`, `ollama-data`, `open-web-ui-data`, `backend-data`, `supabase-storage-data` (defined in `docker-compose` files). Note: Volume names do not currently support environment variable substitution in the top-level `volumes:` definition.

```
genai-vanilla-stack/
├── .env                  # Environment configuration
├── .env.example          # Template environment configuration
├── start.sh                  # Thin wrapper calling Python implementation
├── stop.sh                   # Thin wrapper calling Python implementation
├── docker-compose.yml        # Main compose file (base networks and volumes)
├── docker-compose.ai-local.yml  # Local Ollama flavor (backward compatibility)
├── docker-compose.ai-gpu.yml    # GPU-optimized flavor (backward compatibility)
├── bootstrapper/             # Python implementation and configuration
│   ├── start.py              # Main startup script
│   ├── stop.py               # Main stop script
│   ├── service-configs.yml   # SERVICE SOURCE matrix configuration
│   ├── core/                 # Core utilities
│   │   ├── config_parser.py
│   │   ├── docker_manager.py
│   │   └── port_manager.py
│   ├── services/             # Service management
│   │   ├── source_validator.py
│   │   ├── service_config.py
│   │   └── dependency_manager.py
│   └── utils/                # Utility modules
│       ├── banner.py
│       ├── hosts_manager.py
│       ├── key_generator.py
│       └── supabase_keys.py
├── backend/              # FastAPI backend service
│   ├── Dockerfile
│   └── app/
│       ├── main.py
│       ├── requirements.txt
│       └── data/         # Data storage (mounted as volume)
├── graph-db/             # Neo4j Graph Database configuration
│   ├── Dockerfile
│   ├── scripts/
│   │   ├── backup.sh
│   │   ├── restore.sh
│   │   ├── auto_restore.sh
│   │   └── docker-entrypoint-wrapper.sh
│   └── snapshot/
├── supabase/             # Supabase configuration
│   ├── db/
│   │   ├── scripts/      # Contains db-init-runner.sh and post-init SQL scripts (01-*.sql, etc.)
│   │   └── snapshot/     # Database backup storage (manual dumps)
│   ├── auth/             # Supabase Auth service (GoTrue) - Uses standard image
│   ├── api/              # Supabase API service (PostgREST)
│   └── storage/          # Supabase Storage (if added)
├── bootstrapper/              # Cross-platform Python bootstrapping
│   ├── start.py              # Main startup orchestrator
│   ├── stop.py               # Shutdown orchestrator
│   ├── generate_supabase_keys.sh  # JWT key generator wrapper
│   ├── generate_supabase_keys.py  # JWT key generator implementation
│   ├── services/             # Service configuration
│   │   └── service_config.py # SOURCE-based service management
│   └── utils/                # Utility modules
│       └── kong_config_generator.py # Dynamic Kong configuration
├── volumes/              # Docker volumes and configurations
│   └── api/              # API configurations (dynamically generated)
└── docs/                 # Documentation and diagrams
    ├── diagrams/
    │   ├── README.md
    │   ├── architecture.mermaid
    │   └── generate_diagram.sh
    └── images/
       └── architecture.png
```


Note: Many services will be pre-packaged and pulled directly in docker-compose.yml without needing separate Dockerfiles.

## 12. Python Migration Benefits

The GenAI Vanilla Stack has been migrated from Bash scripts to Python for improved reliability, maintainability, and cross-platform compatibility.

### 12.1. Cross-Platform Compatibility
The stack now uses Python for all configuration and management tasks:
- **Windows Support**: Full compatibility without WSL requirements
- **macOS Support**: Native execution on Intel and Apple Silicon
- **Linux Support**: Consistent behavior across all distributions  
- **No External Dependencies**: Python's built-in libraries handle YAML parsing (no more yq dependency)
- **Better Error Handling**: Clear error messages and comprehensive validation

### 12.2. Enhanced Features
- **Integrated Key Generation**: Automatic generation of all required encryption keys (Supabase JWT, N8N, SearxNG)
- **Service Dependency Management**: Automatic detection and resolution of service dependency conflicts
- **Port Management**: Robust port assignment with conflict detection and dynamic updates
- **Configuration Validation**: Comprehensive validation of SOURCE configurations against service matrix
- **Rich Console Output**: Enhanced progress indicators and colored status messages

### 12.3. Improved Reliability
- **Atomic Operations**: Configuration changes are applied atomically to prevent inconsistent state
- **Backup Creation**: Automatic backup of .env files before modifications
- **Graceful Error Recovery**: Better handling of edge cases and error conditions
- **State Validation**: Comprehensive validation of system state before operations

## 13. Cross-Platform Compatibility

This project is designed to work across different operating systems:

### 13.1. Line Ending Handling

- A `.gitattributes` file is included to enforce consistent line endings across platforms
- All shell scripts use LF line endings (Unix-style) even when checked out on Windows
- Docker files and YAML configurations maintain consistent line endings

### 12.2. Host Script Compatibility

The following scripts that run on the host machine (not in containers) have been made cross-platform compatible:

- `start.sh` - For starting the stack with configurable ports and SOURCE-based service configuration
- `stop.sh` - For stopping the stack and clean up resources
- `bootstrapper/generate_supabase_keys.sh` - For generating JWT keys (automatically invoked by start.sh)
- `docs/diagrams/generate_diagram.sh` - For generating architecture diagrams

These scripts use:
- The more portable `#!/usr/bin/env bash` shebang
- Cross-platform path handling
- Platform detection for macOS vs Linux differences

### 12.3. Container Scripts

Scripts that run inside Docker containers (in the `neo4j-graph-db/scripts/` and `supabase/db/scripts/` directories) use standard Linux shell scripting as they always execute in a Linux environment regardless of the host operating system.

### 12.4. Windows Compatibility Notes

When running on Windows:

- Use Git Bash or WSL (Windows Subsystem for Linux) for running host scripts
- Docker Desktop for Windows handles path translations automatically
- Host scripts will detect Windows environments and provide appropriate guidance

## 13. Architecture Diagram

The `docs/diagrams/` directory contains the Mermaid diagram source for the project architecture.

### 13.1. Generating the Architecture Diagram

The architecture diagram is defined in `architecture.mermaid` and can be generated as a PNG image using the provided script:

1. Make sure you have Node.js and npm installed
2. Run the generation script:
   ```bash
   cd docs/diagrams
   ./generate_diagram.sh
   ```
3. This will:
   - Install the Mermaid CLI tool if needed
   - Convert the Mermaid diagram to PNG
   - Save it as `docs/images/architecture.png`

The generated image will be automatically referenced in the main README.md file.

### 13.2. Modifying the Architecture Diagram

To modify the architecture diagram:

1. Edit the `architecture.mermaid` file
2. Run the generation script to update the PNG image
3. The changes will be reflected in the README.md

### 13.3. Mermaid Diagram Source

The diagram uses Mermaid syntax to define a clean, professional representation of the project architecture with:
- Logical grouping of services by category (Database, AI, API)
- Clear data flow visualization
- Consistent styling

You can also embed the Mermaid code directly in Markdown files for platforms that support Mermaid rendering (like GitHub).

**IMPORTANT**: Always update the architecture diagram when modifying the Docker Compose services!

## 14. License

[Apache License 2.0](LICENSE)

## 15. Redis Service

The Redis service provides a high-performance in-memory data store that is used for caching, pub/sub messaging, and geospatial operations.

### 15.1. Overview

- **Image**: Uses the official `redis:7.2-alpine` image for a lightweight footprint
- **Persistence**: Configured with AOF (Append-Only File) persistence for data durability
- **Security**: Protected with password authentication
- **Port**: Available at `localhost:${REDIS_PORT}` (configured via `REDIS_PORT`)
- **Dependencies**: Starts after the successful completion of the `supabase-db-init` service

### 15.2. Integration with Other Services

- **Kong API Gateway**: Uses Redis for rate limiting and other Redis-backed plugins
- **Backend Service**: Uses Redis for caching, pub/sub messaging, and geospatial operations

### 15.3. Configuration

The Redis service can be configured through the following environment variables:

- `REDIS_PORT`: The port on which Redis is accessible (default: 63001)
- `REDIS_PASSWORD`: The password used to authenticate with Redis
- `REDIS_URL`: The connection URL used by services to connect to Redis

### 15.4. Usage in Backend

The backend service is configured to use Redis for:

- **Caching**: Improving performance by caching frequently accessed data
- **Pub/Sub**: Enabling real-time messaging between components
- **Geohashing**: Supporting geospatial operations and queries

## 16. n8n Workflow Automation Service

The n8n service provides a powerful workflow automation platform that can be used to create, schedule, and monitor automated workflows.

### 16.1. Overview

- **Image**: Uses the official `n8nio/n8n:latest` image
- **Database**: Uses the Supabase PostgreSQL database for storing workflows and execution data
- **Queue Management**: Uses Redis for workflow execution queueing
- **Authentication**: Protected with basic authentication
- **Community Packages**: Automatically installs required community nodes via `n8n-init` service
- **Access Points**:
  - **Direct**: `http://localhost:${N8N_PORT}` (default: 63017) - ✅ **Recommended**
  - **Kong Gateway**: `http://n8n.localhost:${KONG_HTTP_PORT}/` (default: n8n.localhost:63002) - ✅ **Fully Working**
- **Dependencies**: Starts after the successful completion of the `supabase-db-init` and `ollama-pull` services

### 16.1.1. n8n-init Service

The n8n-init service automatically installs and configures community packages for n8n:

- **Purpose**: Installs essential community nodes for enhanced functionality
- **Default Nodes**:
  - `n8n-nodes-comfyui` - ComfyUI integration for image generation workflows
  - `@ksc1234/n8n-nodes-comfyui-image-to-image` - Image transformation workflows
  - `n8n-nodes-mcp` - Model Control Protocol integration
- **Configuration**: Nodes can be customized via `N8N_INIT_NODES` environment variable
- **Execution**: Runs once after n8n startup, then exits
- **Persistence**: Installed nodes persist across container restarts

### 16.2. Access Methods

#### Method 1: Direct Access (Recommended)
Access n8n directly at: `http://localhost:${N8N_PORT}` (default: 63017)

This bypasses Kong entirely and provides full n8n functionality.

#### Method 2: Through Kong Gateway (Domain-based routing) ✅
**FULLY WORKING**: Domain-based routing through Kong

**🚀 Automatic Setup (Recommended):**
The start.sh script can automatically manage hosts file entries for you:

```bash
# Option 1: Automatic setup during startup (requires sudo)
sudo ./start.sh --setup-hosts ./start.sh

# Option 2: Let the script check and prompt you
./start.sh ./start.sh
# The script will detect missing entries and guide you through setup

# Option 3: Skip hosts file management
./start.sh --skip-hosts ./start.sh
```

**Cleanup when done:**
```bash
# Remove hosts entries when stopping the stack
sudo ./stop.sh --clean-hosts ./start.sh
```

**Manual Setup (if preferred):**
If you prefer to manage hosts file entries manually, follow the steps below for your operating system to add the required entries for subdomain-based access.

**macOS/Linux Steps:**
1. Open Terminal
2. Run this command to edit the hosts file:
   ```bash
   sudo nano /etc/hosts
   ```
3. Enter your password when prompted
4. Use arrow keys to navigate to the end of the file
5. Add these lines at the bottom:
   ```
   # GenAI Stack subdomains
   127.0.0.1 n8n.localhost
   127.0.0.1 api.localhost
   127.0.0.1 search.localhost
   127.0.0.1 comfyui.localhost
   127.0.0.1 chat.localhost
   ```
6. Press `Ctrl + O` then `Enter` to save
7. Press `Ctrl + X` to exit
8. The change takes effect immediately

**Windows Steps:**
1. Press `Win + R` to open Run dialog
2. Type `notepad` and press `Ctrl + Shift + Enter` to run as Administrator
3. Click "Yes" when prompted by User Account Control
4. In Notepad, click File → Open
5. Navigate to: `C:\Windows\System32\drivers\etc\`
6. Change file type dropdown from "Text Documents (*.txt)" to "All Files (*.*)"
7. Select the `hosts` file and click Open
8. Scroll to the bottom of the file
9. Add these lines at the end:
   ```
   # GenAI Stack subdomains
   127.0.0.1 n8n.localhost
   127.0.0.1 api.localhost
   127.0.0.1 search.localhost
   127.0.0.1 comfyui.localhost
   127.0.0.1 chat.localhost
   ```
10. Save the file (Ctrl + S)
11. Close Notepad
12. The change takes effect immediately

**Alternative Method (macOS/Linux):**
If you prefer a one-line command for all entries:
```bash
echo -e "\n# GenAI Stack subdomains\n127.0.0.1 n8n.localhost\n127.0.0.1 api.localhost\n127.0.0.1 search.localhost\n127.0.0.1 comfyui.localhost\n127.0.0.1 chat.localhost" | sudo tee -a /etc/hosts
```

2. **Access Services via Subdomains**:
   - **n8n**: `http://n8n.localhost:${KONG_HTTP_PORT}/` (default: n8n.localhost:63002)
   - **Backend API**: `http://api.localhost:${KONG_HTTP_PORT}/` (default: api.localhost:63002)
   - **SearxNG**: `http://search.localhost:${KONG_HTTP_PORT}/` (default: search.localhost:63002)
   - **ComfyUI**: `http://comfyui.localhost:${KONG_HTTP_PORT}/` (default: comfyui.localhost:63002)
   - **Open WebUI**: `http://chat.localhost:${KONG_HTTP_PORT}/` (default: chat.localhost:63002)

**Status**: ✅ All services fully functional with subdomain routing

**Note**: Supabase services remain path-based (`/auth/v1/`, `/rest/v1/`, etc.) to maintain compatibility with Supabase client libraries and Supabase Studio.
- ✅ No proxy trust errors (fixed with `N8N_PROXY_HOPS=1`)
- ✅ Full web interface functionality

#### Authentication
n8n uses its built-in authentication system. Use the credentials configured in your environment variables:
- Username: As set in `N8N_BASIC_AUTH_USER`
- Password: As set in `N8N_BASIC_AUTH_PASSWORD`

#### Success! 🎉
Both access methods now work fully. Domain-based routing through Kong provides the same functionality as direct access.

### 16.3. Features

- **Visual Workflow Editor**: Create workflows with a drag-and-drop interface
- **Node-Based Architecture**: Connect different services and actions using nodes
- **Scheduling**: Run workflows on a schedule or trigger them based on events
- **Error Handling**: Configure retry logic and error workflows
- **Credentials Management**: Securely store and manage credentials for various services
- **Extensibility**: Create custom nodes for specific use cases

### 16.4. Integration with Other Services

- **Backend Service**: The backend service can trigger n8n workflows for tasks like data processing, notifications, and more
- **Supabase PostgreSQL**: n8n uses the Supabase database for storing workflows and execution data
- **Redis**: n8n uses Redis for queue management, improving reliability and scalability of workflow executions

### 16.5. Queue Mode Architecture

n8n operates in queue mode for enhanced scalability and reliability:

#### Main n8n Service (Producer)
- **Role**: Handles web UI, API requests, webhook triggers, and workflow orchestration
- **Functionality**: Receives workflow execution requests and queues them to Redis
- **Access**: Available via Kong proxy and direct connection

#### n8n-worker Service (Consumer)  
- **Role**: Dedicated worker process that executes workflows
- **Functionality**: Pulls workflow execution jobs from Redis queue and processes them
- **Scaling**: Multiple workers can be added for increased throughput
- **Isolation**: Workflow execution is isolated from the main UI process

#### Queue Management
- **Message Broker**: Redis with Bull queue library
- **Job Flow**: Main n8n → Redis queue → Worker(s) → Database
- **Reliability**: Jobs persist in Redis until successfully processed
- **Monitoring**: Health checks available at `/healthz` and `/healthz/readiness` on worker

### 16.6. Kong Gateway Integration

n8n is accessible through the Kong API Gateway with full WebSocket support for real-time features:

- **Proxy URL**: `http://n8n.localhost:${KONG_HTTP_PORT}/` (requires hosts file entries)
- **Direct URL**: `http://localhost:${N8N_PORT}` (bypasses proxy)
- **WebSocket Support**: Kong automatically handles HTTP to WebSocket protocol upgrades for n8n's push backend
- **Real-time Features**: Workflow execution updates, test webhook listening, and collaboration features work seamlessly through the proxy
- **Technical Implementation**: 
  - Kong routes are configured with `preserve_host: true` for proper origin validation
  - n8n runs in development mode (`NODE_ENV: development`) to allow WebSocket connections through proxy
  - WebSocket connections are automatically upgraded when accessing `/rest/push` endpoints

### 16.7. Service Dependencies (Verified)

The following service dependencies have been successfully tested and verified:

#### n8n → Redis (Queue Management)
- **Status**: ✅ **Working**
- **Purpose**: Job queue management for workflow execution
- **Verification**: Bull queue keys created in Redis, worker processes jobs successfully
- **Configuration**: `EXECUTIONS_MODE=queue` with Redis connection parameters

#### n8n → PostgreSQL (Data Storage)
- **Status**: ✅ **Working** 
- **Purpose**: Workflow storage, execution history, and credentials management
- **Verification**: n8n schema and tables created in Supabase database
- **Database**: Uses `n8n` schema in Supabase PostgreSQL

#### n8n PostgreSQL Node → Supabase Database
- **Status**: ✅ **Working**
- **Purpose**: Workflows can query application data (e.g., LLM configurations)
- **Verification**: Successfully queried `public.llms` table from n8n workflows
- **Access**: Via PostgreSQL node with Supabase database credentials

#### Complete Queue Pipeline
- **Status**: ✅ **Working**
- **Flow**: UI trigger → Main n8n → Redis queue → Worker → Database → Response
- **Verification**: End-to-end workflow execution through queue system confirmed

### 16.8. Configuration

The n8n service can be configured through the following environment variables:

- `N8N_PORT`: The port on which n8n is accessible (default: 63014)
- `N8N_ENCRYPTION_KEY`: The encryption key used to secure credentials and other sensitive data
- `N8N_AUTH_ENABLED`: Whether authentication is enabled (default: true)
- `N8N_BASIC_AUTH_ACTIVE`: Whether basic authentication is active (default: true)
- `N8N_BASIC_AUTH_USER`: The username for basic authentication
- `N8N_BASIC_AUTH_PASSWORD`: The password for basic authentication
- `N8N_HOST`: The hostname for n8n (default: localhost)
- `N8N_PROTOCOL`: The protocol for n8n (default: http)
- `N8N_EXECUTIONS_MODE`: The execution mode for n8n (default: queue)
- `N8N_COMMUNITY_PACKAGES_ENABLED`: Enable community package installation (default: true)
- `N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE`: Allow community nodes as AI Agent tools (default: true)
- `N8N_INIT_NODES`: Comma-separated list of community nodes to install automatically

### 16.9. Pre-built Workflows

The `n8n-init/config/` directory contains pre-built n8n workflow templates providing automation and integration capabilities for research tasks.

#### 16.9.1. Available Workflows

**SearxNG Research Workflow** (`searxng-research-workflow.json`):
- **Purpose**: Automated research using SearxNG with AI summarization
- **Webhook**: `/webhook/research`
- **Features**: Searches SearxNG for information, uses AI to summarize results, returns structured research summaries

**Import Instructions**:
Since modern n8n (v1.106.3+) requires user management instead of Basic Auth, workflows must be imported manually:

1. **Complete n8n Setup**: Access n8n and complete user registration
2. **Set Up Database Credentials**: Add PostgreSQL credential for Supabase database
3. **Import Workflows**: Upload JSON files via Workflows → Import from File
4. **Configure Nodes**: Assign database credentials to PostgreSQL nodes
5. **Activate Workflows**: Enable workflows using toggle switches

**Testing**: Use manual triggers or PostgreSQL node queries since webhook functionality has compatibility issues with modern n8n + queue mode.

#### 16.9.2. Integration with Open-WebUI

The research workflow is designed to work with the Open-WebUI n8n integration tool located at `open-webui/tools/n8n_webhook_tool.py`. This tool allows users to trigger n8n workflows directly from chat conversations.

### 16.10. Community Nodes

The following community nodes are automatically installed by the n8n-init service:

- **`n8n-nodes-comfyui`** - ComfyUI integration for image generation workflows
- **`@ksc1234/n8n-nodes-comfyui-image-to-image`** - Advanced image transformation capabilities  
- **`n8n-nodes-mcp`** - Model Context Protocol support for AI integrations

These nodes extend n8n's functionality with specialized AI and image processing capabilities.

---

---

## 17. Open-WebUI Integration

Open-WebUI provides a powerful, user-friendly web interface for interacting with AI models and services in the GenAI Vanilla Stack. This section covers the tools and configurations available for enhanced functionality.

### 17.1. Overview

- **Access Point**: `http://localhost:${OPEN_WEB_UI_PORT}` (default: 63015)
- **Docker Image**: Uses the official Open-WebUI image
- **Features**: Chat interface, model management, tool integration, workflow automation
- **Dependencies**: Backend API, Ollama (containerized or local), optional ComfyUI and research services

### 17.2. Available Tools

The `open-webui/tools/` directory contains specialized tools for extending Open-WebUI capabilities:

#### Research Tools
- `research_tool.py` - Web research tool for comprehensive information gathering
- `research_streaming_tool.py` - Streaming version of the research tool

#### Image Generation Tools
- `comfyui_image_generation_tool.py` - AI-powered image generation using ComfyUI

### 17.3. ComfyUI Image Generation Tool

The ComfyUI image generation tool provides AI-powered image generation capabilities directly within Open-WebUI.

#### Features
- Generate images from text prompts
- Support for negative prompts
- Configurable image dimensions, steps, and CFG scale
- Model selection from available checkpoints
- Real-time status checking
- Queue monitoring

#### Tool Functions
1. **`generate_image(prompt, ...)`** - Generate images with customizable parameters
2. **`get_available_models()`** - List all available ComfyUI models from database
3. **`check_comfyui_status()`** - Check service health and queue status

#### Usage Examples

**Basic Image Generation**:
```
generate_image("a beautiful sunset over mountains")
```

**Advanced Image Generation**:
```
generate_image(
    prompt="a cyberpunk city at night, neon lights, rain",
    negative_prompt="blurry, low quality",
    width=768,
    height=512,
    steps=30,
    cfg=8.0,
    checkpoint="sd_v1-5_pruned_emaonly.safetensors"
)
```

**Check Available Models**:
```
get_available_models()
```

**Check Service Status**:
```
check_comfyui_status()
```

### 17.4. Configuration

The tools are configured via Open-WebUI's tool valve system:

#### ComfyUI Tool Valves
- `backend_url`: Backend API URL (default: http://backend:8000)
- `timeout`: Max wait time for generation (default: 120s)
- `enable_tool`: Enable/disable the tool (default: true)
- `default_width`: Default image width (default: 512)
- `default_height`: Default image height (default: 512)
- `default_steps`: Default generation steps (default: 20)
- `default_cfg`: Default CFG scale (default: 7.0)

#### Research Tool Valves
- `researcher_url`: Deep Researcher service URL (default: http://local-deep-researcher:2024)
- `timeout`: Max wait time for research (default: 300s)
- `enable_tool`: Enable/disable the tool (default: true)

### 17.5. Installation

1. **Tool Import**: Copy the tool files to Open-WebUI's tools directory or import via the admin interface
2. **Volume Mount**: Ensure the tools directory is mounted in the Docker container:
   ```yaml
   volumes:
     - ./open-webui/tools:/app/backend/data/tools
   ```
3. **Environment Variables**: Ensure proper environment variables are set in the Docker Compose file
4. **Model Management**: Use the backend API to manage ComfyUI models in the database

### 17.6. Integration with Other Services

#### Backend API Integration
- ComfyUI tools communicate with the FastAPI backend at `/comfyui/*` endpoints
- Research tools integrate with Local Deep Researcher service
- All tools support health checking and error handling

#### Kong Gateway Routing
- Tools access services through Kong API Gateway for consistent routing
- ComfyUI requests are routed to appropriate ComfyUI instance (containerized or local)
- Authentication and rate limiting can be configured via Kong

#### Database Integration
- ComfyUI models are managed in PostgreSQL database
- Tools can query available models and their metadata
- Support for model categorization (checkpoints, VAE, LoRA, etc.)

### 17.7. Troubleshooting

#### Common Issues

1. **Tool Not Available**
   - Check if tools directory is properly mounted
   - Verify tool files have correct format and metadata
   - Check Open-WebUI logs for import errors

2. **ComfyUI Connection Issues**
   - Verify ComfyUI service is running (use `check_comfyui_status()`)
   - Check backend API connectivity
   - For localhost SOURCE configuration, ensure local ComfyUI is running on port 8000

3. **Image Generation Failures**
   - Check if required models are available (`get_available_models()`)
   - Verify model files are properly downloaded
   - Check ComfyUI queue status for processing issues

4. **Research Tool Issues**
   - Verify Local Deep Researcher service is running
   - Check network connectivity between containers
   - Review research service logs for API errors

#### Debug Commands

```bash
# Check ComfyUI health via backend
curl http://localhost:${BACKEND_PORT}/comfyui/health

# List available models
curl http://localhost:${BACKEND_PORT}/comfyui/db/models

# Check ComfyUI queue
curl http://localhost:${BACKEND_PORT}/comfyui/queue

# Test research service
curl http://localhost:${LOCAL_DEEP_RESEARCHER_PORT}/health
```

#### AI-Local Profile Troubleshooting

**Ollama Connection Issues:**
- Verify Ollama is running: `curl http://localhost:11434/api/tags`
- Check Ollama logs: `journalctl -u ollama -f` (Linux) or check console output
- Ensure port 11434 is not blocked by firewall
- For macOS: Ollama runs as a menu bar app - ensure it's started

**ComfyUI Connection Issues:**
- Verify ComfyUI is running: `curl http://localhost:8000/system_stats`
- Start ComfyUI manually: `cd /path/to/ComfyUI && python main.py --listen --port 8000`
- Check that ComfyUI is bound to all interfaces with `--listen` flag

**Service Detection:**
The start.sh script will show warnings if local services aren't detected:
- "⚠️ Local Ollama: Not detected on port 11434"
- "⚠️ Local ComfyUI: Not running on port 8000"

### 17.8. Profile-Specific Considerations

#### Default Profile
- Uses containerized ComfyUI service
- Models stored in Docker volumes
- Full integration with all services

#### AI-Local Profile
- Uses host-installed ComfyUI (port 8000)
- Models can be synced between host and Docker volumes
- Requires local ComfyUI installation

#### AI-GPU Profile
- Uses CUDA-enabled ComfyUI container
- Optimized for GPU acceleration
- Larger model support for production workloads

## 18. Next-Generation Service Roadmap (vNext)

Based on comprehensive analysis of the current GenAI landscape and emerging 2025 trends, here's our strategic roadmap for expanding the vanilla stack with cutting-edge services.

### 18.1. Tier 1: High-Impact Essentials (Immediate Priority)

#### 18.1.1. Weaviate Vector Database ⭐⭐⭐⭐⭐
- **Purpose**: Dedicated vector database with hybrid search capabilities
- **Value**: Massive upgrade from pgvector for RAG applications
- **Integration**: Easy Docker deployment, 18MB image, GraphQL API
- **Benefits**: Built-in embeddings, multi-modal support, semantic search
- **Complexity**: Low - drop-in replacement with superior performance
- **Configuration**: Dedicated vector services in unified compose file

#### 18.1.2. Whisper Audio Transcription Service ⭐⭐⭐⭐⭐
- **Purpose**: Audio/video transcription and voice-to-text processing
- **Value**: Enables multimedia content processing for research and analysis
- **Integration**: Docker container available, REST API endpoints
- **Benefits**: 99+ language support, high accuracy, batch processing
- **Complexity**: Low - minimal configuration, immediate value
- **Use Cases**: Meeting transcription, podcast analysis, video content extraction

#### 18.1.3. Document Processing Service (Unstructured.io) ⭐⭐⭐⭐⭐
- **Purpose**: Advanced PDF, DOCX, HTML, TXT parsing and intelligent chunking
- **Value**: Critical for RAG applications and knowledge base ingestion
- **Integration**: Docker image available, Python API, webhook support
- **Benefits**: Maintains document structure, handles complex layouts, metadata extraction
- **Complexity**: Medium - requires file handling workflows and storage integration
- **Features**: Table extraction, OCR support, semantic chunking

### 18.2. Tier 2: High-Value Enhancements (Next Phase)

#### 18.2.1. Qdrant Vector Database (Alternative/Complement) ⭐⭐⭐⭐
- **Purpose**: High-performance Rust-based vector search engine
- **Value**: Superior performance for large-scale vector operations (billions of vectors)
- **Integration**: Single Docker container, REST/gRPC APIs, clustering support
- **Benefits**: Advanced filtering, payload search, horizontal scaling
- **Complexity**: Low - similar to Weaviate but optimized for scale

#### 18.2.2. Prometheus + Grafana Monitoring Stack ⭐⭐⭐⭐
- **Purpose**: Comprehensive observability, metrics, and alerting
- **Value**: Essential for production deployments and performance monitoring
- **Integration**: Standard Docker images, Kong metrics integration, service discovery
- **Benefits**: Real-time dashboards, alerting, historical analytics
- **Complexity**: Medium - requires dashboard configuration and alert setup
- **Configuration**: Observability services in unified compose file

#### 18.2.3. Piper TTS (Text-to-Speech) ⭐⭐⭐⭐
- **Purpose**: High-quality, fast neural text-to-speech synthesis
- **Value**: Complements Whisper for complete audio processing pipeline
- **Integration**: Docker container, HTTP API, multiple voice models
- **Benefits**: 30+ languages, neural voices, low latency (<100ms)
- **Complexity**: Low - simple API integration with voice model management

### 18.3. Tier 3: Advanced Capabilities (Future Phases)

#### 18.3.1. Apache Airflow (Advanced Workflow Orchestration) ⭐⭐⭐
- **Purpose**: Complex data pipeline orchestration and scheduling
- **Value**: Advanced workflow management beyond n8n capabilities
- **Integration**: Docker Compose stack, web UI, programmatic DAGs
- **Benefits**: Complex dependencies, retry logic, monitoring, scale
- **Complexity**: High - requires DAG development and learning curve

#### 18.3.2. MeiliSearch (Lightning-Fast Search) ⭐⭐⭐
- **Purpose**: Instant full-text search with typo tolerance
- **Value**: Enhanced search capabilities for documents and content
- **Integration**: Single Docker container, REST API, admin dashboard
- **Benefits**: Sub-50ms search, faceted filtering, multilingual support
- **Complexity**: Low - minimal configuration, immediate value

#### 18.3.3. Keycloak (Enterprise Identity Management) ⭐⭐⭐
- **Purpose**: Advanced authentication, SSO, OAuth2/OIDC provider
- **Value**: Enterprise-grade security beyond basic Supabase Auth
- **Integration**: Docker container, multiple database backends
- **Benefits**: Role-based access, social logins, SAML federation
- **Complexity**: High - complex configuration and administrative overhead

### 18.4. Specialized Use Cases (Evaluation Phase)

#### 18.4.1. LiveKit (Real-time Audio/Video) ⭐⭐
- **Purpose**: Real-time multimedia streaming and processing
- **Value**: Voice AI agents, live transcription, video conferencing
- **Integration**: Multiple Docker services, WebRTC infrastructure
- **Benefits**: Real-time voice bots, conference integration, live AI
- **Complexity**: Very High - requires media server infrastructure

### 18.5. Search Service Integration - SearxNG Only

After comprehensive evaluation, we've selected SearxNG as our sole search service for the Deep Researcher. This decision simplifies our architecture while providing access to 70+ search engines through a single, unified interface.

#### 18.5.1. Selected Search Solution

**SearxNG (Self-hosted Metasearch Engine)** ✅ **SELECTED**
- **Type**: Open-source metasearch aggregator
- **Why Selected**: 
  - Aggregates 70+ search engines including Google Scholar, Semantic Scholar, DuckDuckGo, arxiv, PubMed, GitHub, StackOverflow, Wikipedia, and more
  - Self-hosted with complete privacy control - no data leaves our infrastructure
  - No API keys required - zero external dependencies
  - Built-in result merging, deduplication, and ranking
  - Supports categorized search (academic, general, news, technical)
  - Single service to deploy and maintain
  - Perfect alignment with vanilla stack philosophy
- **Integration**: Docker container with simple REST/JSON API
- **Features**: Privacy-first, customizable engines, result filtering, multi-language support

#### 18.5.2. Discarded Search API Options

**Brave Search API** ❌ **DISCARDED**
- **Rationale for Discarding**:
  - Requires API key registration even for free tier
  - Limited to 2,000-5,000 queries/month on free tier
  - Costs $5 per 1,000 queries after free tier exhausted
  - SearxNG can access Brave search results without API limitations
  - Adds unnecessary complexity and external dependency

**DuckDuckGo Direct API** ❌ **DISCARDED**
- **Rationale for Discarding**:
  - Already available through SearxNG with better integration
  - SearxNG provides superior result formatting and filtering
  - No need to maintain separate API integration
  - Limited to instant answers when used directly

**Semantic Scholar Direct API** ❌ **DISCARDED**
- **Rationale for Discarding**:
  - Already integrated as a search engine within SearxNG
  - SearxNG automatically merges academic results with other sources
  - No need to manage separate rate limits or API keys
  - Results are automatically deduplicated with other academic engines

**Google Custom Search API** ❌ **DISCARDED**
- **Rationale for Discarding**:
  - Restrictive limit of 100 free queries/day
  - Expensive at $5 per 1,000 queries
  - Privacy concerns with sending queries to Google
  - SearxNG provides access to web results without these limitations

**Bing Search API** ❌ **DISCARDED**
- **Rationale for Discarding**:
  - Being discontinued by Microsoft in 2025
  - Would require migration to alternative anyway
  - SearxNG provides more sustainable long-term solution

#### 18.5.3. SearxNG Configuration for Research

SearxNG will be configured with carefully selected engines optimized for research:

**Academic & Research Engines**:
- Semantic Scholar (weight: 2.0)
- Google Scholar (weight: 2.0)
- arxiv (weight: 1.8)
- PubMed (weight: 1.5)
- CrossRef (weight: 1.5)

**General & Technical Engines**:
- DuckDuckGo (weight: 1.5)
- GitHub (weight: 1.5)
- StackOverflow (weight: 1.8)
- Wikipedia (weight: 1.2)

**Privacy-First Approach**:
- Google: Disabled
- Bing: Disabled
- All tracking engines: Disabled

#### 18.5.4. Simplified Implementation Plan

**Phase 1** (Immediate):
- Deploy SearxNG as a Docker service
- Configure selected search engines and weights
- Integrate with Deep Researcher service
- Add to Kong API Gateway routing

**Phase 2** (Optimization):
- Fine-tune engine weights based on usage
- Implement result caching in Redis
- Add search analytics and monitoring
- Create custom search categories

**Phase 3** (Enhancement):
- Add custom search plugins if needed
- Implement advanced filtering rules
- Optimize for specific research domains
- Consider federation with other SearxNG instances

### 18.6. Implementation Timeline

#### Q1 2025 (Foundation)
- **Weaviate** for vector storage upgrade
- **Whisper** for audio transcription
- **Document Processing** for RAG enhancement
- **SearxNG** self-hosted search (moved from Q2 - sole search solution)

#### Q2 2025 (Enhancement)
- **Prometheus/Grafana** monitoring stack
- **Piper TTS** for audio synthesis
- **MeiliSearch** for fast document search (distinct from web search)

#### Q3 2025 (Advanced)
- **Qdrant** for scale vector operations
- **Airflow** for complex workflows

#### Q4 2025 (Enterprise)
- **Keycloak** for enterprise auth
- **LiveKit** evaluation for real-time features
- **Performance optimization** and scaling

### 18.7. Unified Service Architecture

To accommodate these services, they will be integrated into the unified docker-compose.yml file with SOURCE-based configuration:

```
# Services configured via SOURCE environment variables:
# - Vector databases and embedding services (WEAVIATE_SOURCE, etc.)
# - Audio processing services (WHISPER_SOURCE, PIPER_SOURCE)  
# - Search services (SEARXNG_SOURCE)
# - Monitoring services (PROMETHEUS_SOURCE, GRAFANA_SOURCE)
├── workflow.yml       # NEW: Advanced workflow orchestration
└── security.yml       # NEW: Enhanced authentication and security
```

### 18.8. Integration Benefits

This roadmap positions the GenAI Vanilla Stack as:
- **Production-Ready**: Monitoring, security, and scaling capabilities
- **RAG-Optimized**: Advanced vector storage and document processing
- **Multi-Modal**: Audio, text, image, and video processing
- **Research-Enhanced**: Multiple search APIs and academic sources
- **Enterprise-Grade**: Advanced auth, monitoring, and compliance
- **Developer-Friendly**: Rich tooling and automation capabilities

### 18.9. Technology Choice Analysis & Comparisons

The following section provides detailed analysis of why specific technologies were recommended and how they compare to alternatives, including existing services in the stack.

#### 18.9.1. Search Engine Comparison: MeiliSearch vs Elasticsearch

| Feature | MeiliSearch ⭐ | Elasticsearch | Analysis |
|---------|----------------|---------------|----------|
| **Setup Complexity** | Very Low (single Docker container) | High (cluster setup, multiple nodes) | MeiliSearch wins for simplicity |
| **Memory Usage** | Low (~50-100MB) | High (1GB+ per node) | MeiliSearch 10x more efficient |
| **Search Speed** | Ultra-fast (<50ms) | Fast (100-200ms) | MeiliSearch optimized for speed |
| **Configuration** | Zero-config out-of-the-box | Complex (mappings, analyzers, shards) | MeiliSearch ready immediately |
| **Typo Tolerance** | Built-in, intelligent | Requires custom configuration | MeiliSearch handles typos naturally |
| **Faceted Search** | Native support | Requires aggregations setup | MeiliSearch simpler implementation |
| **API Design** | RESTful, intuitive | Powerful but complex | MeiliSearch easier to integrate |
| **Scaling** | Horizontal (simple) | Horizontal (complex) | Elasticsearch better for massive scale |
| **Analytics** | Basic | Advanced (Kibana ecosystem) | Elasticsearch wins for analytics |
| **Multi-language** | Excellent | Good (requires config) | MeiliSearch better i18n support |
| **Resource Requirements** | Minimal | Substantial | MeiliSearch fits vanilla stack philosophy |
| **Learning Curve** | Minimal | Steep | MeiliSearch faster to implement |
| **Production Scale** | Medium (millions of docs) | Massive (billions of docs) | Depends on use case |

**Why MeiliSearch for GenAI Vanilla Stack:**
- **Philosophy Alignment**: Matches "vanilla" approach - simple, fast, effective
- **Developer Experience**: Zero-config, instant search, intuitive API
- **Resource Efficiency**: Perfect for containerized environments
- **GenAI Use Cases**: Optimized for document search, knowledge bases, RAG applications
- **Immediate Value**: Working search in minutes, not days

**When to Choose Elasticsearch Instead:**
- Massive scale requirements (100M+ documents)
- Complex analytics and aggregations needed
- Existing Elastic ecosystem investment
- Advanced enterprise features required
- Team has Elasticsearch expertise

#### 18.9.2. Authentication Comparison: Keycloak vs Supabase Auth

| Feature | Supabase Auth ✅ | Keycloak 🏢 | Analysis |
|---------|------------------|-------------|----------|
| **Setup Complexity** | Very Low (integrated) | High (standalone service) | Supabase wins for simplicity |
| **Integration** | Native to stack | Requires integration work | Supabase already integrated |
| **OAuth2/OIDC** | Basic support | Full compliance | Keycloak is standard-compliant |
| **Social Logins** | Built-in (Google, GitHub, etc.) | Configurable | Both support major providers |
| **Enterprise SSO** | Limited | Full SAML/LDAP support | Keycloak wins for enterprise |
| **Role-Based Access** | Basic roles | Advanced RBAC + ABAC | Keycloak more sophisticated |
| **Multi-tenancy** | Single tenant | Full multi-tenant | Keycloak for SaaS platforms |
| **User Management** | Simple admin | Advanced admin console | Keycloak more feature-rich |
| **Customization** | Limited theming | Full customization | Keycloak highly customizable |
| **Compliance** | Basic | SOC2, GDPR, HIPAA ready | Keycloak for regulated industries |
| **Performance** | Lightweight | Resource intensive | Supabase more efficient |
| **Maintenance** | Managed by Supabase | Self-managed | Supabase requires less ops |
| **Cost** | Free tier available | Open source (hosting costs) | Both can be cost-effective |

**Why Supabase Auth is Recommended for Most Cases:**
- **Integrated Experience**: Already part of the stack, zero additional setup
- **Simplicity**: Covers 80% of use cases with minimal complexity
- **Developer Productivity**: Working auth in minutes
- **Maintenance**: One fewer service to manage and monitor
- **GenAI Focus**: Perfect for AI applications, research tools, content platforms

**When to Add Keycloak Instead:**
- **Enterprise Requirements**: Large organizations with complex auth needs
- **Compliance**: Regulated industries (healthcare, finance, government)
- **Multi-tenancy**: SaaS platforms with tenant isolation
- **Legacy Integration**: Existing LDAP/AD infrastructure
- **Advanced RBAC**: Complex permission systems
- **Federation**: Multiple identity providers

**Hybrid Approach (Best of Both):**
```
Public Users → Supabase Auth (simple, fast)
Enterprise Users → Keycloak (via federation)
Internal Admin → Keycloak (advanced RBAC)
```

#### 18.9.3. Vector Database Comparison: pgvector vs Weaviate vs Qdrant

| Feature | pgvector (Current) ✅ | Weaviate 🚀 | Qdrant ⚡ | Analysis |
|---------|----------------------|-------------|-----------|----------|
| **Setup Complexity** | Zero (already integrated) | Low (single container) | Low (single container) | pgvector wins for existing stacks |
| **Performance** | Good (PostgreSQL optimized) | Excellent (purpose-built) | Excellent (Rust performance) | Weaviate/Qdrant 3-5x faster |
| **Scalability** | Limited (PostgreSQL limits) | High (distributed) | Very High (horizontal) | Dedicated DBs scale better |
| **Vector Operations** | Basic (L2, cosine, inner) | Advanced (hybrid search) | Advanced (payload filtering) | Specialized DBs more capable |
| **Hybrid Search** | Manual implementation | Native (vector + keyword) | Native (vector + payload) | Native support is superior |
| **Multi-modal** | No | Yes (text, images, audio) | Limited | Weaviate best for multi-modal |
| **GraphQL Support** | No | Yes (native) | No | Weaviate unique advantage |
| **Filtering** | SQL WHERE clauses | Native filters | Advanced payload filters | SQL familiar but limited |
| **Memory Usage** | Shared with PostgreSQL | Optimized for vectors | Optimized for vectors | Dedicated memory management |
| **Backup/Recovery** | PostgreSQL tools | Built-in snapshots | Built-in snapshots | PostgreSQL tools mature |
| **ACID Transactions** | Yes (PostgreSQL) | Limited | Limited | PostgreSQL advantage |
| **Ecosystem** | PostgreSQL ecosystem | Growing ecosystem | Smaller ecosystem | PostgreSQL mature ecosystem |
| **Embeddings** | Manual generation | Auto-vectorization | Manual generation | Weaviate automates workflow |
| **Language Support** | SQL + any PostgreSQL client | GraphQL, REST, gRPC | REST, gRPC | SQL most familiar |
| **Resource Requirements** | Shared with DB | Dedicated resources | Dedicated resources | Shared resources more efficient |
| **Production Scale** | Millions of vectors | Billions of vectors | Billions of vectors | Scale ceiling differences |

**Why pgvector is Great for Getting Started:**
- **Zero Setup**: Already running, no additional services
- **Familiar**: SQL interface, PostgreSQL ecosystem
- **Integrated**: Seamless with existing data and transactions
- **Cost Effective**: No additional infrastructure
- **ACID Compliance**: Full transaction support
- **Rapid Prototyping**: Vector search working immediately

**Why Upgrade to Weaviate:**
- **Performance**: 3-5x faster vector operations
- **Hybrid Search**: Native vector + keyword search
- **Multi-modal**: Text, images, audio in one system
- **Auto-vectorization**: Automatic embedding generation
- **GraphQL**: Modern API with powerful querying
- **Scale**: Handle billions of vectors efficiently
- **Purpose-built**: Optimized specifically for vector operations

**Why Choose Qdrant:**
- **Performance**: Rust-based, extremely fast
- **Filtering**: Advanced payload filtering capabilities
- **Scalability**: Horizontal scaling for massive datasets
- **Memory Efficiency**: Optimized memory usage patterns
- **Production Ready**: Built for high-throughput applications
- **Flexibility**: Rich query capabilities and filters

**Recommended Migration Path:**

1. **Start with pgvector** (Current):
   - Perfect for prototyping and early development
   - Learn vector search concepts
   - Build initial RAG applications

2. **Upgrade to Weaviate** (When you need):
   - Better performance (>1M vectors)
   - Multi-modal capabilities
   - Hybrid search features
   - Auto-vectorization workflows

3. **Consider Qdrant** (For scale/performance):
   - Massive datasets (>10M vectors)
   - High-throughput applications
   - Complex filtering requirements
   - Performance-critical applications

**Hybrid Approach (Best of All Worlds):**
```
Relational Data → PostgreSQL (with pgvector for basic vectors)
Vector Search → Weaviate (for AI/ML workloads)
High-Performance → Qdrant (for production scale)
Transactional → PostgreSQL (for consistency requirements)
```

#### 18.9.4. Decision Framework

**For Startups/Small Teams:**
- Keep Supabase Auth + pgvector
- Add MeiliSearch for search
- Upgrade incrementally as you scale

**For Growing Applications:**
- Migrate to Weaviate for vectors
- Keep Supabase Auth
- Add MeiliSearch for document search
- Monitor and scale as needed

**For Enterprise/Scale:**
- Weaviate or Qdrant for vectors
- Keycloak for complex auth
- Elasticsearch for advanced analytics
- Full monitoring and observability

**Key Principle: Progressive Enhancement**
The vanilla stack philosophy is to start simple and enhance progressively. Each recommendation provides a clear upgrade path without forcing premature optimization.

## 19. TODO - Current Planned Improvements

### 19.1. Docker Compose Architecture Restructuring ✅

**Priority**: High | **Status**: Completed | **Complexity**: Medium

**Overview**: Successfully restructured the Docker Compose architecture to improve modularity, reusability, and service management. The unified architecture with SOURCE-based configuration enables better service control and makes the stack more suitable as a foundation for specialized projects.

#### Issues Resolved:
- ✅ **Redundant service definitions**: Eliminated through unified compose structure
- ✅ **All-or-nothing service deployment**: Resolved with SOURCE-based configuration system  
- ✅ **Difficult service group control**: Now possible with granular SOURCE variables
- ✅ **Limited reusability**: Improved modularity for derivative projects
- ✅ **Environment file path issues**: Consistent env file handling with unified compose file

#### Final Implemented Structure:
```
vanilla-genai/
├── docker-compose.yml              # Unified service definitions with SOURCE-based configuration
├── docker-compose.ai-local.yml     # Legacy: Local Ollama flavor (backward compatibility)
├── docker-compose.ai-gpu.yml       # Legacy: GPU-optimized flavor (backward compatibility)
├── bootstrapper/                   # Python configuration management
│   ├── start.py                    # Main startup script  
│   ├── stop.py                     # Main stop script
│   └── service-configs.yml         # SOURCE matrix for dynamic service configuration
```

#### Service Grouping:

**Data Services** (`data.yml`):
- `supabase-db` - PostgreSQL with pgvector and PostGIS
- `supabase-db-init` - Database initialization scripts
- `redis` - Caching and session management
- `supabase-meta` - Database metadata service
- `supabase-auth` - Authentication service
- `supabase-api` - REST API service (PostgREST)
- `supabase-storage` - File storage service
- `supabase-realtime` - Real-time subscriptions
- `neo4j-graph-db` - Graph database for AI knowledge graphs

**AI Services** (`ai.yml`, `ai-local.yml`, `ai-gpu.yml`):
- `ollama` - Local LLM inference (containerized/local/GPU variants)
- `ollama-pull` - Model management
- `local-deep-researcher` - AI-powered research service
- `n8n` - Workflow automation platform

**Application Services** (`apps.yml`, `apps-local.yml`, `apps-gpu.yml`):
- `supabase-studio` - Database management UI
- `kong-api-gateway` - API gateway and routing
- `open-web-ui` - Chat interface
- `backend` - FastAPI backend service

#### Implementation Benefits:

1. **✅ Granular Control**: Start only needed services
   ```bash
   # Default stack (all services)
   ./start.sh
   
   # AI-focused stack
   ./start.sh  # with LLM_PROVIDER_SOURCE=ollama-localhost in .env.example
   
   # GPU-optimized stack
   ./start.sh --base-port 64000  # all services containerized
   ```

2. **✅ Modular Architecture**: Clean separation of concerns
   - Data services are independent of AI services
   - AI services can be swapped between local/containerized/GPU
   - App services adapt to the AI configuration

3. **✅ Better Resource Utilization**: Run only what you need
4. **✅ Improved Reusability**: Perfect foundation for specialized projects
5. **✅ Simplified Maintenance**: DRY principle, no redundant definitions

#### Migration Strategy (Completed):
1. **✅ Phase 1**: Consolidated all services into unified docker-compose.yml
2. **✅ Phase 2**: Implemented SOURCE-based configuration system
3. **✅ Phase 3**: Updated documentation and convenience scripts
4. **✅ Phase 4**: Migrated to YAML-driven service matrix configuration

#### Environment-Based Control:
```bash
# Enhanced .env configuration
ENABLE_AI_SERVICES=true
ENABLE_AUTOMATION_SERVICES=true  
ENABLE_UI_SERVICES=true
ENABLE_GRAPH_DB=true
ENABLE_COMFYUI=false  # NEW
```

#### Updated Convenience Scripts:
```bash
# Enhanced start.sh options
# Configure SOURCE variables in .env.example for specific service combinations
# All configuration is done via SOURCE variables
./start.sh --disable ui                    # Disable UI services
./start.sh --enable comfyui               # Enable ComfyUI specifically
```

---

### 19.2. Service Dependencies Enhancement 🔗

**Priority**: High | **Status**: Planned | **Complexity**: Medium

**Overview**: Enhance service modularity by implementing configurable dependencies between services using built-in features, community plugins, and HTTP APIs. This will enable more sophisticated workflows while maintaining the ability to selectively enable/disable services.

#### High-Value Service Dependencies (Implementation Ready)

**1. n8n → Ollama Integration** ⭐⭐⭐⭐⭐
- **Method**: Built-in HTTP Request nodes
- **Implementation**: Native HTTP nodes for LLM API calls
- **Benefits**: LLM-powered automation workflows
- **Configuration**: Use n8n's HTTP Request node with Ollama API endpoints

**2. Open-WebUI → n8n Webhooks** ⭐⭐⭐⭐
- **Method**: Webhook integration via Open-WebUI API
- **Implementation**: Open-WebUI can trigger n8n workflows via webhooks
- **Benefits**: Chat-triggered automation, workflow execution from UI
- **Configuration**: Configure webhook URLs in Open-WebUI settings

**3. ComfyUI → SearxNG Search** ⭐⭐⭐⭐
- **Method**: HTTP Request nodes for web search
- **Implementation**: Custom nodes making API calls to SearxNG
- **Benefits**: Web search-enhanced image generation workflows
- **Configuration**: Custom ComfyUI nodes calling SearxNG API

**4. n8n → SearxNG Automation** ⭐⭐⭐⭐
- **Method**: Built-in HTTP Request nodes
- **Implementation**: Native HTTP nodes for search automation
- **Benefits**: Automated research workflows, content discovery
- **Configuration**: HTTP Request nodes configured with SearxNG endpoints

#### Medium-Value Service Dependencies

**7. Backend → Neo4j Integration** ⭐⭐⭐
- **Method**: Neo4j driver integration
- **Implementation**: Built-in graph database connectivity
- **Benefits**: Knowledge graph storage, relationship mapping
- **Configuration**: Add Neo4j driver and connection settings

**8. Open-WebUI → SearxNG Search** ⭐⭐⭐
- **Method**: API integration for web search
- **Implementation**: Built-in search provider configuration
- **Benefits**: Enhanced chat with web search capabilities
- **Configuration**: Configure SearxNG as search provider

**9. n8n → Neo4j Workflows** ⭐⭐⭐
- **Method**: Community nodes for graph operations
- **Implementation**: Install `@n8n/n8n-nodes-neo4j` package
- **Benefits**: Automated graph data management
- **Configuration**: Community package installation + credentials

**10. ComfyUI → Ollama Integration** ⭐⭐⭐
- **Method**: Community nodes for local LLM
- **Implementation**: Custom nodes for Ollama API integration
- **Benefits**: AI-enhanced image generation workflows
- **Configuration**: Custom nodes + Ollama API configuration

#### Lower-Value Dependencies (Nice-to-Have)

**11. Kong → Redis Rate Limiting** ⭐⭐
- **Method**: Built-in Redis plugin configuration
- **Implementation**: Native Kong rate limiting plugin
- **Benefits**: Distributed rate limiting, session management
- **Configuration**:
  ```yaml
  kong-api-gateway:
    environment:
      - KONG_RATE_LIMITING_REDIS_HOST=redis
      - KONG_RATE_LIMITING_REDIS_PORT=6379
  ```

**12. Backend → SearxNG Integration** ⭐⭐
- **Method**: Search API integration
- **Implementation**: HTTP API calls to SearxNG service
- **Benefits**: Enhanced search capabilities in backend services
- **Configuration**: Add SearxNG API endpoints to backend configuration

#### Implementation Strategy

**Phase 1: High-Impact Integrations**
1. ✅ Implement n8n → ComfyUI (community nodes) - COMPLETED
2. ✅ Enable Open-WebUI → Redis caching - COMPLETED ✨ **FEATURE**
3. Configure n8n → Ollama workflows

**Phase 2: Medium-Value Additions**
1. Backend → Neo4j integration
2. Enhanced search integrations
3. Additional n8n workflow capabilities

**Phase 3: Infrastructure Optimizations**
1. Kong → Redis rate limiting
2. SearxNG → Redis caching
3. Cross-service monitoring

#### Benefits of This Approach

- **Built-in Features Only**: No custom code required, only configuration
- **Progressive Enhancement**: Services work independently, better together
- **Maintenance Friendly**: Uses officially supported integration methods
- **Scalable**: Dependencies can be enabled/disabled per deployment
- **Documentation**: All integrations use documented APIs and features

---

### 19.3. ComfyUI Integration 🎨

**Priority**: Medium | **Status**: ✅ Completed | **Complexity**: Low-Medium

**Overview**: ComfyUI has been successfully integrated as an AI image generation service, providing node-based workflow interface for Stable Diffusion and advanced image generation capabilities.

#### Why ComfyUI?
- **Node-based Interface**: Perfect fit with n8n workflow philosophy
- **Advanced AI Image Generation**: Stable Diffusion, ControlNet, and more
- **Workflow Automation**: Can be integrated with n8n for automated image generation
- **Modular Architecture**: Fits well with our service-oriented approach

#### ✅ Implemented Features:
- **Multi-Architecture Support**: CPU (development) and GPU (production) deployment configurations
- **Docker Images**: Uses `ghcr.io/ai-dock/comfyui` with CPU and CUDA variants
- **Service Integration**: Full integration with unified service architecture
- **Port Assignment**: ComfyUI on port 63018 (BASE_PORT + 17)
- **Kong Gateway**: API routing through Kong for security and load balancing
- **Supabase Integration**: Automatic image storage in Supabase Storage
- **Health Checks**: Proper dependency management and service health monitoring
- **OpenWebUI Integration**: Direct image generation from chat interface
- **Backend API**: RESTful endpoints for programmatic image generation
- **n8n Integration**: Workflow automation with webhook support

#### Integration Features:
- **API Integration**: ComfyUI provides REST API for workflow execution
- **n8n Integration**: Create n8n workflows that trigger ComfyUI image generation
- **Model Management**: Shared model storage with other AI services
- **Workflow Library**: Pre-built workflows for common image generation tasks

#### Use Cases:
- **Automated Content Creation**: Generate images for blog posts, reports
- **Dynamic Image Generation**: Create images based on research findings
- **Workflow Chaining**: Research → Content → Images in single n8n workflow
- **A/B Testing**: Generate multiple image variants automatically

#### Configuration:
```bash
# New environment variables
COMFYUI_PORT=63017
ENABLE_COMFYUI=false  # Disabled by default (requires GPU)
COMFYUI_GPU_MEMORY=8  # GPU memory allocation
```

---

### 19.4. Enhanced Service Management 🔧

**Priority**: Medium | **Status**: Planned | **Complexity**: Low

**Overview**: Improve service discovery, health checking, and management capabilities.

#### Planned Improvements:
1. **Service Registry**: Central service discovery mechanism
2. **Health Dashboard**: Real-time service status monitoring  
3. **Resource Monitoring**: CPU, memory, and GPU usage tracking
4. **Auto-scaling**: Dynamic service scaling based on load
5. **Dependency Management**: Smarter service startup ordering

#### Implementation:
- **Consul**: Service discovery and health checking
- **Prometheus + Grafana**: Metrics and monitoring
- **Portainer**: Docker container management UI
- **Watchtower**: Automatic service updates

---

### 19.5. RAG Foundation Preparation 📚

**Priority**: High | **Status**: Planned | **Complexity**: High

**Overview**: Prepare the vanilla stack to serve as a foundation for RAG (Retrieval-Augmented Generation) implementations including GraphRAG, LightRAG, and Agentic RAG.

#### Database Schema Extensions:
```sql
-- RAG-specific tables (planned)
CREATE TABLE rag_documents (
    id UUID PRIMARY KEY,
    content TEXT,
    embeddings VECTOR(1536),
    metadata JSONB
);

CREATE TABLE rag_entities (
    id UUID PRIMARY KEY, 
    name TEXT,
    entity_type TEXT,
    embeddings VECTOR(1536)
);

CREATE TABLE rag_relationships (
    source_entity_id UUID,
    target_entity_id UUID,
    relationship_type TEXT,
    weight FLOAT
);
```

#### Service Extensions:
- **Text Processing Endpoints**: Entity extraction, relationship mapping
- **Embedding Service**: Unified embedding generation API
- **Graph Processing**: Community detection, graph traversal
- **Memory Management**: Agent memory systems for Agentic RAG

---

### 19.6. Developer Experience Improvements 🛠️

**Priority**: Medium | **Status**: Planned | **Complexity**: Low

#### Planned Enhancements:
1. **Development Templates**: Quick-start templates for common use cases
2. **CLI Tools**: Enhanced command-line interface for stack management
3. **Hot Reload**: Development mode with automatic service reloading
4. **Testing Framework**: Automated testing for all service integrations
5. **Documentation Generator**: Auto-generated API documentation

## 20. Completed Integrations

### 20.1 Supabase Realtime ✅

**Status**: Fully integrated and operational

**Implementation Details**:
- ✅ Added `supabase/realtime:v2.33.72` service to all Docker Compose flavors
- ✅ Configured `wal_level=logical` for PostgreSQL logical replication
- ✅ Created dedicated replication slot (`supabase_realtime_slot`)
- ✅ Exposed `/realtime/v1` endpoint via Kong API Gateway
- ✅ Added required database extensions (`pgcrypto`) and schema (`realtime`)
- ✅ Configured proper service dependencies and environment variables
- ✅ Updated port assignments and documentation

**Features Available**:
- Real-time database change notifications via WebSocket
- Presence channels for tracking online users
- Broadcast messaging between clients
- Row-Level Security (RLS) enforcement for secure channels
- Integration with existing JWT authentication system

**Access Points**:
- WebSocket: `ws://localhost:${KONG_HTTP_PORT}/realtime/v1/websocket`
- Direct API: `http://localhost:${SUPABASE_REALTIME_PORT}`

> This integration enables live data synchronization without polling, providing a foundation for real-time features in Open Web UI, backend services, and future frontend applications.

### 20.2 n8n → ComfyUI Integration ✅
**Status**: Fully integrated and operational
**Implementation Details**:
- ✅ Created n8n-init service for automatic community node installation
- ✅ Installed `n8n-nodes-comfyui` for direct ComfyUI workflow execution
- ✅ Installed `@ksc1234/n8n-nodes-comfyui-image-to-image` for image transformations
- ✅ Installed `n8n-nodes-mcp` for Model Context Protocol integration
- ✅ Configured environment variables for community package support
- ✅ Added to unified Docker Compose with proper service dependencies
- ✅ Backend service waits for n8n-init completion before starting
**Features Available**:
- Direct n8n → ComfyUI workflow execution
- Automated image generation pipelines
- Batch image processing capabilities
- Integration with other stack services
- Configurable community node installation
**Configuration**:
- `N8N_COMMUNITY_PACKAGES_ENABLED=true` - Enables community packages
- `N8N_COMMUNITY_PACKAGES_ALLOW_TOOL_USAGE=true` - Allows tool usage
- `N8N_INIT_NODES` - Configurable list of nodes to install
> This integration enables n8n to trigger ComfyUI workflows directly, creating powerful automated image generation and processing pipelines that integrate seamlessly with the rest of the stack.

### 20.3 Open-WebUI → Redis Integration ✅ **FEATURE**
**Status**: ✨ **RESOLVED** - Fully integrated and operational (Previously TODO item)
**Implementation Details**:
- ✅ Added Redis dependency to all Open-WebUI services
- ✅ Configured WebSocket Redis management for real-time features
- ✅ Implemented model list caching with configurable TTL
- ✅ Set up dedicated Redis database (DB 2) to avoid conflicts
- ✅ Added environment variables for Redis WebSocket integration
- ✅ Updated unified Docker Compose with Redis WebSocket configuration
**Features Available**:
- Real-time WebSocket communication via Redis
- Model list caching (5-minute TTL by default)
- Multi-tab session synchronization
- Presence indicators for online users
- Reduced API calls to Ollama and external providers
**Configuration**:
- `ENABLE_WEBSOCKET_SUPPORT=true` - Enables WebSocket features
- `WEBSOCKET_MANAGER=redis` - Uses Redis for WebSocket management  
- `WEBSOCKET_REDIS_URL=redis://:password@redis:6379/2` - Redis connection
- `REDIS_KEY_PREFIX=openwebui` - Namespace for Redis keys
- `MODEL_LIST_CACHE_TTL=300` - Cache duration for model lists (seconds)
**Redis Database Allocation**:
- Database 0: Backend services, n8n queues
- Database 1: SearxNG search caching
- Database 2: Open-WebUI WebSocket management (NEW)
> This integration enables real-time chat features and improves performance through caching, providing a foundation for advanced multi-user capabilities.

### 20.4 Local Deep Researcher ✅

**Status**: Fully integrated and operational

**Implementation Details**:
- ✅ Added `local-deep-researcher` service to all Docker Compose flavors (default, ai-local, ai-gpu)
- ✅ Built custom Docker container with LangGraph CLI and uv package management
- ✅ Implemented database-driven configuration that queries `public.llms` table for active models
- ✅ Created initialization scripts for dynamic LLM detection and runtime configuration
- ✅ Added proper service dependencies (supabase-db-init, ollama-pull)
- ✅ Configured health checks and restart policies
- ✅ Updated port assignments and environment variables
- ✅ Added persistent volume for research data storage

**Features Available**:
- AI-powered web research with configurable depth and search backends
- Automatic LLM model detection from database with Ollama preference
- LangGraph-based workflow orchestration for complex research tasks
- Configurable search APIs (DuckDuckGo default) and research iteration loops
- Persistent storage for research findings and workflow data
- Multi-deployment support (containerized/local/GPU-accelerated Ollama)

**Access Points**:
- Web Interface: `http://localhost:${LOCAL_DEEP_RESEARCHER_PORT}` (default: 55679)
- LangGraph Server: Internal port 2024, exposed via configured port
- Research Data: Stored in `local-deep-researcher-data` Docker volume

**Configuration**:
- Environment variables: `LOCAL_DEEP_RESEARCHER_LOOPS`, `LOCAL_DEEP_RESEARCHER_SEARCH_API`
- Database integration: Automatic query of `public.llms` table for model selection
- Fallback configuration: llama3.2 model if no active models detected

> This integration provides advanced AI research capabilities, enabling automated multi-source web research with intelligent model selection and persistent result storage.

### 20.3 ComfyUI Integration ✅

**Status**: Fully integrated and operational

**Implementation Details**:
- ✅ Added `comfyui` service to all Docker Compose flavors (ai.yml, ai-local.yml, ai-gpu.yml)
- ✅ Multi-architecture support with CPU and CUDA variants
- ✅ Proper service dependencies (supabase-db-init, ollama-pull, supabase-storage, redis)
- ✅ Kong API Gateway routing for secure API access
- ✅ Supabase Storage integration for generated images
- ✅ Health checks and service monitoring
- ✅ Updated port assignments (BASE_PORT + 17)
- ✅ Environment variable configuration
- ✅ Persistent volumes for models and outputs

**Features Available**:
- Node-based workflow interface for AI image generation
- Support for multiple AI models (SDXL, SD 1.5, ControlNet, LoRA)
- RESTful API endpoints for programmatic access
- WebSocket support for real-time progress updates
- Automatic image storage in Supabase Storage
- OpenWebUI integration for chat-based image generation
- n8n workflow automation support
- Backend API integration for custom applications

**Access Points**:
- Web Interface (Containerized): `http://localhost:${COMFYUI_PORT}` (default: 63018)
- Web Interface (Local/localhost SOURCE configuration): `http://localhost:8000`
- Kong Gateway: `http://localhost:${KONG_HTTP_PORT}/comfyui/` (works for both containerized and local)
- API Endpoints: `/prompt`, `/history`, `/view`, `/system_stats`
- Model Storage: `comfyui-models` Docker volume
- Generated Images: `comfyui-output` Docker volume

**Configuration**:
- Environment variables: `COMFYUI_ARGS`, `COMFYUI_AUTO_UPDATE`, `COMFYUI_UPLOAD_TO_SUPABASE`
- Image variants: CPU (`v2-cpu-22.04-v0.2.7`) and GPU (`latest-cuda`)
- Storage integration: Automatic upload to Supabase Storage bucket
- Model management: Persistent volumes for checkpoints, VAE, LoRA, and custom nodes

> This integration provides comprehensive AI image generation capabilities with seamless workflow automation, storage management, and cross-service integration.

### 20.4 Deep Researcher Integration ✅

**Status**: Fully integrated with dynamic LLM selection and Pipe-based Open-WebUI interface

**Overview**: The Deep Researcher integration provides comprehensive AI-powered web research capabilities with database-driven model selection, accessible through multiple interfaces including a modern Pipe function in Open-WebUI.

#### Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Open-WebUI    │    │      n8n        │    │   External      │
│  (Pipe Interface)│    │   Workflows     │    │   Applications  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          │ Pipe Function        │ HTTP Requests        │ REST API
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼───────────┐
                    │     Backend API         │
                    │   (FastAPI Service)     │
                    └─────────────┬───────────┘
                                  │ HTTP Client
                                  │
                    ┌─────────────▼───────────┐
                    │ Local Deep Researcher   │◄──────┐
                    │   (LangGraph Service)   │       │
                    └─────────────┬───────────┘       │ Config
                                  │                    │
          ┌───────────────────────┼────────────────────┼───────┐
          │                       │                    │       │
    ┌─────▼─────┐       ┌─────────▼────────┐    ┌────▼────┐  │
    │ Supabase  │       │     Ollama       │◄───│ Ollama  │  │
    │ Database  │       │   AI Models      │    │  Pull   │  │
    │  + llms   │       │  (qwen3:latest)  │    │ Service │  │
    │   table   │       └──────────────────┘    └─────────┘  │
    └───────────┘                                             │
          │                                                   │
          └───────────────────────────────────────────────────┘
                        Model Configuration Flow
```

#### Components

**1. Database Layer (Supabase)**

**Research Tables**:
- `research_sessions`: Track research requests and status
- `research_results`: Store completed research findings
- `research_sources`: Individual sources and references
- `research_logs`: Step-by-step research process logs

**LLM Configuration Table**:
- `llms`: Manages available AI models
  - `active`: Whether the model is available for use
  - `content`: Whether the model can be used for research content generation
  - `provider`: Model provider (e.g., ollama, openai)
  - `name`: Model identifier (e.g., qwen3:latest)

**Key Features**:
- Row Level Security (RLS) for user data isolation
- Automatic timestamps and status tracking
- Comprehensive audit trail
- Integration with existing user management
- Dynamic model configuration

**2. Backend API (FastAPI)**

**Research Endpoints**:
- `POST /research/start` - Start new research session
- `GET /research/{session_id}/status` - Check research progress
- `GET /research/{session_id}/result` - Get completed results
- `POST /research/{session_id}/cancel` - Cancel running research
- `GET /research/{session_id}/logs` - Get detailed process logs
- `GET /research/sessions` - List user research history
- `GET /research/health` - Service health check

**Features**:
- Async task management for long-running research
- Comprehensive error handling and validation
- Database persistence and session tracking
- Health monitoring and diagnostics

**3. n8n Workflow Integration**

**Pre-built Workflows**:

1. **Simple Research** (`research-simple.json`)
   - Single query research via webhook
   - Automatic result retrieval
   - Webhook: `/webhook/research-trigger`

2. **Batch Research** (`research-batch.json`)
   - Multiple query processing
   - Consolidated results
   - Webhook: `/webhook/batch-research`

3. **Scheduled Research** (`research-scheduled.json`)
   - Automated weekly research reports
   - Configurable topics and schedules
   - Report generation and storage

**4. Open-WebUI Integration (Pipe Function)**

The Deep Researcher is integrated as a **Pipe function** in Open-WebUI, providing a seamless research experience:

**Deep Researcher Pipe** (`deep_researcher_pipe.py`):
- **Type**: Pipe function (appears in model dropdown)
- **Name**: "Deep Researcher 🔍"
- **Features**:
  - Real-time progress updates during research
  - Formatted results with sources and metadata
  - Configurable settings via Valves
  - Async operation with event emitters

**Key Capabilities**:
- Comprehensive web research on any topic
- Dynamic status updates (loops, sources found)
- Structured output with summary, findings, and sources
- Uses database-configured LLM (qwen3:latest by default)

**Important Note**: The Deep Researcher uses its own LLM configuration from the database, not the model selected in Open-WebUI's main interface

**5. API Gateway (Kong)**

**Research API Routes**:
- External access via `/research/` path
- Rate limiting (30/minute, 500/hour)
- CORS support for web applications
- Optional API key authentication

#### Dynamic LLM Selection

The Local Deep Researcher uses a database-driven approach for selecting which LLM model to use for research:

**How It Works**

1. **Database Configuration**:
   - Models are stored in the `llms` table in Supabase
   - Each model has flags: `active` (boolean), `content`, `embeddings`, `vision`, `structured_content` (integer priorities)
   - The Deep Researcher uses models marked with `active = true` AND `content > 0` (priority-based selection)

2. **Automatic Model Selection**:
   ```
   Database Query → Active Content Model → Configuration → Deep Researcher
   ```
   - On startup, `init-config.py` queries the database
   - Prefers Ollama providers (for local inference)
   - Creates runtime configuration with selected model
   - Default: `qwen3:latest` (not llama3.2)

3. **Model Pull Process**:
   - The `ollama-pull` service automatically pulls all active Ollama models
   - Runs before Deep Researcher starts
   - Ensures models are available locally

**Current Default Model**

Based on the seed data, the default model is:
- **Model**: `qwen3:latest`
- **Provider**: ollama
- **Features**: 100+ language support, strong reasoning capabilities
- **Context Window**: 40,000 tokens

**Changing the Research Model**

To use a different model for research:

1. **Add the model to the database**:
   ```sql
   INSERT INTO public.llms (name, provider, active, content, description)
   VALUES ('llama3.2', 'ollama', true, true, 'Meta Llama 3.2 model');
   ```

2. **Deactivate the current model** (optional):
   ```sql
   UPDATE public.llms 
   SET active = false 
   WHERE name = 'qwen3:latest' AND content > 0;
   ```

3. **Restart the services**:
   ```bash
   docker compose restart ollama-pull local-deep-researcher
   ```

The system will automatically:
- Pull the new model via ollama-pull
- Configure Deep Researcher to use it
- Apply the change to all research operations

#### Open-WebUI Usage

The Deep Researcher is now available as a Pipe function in Open-WebUI:

**Using the Deep Researcher**

1. **Select the Deep Researcher**:
   - Open the model dropdown in Open-WebUI
   - Select "Deep Researcher 🔍"
   - The interface will switch to use the research pipe

2. **Perform Research**:
   - Simply type your research question
   - No special commands or formatting needed
   - Watch real-time progress updates

**Example Interactions**

**Basic Research**:
```
User: What are the latest cybersecurity threats in 2024?

Deep Researcher 🔍: [Shows progress: 🔍 Researching... Loop 1/3 | Sources found: 5]
[After completion, displays formatted research report with summary, findings, and sources]
```

**Complex Research**:
```
User: Compare the features, pricing, and performance of AWS, Azure, and Google Cloud for machine learning workloads

Deep Researcher 🔍: [Shows progress updates throughout the research process]
[Returns comprehensive comparison with multiple sources]
```

**Configuring the Pipe (Admin Only)**

1. Navigate to Workspace → Functions
2. Find "Deep Researcher Pipe"
3. Click the gear icon
4. Adjust settings:
   - `backend_url`: Backend service URL
   - `timeout`: Maximum research time (seconds)
   - `max_loops`: Research depth (1-6)
   - `show_status`: Enable/disable progress updates

**Important Notes**

- The Deep Researcher uses the model configured in the database (qwen3:latest by default)
- It does NOT use the model you might have selected before switching to Deep Researcher
- Research depth and quality depend on the `max_loops` setting
- All research is persisted in the database for future reference

#### Configuration

**Environment Variables**

**Backend Service**:
- `DATABASE_URL`: PostgreSQL connection string
- `LOCAL_DEEP_RESEARCHER_URL`: Research service endpoint (default: `http://local-deep-researcher:2024`)
- `BACKEND_PORT`: API service port (default: 63016)

**Local Deep Researcher**:
- `LOCAL_DEEP_RESEARCHER_PORT`: Service port (default: 63013)
- `LOCAL_DEEP_RESEARCHER_LOOPS`: Default research iterations (default: 3)
- `LOCAL_DEEP_RESEARCHER_SEARCH_API`: Search engine (default: duckduckgo)
- `OLLAMA_BASE_URL`: Ollama service URL (set automatically to `http://ollama:11434`)
- `DATABASE_URL`: PostgreSQL connection for model configuration

**Model Configuration** (via Database):
- `LOCAL_LLM`: Dynamically set from llms table (default: qwen3:latest)
- `LLM_PROVIDER`: Dynamically set from llms table (default: ollama)

**Open-WebUI**:
- `OPEN_WEB_UI_PORT`: Web interface port (default: 63015)
- `OPEN_WEB_UI_SECRET_KEY`: Session encryption key

#### LLM Configuration

The Deep Researcher's LLM selection is entirely database-driven, providing flexibility and easy management:

**Understanding the LLM Table**

The `llms` table structure:
```sql
CREATE TABLE public.llms (
  id bigint PRIMARY KEY,
  active boolean NOT NULL DEFAULT false,
  vision integer NOT NULL DEFAULT 0,
  content integer NOT NULL DEFAULT 0,
  structured_content integer NOT NULL DEFAULT 0,
  embeddings integer NOT NULL DEFAULT 0,
  provider varchar NOT NULL,
  name varchar NOT NULL UNIQUE,
  description text,
  size_gb numeric,
  context_window integer,
  api_key text,
  api_endpoint text,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
```

**Key Schema Updates:**
- **Capability Fields**: Now use `integer` for priority-based selection (0 = not capable, higher = higher priority)
- **API Support**: Added `api_key` and `api_endpoint` columns for external API providers
- **Active Field**: Remains `boolean` for general filtering capability

**Model Selection Logic**

1. **Query Priority**:
   ```sql
   SELECT provider, name FROM public.llms 
   WHERE active = true AND content > 0 
   ORDER BY content DESC, provider = 'ollama' DESC, name
   LIMIT 1;
   ```

2. **Selection Criteria**:
   - Must have `active = true`
   - Must have `content > 0` (for text generation, higher values = higher priority)
   - Prioritizes models with highest `content` score
   - Among equal priorities, prefers `ollama` provider for local inference
   - Falls back to `llama3.2` if no models found

**Managing Research Models**

View Available Models:
```sql
-- See all content-capable models
SELECT name, provider, active, description 
FROM public.llms 
WHERE content > 0;

-- Check current active research model
SELECT name, provider 
FROM public.llms 
WHERE active = true AND content > 0 
ORDER BY content DESC, provider = 'ollama' DESC
LIMIT 1;
```

Add New Models:
```sql
-- Add a new Ollama model
INSERT INTO public.llms (
  name, provider, active, content, 
  description, context_window
) VALUES (
  'llama3.1:70b', 'ollama', true, 10,
  'Large Llama 3.1 model with enhanced capabilities', 128000
);
```

Switch Active Model:
```sql
-- Deactivate current model
UPDATE public.llms 
SET active = false 
WHERE name = 'qwen3:latest';

-- Activate new model
UPDATE public.llms 
SET active = true 
WHERE name = 'llama3.1:70b';
```

**Model Pull Process**

The `ollama-pull` service automatically:
1. Queries the database for all active Ollama models
2. Pulls each model using Ollama's API
3. Ensures models are available before services start

To manually trigger a model pull:
```bash
docker compose restart ollama-pull
```

**API Provider Configuration**

For external API providers (OpenAI, Anthropic, etc.), use the new database-driven configuration:

1. **Set SOURCE to api**:
   ```bash
   # In .env.example:
   LLM_PROVIDER_SOURCE=api
   ```

2. **Configure API providers in database**:
   ```sql
   -- Add OpenAI GPT-4 model
   INSERT INTO public.llms (
     name, provider, active, content, vision, api_key, api_endpoint,
     description, context_window
   ) VALUES (
     'gpt-4o', 'openai', true, 15, 10, 'sk-your-openai-api-key', 'https://api.openai.com/v1',
     'OpenAI GPT-4 Omni with vision capabilities', 128000
   );

   -- Add Anthropic Claude model
   INSERT INTO public.llms (
     name, provider, active, content, api_key, api_endpoint,
     description, context_window
   ) VALUES (
     'claude-3-5-sonnet-20241022', 'anthropic', true, 20, 'sk-ant-your-anthropic-key', 'https://api.anthropic.com',
     'Anthropic Claude 3.5 Sonnet latest version', 200000
   );
   ```

3. **Priority-based Selection**:
   - Higher `content` values = higher priority for text generation
   - Higher `vision` values = higher priority for image analysis
   - Higher `embeddings` values = higher priority for vector embeddings
   - `active = false` excludes models from selection entirely

4. **API Key Security**:
   - API keys are stored securely in the database
   - Use environment variables for sensitive keys when possible
   - Rotate keys regularly and update in database

**Integration with Services**

- **Local Deep Researcher**: Uses `init-config.py` to read model configuration
- **Open-WebUI**: The Pipe function uses the backend API, which connects to the configured model
- **n8n Workflows**: Research workflows use the same backend API

#### Troubleshooting

**Research Service Unavailable**
```bash
# Check service status
docker compose ps local-deep-researcher

# Check logs
docker compose logs local-deep-researcher

# Restart if needed
docker compose restart local-deep-researcher
```

**Model Not Found or Not Loading**
```bash
# Check if model is in database
docker compose exec supabase-db psql -U postgres -d postgres -c \
  "SELECT name, provider, active FROM public.llms WHERE content > 0;"

# Check ollama-pull logs
docker compose logs ollama-pull

# Manually pull a model
docker compose exec ollama ollama pull qwen3:latest

# Restart services to reload configuration
docker compose restart ollama-pull local-deep-researcher
```

**Deep Researcher Not Appearing in Open-WebUI**
1. Check if the pipe function file exists:
   ```bash
   ls -la open-webui/functions/deep_researcher_pipe.py
   ```
2. Restart Open-WebUI to reload functions:
   ```bash
   docker compose restart open-web-ui
   ```
3. Check Open-WebUI logs for function loading errors:
   ```bash
   docker compose logs open-web-ui | grep -i "deep_researcher"
   ```

**Wrong Model Being Used**
```sql
-- Check which model is active
SELECT name, provider FROM public.llms 
WHERE active = true AND content > 0 
ORDER BY content DESC, provider = 'ollama' DESC;

-- If multiple models are active, deactivate unwanted ones
UPDATE public.llms SET active = false 
WHERE name != 'your-preferred-model' AND content > 0;
```

**Model Configuration Not Updating**
1. Ensure init-config.py ran successfully:
   ```bash
   docker compose logs local-deep-researcher | grep -i "config"
   ```
2. Check runtime configuration:
   ```bash
   docker compose exec local-deep-researcher cat /app/config/runtime_config.json
   ```
3. Force reconfiguration:
   ```bash
   docker compose restart local-deep-researcher
   ```

> This integration provides a modern, database-driven research platform with intelligent model selection, real-time status updates, and seamless integration across all services. The Pipe-based Open-WebUI interface offers an intuitive user experience while maintaining the flexibility to use different models and configurations.

#### Tool Integration for Open-WebUI

The Deep Researcher is available as both **Functions** and **Tools** in Open-WebUI for maximum flexibility.

**Integration Types:**
- **Functions**: User-invoked via slash commands (e.g., `/deep_researcher`) - auto-loaded via volume mount
- **Tools**: AI-invoked automatically when models need research capabilities - manual import required

**Manual Tool Setup**

The project includes a Deep Researcher Tool (`open-webui/tools/deep_researcher_tool.py`) that can be imported into Open-WebUI for automatic use by AI models.

**Setup Process (Manual Import Required)**

Tools require one-time manual import via the Open-WebUI admin interface:

```bash
# 1. Start any docker-compose flavor
docker compose up -d
# Functions work immediately, tools require manual import

# 2. Import tools via Open-WebUI admin interface (see steps below)
```

**Import Steps:**
1. Access Open-WebUI at `http://localhost:${OPEN_WEB_UI_PORT}`
2. Go to **Admin Panel** → **Tools**
3. Click **"+"** to add a new tool
4. Copy contents of `open-webui/tools/deep_researcher_tool.py`
5. Paste into the tool editor
6. Click **Save**

**Enable Tool for AI Models**

After importing the tool:

1. Go to **Admin Panel** → **Models**
2. Select a model (e.g., your default LLM) and click **Edit**
3. Find **"Deep Researcher Tool"** in the Tools section
4. **Toggle it ON** to enable it for that model
5. Click **Save** to confirm changes

**Using the Tool in Conversations**

Once enabled, the AI can automatically use the tool when appropriate:

```
User: "What are the latest developments in quantum computing?"
AI: [Automatically calls research_web tool] Based on my research, here are the latest developments...

User: "Research the current state of renewable energy adoption"
AI: [Calls research_web tool] I'll research that for you...
```

**Tool Configuration**

The tool can be configured via the Valves interface:
- `backend_url`: Backend service URL (default: http://backend:8000)
- `timeout`: Maximum research time (default: 300 seconds)
- `poll_interval`: Status check interval (default: 5 seconds)
- `default_max_loops`: Default research depth (default: 3)
- `default_search_api`: Default search engine (default: duckduckgo)
- `enable_tool`: Enable/disable the tool (default: true)

**Tool Troubleshooting**

**If manual tool import fails:**
```bash
# Check if tool was imported successfully
docker exec -it ${PROJECT_NAME}-open-web-ui sqlite3 /app/backend/data/webui.db "SELECT name FROM tool;"

# Check Open-WebUI logs for errors
docker logs ${PROJECT_NAME}-open-web-ui | grep -i "error"

# Verify tool file syntax before importing
python -m py_compile open-webui/tools/deep_researcher_tool.py
```

**If AI doesn't use the tool when expected:**
1. Verify tool is enabled in Admin Panel → Models → [Model] → Tools
2. Check that the tool was successfully imported via Admin Panel → Tools
3. Try being more explicit: "Please research..." or "Can you look up..."
4. Check tool configuration in the Valves section

**Development Notes**

- **Architecture**: Shared modules in `open-webui/shared/` eliminate code duplication
- **Database**: Tools stored in Open-WebUI's SQLite database at `/app/backend/data/webui.db`
- **Tool Files**: Located in `open-webui/tools/` directory  
- **Function Files**: Located in `open-webui/functions/` directory
- **Configuration**: Auto-enablement controlled by `open-webui/tool_config.json`
- **LLM Selection**: Research uses database-configured LLM, not the chat model
- **Status Updates**: Tools support real-time progress updates during research operations

### 20.5 n8n → Redis Queue Management ✅

**Status**: Fully integrated and operational

**Implementation Details**:
- ✅ Added Redis dependency to n8n service in unified Docker Compose
- ✅ Configured n8n with `EXECUTIONS_MODE=queue` for queue-based execution
- ✅ Set up Bull queue management using Redis database 0
- ✅ Added proper health check conditions for service startup order
- ✅ Resolved "Connection Lost" error when accessing n8n through Kong proxy
- ✅ Implemented WebSocket backend support for real-time features

**Technical Configuration**:
- Queue backend: Bull (Redis-based queue library)
- Redis connection: `QUEUE_BULL_REDIS_HOST=redis`
- Database allocation: Redis DB 0 (shared with backend services)
- Push backend: WebSocket (switched from SSE for bidirectional communication)

**Kong Proxy Fix Details**:
- Added `preserve_host: true` to Kong n8n route configuration
- Removed invalid WebSocket protocol configurations that caused Kong startup failures
- Kong now properly proxies WebSocket connections for n8n's real-time features

**Benefits Achieved**:
- Reliable workflow execution with queue management
- Improved scalability for concurrent workflow processing
- Real-time workflow status updates through WebSocket
- Proper service dependency management preventing startup failures
- Seamless access through Kong proxy without connection issues

> This integration transformed n8n from a single-process execution model to a scalable, queue-based system with proper Redis dependency management and full Kong proxy support.

### 20.6 SearxNG → Redis Caching ✅

**Status**: Fully integrated and operational

**Implementation Details**:
- ✅ SearxNG already configured with Redis caching in `settings.yml`
- ✅ Added formal Docker dependency (`depends_on: redis`) to unified compose file
- ✅ Configured to use Redis database 1 for search result caching
- ✅ Updated architecture diagram to show caching relationship
- ✅ Verified Redis connection and caching functionality

**Technical Configuration**:
```yaml
redis:
  url: redis://:redis_password@redis:6379/1
```

**Features Available**:
- Cached search results for improved performance
- Reduced external API calls to search providers
- Configurable cache TTL for different search types
- Automatic cache invalidation for stale results

**Benefits Achieved**:
- Faster search response times for repeated queries
- Reduced load on external search providers
- Better reliability during external API outages
- Resource optimization through intelligent caching

> This integration enhances SearxNG's performance by leveraging Redis for intelligent search result caching, providing faster responses and reducing external dependencies.

## 21. Future Enhancements: Docker MCP Servers Integration

### 21.1. Overview

The [Docker MCP (Model Context Protocol) Servers](https://github.com/docker/mcp-servers) project represents a significant opportunity to enhance our GenAI stack with standardized, secure AI-tool integration capabilities. MCP provides a unified protocol for Large Language Models to interact with external tools and data sources in a controlled, secure manner.

### 21.2. Integration Benefits

**Enhanced AI Capabilities**:
- **Structured Data Access**: Enable Ollama models to interact with databases through standardized protocols
- **Secure Tool Integration**: Sandboxed execution environment with resource limits (1 CPU, 2GB RAM)
- **Open-WebUI Enhancement**: Extend tool capabilities beyond current research functions

**Stack-Specific Advantages**:
- **PostgreSQL MCP Server**: Direct, secure Supabase database queries for AI models
- **Redis MCP Server**: Enhanced Redis operations beyond basic caching
- **Neo4j MCP Server**: Advanced graph database queries and schema inspection
- **Search Integration**: Complement SearxNG with additional search capabilities

### 21.3. Recommended MCP Servers for Integration

**Database Servers** (High Priority):
1. **PostgreSQL MCP Server**: 
   - Direct integration with existing Supabase PostgreSQL
   - Schema inspection and read-only database access
   - Enhanced AI-driven database queries

2. **Redis MCP Server**:
   - Advanced Redis operations beyond current caching
   - Key-value store interactions for AI workflows

3. **Neo4j MCP Server**:
   - Graph database queries and schema management
   - Enhanced relationship analysis capabilities

**Search & Content Servers** (Medium Priority):
1. **Tavily Search**: AI-optimized search with extraction capabilities
2. **Meilisearch**: Full-text and semantic search API integration
3. **Chroma**: Vector embeddings and document storage

**Development & Integration Servers** (Low Priority):
1. **Docker MCP Server**: Container and image management
2. **Kubernetes MCP Server**: Orchestration and deployment management

### 21.4. Implementation Architecture

**Proposed Service Structure**:
```yaml
mcp-gateway:
  image: docker/mcp-gateway:latest
  container_name: ${PROJECT_NAME}-mcp-gateway
  depends_on:
    - supabase-db
    - redis
    - neo4j-graph-db
  environment:
    - MCP_SERVERS=postgresql,redis,neo4j
    - POSTGRES_URL=${DATABASE_URL}
    - REDIS_URL=${REDIS_URL}
    - NEO4J_URL=bolt://neo4j-graph-db:7687
  ports:
    - "${MCP_GATEWAY_PORT}:8080"
```

**Integration Points**:
- **Open-WebUI**: MCP servers as additional tool providers
- **Backend API**: Structured AI-database interactions
- **Deep Researcher**: Enhanced data access and analysis
- **Kong Gateway**: Secure routing to MCP services

### 21.5. Security Considerations

**Built-in Security Features**:
- **Container Isolation**: Each MCP server runs in sandboxed environment
- **Resource Limits**: CPU and memory restrictions prevent resource abuse
- **Access Control**: Explicit filesystem and network permissions
- **OAuth Support**: Secure credential management without hardcoded secrets
- **Digital Signatures**: All MCP server images digitally signed by Docker

**Implementation Security**:
- **Environment Variable Management**: Secure credential passing via Docker secrets
- **Network Isolation**: Dedicated Docker network for MCP communications
- **Kong Integration**: API gateway for secure external access

### 21.6. Development Roadmap

**Phase 1: Foundation** (4-6 weeks):
- [ ] Add MCP Gateway service to unified Docker Compose
- [ ] Integrate PostgreSQL MCP server with Supabase
- [ ] Configure basic security and networking
- [ ] Update environment variable management

**Phase 2: Core Integration** (6-8 weeks):
- [ ] Add Redis and Neo4j MCP servers
- [ ] Integrate MCP servers with Open-WebUI tool system
- [ ] Enhance Backend API with MCP-powered endpoints
- [ ] Implement Kong Gateway routing for MCP services

**Phase 3: Advanced Features** (8-10 weeks):
- [ ] Add search and content MCP servers
- [ ] Implement vector embedding and semantic search
- [ ] Create custom MCP servers for stack-specific needs
- [ ] Optimize performance and resource utilization

**Phase 4: Production Readiness** (4-6 weeks):
- [ ] Comprehensive security audit and hardening  
- [ ] Performance optimization and scaling
- [ ] Documentation and operational procedures
- [ ] Integration testing across all SOURCE configurations

### 21.7. Expected Outcomes

**Enhanced AI Capabilities**:
- Structured, secure database access for AI models
- Advanced search and content analysis capabilities
- Improved research quality and data integration

**Developer Experience**:
- Standardized protocol for AI-tool integration
- Simplified tool development and deployment
- Consistent security and access control patterns

**System Architecture**:
- Modular, extensible AI tooling framework
- Enhanced observability and debugging capabilities
- Future-proof integration patterns for emerging AI tools

### 21.8. Next Steps

1. **Feasibility Study**: Detailed technical assessment of MCP server integration requirements
2. **Prototype Development**: Basic PostgreSQL MCP server integration
3. **Security Review**: Comprehensive security architecture evaluation
4. **Performance Testing**: Resource utilization and scaling analysis
5. **Implementation Planning**: Detailed project timeline and resource allocation

This integration would position the GenAI Vanilla Stack as a cutting-edge, production-ready platform for AI-powered applications with enterprise-grade security and extensibility.

