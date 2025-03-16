# Vanilla GenAI Stack

A flexible, modular GenAI project boilerplate with customizable services.

## Project Overview

Vanilla GenAI Stack is a customizable multi-service architecture for AI applications, featuring:

- Multiple deployment profiles managed by Docker Compose
- Modular service architecture with interchangeability between containerized and external services
- Support for local development and cloud deployment (AWS ECS compatible)
- Key services including Ollama, PostgreSQL, Neo4j, pgAdmin, OpenWebUI, and FastAPI

## Features

- **Flexible Service Configuration**: Switch between containerized services or connect to existing external endpoints
- **Multiple Deployment Profiles**: Choose different service combinations with Docker Compose profiles
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
# Start all services
docker compose up

# Start with a specific profile
docker compose --profile <profile_name> up

# Build services
docker compose build
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
OLLAMA_ENDPOINT=http://host.docker.internal:11434

# Then run with external-ollama profile
docker compose --profile external-ollama up
```

## Database Service

The PostgreSQL database service comes with pgvector and PostGIS extensions for vector operations and geospatial functionality.

### Database Setup Process

When the database container starts for the first time, the following steps happen automatically:

1. PostgreSQL initializes with the credentials from `.env`
2. `setup_extensions.sh` runs to install pgvector and PostGIS extensions
3. `init_extensions.sql` runs to:
   - Enable the vector and postgis extensions in the database
   - Create the application user with credentials from `.env`
   - Set appropriate permissions for the application user

### Database Backup and Restore

The database service includes a comprehensive backup and restore system:

#### Manual Backup

To manually create a database backup:

```bash
# Connect to the running container
docker exec -it vanilla-genai-db bash

# Run the backup script (requires environment variables to be set)
backup.sh
```

This creates a timestamped SQL dump in the `db/snapshot/` directory, which is mounted as a volume.

#### Automatic Backup (Optional)

For automatic periodic backups:

1. Uncomment the cron job section in the `db/Dockerfile`
2. Rebuild the container with `docker compose build db`

This will run a daily backup at midnight, storing it in the snapshot directory.

#### Manual Restore

To manually restore from a backup:

```bash
# Connect to the running container
docker exec -it vanilla-genai-db bash

# Run the restore script (finds and uses latest backup)
restore.sh
```

#### Automatic Restore

When the container starts and if backup files exist in the `db/snapshot/` directory:
- The container initializes the database
- Any snapshot files in the mounted snapshot directory are available for manual restore
- Automatic restore is not enabled by default to prevent unintended data overwriting
- To enable automatic restore at startup, mount backup files to `/docker-entrypoint-initdb.d/`

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
