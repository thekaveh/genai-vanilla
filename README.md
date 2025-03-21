# Vanilla GenAI Stack

A flexible, modular GenAI project boilerplate with customizable services.

## 1. Project Overview

Vanilla GenAI Stack is a customizable multi-service architecture for AI applications, featuring:

- Multiple deployment flavors using standalone Docker Compose files
- Modular service architecture with interchangeability between containerized and external services
- Support for local development and cloud deployment (AWS ECS compatible)
- Key services including Supabase (PostgreSQL + Studio), Neo4j, Ollama, and FastAPI backend

## 2. Features

- **2.1. Flexible Service Configuration**: Switch between containerized services or connect to existing external endpoints
- **2.2. Multiple Deployment Flavors**: Choose different service combinations with standalone Docker Compose files
- **2.3. Cloud Ready**: Designed for seamless deployment to cloud platforms like AWS ECS
- **2.4. Health Monitoring**: Built-in healthchecks for all applicable services
- **2.5. Environment-based Configuration**: Easy configuration through environment variables

## 3. Getting Started

### 3.1. Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development)
- UV package manager (optional, for Python dependency management)

### 3.2. Running the Stack

```bash
# First, make sure all previous services are stopped to avoid port conflicts
docker compose down --remove-orphans

# Start all services
docker compose up

# Start with a specific flavor
docker compose -f docker-compose.<flavor_name>.yml down --remove-orphans
docker compose -f docker-compose.<flavor_name>.yml up

# Build services
docker compose build

# Fresh/Cold Start (completely reset the environment)
# This will remove all volumes, containers, and orphaned services before rebuilding and starting
docker compose down --volumes --remove-orphans && docker compose up --build
```

For a fresh/cold start with a specific flavor, use:

```bash
docker compose -f docker-compose.<flavor_name>.yml down --volumes --remove-orphans && docker compose -f docker-compose.<flavor_name>.yml up --build
```

## 4. Service Configuration

Services can be configured through environment variables or by selecting different Docker Compose profiles:

### 4.1. Environment Variables

The project uses two environment files:
- `.env` - Contains actual configuration values (not committed to git)
- `.env.example` - Template with the same structure but empty secret values (committed to git)

When setting up the project:
1. Copy `.env.example` to `.env`
2. Fill in the required values in `.env`
3. Keep both files in sync when adding new variables

## 5. Database Services

### 5.1. Supabase Services

The Supabase services provide a PostgreSQL database with additional capabilities along with a web-based Studio interface for management:

#### 5.1.1. Supabase PostgreSQL Database

The Supabase PostgreSQL database comes with pgvector and PostGIS extensions for vector operations and geospatial functionality.

#### 5.1.2. Supabase Auth Service

The Supabase Auth service (GoTrue) provides user authentication and management:

- **API Endpoint**: Available at http://localhost:${SUPABASE_AUTH_PORT} (configured via `SUPABASE_AUTH_PORT`)
- **JWT Authentication**: Uses a secure JWT token system for authentication
- **Features**: User registration, login, password recovery, email confirmation, and more

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

#### 5.1.3. Supabase Studio Dashboard

The Supabase Studio provides a modern web-based administration interface for PostgreSQL:

- **Accessible**: Available at http://localhost:${SUPABASE_STUDIO_PORT} (configured via `SUPABASE_STUDIO_PORT`)
- **Database**: The dashboard automatically connects to the PostgreSQL database
- **Features**: Table editor, SQL editor, database structure visualization, and more
- **Authentication**: Integrated with the Auth service for user management

### 5.2. Graph Database (Neo4j)

The Graph Database service (Neo4j) provides a robust graph database for storing and querying connected data:

- **Built-in Dashboard Interface**: Available at http://localhost:${GRAPH_DB_DASHBOARD_PORT} (configured via `GRAPH_DB_DASHBOARD_PORT`)
- **First-time Login**: 
  1. When you first access the dashboard, you'll see the Neo4j Browser interface
  2. In the connection form, you'll see it's pre-filled with "neo4j://graph-db:7687"
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
- **Backup and Restore Workflow**:
  1. **Backing Up Data**: Create a snapshot while Neo4j is running:
     ```bash
     # Create a backup (will temporarily stop and restart Neo4j)
     docker exec -it ${PROJECT_NAME}-graph-db /usr/local/bin/backup.sh
     ```
     The backup will be stored in the `/snapshot` directory inside the container, which is mounted to the `./graph-db/snapshot/` directory on your host machine.
  
  2. **Data Persistence**: By default, data persists in the Docker volume between restarts.
  
  3. **Manual Restoration**: To restore from a previous backup:
     ```bash
     # Restore from the latest backup
     docker exec -it ${PROJECT_NAME}-graph-db /usr/local/bin/restore.sh
     ```
     
  4. **Important Note**: Automatic restoration at startup is now enabled by default. When the container starts, it will automatically restore from the latest backup if one is available. To disable this behavior, remove or rename the auto_restore.sh script in the Dockerfile.

## 6. AI Services

### 6.1. Ollama Service

The Ollama service provides a containerized environment for running large language models locally:

- **API Endpoint**: Available at http://localhost:${OLLAMA_PORT}
- **Persistent Storage**: Model files are stored in a Docker volume for persistence between container restarts
- **Multiple Deployment Options**:
  - **Default (Containerized)**: Uses the Ollama container within the stack
  - **Local Ollama**: Connect to an Ollama instance running on your host machine
  - **Production with GPU**: Use NVIDIA GPU acceleration for improved performance

#### 6.1.1. Switching Between Deployment Options

The Ollama service can be deployed in different configurations using separate Docker Compose files:

```bash
# Default: Use the containerized Ollama service (CPU)
docker compose up

# Development with local Ollama (running on your host machine)
# First ensure Ollama is running on your host
docker compose -f docker-compose.dev-ollama-local.yml up

# Production with NVIDIA GPU support
docker compose -f docker-compose.prod-gpu.yml up
```

#### 6.1.2. Environment-Specific Configuration

The Ollama service is configured for different environments using standalone Docker Compose files:

- **Default (docker-compose.yml)**: Standard containerized Ollama service (runs on CPU)
- **dev-ollama-local (docker-compose.dev-ollama-local.yml)**: Complete stack without an Ollama container, connects directly to a locally running Ollama instance
- **prod-gpu (docker-compose.prod-gpu.yml)**: Complete stack with NVIDIA GPU acceleration for the Ollama container

The configuration includes an `ollama-pull` service that automatically downloads required models from the Supabase database. It queries the `llms` table for models where `provider='ollama'` and `active=true`, then pulls each model via the Ollama API. This ensures the necessary models are always available for dependent services.

### 6.2. Open Web UI

The Open Web UI service provides a web interface for interacting with the Ollama models:

- **Accessible**: Available at http://localhost:${OPEN_WEB_UI_PORT} (configured via `OPEN_WEB_UI_PORT`)
- **Automatic Connection**: Automatically connects to the Ollama API endpoint
- **Database Integration**: Uses the Supabase PostgreSQL database for storing conversations and settings

### 6.3. Backend API Service

The Backend service provides a FastAPI-based REST API that connects to both Supabase PostgreSQL and Ollama for AI model inference:

- **REST API Endpoint**: Available at http://localhost:${BACKEND_PORT} (configured via `BACKEND_PORT`)
- **API Documentation**: 
  - Swagger UI: http://localhost:${BACKEND_PORT}/docs
  - ReDoc: http://localhost:${BACKEND_PORT}/redoc
- **Features**:
  - Connection to Supabase PostgreSQL with pgvector support
  - Integration with Ollama for local AI model inference
  - Support for multiple LLM providers (OpenAI, Groq, etc.)
  - Dependency management with uv instead of pip/virtualenv

#### 6.3.1. Configuration

The backend service is configured via environment variables:

- `DATABASE_URL`: PostgreSQL connection string for Supabase
- `OLLAMA_BASE_URL`: URL for Ollama API
- `BACKEND_PORT`: Port to expose the API (configured via `BACKEND_PORT`)

#### 6.3.2. Local Development

For local development outside of Docker:

```bash
# Navigate to app directory
cd backend/app

# Install dependencies using uv
uv pip install -r requirements.txt

# Run the server in development mode
uvicorn main:app --reload
```

## 7. Database Setup Process

When the database containers start for the first time, the following steps happen automatically:

1. PostgreSQL initializes with the credentials from `.env`
2. The Supabase database initializes with the following:
   - Extensions: pgvector and PostGIS
   - Tables: Default tables including the `llms` table for managing LLM configurations
   - Default data: Initial records (e.g., default Ollama models)

The `llms` table stores:
- Model names and providers
- Active status (determines which models are pulled by the ollama-pull service)
- Capability flags (vision, content, structured_content, embeddings)
- Creation and update timestamps

## 8. Database Backup and Restore

The database services (Supabase/PostgreSQL and Neo4j) include comprehensive backup and restore systems:

### 8.1. Supabase PostgreSQL Backup and Restore

#### 8.1.1. Manual Backup

To manually create a database backup:

```bash
# Create a backup directly from the container
docker exec ${PROJECT_NAME}-supabase-db /usr/local/bin/backup.sh
```

This creates a timestamped SQL dump in the `/snapshot` directory inside the container, which is mounted to the `./supabase/db/snapshot/` directory on your host machine.

#### 8.1.2. Manual Restore

To manually restore from a backup:

```bash
# Restore the database from the latest backup
docker exec ${PROJECT_NAME}-supabase-db /usr/local/bin/restore.sh
```

The restore script automatically finds and uses the most recent backup file from the snapshot directory.

#### 8.1.3. Important Notes:

- Backups are stored in `./supabase/db/snapshot/` on your host machine with timestamped filenames
- The restore process does not interrupt normal database operations
- Automatic restore on startup can be enabled via the auto_restore.sh script

### 8.2. Neo4j Graph Database Backup and Restore

#### 8.2.1. Manual Backup

To manually create a graph database backup:

```bash
# Create a backup (will temporarily stop and restart Neo4j)
docker exec -it ${PROJECT_NAME}-graph-db /usr/local/bin/backup.sh
```

The backup will be stored in the `/snapshot` directory inside the container, which is mounted to the `./graph-db/snapshot/` directory on your host machine.

#### 8.2.2. Manual Restore

To restore from a previous backup:

```bash
# Restore from the latest backup
docker exec -it ${PROJECT_NAME}-graph-db /usr/local/bin/restore.sh
```

#### 8.2.3. Important Notes:
- By default, data persists in the Docker volume between restarts
- Automatic restoration at startup is enabled by default for Neo4j. When the container starts, it will automatically restore from the latest backup if one is available
- To disable automatic restore for Neo4j, remove or rename the auto_restore.sh script in the Dockerfile

## 9. Project Structure

```
vanilla-genai/
├── .env                  # Environment configuration
├── docker-compose.yml    # Main compose file
├── docker-compose.dev-ollama-local.yml  # Local Ollama flavor
├── docker-compose.prod-gpu.yml          # GPU-optimized flavor
├── backend/              # FastAPI backend service
│   ├── Dockerfile
│   └── app/
│       ├── main.py
│       ├── requirements.txt
│       └── data/         # Data storage (mounted as volume)
├── graph-db/             # Neo4j Graph Database configuration
│   ├── Dockerfile
│   ├── scripts/
│   └── snapshot/
├── supabase/             # Supabase configuration
│   ├── db/
│   │   ├── Dockerfile
│   │   ├── init.sql
│   │   ├── scripts/
│   │   └── snapshot/
│   ├── auth/             # Supabase Auth service (GoTrue)
│   └── storage/
└── docs/                 # Documentation and diagrams
    ├── diagrams/
    └── images/
```

Note: Many services will be pre-packaged and pulled directly in docker-compose.yml without needing separate Dockerfiles.

## 10. License

[MIT](LICENSE)