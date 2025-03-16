# CLAUDE.md - Guidelines for Vanilla GenAI Stack

## Project Overview
- Vanilla, boilerplate GenAI project with customizable services
- Multi-service architecture managed by Docker Compose with multiple profiles/flavors
- Services include: SQL Database (PostgreSQL with pgvector/PostGIS), SQL Database Dashboard (pgAdmin), Ollama, Neo4j, OpenWebUI, FastAPI, etc.
- Each service will have its own dedicated directory structure
- No src folder in root directory; each service that needs it will have its own

## Build/Test/Lint Commands
- Run Docker services: `docker compose up`
- Run specific profile: `docker compose --profile <profile_name> up`
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
  - Use conditional configuration in Docker Compose based on environment variables
  - Implement profiles for different service configurations (e.g., `local-ollama`, `external-ollama`)

## Code Style Guidelines
- **Python**: Follow PEP 8 guidelines, managed by uv
- **Docker**: Organized by service with appropriate networking and volume configuration
- **Docker Compose**: Use profiles for different deployment flavors
- **Imports**: Sort automatically with ruff, group standard library, third-party, local
- **Naming**: snake_case for Python variables/functions, CamelCase for classes
- **Error Handling**: Use explicit exception handling with proper logging
- **Documentation**: Docstrings for modules, classes, and functions
- **Environment**: Configure services using environment variables
  - Maintain both `.env` and `.env.example` files
  - Keep structure identical between both files
  - Leave API keys/secrets empty in `.env.example`
  - Update both files whenever adding new variables