# Vanilla GenAI Stack

A flexible, modular GenAI project boilerplate with customizable services.

## Architecture Diagram

![Architecture Diagram](./docs/images/architecture.png)

*Note: Run `./docs/diagrams/generate_diagram.sh` to update this diagram after making changes to the architecture.*

## Project Overview

Vanilla GenAI Stack is a customizable multi-service architecture for AI applications, featuring:

- Multiple deployment flavors using standalone Docker Compose files
- Modular service architecture with interchangeability between containerized and external services
- Support for local development and cloud deployment (AWS ECS compatible)
- Key services including Supabase (PostgreSQL + Studio), Neo4j, and Ollama

## Features

- **Flexible Service Configuration**: Switch between containerized services or connect to existing external endpoints
- **Multiple Deployment Flavors**: Choose different service combinations with standalone Docker Compose files
- **Cloud Ready**: Designed for seamless deployment to cloud platforms like AWS ECS
- **Health Monitoring**: Built-in healthchecks for all applicable services
- **Environment-based Configuration**: Easy configuration through environment variables

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development)
- UV package manager (optional, for Python dependency management)

### Running the Stack

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

## Service Configuration

Services can be configured through environment variables or by selecting different Docker Compose profiles:

### Environment Variables

The project uses two environment files:
- `.env` - Contains actual configuration values (not committed to git)
- `.env.example` - Template with the same structure but empty secret values (committed to git)

When setting up the project:
1. Copy `.env.example` to `.env`
2. Fill in the required values in `.env`
3. Keep both files in sync when adding new variables

```bash
# Example: Use external Ollama instead of containerized version
# In .env file:
OLLAMA_API_ENDPOINT=http://host.docker.internal:11434

# Then run with dev-ollama-local flavor
docker compose -f docker-compose.dev-ollama-local.yml up
```

## Database Services

### Supabase Services

The Supabase services provide a PostgreSQL database with additional capabilities along with a web-based Studio interface for management:

#### Supabase PostgreSQL Database

The Supabase PostgreSQL database comes with pgvector and PostGIS extensions for vector operations and geospatial functionality.

#### Supabase Studio Dashboard

The Supabase Studio provides a modern web-based administration interface for PostgreSQL:

- **Accessible**: Available at http://localhost:${SUPABASE_STUDIO_PORT} (configured via `SUPABASE_STUDIO_PORT`)
- **Database**: The dashboard automatically connects to the PostgreSQL database
- **Features**: Table editor, SQL editor, database structure visualization, and more

## Graph Database Services

### Graph Database (Neo4j)

The Graph Database service (Neo4j) provides a robust graph database for storing and querying connected data:

- **Built-in Dashboard Interface**: Available at http://localhost:60003 (configured via `GRAPH_DB_DASHBOARD_PORT`)
- **First-time Login**: 
  1. When you first access the dashboard, you'll see the Neo4j Browser interface
  2. In the connection form, you'll see it's pre-filled with "neo4j://graph-db:7687"
  3. **Change the connection URL to**: `neo4j://localhost:60002` or `bolt://localhost:60002`
  4. Connection details:
     - Database: Leave as default (neo4j)
     - Authentication type: Username / Password
     - Username: `neo4j`
     - Password: Value of `GRAPH_DB_PASSWORD` from your `.env` file (default: neo4j_password)
  5. Click "Connect" button

- **Application Connection**: Applications can connect to the database using the Bolt protocol:
  - Bolt URL: `bolt://localhost:60002` 
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

### Ollama Service

The Ollama service provides a containerized environment for running large language models locally:

- **API Endpoint**: Available at http://localhost:11434
- **Persistent Storage**: Model files are stored in a Docker volume for persistence between container restarts
- **Multiple Deployment Options**:
  - **Default (Containerized)**: Uses the Ollama container within the stack
  - **Local Ollama**: Connect to an Ollama instance running on your host machine
  - **Production with GPU**: Use NVIDIA GPU acceleration for improved performance

#### Switching Between Deployment Options

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

#### Environment-Specific Configuration

The Ollama service is configured for different environments using standalone Docker Compose files:

- **Default (docker-compose.yml)**: Standard containerized Ollama service (runs on CPU)
- **dev-ollama-local (docker-compose.dev-ollama-local.yml)**: Complete stack without an Ollama container, connects directly to a locally running Ollama instance
- **prod-gpu (docker-compose.prod-gpu.yml)**: Complete stack with NVIDIA GPU acceleration for the Ollama container

The configuration includes an `ollama-pull` service that automatically downloads required models from the Supabase database. It queries the `llms` table for models where `provider='ollama'` and `active=true`, then pulls each model via the Ollama API. This ensures the necessary models are always available for dependent services.

This approach ensures that dependent services can always reference the `ollama` service without needing environment-specific configurations.

#### Using Local Ollama

When using the dev-ollama-local configuration to connect to a locally running Ollama instance:

1. Make sure Ollama is installed and running on your host machine
2. Run Docker Compose with the dev-ollama-local file:
   ```bash
   docker compose -f docker-compose.dev-ollama-local.yml up
   ```


### Database Setup Process

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

### Database Backup and Restore

The database services (Supabase/PostgreSQL and Neo4j) include comprehensive backup and restore systems:

#### Supabase PostgreSQL Backup and Restore

##### Manual Backup

To manually create a database backup:

```bash
# Create a backup directly from the container
docker exec ${PROJECT_NAME}-supabase-db /usr/local/bin/backup.sh
```

This creates a timestamped SQL dump in the `/snapshot` directory inside the container, which is mounted to the `./supabase/db/snapshot/` directory on your host machine.

##### Manual Restore

To manually restore from a backup:

```bash
# Restore the database from the latest backup
docker exec ${PROJECT_NAME}-supabase-db /usr/local/bin/restore.sh
```

The restore script automatically finds and uses the most recent backup file from the snapshot directory.

##### Important Notes:

- Backups are stored in `./supabase/db/snapshot/` on your host machine with timestamped filenames
- The restore process does not interrupt normal database operations
- Automatic restore on startup can be enabled via the auto_restore.sh script

#### Neo4j Graph Database Backup and Restore

##### Manual Backup

To manually create a graph database backup:

```bash
# Create a backup (will temporarily stop and restart Neo4j)
docker exec -it ${PROJECT_NAME}-graph-db /usr/local/bin/backup.sh
```

The backup will be stored in the `/snapshot` directory inside the container, which is mounted to the `./graph-db/snapshot/` directory on your host machine.

##### Manual Restore

To restore from a previous backup:

```bash
# Restore from the latest backup
docker exec -it ${PROJECT_NAME}-graph-db /usr/local/bin/restore.sh
```

##### Important Notes:
- By default, data persists in the Docker volume between restarts
- Automatic restoration at startup is enabled by default for Neo4j. When the container starts, it will automatically restore from the latest backup if one is available
- To disable automatic restore for Neo4j, remove or rename the auto_restore.sh script in the Dockerfile

## Development

```bash
# Python management with UV
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Running tests
cd <service_dir> && pytest

# Running a specific test
cd <service_dir> && pytest path/to/test_file.py::test_function_name

# Linting
cd <service_dir> && ruff check .

# Formatting
cd <service_dir> && ruff format .
```

## Project Structure

```
vanilla-genai/
├── .env                  # Environment configuration
├── docker-compose.yml    # Main compose file
├── custom-service1/      # Custom services have their own directories
│   ├── Dockerfile        # Only needed for custom services
│   ├── src/
│   └── ...
├── custom-service2/
│   ├── Dockerfile
│   └── ...
└── ...
```

Note: Many services will be pre-packaged and pulled directly in docker-compose.yml without needing separate Dockerfiles.

## License

[MIT](LICENSE)
