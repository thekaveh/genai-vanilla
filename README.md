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
