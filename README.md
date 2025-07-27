# GenAI Vanilla Stack

A flexible, modular GenAI project boilerplate with customizable services.

This project provides a solid foundation for building GenAI applications with a focus on modularity, allowing developers to swap components or connect to external services as needed. It supports both local development and production deployment with GPU acceleration.

![Architecture Diagram](./docs/images/architecture.png)

## 1. Project Overview

GenAI Vanilla Stack is a customizable multi-service architecture for AI applications, featuring:

- Multiple deployment flavors using standalone Docker Compose files
- Modular service architecture with interchangeability between containerized and external services
- Support for local development and cloud deployment (AWS ECS compatible)
- Key services including Supabase (PostgreSQL + Meta + Auth + Storage + Studio), Neo4j, Redis, Ollama, FastAPI backend, and Kong API Gateway

## 2. Features

- **2.1. API Gateway (Kong)**: Centralized API management, authentication, and routing for backend services.
- **2.2. Real-time Data Synchronization**: Live database change notifications via Supabase Realtime WebSocket connections.
- **2.3. Flexible Service Configuration**: Switch between containerized services or connect to existing external endpoints by using different Docker Compose profiles (e.g., `ai-local` for local Ollama, `ai-gpu` for GPU support).
- **2.4. Multiple Deployment Profiles**: Choose different service combinations with modular Docker Compose profile files
- **2.5. Cloud Ready**: Designed for seamless deployment to cloud platforms like AWS ECS
- **2.6. Environment-based Configuration**: Easy configuration through environment variables
- **2.7. Explicit Initialization Control**: Uses a dedicated `supabase-db-init` service to manage custom database setup after the base database starts.

## 3. Getting Started

### 3.1. Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development)
- UV package manager (optional, for Python dependency management)

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

### 3.2. Quick Start with Local AI Services

For users who want to use their own local Ollama installation:

1. **Install and start Ollama:**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama serve
   # In another terminal:
   ollama pull llama3.2
   ```

2. **Start the stack:**
   ```bash
   ./start.sh --profile ai-local
   ```

3. **Access services:**
   - Open-WebUI: http://localhost:63015
   - Backend API: http://localhost:63016/docs
   - The stack will use your local Ollama for all AI operations

### 3.3. Running the Stack

#### Using Convenience Scripts (Recommended)

The project includes cross-platform scripts that simplify starting and stopping the stack:

```bash
# Start the stack with default settings (all services)
./start.sh

# Start with a custom base port (all service ports will be incremented from this base)
./start.sh --base-port 64000

# Start with a specific deployment profile
./start.sh --profile ai-local

# Combine options
./start.sh --base-port 64000 --profile ai-gpu

# Stop the stack and clean up resources
./stop.sh

# Stop a specific profile
./stop.sh --profile ai-gpu
```

**Available Profiles:**
- `default`: Complete stack with containerized Ollama (CPU-based)
- `ai-local`: Complete stack using local Ollama and ComfyUI installations on host machine (requires pre-installed Ollama on port 11434 and optionally ComfyUI on port 8000)
- `ai-gpu`: Complete stack with GPU-accelerated containerized Ollama

#### Prerequisites for AI-Local Profile

To use the `ai-local` profile, you need to have Ollama installed and running on your host machine:

**Install Ollama:**
- **macOS/Linux**: `curl -fsSL https://ollama.com/install.sh | sh`
- **Windows**: Download from [ollama.com/download](https://ollama.com/download)

**Start Ollama:**
```bash
# Verify Ollama is installed
ollama --version

# Start Ollama service (if not already running)
ollama serve

# Pull required models (in another terminal)
ollama pull llama3.2
ollama pull qwen2.5:latest
```

**Verify Ollama is accessible:**
```bash
curl http://localhost:11434/api/tags
```

The ai-local profile expects Ollama to be running on `http://localhost:11434`.

#### Manual Docker Compose Commands (Alternative)

You can also use Docker Compose commands directly with the new profile structure:

```bash
# First, make sure all previous services are stopped to avoid port conflicts
docker compose --env-file=.env down --remove-orphans

# Start with default profile (all services, containerized Ollama)
docker compose -f docker-compose.yml -f compose-profiles/data.yml -f compose-profiles/ai.yml -f compose-profiles/apps.yml --env-file=.env up

# Start with ai-local profile (local Ollama)
docker compose -f docker-compose.yml -f compose-profiles/data.yml -f compose-profiles/ai-local.yml -f compose-profiles/apps-local.yml --env-file=.env up

# Start with ai-gpu profile (GPU Ollama)
docker compose -f docker-compose.yml -f compose-profiles/data.yml -f compose-profiles/ai-gpu.yml -f compose-profiles/apps-gpu.yml --env-file=.env up

# Build services for a specific profile
docker compose -f docker-compose.yml -f compose-profiles/data.yml -f compose-profiles/ai.yml -f compose-profiles/apps.yml --env-file=.env build

# Recommended: Use start.sh script instead for easier profile management
./start.sh --profile ai-local
```

### 3.4. Convenience Scripts

The project includes two cross-platform scripts to simplify deployment and port management:

#### start.sh

This script provides a streamlined way to start the stack with configurable ports and deployment profiles:

```bash
Usage: ./start.sh [options]
Options:
  --base-port PORT   Set the base port number (default: 63000)
  --profile PROFILE  Set the deployment profile (default: default)
                     Supported profiles: default, ai-local, ai-gpu
  --cold             Force creation of new .env file and generate new keys
  --help             Show this help message
```

The script automatically:
1. Checks if `.env` exists, and if not, creates one from `.env.example` and generates Supabase keys
2. Generates a new `.env` file with incremented port numbers based on the specified base port
3. Preserves all non-port-related environment variables and comments from the source `.env` file
4. Backs up your existing `.env` file with a timestamp (e.g., `.env.backup.YYYYMMDDHHMMSS`)
5. Displays a detailed port assignment table for all services
6. Explicitly uses the `.env` file when starting Docker Compose to ensure port settings are applied consistently
7. Starts the appropriate Docker Compose configuration

**First-time Setup:**
When running for the first time, the script will automatically:
- Create the `.env` file from `.env.example`
- Run `generate_supabase_keys.sh` to generate required JWT keys
- Set all port numbers based on the specified base port

**Cold Start Option:**
Use the `--cold` option to force a complete reset of the environment:
```bash
./start.sh --cold
```
This will:
- Back up your existing `.env` file with a timestamp
- Create a fresh `.env` file from `.env.example`
- Generate new Supabase keys
- Set all port numbers based on the specified base port
- Remove Docker volumes if specified

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
- OLLAMA_PORT = BASE_PORT + 12
- LOCAL_DEEP_RESEARCHER_PORT = BASE_PORT + 13
- SEARXNG_PORT = BASE_PORT + 14
- OPEN_WEB_UI_PORT = BASE_PORT + 15
- BACKEND_PORT = BASE_PORT + 16
- N8N_PORT = BASE_PORT + 17
- COMFYUI_PORT = BASE_PORT + 18

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

This script stops the stack and cleans up resources:

```bash
Usage: ./stop.sh [options]
Options:
  --profile PROFILE  Set the deployment profile (default: default)
                     Supported profiles: default, ai-local, ai-gpu
  --cold             Remove volumes (data will be lost)
  --help             Show this help message
```

The script:
1. Stops all containers in the specified profile
2. Removes orphaned containers
3. Preserves data volumes by default

**Cold Stop Option:**
Use the `--cold` option to perform a complete cleanup including volumes:
```bash
./stop.sh --cold
```
This will:
- Stop all containers in the specified profile
- Remove all volumes (all data will be lost)
- Remove orphaned containers

This is useful when you want to start completely fresh, but be careful as all database data will be lost.

## 4. Quick Access Guide

Once the stack is running, you can access services at the following URLs:

### Main Services
- **Supabase Studio**: `http://localhost:${SUPABASE_STUDIO_PORT}` (default: 63009)
- **Neo4j Dashboard**: `http://localhost:${GRAPH_DB_DASHBOARD_PORT}` (default: 63011)
- **SearxNG Privacy Search**: `http://localhost:${SEARXNG_PORT}` (default: 63014)
- **Open-WebUI**: `http://localhost:${OPEN_WEB_UI_PORT}` (default: 63015)
- **n8n Workflow Automation**: 
  - Direct: `http://localhost:${N8N_PORT}` (default: 63017)
  - Via Kong: `http://localhost:${KONG_HTTP_PORT}/n8n/` (default: 63002/n8n/)
- **ComfyUI Image Generation**:
  - Containerized: `http://localhost:${COMFYUI_PORT}` (default: 63018)
  - Local (ai-local profile): `http://localhost:8000`
  - Via Kong: `http://localhost:${KONG_HTTP_PORT}/comfyui/` (default: 63002/comfyui/)

### API Endpoints
- **Backend API**: `http://localhost:${BACKEND_PORT}` (default: 63016)
- **Research API**: `http://localhost:${BACKEND_PORT}/research/`
- **Kong API Gateway**: `http://localhost:${KONG_HTTP_PORT}` (default: 63002)

### Database Services
- **PostgreSQL**: `localhost:${SUPABASE_DB_PORT}` (default: 63000)
- **Neo4j**: `bolt://localhost:${GRAPH_DB_PORT}` (default: 63010)
- **Redis**: `localhost:${REDIS_PORT}` (default: 63001)

## 5. Service Configuration

Services can be configured through environment variables or by selecting different Docker Compose profiles:

### 5.1. Environment Variables

The project uses two environment files:
- `.env` - Contains actual configuration values (not committed to git)
- `.env.example` - Template with the same structure but empty secret values (committed to git)

**Note on Service Naming:**

The service names used in the `docker-compose.yml` files (e.g., `supabase-auth`, `supabase-api`) differ from the internal service names used within the `kong.yml` declarative configuration (e.g., `auth`, `rest`). The Kong gateway routes requests to the internal service names defined in `kong.yml`, which are mapped to the corresponding Docker Compose service names.

### 5.2. Kong API Gateway Configuration

The Kong API Gateway is used for centralized API management, including routing, authentication, and plugin management. It is configured using a declarative configuration file (`kong.yml`).

*   **Configuration File:** `./volumes/api/kong.yml` defines the services and routes managed by Kong.
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
- **Gateway:** The Kong API Gateway (`kong-api-gateway`) acts as the entry point for most API requests, routing them to the appropriate backend services. While Kong can enforce authentication policies, the `key-auth` and `acl` plugins are currently commented out in `kong.yml` due to potential compatibility issues with DB-less mode and the need for further investigation based on official Kong documentation. Authentication is primarily handled by the upstream Supabase services.
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

1.  **Generate Keys:** Before starting the stack for the first time, run the `generate_supabase_keys.sh` script. This will create secure values for `SUPABASE_JWT_SECRET`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_KEY` and populate them in your `.env` file.
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

### Automatic setup (recommended)

Run the included script to automatically generate all required keys:

```bash
# Make the script executable
chmod +x generate_supabase_keys.sh

# Run the script to generate and set all required keys in your .env file
./generate_supabase_keys.sh
```

This script will:
1. Generate a secure random JWT secret
2. Create properly signed JWT tokens for both anonymous and service role access
3. Update your .env file with all three values

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
./start.sh --profile ai-local

# Production with NVIDIA GPU support
./start.sh --profile ai-gpu
```

#### 7.1.2. Environment-Specific Configuration

The Ollama service is configured for different environments using standalone Docker Compose files:

- **Default (default profile)**: Standard containerized Ollama service (runs on CPU)
- **ai-local profile**: Complete stack without an Ollama container, connects directly to a locally running Ollama instance
- **ai-gpu profile**: Complete stack with NVIDIA GPU acceleration for the Ollama container

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
  - Queries `public.llms` table for active content LLMs: `SELECT provider, name FROM public.llms WHERE active = true AND content = true ORDER BY provider = 'ollama' DESC, name LIMIT 1`
  - Automatically configures runtime settings based on detected models
  - Falls back to llama3.2 if no active models are found

#### 7.2.3. Dependencies and Startup

The Local Deep Researcher service depends on:
- **Supabase Database**: For LLM configuration queries and potential data storage
- **Ollama Service**: For AI model inference (either containerized or local host)
- **Ollama Pull Service**: Ensures required models are available before startup

#### 7.2.4. Different Deployment Configurations

The service adapts to different deployment scenarios:

- **Default (default profile)**: Connects to containerized Ollama service
- **Development (ai-local profile)**: Connects to local host Ollama instance
- **Production (ai-gpu profile)**: Connects to GPU-accelerated containerized Ollama

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
   SELECT name, provider FROM llms WHERE active = true AND content = true;
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
COMFYUI_BASE_URL=http://comfyui:8188
COMFYUI_ARGS=--listen
COMFYUI_AUTO_UPDATE=false
COMFYUI_PLATFORM=linux/amd64
COMFYUI_IMAGE_TAG=v2-cpu-22.04-v0.2.7  # latest-cuda for GPU

# Storage Integration
COMFYUI_UPLOAD_TO_SUPABASE=true
COMFYUI_STORAGE_BUCKET=comfyui-images
```

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

#### 7.6.4. Local ComfyUI Installation (AI-Local Profile)

For the AI-Local profile, you'll need to install ComfyUI locally on your host machine. This is particularly beneficial for macOS users with Apple Silicon processors.

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
- When you start the GenAI stack with the AI-Local profile, the `comfyui-init` service will automatically download essential models
- Models are stored in the `comfyui-models` Docker volume and shared with your local ComfyUI installation
- You can access models at: `./models/` directory in your ComfyUI installation

**Performance Benefits:**
- **Apple Silicon**: Utilizes Metal Performance Shaders for hardware-accelerated inference
- **Memory Efficiency**: Better memory management on macOS
- **Native Integration**: Seamless integration with macOS system resources

**Using the AI-Local Profile:**
```bash
# Start the stack with local ComfyUI
./start.sh --profile ai-local

# Or manually
docker compose -f docker-compose.yml -f compose-profiles/data.yml -f compose-profiles/ai-local.yml -f compose-profiles/apps-local.yml up
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
├── generate_supabase_keys.sh # Script to generate JWT keys for Supabase
├── start.sh              # Script to start the stack with configurable ports
├── stop.sh              # Script to stop the stack and clean up resources
├── docker-compose.yml    # Main compose file (base networks and volumes)
├── docker-compose.ai-local.yml  # Local Ollama flavor (backward compatibility)
├── docker-compose.ai-gpu.yml    # GPU-optimized flavor (backward compatibility)
├── compose-profiles/     # Modular service profiles
│   ├── data.yml         # Data services (DB, Redis, Neo4j)
│   ├── ai.yml           # AI services (Ollama, Deep Researcher)
│   ├── ai-local.yml     # AI services for local Ollama
│   ├── ai-gpu.yml       # AI services with GPU support
│   ├── apps.yml         # Application services
│   ├── apps-local.yml   # App services for local Ollama
│   └── apps-gpu.yml     # App services with GPU support
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
├── volumes/              # Docker volumes and configurations
│   └── api/              # API gateway configurations
│       └── kong.yml      # Kong declarative configuration file
└── docs/                 # Documentation and diagrams
    ├── diagrams/
    │   ├── README.md
    │   ├── architecture.mermaid
    │   └── generate_diagram.sh
    └── images/
       └── architecture.png
```


Note: Many services will be pre-packaged and pulled directly in docker-compose.yml without needing separate Dockerfiles.

## 12. Cross-Platform Compatibility

This project is designed to work across different operating systems:

### 12.1. Line Ending Handling

- A `.gitattributes` file is included to enforce consistent line endings across platforms
- All shell scripts use LF line endings (Unix-style) even when checked out on Windows
- Docker files and YAML configurations maintain consistent line endings

### 12.2. Host Script Compatibility

The following scripts that run on the host machine (not in containers) have been made cross-platform compatible:

- `start.sh` - For starting the stack with configurable ports and profiles
- `stop.sh` - For stopping the stack and clean up resources
- `generate_supabase_keys.sh` - For generating JWT keys
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
- **Access Points**:
  - Direct: `http://localhost:${N8N_PORT}` (default: 63017)
  - Kong Gateway: `http://localhost:${KONG_HTTP_PORT}/n8n/`
- **Dependencies**: Starts after the successful completion of the `supabase-db-init` and `ollama-pull` services

### 16.2. Features

- **Visual Workflow Editor**: Create workflows with a drag-and-drop interface
- **Node-Based Architecture**: Connect different services and actions using nodes
- **Scheduling**: Run workflows on a schedule or trigger them based on events
- **Error Handling**: Configure retry logic and error workflows
- **Credentials Management**: Securely store and manage credentials for various services
- **Extensibility**: Create custom nodes for specific use cases

### 16.3. Integration with Other Services

- **Backend Service**: The backend service can trigger n8n workflows for tasks like data processing, notifications, and more
- **Supabase PostgreSQL**: n8n uses the Supabase database for storing workflows and execution data
- **Redis**: n8n uses Redis for queue management, improving reliability and scalability of workflow executions

### 16.4. Configuration

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

### 16.5. Pre-built Workflows

The `n8n/` directory contains pre-built n8n workflow templates providing automation and integration capabilities for research and image generation tasks.

#### 15.5.1. Research Workflows

**Available Workflows**:
- `research-simple.json` - Basic research workflow with webhook trigger
- `research-batch.json` - Batch research processing workflow  
- `research-scheduled.json` - Scheduled research automation workflow

**Simple Research Workflow**

**Purpose**: Execute single research queries via webhook with automatic result retrieval.

**Webhook URL**: `http://localhost:${N8N_PORT}/webhook/research-trigger`

**Request Format**:
```json
{
  "query": "Your research question here",
  "max_loops": 3,
  "search_api": "duckduckgo",
  "user_id": "optional-user-id"
}
```

**Response**: Complete research results including title, summary, content, and sources.

#### 15.5.2. ComfyUI Image Generation Workflows

**Available Workflows**:
- `comfyui-image-generation.json` - Comprehensive image generation workflow with validation and error handling
- `comfyui-simple.json` - Simple image generation workflow for basic use cases

**Comprehensive Image Generation Workflow**

**Features**:
- **Input Validation**: Validates all parameters before generation
- **Health Checking**: Verifies ComfyUI service availability  
- **Error Handling**: Comprehensive error handling with meaningful responses
- **Model Support**: Works with all available ComfyUI models
- **Response Processing**: Extracts and formats generation results

**Webhook URL**: `http://localhost:${N8N_PORT}/webhook/comfyui-trigger`

**Request Format**:
```json
{
  "prompt": "a beautiful sunset over mountains",
  "negative_prompt": "blurry, low quality",
  "width": 512,
  "height": 512,
  "steps": 20,
  "cfg": 7.0,
  "checkpoint": "sd_v1-5_pruned_emaonly.safetensors",
  "wait_for_completion": true
}
```

**Response Format**:
```json
{
  "success": true,
  "prompt_id": "12345-abcde",
  "client_id": "67890-fghij",
  "message": "Image generated successfully",
  "generation_parameters": {
    "prompt": "a beautiful sunset over mountains",
    "width": 512,
    "height": 512,
    "steps": 20,
    "cfg": 7.0,
    "checkpoint": "sd_v1-5_pruned_emaonly.safetensors"
  },
  "generated_images": [
    {
      "filename": "ComfyUI_00001_.png",
      "subfolder": "",
      "folder_type": "output",
      "node_id": "SaveImage_9"
    }
  ],
  "image_count": 1,
  "workflow_info": {
    "execution_id": "n8n-exec-123",
    "workflow_name": "ComfyUI Image Generation Workflow",
    "completed_at": "2024-01-15T12:30:45Z",
    "processing_time": 15
  }
}
```

**Simple Image Generation Workflow**

**Webhook URL**: `http://localhost:${N8N_PORT}/webhook/comfyui-simple`

**Request Format**:
```json
{
  "prompt": "a cute cat",
  "width": 512,
  "height": 512,
  "steps": 20
}
```
- Competitive analysis
- Content research for multiple articles
- Academic research compilation

#### 15.5.3. Scheduled Research Workflow (`research-scheduled.json`)

**Purpose**: Automatically execute predefined research queries on a schedule (default: weekly on Mondays at 9 AM).

**Schedule**: Configurable via cron expression (default: `0 9 * * MON`)

**Features**:
- Predefined research topics (AI breakthroughs, tech trends, cybersecurity, open source)
- Automatic report generation
- Result storage in Supabase Storage
- Execution summaries and statistics

**Use Cases**:
- Weekly industry reports
- Trend monitoring
- Automated competitive intelligence
- Research newsletter generation

### 16.6. Workflow Installation and Configuration

1. **Import Workflows**:
   - Access n8n at `http://localhost:${N8N_PORT}`
   - Go to "Workflows" → "Import from JSON"
   - Copy and paste the contents of each workflow file from the `n8n/workflows/` directory
   - Save and activate the workflows

2. **Configure Environment**:
   - Ensure the backend service is running on the correct port
   - Verify the Local Deep Researcher service is accessible
   - Test webhook endpoints after import

3. **Set up Credentials** (if needed):
   - Configure any required API keys
   - Set up database connections if using custom storage

### 16.7. API Integration Examples

#### Simple Research Request

```bash
curl -X POST "http://localhost:${N8N_PORT}/webhook/research-trigger" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Latest developments in artificial intelligence",
    "max_loops": 4,
    "user_id": "user123"
  }'
```

#### Batch Research Request

```bash
curl -X POST "http://localhost:${N8N_PORT}/webhook/batch-research" \
  -H "Content-Type: application/json" \
  -d '{
    "queries": [
      "Machine learning trends 2024",
      "AI ethics and regulations",
      "Neural network architectures"
    ],
    "config": {
      "max_loops": 3,
      "user_id": "user123"
    }
  }'
```

#### JavaScript Integration

```javascript
// Simple research
async function performResearch(query) {
  const response = await fetch('http://localhost:63016/webhook/research-trigger', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: query,
      max_loops: 3,
      user_id: 'web-app-user'
    })
  });
  return response.json();
}

// Batch research
async function performBatchResearch(queries) {
  const response = await fetch('http://localhost:63016/webhook/batch-research', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      queries: queries,
      config: { max_loops: 3 }
    })
  });
  return response.json();
}
```

### 16.8. Configuration Options

#### Timing Configuration

- **Simple Research**: 30-second processing timeout with 10-second retry intervals
- **Batch Research**: 45-second initial wait, 15-second retry intervals
- **Scheduled Research**: 5-minute completion timeout for all queries

#### Error Handling

All workflows include:
- Automatic retry mechanisms for transient failures
- Timeout handling for long-running research
- Error response formatting
- Status tracking and logging

#### Customization

You can customize the workflows by:
1. Modifying timing parameters in wait nodes
2. Changing retry logic and timeout values
3. Adding notification nodes (email, Slack, etc.)
4. Integrating with other services (databases, APIs)
5. Customizing the scheduled research topics

### 16.9. Monitoring and Debugging

#### Execution Logs

- Access workflow execution logs in n8n interface
- Monitor research session status via backend API endpoints
- Check Local Deep Researcher service logs for detailed processing information

#### Health Checks

Test service health:
```bash
# Backend service health
curl http://localhost:${BACKEND_PORT}/research/health

# n8n workflow health
curl http://localhost:${N8N_PORT}/webhook/research-trigger \
  -X POST -H "Content-Type: application/json" \
  -d '{"query": "test query"}'
```

#### Common Issues

1. **Webhook not responding**: Check n8n service status and workflow activation
2. **Research timeouts**: Adjust wait times or check Local Deep Researcher performance
3. **Database errors**: Verify Supabase connection and research table setup
4. **Missing results**: Check backend service logs and research session status

### 16.10. Advanced Usage

#### Custom Workflows

Create custom workflows by:
1. Starting with one of the provided templates
2. Adding pre-processing nodes for data transformation
3. Integrating with external APIs or databases
4. Adding post-processing for custom result formatting

#### Integration with Other Services

These workflows can be extended to integrate with:
- Slack for result notifications
- Email services for report delivery
- Google Sheets for result tracking
- Custom databases for analytics
- Frontend applications for real-time updates

#### Security Considerations

- Use authentication for webhook endpoints in production
- Implement rate limiting to prevent abuse
- Validate input data to prevent injection attacks
- Use HTTPS for secure communication
- Implement proper user access controls

### 16.11. Integration with Other Services

#### Open-WebUI Integration
- Import the ComfyUI tool in Open-WebUI for direct image generation
- Use n8n workflows for batch processing and automation
- Tools can trigger n8n workflows for complex operations

#### Backend API Integration
- Workflows communicate with FastAPI backend
- Access to model management and health checking
- Consistent error handling and response formatting

#### Kong Gateway Routing
- All workflows route through Kong for consistency
- Rate limiting and authentication can be applied
- Centralized service discovery and load balancing

### 16.12. Workflow Customization

#### Adding Custom Parameters
To add new generation parameters:

1. **Update Webhook Node**: Add new input fields
2. **Update Validation**: Add parameter validation in code nodes
3. **Update API Call**: Include new parameters in HTTP request
4. **Update Response**: Include new parameters in response formatting

#### Error Handling
All workflows include comprehensive error handling:
- **Service Health Checks**: Verify ComfyUI availability
- **Parameter Validation**: Validate input parameters
- **API Error Handling**: Handle backend API errors
- **Response Formatting**: Consistent error response format

#### Monitoring and Logging
- Use n8n's built-in execution history for monitoring
- Custom logging can be added via code nodes
- Integration with external monitoring systems via webhooks

### 16.13. General Usage Examples

n8n can be used for a wide variety of automation tasks beyond research and image generation, including:

- **Data Processing**: Automatically process and transform data from various sources
- **Notifications**: Send notifications to Slack, email, or other channels based on events
- **Scheduled Tasks**: Run tasks on a schedule, such as nightly vector database refreshes
- **API Integrations**: Connect to external APIs to fetch or send data
- **Conditional Logic**: Create complex workflows with conditional branching
- **Error Handling**: Configure retry logic and error workflows

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
   - For ai-local profile, ensure local ComfyUI is running on port 8000

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
- **Profile**: New `vector.yml` profile for dedicated vector services

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
- **Profile**: New `monitoring.yml` profile for observability services

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

### 18.7. New Profile Structure

To accommodate these services, we'll introduce new modular profiles:

```
compose-profiles/
├── data.yml           # Existing: Core data services
├── ai.yml             # Existing: AI inference services
├── apps.yml           # Existing: Application services
├── vector.yml         # NEW: Vector databases and embedding services
├── audio.yml          # NEW: Audio processing (Whisper, Piper TTS)
├── search.yml         # NEW: SearxNG metasearch service
├── monitoring.yml     # NEW: Observability and monitoring
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

**Overview**: Successfully restructured the Docker Compose architecture to improve modularity, reusability, and service management. This implementation enables better service control and makes the stack more suitable as a foundation for specialized projects.

#### Issues Resolved:
- ✅ **Redundant service definitions**: Eliminated through modular profile structure
- ✅ **All-or-nothing service deployment**: Resolved with profile-based deployment system
- ✅ **Difficult service group control**: Now possible with granular profiles
- ✅ **Limited reusability**: Improved modularity for derivative projects
- ✅ **Environment file path issues**: Consistent env file handling across all profiles

#### Final Implemented Structure:
```
vanilla-genai/
├── docker-compose.yml              # Base networks and volumes only
├── docker-compose.ai-local.yml     # Legacy: Local Ollama flavor (backward compatibility)
├── docker-compose.ai-gpu.yml       # Legacy: GPU-optimized flavor (backward compatibility)
├── compose-profiles/               # New modular profile system
│   ├── data.yml                    # Data services (Supabase, Redis, Neo4j)
│   ├── ai.yml                      # AI services (Ollama, Deep Researcher, n8n)
│   ├── ai-local.yml                # AI services for local Ollama (no Ollama container)
│   ├── ai-gpu.yml                  # AI services with GPU support
│   ├── apps.yml                    # Application services (UI, Backend, Kong)
│   ├── apps-local.yml              # App services configured for local Ollama
│   └── apps-gpu.yml                # App services with GPU optimization
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
   ./start.sh --profile ai-local
   
   # GPU-optimized stack
   ./start.sh --profile ai-gpu
   ```

2. **✅ Modular Architecture**: Clean separation of concerns
   - Data services are independent of AI services
   - AI services can be swapped between local/containerized/GPU
   - App services adapt to the AI configuration

3. **✅ Better Resource Utilization**: Run only what you need
4. **✅ Improved Reusability**: Perfect foundation for specialized projects
5. **✅ Simplified Maintenance**: DRY principle, no redundant definitions

#### Migration Strategy (Completed):
1. **✅ Phase 1**: Created profile files alongside existing structure
2. **✅ Phase 2**: Updated documentation and convenience scripts
3. **✅ Phase 3**: Renamed profiles to cleaner names (ai-local, ai-gpu)
4. **Future**: Remove deprecated files in next major version

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
./start.sh --profile ai                    # AI services only
./start.sh --profile automation            # Automation services only  
./start.sh --profile "ai,automation"       # Multiple profiles
./start.sh --disable ui                    # Disable UI services
./start.sh --enable comfyui               # Enable ComfyUI specifically
```

---

### 19.2. ComfyUI Integration 🎨

**Priority**: Medium | **Status**: ✅ Completed | **Complexity**: Low-Medium

**Overview**: ComfyUI has been successfully integrated as an AI image generation service, providing node-based workflow interface for Stable Diffusion and advanced image generation capabilities.

#### Why ComfyUI?
- **Node-based Interface**: Perfect fit with n8n workflow philosophy
- **Advanced AI Image Generation**: Stable Diffusion, ControlNet, and more
- **Workflow Automation**: Can be integrated with n8n for automated image generation
- **Modular Architecture**: Fits well with our service-oriented approach

#### ✅ Implemented Features:
- **Multi-Architecture Support**: CPU (development) and GPU (production) deployment profiles
- **Docker Images**: Uses `ghcr.io/ai-dock/comfyui` with CPU and CUDA variants
- **Service Integration**: Full integration with all AI and Apps profiles
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

### 19.3. Enhanced Service Management 🔧

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

### 19.4. RAG Foundation Preparation 📚

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

### 19.5. Developer Experience Improvements 🛠️

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

### 20.2 Local Deep Researcher ✅

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
- Web Interface (Local/ai-local profile): `http://localhost:8000`
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
   - Each model has flags: `active`, `content`, `embeddings`, `vision`
   - The Deep Researcher uses models marked with `active = true` AND `content = true`

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
   WHERE name = 'qwen3:latest' AND content = true;
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
  vision boolean NOT NULL DEFAULT false,
  content boolean NOT NULL DEFAULT false,
  structured_content boolean NOT NULL DEFAULT false,
  embeddings boolean NOT NULL DEFAULT false,
  provider varchar NOT NULL,
  name varchar NOT NULL UNIQUE,
  description text,
  size_gb numeric,
  context_window integer,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
```

**Model Selection Logic**

1. **Query Priority**:
   ```sql
   SELECT provider, name FROM public.llms 
   WHERE active = true AND content = true 
   ORDER BY provider = 'ollama' DESC, name
   LIMIT 1;
   ```

2. **Selection Criteria**:
   - Must have `active = true`
   - Must have `content = true` (for text generation)
   - Prefers `ollama` provider for local inference
   - Falls back to `llama3.2` if no models found

**Managing Research Models**

View Available Models:
```sql
-- See all content-capable models
SELECT name, provider, active, description 
FROM public.llms 
WHERE content = true;

-- Check current active research model
SELECT name, provider 
FROM public.llms 
WHERE active = true AND content = true 
ORDER BY provider = 'ollama' DESC
LIMIT 1;
```

Add New Models:
```sql
-- Add a new Ollama model
INSERT INTO public.llms (
  name, provider, active, content, 
  description, context_window
) VALUES (
  'llama3.1:70b', 'ollama', true, true,
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
  "SELECT name, provider, active FROM public.llms WHERE content = true;"

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
WHERE active = true AND content = true 
ORDER BY provider = 'ollama' DESC;

-- If multiple models are active, deactivate unwanted ones
UPDATE public.llms SET active = false 
WHERE name != 'your-preferred-model' AND content = true;
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
- [ ] Add MCP Gateway service to Docker Compose profiles
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
- [ ] Integration testing across all profiles

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

