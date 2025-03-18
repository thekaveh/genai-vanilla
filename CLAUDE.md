# CLAUDE.md - Guidelines for Vanilla GenAI Stack

## Project Overview
- Vanilla, boilerplate GenAI project with customizable services
- Multi-service architecture managed by Docker Compose with multiple flavors via standalone files
- Services include: 
  - Supabase (PostgreSQL with pgvector/PostGIS + Studio dashboard)
  - Neo4j Graph Database with dashboard
  - Ollama for local AI model inference
  - Additional services can be added as needed (OpenWebUI, FastAPI, etc.)
- Each service has its own dedicated directory structure
- No src folder in root directory; each service that needs it will have its own
- Architecture diagram is automatically generated using Python and Diagrams library

## Build/Test/Lint Commands
- Run Docker services: `docker compose up`
- Run specific flavor: `docker compose -f docker-compose.<flavor_name>.yml up`
- Available flavors: default (docker-compose.yml), dev-ollama-local, prod-gpu
- Build services: `docker compose build`
- Python management: `uv` (instead of pip/virtualenv)
- Run tests: `cd <service_dir> && pytest`
- Run single test: `cd <service_dir> && pytest path/to/test_file.py::test_function_name`
- Lint Python: `cd <service_dir> && ruff check .`
- Format Python: `cd <service_dir> && ruff format .`

## Docker Configuration Guidelines
- **Service Organization**: Services may be organized in two ways:
  - Pre-packaged services pulled directly in docker-compose.yml (no separate Dockerfile needed)
  - Custom services with dedicated directories and Dockerfiles
- **Healthchecks**: Implement healthchecks for all applicable services
  - Use `healthcheck` block in Docker Compose with appropriate test commands
  - Set reasonable intervals, timeouts, retries, and start periods
- **Deployment Flexibility**: Support both local and cloud deployments
  - Design compatible with AWS ECS and other cloud platforms
  - Use environment variables to configure deployment settings
- **Service Interchangeability**: Allow switching between containerized and external services
  - Configure service endpoints via environment variables in .env files
  - Use separate Docker Compose files for different service configurations
  - Implement different flavors via standalone files (e.g., `docker-compose.dev-ollama-local.yml`, `docker-compose.prod-gpu.yml`)

## Supabase Configuration
- **Database**: Uses the official Supabase Postgres image (supabase/postgres)
  - Includes pgvector and PostGIS extensions
  - Auto-initializes with init.sql on first startup
- **Dashboard**: Supabase Studio for database management
  - Connects via Postgres Meta service to ensure compatibility
- **Backup & Restore**: Automated database backup and restore functionality
  - Commands:
    - `docker exec -it vanilla-genai-supabase-db backup.sh` - Create a backup
    - `docker exec -it vanilla-genai-supabase-db restore.sh` - Restore from latest backup
  - Automatic restore from latest backup on container startup
  - Backups stored in ./supabase/db/snapshot directory

## Architecture Diagram Maintenance
- Located in `docs/diagrams/`
- Automatically generates a visual representation of the Docker Compose services and their relationships
- To update the diagram after making changes to the architecture:
  1. Run `./docs/diagrams/generate_diagram.sh`
  2. This will generate a new diagram and update the README.md file
  3. If you add new services, you may need to update the icon mappings in `architecture.py`
- IMPORTANT: Always update the architecture diagram when modifying the Docker Compose services!

## Code Style Guidelines
- **Python**: Follow PEP 8 guidelines, managed by uv
- **Docker**: Organized by service with appropriate networking and volume configuration
- **Docker Compose**: Use standalone files for different deployment flavors
- **Imports**: Sort automatically with ruff, group standard library, third-party, local
- **Naming**: snake_case for Python variables/functions, CamelCase for classes
- **Error Handling**: Use explicit exception handling with proper logging
- **Documentation**: Docstrings for modules, classes, and functions
- **Environment**: Configure services using environment variables
  - Maintain both `.env` and `.env.example` files
  - Keep structure identical between both files
  - Leave API keys/secrets empty in `.env.example`
  - Update both files whenever adding new variables