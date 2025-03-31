#!/usr/bin/env bash
# Cross-platform script to start the GenAI Vanilla Stack with configurable ports and profile

# Function to detect available docker compose command
detect_docker_compose_cmd() {
  if command -v docker &> /dev/null; then
    if docker compose version &> /dev/null; then
      echo "docker compose"
    elif command -v docker-compose &> /dev/null; then
      echo "docker-compose"
    else
      echo "Error: Neither 'docker compose' nor 'docker-compose' command is available."
      exit 1
    fi
  else
    echo "Error: Docker is not installed or not in PATH."
    exit 1
  fi
}

# Store the detected command in a variable
DOCKER_COMPOSE_CMD=$(detect_docker_compose_cmd)

# Default values
DEFAULT_BASE_PORT=63000
DEFAULT_PROFILE="default"
COLD_START=false

# Function to show usage
show_usage() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --base-port PORT   Set the base port number (default: $DEFAULT_BASE_PORT)"
  echo "  --profile PROFILE  Set the deployment profile (default: $DEFAULT_PROFILE)"
  echo "                     Supported profiles: default, dev-ollama-local, prod-gpu"
  echo "  --cold             Force creation of new .env file and generate new keys"
  echo "  --help             Show this help message"
}

# Parse command line arguments
BASE_PORT=$DEFAULT_BASE_PORT
PROFILE=$DEFAULT_PROFILE

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --base-port)
      if [[ -n "$2" && "$2" =~ ^[0-9]+$ ]]; then
        BASE_PORT=$2
        shift 2
      else
        echo "Error: --base-port requires a numeric argument"
        show_usage
        exit 1
      fi
      ;;
    --profile)
      if [[ -n "$2" && "$2" =~ ^(default|dev-ollama-local|prod-gpu)$ ]]; then
        PROFILE=$2
        shift 2
      else
        echo "Error: --profile must be one of: default, dev-ollama-local, prod-gpu"
        show_usage
        exit 1
      fi
      ;;
    --cold)
      COLD_START=true
      shift
      ;;
    --help)
      show_usage
      exit 0
      ;;
    *)
      echo "Unknown parameter: $1"
      show_usage
      exit 1
      ;;
  esac
done

# Since port issues can sometimes persist due to Docker's caching, let's
# explicitly verify and indicate the env file is being used
if [[ -f .env ]]; then
  echo "• Found .env file with timestamp: $(stat -c %y .env 2>/dev/null || stat -f %m .env 2>/dev/null)"
fi

echo "• Using Docker Compose command: $DOCKER_COMPOSE_CMD"

# Determine Docker Compose file based on profile
COMPOSE_FILE="docker-compose.yml"
if [[ "$PROFILE" != "default" ]]; then
  COMPOSE_FILE="docker-compose.$PROFILE.yml"
fi

echo "🚀 Starting GenAI Vanilla Stack with:"
echo "  • Base Port: $BASE_PORT"
echo "  • Profile: $PROFILE"
echo "  • Compose File: $COMPOSE_FILE"
echo "  • Using .env file: YES (--env-file=.env flag will be used)"
if [[ "$COLD_START" == "true" ]]; then
  echo "  • Cold Start: Yes (forcing new environment setup)"
fi
echo ""

# Check if .env exists, if not or if cold start is requested, create from .env.example
if [[ ! -f .env || "$COLD_START" == "true" ]]; then
  echo "📋 Setting up environment..."
  if [[ -f .env && "$COLD_START" == "true" ]]; then
    echo "  • Cold start requested, backing up existing .env to .env.backup.$(date +%Y%m%d%H%M%S)"
    cp .env ".env.backup.$(date +%Y%m%d%H%M%S)"
  fi
  
  echo "  • Creating new .env file from .env.example"
  cp .env.example .env
  
  # Check if generate_supabase_keys.sh exists and is executable
  if [[ -f ./generate_supabase_keys.sh && -x ./generate_supabase_keys.sh ]]; then
    echo "  • Generating Supabase keys..."
    ./generate_supabase_keys.sh
    echo "  • Supabase keys generated successfully"
  else
    echo "  • ⚠️  Warning: generate_supabase_keys.sh not found or not executable"
    echo "    Please run 'chmod +x generate_supabase_keys.sh' and then './generate_supabase_keys.sh'"
    echo "    to generate the required JWT keys for Supabase services."
  fi
  
  ENV_SOURCE=".env"
else
  echo "📝 Updating .env file with base port $BASE_PORT..."
  
  # Backup existing .env
  cp .env .env.backup
  echo "  • Backed up existing .env to .env.backup"
  
  ENV_SOURCE=".env"
fi

# Extract important non-port variables
PROJECT_NAME=$(grep "^PROJECT_NAME=" $ENV_SOURCE | cut -d '=' -f2)
SUPABASE_DB_USER=$(grep "^SUPABASE_DB_USER=" $ENV_SOURCE | cut -d '=' -f2)
SUPABASE_DB_PASSWORD=$(grep "^SUPABASE_DB_PASSWORD=" $ENV_SOURCE | cut -d '=' -f2)
SUPABASE_DB_NAME=$(grep "^SUPABASE_DB_NAME=" $ENV_SOURCE | cut -d '=' -f2)
SUPABASE_DB_APP_USER=$(grep "^SUPABASE_DB_APP_USER=" $ENV_SOURCE | cut -d '=' -f2)
SUPABASE_DB_APP_PASSWORD=$(grep "^SUPABASE_DB_APP_PASSWORD=" $ENV_SOURCE | cut -d '=' -f2)
SUPABASE_JWT_SECRET=$(grep "^SUPABASE_JWT_SECRET=" $ENV_SOURCE | cut -d '=' -f2)
SUPABASE_ANON_KEY=$(grep "^SUPABASE_ANON_KEY=" $ENV_SOURCE | cut -d '=' -f2)
SUPABASE_SERVICE_KEY=$(grep "^SUPABASE_SERVICE_KEY=" $ENV_SOURCE | cut -d '=' -f2)
GRAPH_DB_USER=$(grep "^GRAPH_DB_USER=" $ENV_SOURCE | cut -d '=' -f2)
GRAPH_DB_PASSWORD=$(grep "^GRAPH_DB_PASSWORD=" $ENV_SOURCE | cut -d '=' -f2)
GRAPH_DB_AUTH=$(grep "^GRAPH_DB_AUTH=" $ENV_SOURCE | cut -d '=' -f2)
OPEN_WEB_UI_SECRET_KEY=$(grep "^OPEN_WEB_UI_SECRET_KEY=" $ENV_SOURCE | cut -d '=' -f2)
PROD_ENV_CPUS=$(grep "^PROD_ENV_CPUS=" $ENV_SOURCE | cut -d '=' -f2)
PROD_ENV_MEM_LIMIT=$(grep "^PROD_ENV_MEM_LIMIT=" $ENV_SOURCE | cut -d '=' -f2)

# Generate new .env file with calculated ports
cat > .env << EOF
# GenAI Vanilla Stack - Environment Variables
# Auto-generated by start.sh with base port $BASE_PORT

# Docker Compose Configuration
PROJECT_NAME=$PROJECT_NAME

# Service Endpoints (for external services)
# Uncomment and set these when using external services
# SUPABASE_DB_HOST=
# SUPABASE_STUDIO_HOST=

# Supabase Database Configuration
SUPABASE_DB_PORT=$BASE_PORT
SUPABASE_DB_USER=$SUPABASE_DB_USER
SUPABASE_DB_PASSWORD=$SUPABASE_DB_PASSWORD
SUPABASE_DB_NAME=$SUPABASE_DB_NAME
# Additional DB users (for application use)
SUPABASE_DB_APP_USER=$SUPABASE_DB_APP_USER
SUPABASE_DB_APP_PASSWORD=$SUPABASE_DB_APP_PASSWORD

# Supabase Meta Configuration
SUPABASE_META_PORT=$(($BASE_PORT + 1))

# Supabase authentication configuration
SUPABASE_AUTH_PORT=$(($BASE_PORT + 2))
# IMPORTANT: Run ./generate_supabase_keys.sh to automatically generate these keys
# The script will update this file with secure values for all three keys below
SUPABASE_JWT_SECRET=$SUPABASE_JWT_SECRET
SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY
SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY

# Supabase API (PostgREST) Configuration
SUPABASE_API_PORT=$(($BASE_PORT + 3))

# Supabase Studio Configuration
SUPABASE_STUDIO_PORT=$(($BASE_PORT + 4))

# Graph Database (Neo4j) Configuration
GRAPH_DB_HOST=graph-db
GRAPH_DB_PORT=$(($BASE_PORT + 5))
GRAPH_DB_DASHBOARD_PORT=$(($BASE_PORT + 6))
GRAPH_DB_USER=$GRAPH_DB_USER
GRAPH_DB_PASSWORD=$GRAPH_DB_PASSWORD
# Neo4j format: username/password
GRAPH_DB_AUTH=$GRAPH_DB_AUTH

# Ollama Configuration
OLLAMA_PORT=$(($BASE_PORT + 7))

# OpenWebUI Configuration
OPEN_WEB_UI_PORT=$(($BASE_PORT + 8))
OPEN_WEB_UI_SECRET_KEY=$OPEN_WEB_UI_SECRET_KEY

# Backend Configuration
BACKEND_PORT=$(($BASE_PORT + 9))

# GPU configuration for prod-gpu flavor
PROD_ENV_CPUS=$PROD_ENV_CPUS
PROD_ENV_MEM_LIMIT=$PROD_ENV_MEM_LIMIT
EOF

echo "✅ .env file generated successfully!"

# Display fancy port assignment table
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                     🚀 PORT ASSIGNMENTS 🚀                     ║"
echo "╠════════════════════════════════════════╦═══════════════════════╣"
echo "║ Service                                ║ Port                  ║"
echo "╠════════════════════════════════════════╬═══════════════════════╣"
echo "║ Supabase PostgreSQL Database           ║ $BASE_PORT            ║"
echo "║ Supabase Meta Service                  ║ $(($BASE_PORT + 1))   ║"
echo "║ Supabase Auth Service                  ║ $(($BASE_PORT + 2))   ║"
echo "║ Supabase API (PostgREST)               ║ $(($BASE_PORT + 3))   ║"
echo "║ Supabase Studio Dashboard              ║ $(($BASE_PORT + 4))   ║"
echo "║ Neo4j Graph Database (Bolt)            ║ $(($BASE_PORT + 5))   ║"
echo "║ Neo4j Graph Database (Dashboard)       ║ $(($BASE_PORT + 6))   ║"
echo "║ Ollama API                             ║ $(($BASE_PORT + 7))   ║"
echo "║ Open Web UI                            ║ $(($BASE_PORT + 8))   ║"
echo "║ Backend API                            ║ $(($BASE_PORT + 9))   ║"
echo "╚════════════════════════════════════════╩═══════════════════════╝"
echo ""
echo "📋 Access Points:"
echo "  • Supabase Studio: http://localhost:$(($BASE_PORT + 4))"
echo "  • Neo4j Browser: http://localhost:$(($BASE_PORT + 6))"
echo "  • Open Web UI: http://localhost:$(($BASE_PORT + 8))"
echo "  • Backend API: http://localhost:$(($BASE_PORT + 9))/docs"
echo ""

# Start the stack with the selected profile
echo "🔄 Starting the stack with profile: $PROFILE"

# Aggressively clean Docker environment to prevent caching issues
echo "  • Performing deep clean of Docker environment..."

if [[ "$PROFILE" == "default" ]]; then
  # Stop and remove containers from previous runs
  echo "    - Stopping and removing containers..."
  $DOCKER_COMPOSE_CMD down --remove-orphans
  
  # Remove volumes if cold start is requested
  if [[ "$COLD_START" == "true" ]]; then
    echo "    - Removing volumes (cold start)..."
    $DOCKER_COMPOSE_CMD down -v
  fi
  
  # Prune Docker system to remove any cached configurations
  echo "    - Pruning Docker system..."
  docker system prune -f
  
  # Small delay to ensure everything is cleaned up
  sleep 2
  
  # Start with a completely fresh build
  echo "  • Starting containers with new configuration..."
  echo "    - Building images without cache..."
  # Force Docker to use the updated environment file by explicitly passing it
  $DOCKER_COMPOSE_CMD --env-file=.env build --no-cache
  
  echo "    - Starting containers..."
  # Force Docker to use the updated environment file by explicitly passing it
  $DOCKER_COMPOSE_CMD --env-file=.env up -d
  
  # Show the actual port mappings to verify
  echo ""
  echo "🔍 Verifying port mappings..."
  $DOCKER_COMPOSE_CMD ps
  
  # Show logs
  echo ""
  echo "📋 Container logs (press Ctrl+C to exit):"
  $DOCKER_COMPOSE_CMD logs -f
else
  # Stop and remove containers from previous runs
  echo "    - Stopping and removing containers..."
  $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE down --remove-orphans
  
  # Remove volumes if cold start is requested
  if [[ "$COLD_START" == "true" ]]; then
    echo "    - Removing volumes (cold start)..."
    $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE down -v
  fi
  
  # Prune Docker system to remove any cached configurations
  echo "    - Pruning Docker system..."
  docker system prune -f
  
  # Small delay to ensure everything is cleaned up
  sleep 2
  
  # Start with a completely fresh build
  echo "  • Starting containers with new configuration..."
  echo "    - Building images without cache..."
  # Force Docker to use the updated environment file by explicitly passing it
  $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file=.env build --no-cache
  
  echo "    - Starting containers..."
  # Force Docker to use the updated environment file by explicitly passing it
  $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file=.env up -d
  
  # Show the actual port mappings to verify
  echo ""
  echo "🔍 Verifying port mappings..."
  $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE ps
  
  # Show logs
  echo ""
  echo "📋 Container logs (press Ctrl+C to exit):"
  $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE logs -f
fi
