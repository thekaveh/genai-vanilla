# Using genai-vanilla as a Git Submodule

This guide explains how to use the genai-vanilla stack as a git submodule in your project, allowing you to build on top of it as an infrastructure foundation while maintaining the ability to contribute back to the project.

## Table of Contents

- [Quick Start](#quick-start)
- [Why Use as a Submodule?](#why-use-as-a-submodule)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Integration Patterns](#integration-patterns)
- [Contributing Back](#contributing-back)
- [Troubleshooting](#troubleshooting)

## Quick Start

### 1. Add genai-vanilla as a Submodule

In your project root, add genai-vanilla as a submodule in an `infra/` directory:

```bash
# Add the submodule (replace with your repository URL)
git submodule add <repository-url> infra

# Initialize and update the submodule
git submodule init
git submodule update
```

### 2. Configure the Environment

```bash
cd infra

# Copy the example configuration
cp .env.example .env

# Edit .env and customize PROJECT_NAME
# IMPORTANT: Set PROJECT_NAME to match your project name
vim .env
```

**Critical Configuration:**
```bash
# In infra/.env
PROJECT_NAME=myproject  # Change from 'genai' to your project name
```

### 3. Start the Infrastructure

```bash
# From the infra directory
./start.sh

# Or from your project root
(cd infra && ./start.sh)
```

### 4. Access Services

Services are accessible on ports starting from 63000 (base port):
- **Supabase DB**: http://localhost:63000 (base + 0)
- **Supabase Studio**: http://localhost:63009 (base + 9)
- **Kong API Gateway**: http://localhost:63002 (base + 2)
- **N8N**: http://localhost:63017 (base + 17)
- **Ollama**: http://localhost:63012 (base + 12)

See the startup output for the complete port mapping of all services.

## Why Use as a Submodule?

Using genai-vanilla as a git submodule provides these capabilities:

- Separation of infrastructure code from application code
- Ability to pull upstream improvements while maintaining local configurations
- Project-specific environment settings tracked in parent repository
- Standard git workflow for contributing improvements back to genai-vanilla
- Multiple independent instances with isolated Docker resources (networks, volumes, containers)
- Infrastructure version pinning to specific commits or tags

## Project Structure

### Recommended Directory Layout

```
myproject/
├── .git/
├── .gitmodules              # Git submodule configuration
├── src/                     # Your application code
│   ├── backend/
│   ├── frontend/
│   └── ...
├── infra/                   # genai-vanilla submodule
│   ├── .git -> ../.git/modules/infra
│   ├── .env                 # Your custom configuration (gitignored)
│   ├── .env.example
│   ├── docker-compose.yml
│   ├── start.sh
│   ├── stop.sh
│   ├── bootstrapper/
│   ├── services/
│   └── ...
├── scripts/
│   ├── start-all.sh         # Start infra + your app
│   └── stop-all.sh
├── docker-compose.yml       # Optional: Your app services
└── README.md
```

### Parent .gitignore Configuration

Add these entries to your parent project's `.gitignore`:

```
# Infrastructure environment and data
infra/.env
infra/volumes/
infra/data/

# Keep .env.example for documentation
!infra/.env.example
```

## Configuration

### PROJECT_NAME: The Key to Isolation

The `PROJECT_NAME` environment variable is critical for submodule usage. It prefixes all Docker resources to prevent conflicts:

**Docker Resources Prefixed with PROJECT_NAME:**
- **Networks**: `${PROJECT_NAME}-network`
- **Containers**: `${PROJECT_NAME}-supabase-db`, `${PROJECT_NAME}-ollama`, etc.
- **Volumes**: `${PROJECT_NAME}-supabase-db-data`, `${PROJECT_NAME}-redis-data`, etc.

**Example:**

```bash
# In infra/.env
PROJECT_NAME=myproject
```

Results in:
- Network: `myproject-network`
- Container: `myproject-supabase-db`
- Volume: `myproject-supabase-db-data`

This allows multiple projects to use genai-vanilla simultaneously without conflicts.

### Custom Environment File Location (Advanced)

If you prefer to manage your infrastructure configuration from the parent project, you can use the `GENAI_ENV_FILE` environment variable:

```bash
# Parent project structure
myproject/
├── config/
│   ├── dev.env      # Development infrastructure config
│   ├── prod.env     # Production infrastructure config
│   └── test.env
└── infra/           # genai-vanilla submodule

# Start with custom config location
GENAI_ENV_FILE=../config/prod.env ./infra/start.sh
```

This is useful for:
- Centralized configuration management
- CI/CD pipelines with secret injection
- Running multiple instances with different configurations

### Port Configuration

By default, services start at port 63000. If these ports conflict with your application:

```bash
# Use custom base port
./start.sh --base-port 64000

# Or set in .env
BASE_PORT=64000
```

## Integration Patterns

### Pattern 1: Docker Network Integration

Connect your application services to the genai-vanilla network.

**Parent docker-compose.yml:**

```yaml
version: '3.8'

networks:
  # Connect to genai-vanilla network
  infra-network:
    external: true
    name: myproject-network  # Must match PROJECT_NAME in infra/.env

services:
  my-app:
    build: ./src/backend
    networks:
      - infra-network
    environment:
      # Access infrastructure services by container name
      DATABASE_URL: postgresql://postgres:password@myproject-supabase-db:5432/postgres
      REDIS_URL: redis://:password@myproject-redis:6379
      OLLAMA_URL: http://myproject-ollama:11434
      KONG_URL: http://myproject-kong-api-gateway:8000
    ports:
      - "8080:8080"
    depends_on:
      - myproject-supabase-db  # Ensure infra is running
```

**Start both stacks:**

```bash
# Start infrastructure first
cd infra && ./start.sh && cd ..

# Start your application
docker-compose up -d
```

### Pattern 2: Kong Gateway as Single Entry Point

Use Kong (port 63002) to access all infrastructure services from your application:

```python
# Python example
import requests

KONG_BASE = "http://localhost:63002"

# Access Supabase through Kong
supabase_url = f"{KONG_BASE}/supabase"
response = requests.get(f"{supabase_url}/rest/v1/your-table")

# Access N8N through Kong
n8n_url = f"{KONG_BASE}/n8n"
```

```javascript
// JavaScript example
const KONG_BASE = "http://localhost:63002";

// Access services through Kong
const supabaseUrl = `${KONG_BASE}/supabase`;
const n8nUrl = `${KONG_BASE}/n8n`;
const jupyterUrl = `${KONG_BASE}/jupyterhub`;
```

### Pattern 3: Direct Port Access

Access services directly via their exposed ports:

```python
import os

# Development configuration
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:63004")
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:63001")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:63007")
```

### Pattern 4: Service Extension

Extend infrastructure services with custom functionality:

```yaml
# Parent docker-compose.yml
services:
  custom-processor:
    build: ./src/processor
    networks:
      - infra-network
    environment:
      # Process data from Weaviate
      WEAVIATE_URL: http://myproject-weaviate:8080
      # Store results in Supabase
      SUPABASE_URL: http://myproject-kong-api-gateway:8000/supabase
    volumes:
      - ./data:/data
```

### Complete Integration Example

**scripts/start-all.sh:**

```bash
#!/bin/bash
set -e

echo "Starting infrastructure..."
cd infra && ./start.sh && cd ..

echo "Waiting for services to be ready..."
sleep 10

echo "Starting application services..."
docker-compose up -d

echo "All services started!"
echo "Infrastructure: http://localhost:63002"
echo "Application: http://localhost:8080"
```

**scripts/stop-all.sh:**

```bash
#!/bin/bash

echo "Stopping application services..."
docker-compose down

echo "Stopping infrastructure..."
cd infra && ./stop.sh && cd ..

echo "All services stopped!"
```

## Contributing Back

When using genai-vanilla as a submodule, you can contribute improvements back to the project using the standard git workflow.

### Contribution Workflow

#### 1. Create a Fork

```bash
# Fork the genai-vanilla repository to your account on GitHub
# Then add your fork as a remote (replace with your fork URL)

cd infra
git remote add fork <your-fork-url>
```

#### 2. Create a Feature Branch

```bash
cd infra
git checkout -b feature/my-improvement
```

#### 3. Make Your Changes

```bash
# Edit files in the infra/ directory
vim bootstrapper/start.py

# Test your changes
./start.sh

# Commit your changes
git add .
git commit -m "Add feature: improved startup validation"
```

#### 4. Push to Your Fork

```bash
git push fork feature/my-improvement
```

#### 5. Create Pull Request

- Go to GitHub and create a PR from your fork's branch
- Target the original genai-vanilla repository's `main` branch
- Describe your changes and their benefits

#### 6. Update Submodule After Merge

Once your PR is merged:

```bash
cd infra
git checkout main
git pull origin main

# Update parent repository to track new commit
cd ..
git add infra
git commit -m "Update genai-vanilla submodule to latest version"
```

### Local Customizations vs. Contributions

**Keep as local changes (don't contribute):**
- `.env` configuration
- Project-specific customizations
- Temporary debugging changes

**Consider contributing back:**
- Bug fixes
- New service integrations
- Performance improvements
- Documentation enhancements
- Error handling improvements

### Maintaining Local Customizations

If you need to maintain local customizations while staying up-to-date:

```bash
cd infra

# Create a local customization branch
git checkout -b local-customizations

# Make your custom changes
vim services/custom-service/docker-compose.yml

git add .
git commit -m "Local: Add company-specific service"

# When upstream updates are available
git fetch origin
git rebase origin/main

# Resolve conflicts if any
```

## Troubleshooting

### Issue: Port Conflicts

**Symptom**: Services fail to start due to port already in use.

**Solution 1**: Use custom base port
```bash
./infra/start.sh --base-port 64000
```

**Solution 2**: Stop conflicting services
```bash
# Find what's using the port
lsof -i :63002

# Stop the conflicting service
```

### Issue: Docker Network Already Exists

**Symptom**: Error creating network `${PROJECT_NAME}-network`.

**Solution**: Ensure PROJECT_NAME is unique across your system
```bash
# In infra/.env
PROJECT_NAME=myproject-dev  # Make it unique
```

### Issue: Submodule Not Updating

**Symptom**: Changes from upstream don't appear in your submodule.

**Solution**: Update the submodule explicitly
```bash
cd infra
git checkout main
git pull origin main

cd ..
git add infra
git commit -m "Update submodule"
```

### Issue: Can't Access Services from Application

**Symptom**: Application can't connect to infrastructure services.

**Solution 1**: Verify network connection
```bash
# Check if networks are shared
docker network inspect myproject-network

# Ensure your app service is on the same network
```

**Solution 2**: Use correct hostnames
```bash
# From within Docker: use container names
DATABASE_URL=postgresql://user:pass@myproject-supabase-db:5432/db

# From host machine: use localhost
DATABASE_URL=postgresql://user:pass@localhost:63006/db
```

### Issue: .env Changes Not Taking Effect

**Symptom**: Updated `.env` values don't apply to running services.

**Solution**: Restart with cold start
```bash
./infra/stop.sh
./infra/start.sh --cold
```

### Issue: Permission Denied for Volumes

**Symptom**: Permission errors when services try to write to volumes.

**Solution**: Check volume ownership
```bash
# Fix permissions
sudo chown -R $USER:$USER ./infra/volumes/
```

### Issue: Submodule Shows Modifications

**Symptom**: `git status` shows infra/ as modified even though you didn't change it.

**Solution**: This is normal - the submodule tracks a specific commit
```bash
# See what changed
cd infra
git status

# If you want to keep current version
cd ..
git add infra
git commit -m "Update submodule reference"

# If you want to reset to committed version
git submodule update --init
```

## Advanced Topics

### Running Multiple Infrastructure Stacks

You can run multiple instances of genai-vanilla for different projects:

```bash
# Project 1
cd ~/project1/infra
PROJECT_NAME=project1 ./start.sh --base-port 63000

# Project 2
cd ~/project2/infra
PROJECT_NAME=project2 ./start.sh --base-port 64000
```

Each will have isolated:
- Docker networks
- Docker volumes
- Container names
- Exposed ports

### CI/CD Integration

**GitHub Actions example:**

```yaml
name: Test with Infrastructure

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          submodules: recursive  # Important!

      - name: Start Infrastructure
        run: |
          cd infra
          cp .env.example .env
          echo "PROJECT_NAME=ci-test-${{ github.run_id }}" >> .env
          ./start.sh

      - name: Wait for Services
        run: sleep 30

      - name: Run Tests
        run: |
          npm test

      - name: Stop Infrastructure
        if: always()
        run: cd infra && ./stop.sh
```

### Using with Docker Compose Profiles

Optimize which services start based on your needs:

```bash
# In infra/.env, enable only needed services
SOURCE_SUPABASE=true
SOURCE_REDIS=true
SOURCE_OLLAMA=true

# Disable unused services
SOURCE_COMFYUI=false
SOURCE_DOCLING=false
```

## Best Practices

1. **Pin Submodule Versions**: In production, lock to specific tested commits or tags
   ```bash
   cd infra
   git checkout <commit-hash-or-tag>
   cd ..
   git add infra
   git commit -m "Lock infrastructure to tested version"
   ```

2. **Document Your Configuration**: Add README in parent project explaining infra setup

3. **Backup Your .env**: Keep template with comments for new team members
   ```bash
   # Create template
   cp infra/.env infra/.env.template
   # Add to git (with secrets removed)
   git add infra/.env.template
   ```

4. **Use PROJECT_NAME Consistently**: Match your project name across all configurations

5. **Test Updates in Branches**: Before updating submodule, test in a branch
   ```bash
   git checkout -b update-infra
   cd infra && git pull origin main && cd ..
   # Test everything
   git add infra
   git commit -m "Update infrastructure"
   ```

## Additional Resources

- [Main genai-vanilla README](../../README.md)
- [Source Configuration](source-configuration.md)
- [Git Submodules Documentation](https://git-scm.com/book/en/v2/Git-Tools-Submodules)

## Getting Help

If you encounter issues:

1. Check the [troubleshooting section](#troubleshooting) above
2. Review container logs: `cd infra && docker compose logs`
3. Check the main README and other documentation in `docs/`

---

*This guide is part of the genai-vanilla documentation. For updates and improvements, please contribute back to the project!*
