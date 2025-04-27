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
  echo "                     Supported profiles: default, dev-ollama-local, prod-gpu, fixed"
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
      if [[ -n "$2" && "$2" =~ ^(default|dev-ollama-local|prod-gpu|fixed)$ ]]; then
        PROFILE=$2
        shift 2
      else
        echo "Error: --profile must be one of: default, dev-ollama-local, prod-gpu, fixed"
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

# Unset potentially lingering port environment variables if cold start and custom base port are used
if [[ "$COLD_START" == "true" && "$BASE_PORT" != "$DEFAULT_BASE_PORT" ]]; then
  echo "📋 Unsetting potentially lingering port environment variables..."
  unset SUPABASE_DB_PORT
  unset KONG_HTTP_PORT
  unset KONG_HTTPS_PORT
  unset SUPABASE_META_PORT
  unset SUPABASE_STORAGE_PORT
  unset SUPABASE_AUTH_PORT
  unset SUPABASE_API_PORT
  unset SUPABASE_STUDIO_PORT
  unset GRAPH_DB_PORT
  unset GRAPH_DB_DASHBOARD_PORT
  unset OLLAMA_PORT
  unset OPEN_WEB_UI_PORT
  unset BACKEND_PORT
fi


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
  
  # Backup existing .env with timestamp
  BACKUP_FILE=".env.backup.$(date +%Y%m%d%H%M%S)"
  cp .env "$BACKUP_FILE"
  echo "  • Backed up existing .env to $BACKUP_FILE"
  
  ENV_SOURCE=".env"
fi

# Define port variables that need calculation
PORT_VARS=(
  "SUPABASE_DB_PORT"
  "KONG_HTTP_PORT"
  "KONG_HTTPS_PORT"
  "SUPABASE_META_PORT"
  "SUPABASE_STORAGE_PORT"
  "SUPABASE_AUTH_PORT"
  "SUPABASE_API_PORT"
  "SUPABASE_STUDIO_PORT"
  "GRAPH_DB_PORT"
  "GRAPH_DB_DASHBOARD_PORT"
  "OLLAMA_PORT"
  "OPEN_WEB_UI_PORT"
  "BACKEND_PORT"
)

# Create a temporary file to store non-port variables
TEMP_ENV=$(mktemp)

# Read the source .env file, preserve non-port variables and comments,
# but exclude lines that define port variables, even with comments.
if [[ -f "$ENV_SOURCE" ]]; then
  # Construct a regex pattern to match lines starting with any PORT_VARS followed by =
  # This pattern accounts for potential whitespace and comments after the assignment.
  PORT_VARS_REGEX="^($(IFS=\|; echo "${PORT_VARS[*]}")[[:space:]]*=)"
  
  # Use grep -vE to exclude lines matching the regex
  grep -vE "$PORT_VARS_REGEX" "$ENV_SOURCE" >> "$TEMP_ENV"
fi

# Generate new .env file: copy preserved lines, then add calculated ports
cat "$TEMP_ENV" > .env # Overwrite .env with preserved non-port variables
rm "$TEMP_ENV" # Clean up temporary file

# Append calculated ports to the new .env file
cat >> .env << EOF

# --- Port Assignments (Auto-calculated by start.sh) ---
SUPABASE_DB_PORT=$BASE_PORT
KONG_HTTP_PORT=$(($BASE_PORT + 1))
KONG_HTTPS_PORT=$(($BASE_PORT + 2))
SUPABASE_META_PORT=$(($BASE_PORT + 3))
SUPABASE_STORAGE_PORT=$(($BASE_PORT + 4))
SUPABASE_AUTH_PORT=$(($BASE_PORT + 5))
SUPABASE_API_PORT=$(($BASE_PORT + 6))
SUPABASE_STUDIO_PORT=$(($BASE_PORT + 7))
GRAPH_DB_PORT=$(($BASE_PORT + 8))
GRAPH_DB_DASHBOARD_PORT=$(($BASE_PORT + 9))
OLLAMA_PORT=$(($BASE_PORT + 10))
OPEN_WEB_UI_PORT=$(($BASE_PORT + 11))
BACKEND_PORT=$(($BASE_PORT + 12))
EOF

echo "✅ .env file generated successfully!"

# Read back port values from the .env file to verify they were written correctly
echo "📋 Verifying port assignments from .env file..."
VERIFIED_SUPABASE_DB_PORT=$(grep "^SUPABASE_DB_PORT=" .env | cut -d '=' -f2)
VERIFIED_KONG_HTTP_PORT=$(grep "^KONG_HTTP_PORT=" .env | cut -d '=' -f2)
VERIFIED_KONG_HTTPS_PORT=$(grep "^KONG_HTTPS_PORT=" .env | cut -d '=' -f2)
VERIFIED_SUPABASE_META_PORT=$(grep "^SUPABASE_META_PORT=" .env | cut -d '=' -f2)
VERIFIED_SUPABASE_STORAGE_PORT=$(grep "^SUPABASE_STORAGE_PORT=" .env | cut -d '=' -f2)
VERIFIED_SUPABASE_AUTH_PORT=$(grep "^SUPABASE_AUTH_PORT=" .env | cut -d '=' -f2)
VERIFIED_SUPABASE_API_PORT=$(grep "^SUPABASE_API_PORT=" .env | cut -d '=' -f2)
VERIFIED_SUPABASE_STUDIO_PORT=$(grep "^SUPABASE_STUDIO_PORT=" .env | cut -d '=' -f2)
VERIFIED_GRAPH_DB_PORT=$(grep "^GRAPH_DB_PORT=" .env | cut -d '=' -f2)
VERIFIED_GRAPH_DB_DASHBOARD_PORT=$(grep "^GRAPH_DB_DASHBOARD_PORT=" .env | cut -d '=' -f2)
VERIFIED_OLLAMA_PORT=$(grep "^OLLAMA_PORT=" .env | cut -d '=' -f2)
VERIFIED_OPEN_WEB_UI_PORT=$(grep "^OPEN_WEB_UI_PORT=" .env | cut -d '=' -f2)
VERIFIED_BACKEND_PORT=$(grep "^BACKEND_PORT=" .env | cut -d '=' -f2)

# Display port assignments in a cleaner format with aligned port numbers
echo ""
echo "🚀 PORT ASSIGNMENTS (verified from .env file):"
printf "  • %-35s %s\n" "Supabase PostgreSQL Database:" "$VERIFIED_SUPABASE_DB_PORT"
printf "  • %-35s %s\n" "Kong HTTP Gateway:" "$VERIFIED_KONG_HTTP_PORT"
printf "  • %-35s %s\n" "Kong HTTPS Gateway:" "$VERIFIED_KONG_HTTPS_PORT"
printf "  • %-35s %s\n" "Supabase Meta Service:" "$VERIFIED_SUPABASE_META_PORT"
printf "  • %-35s %s\n" "Supabase Storage Service:" "$VERIFIED_SUPABASE_STORAGE_PORT"
printf "  • %-35s %s\n" "Supabase Auth Service:" "$VERIFIED_SUPABASE_AUTH_PORT"
printf "  • %-35s %s\n" "Supabase API (PostgREST):" "$VERIFIED_SUPABASE_API_PORT"
printf "  • %-35s %s\n" "Supabase Studio Dashboard:" "$VERIFIED_SUPABASE_STUDIO_PORT"
printf "  • %-35s %s\n" "Neo4j Graph Database (Bolt):" "$VERIFIED_GRAPH_DB_PORT"
printf "  • %-35s %s\n" "Neo4j Graph Database (Dashboard):" "$VERIFIED_GRAPH_DB_DASHBOARD_PORT"
printf "  • %-35s %s\n" "Ollama API:" "$VERIFIED_OLLAMA_PORT"
printf "  • %-35s %s\n" "Open Web UI:" "$VERIFIED_OPEN_WEB_UI_PORT"
printf "  • %-35s %s\n" "Backend API:" "$VERIFIED_BACKEND_PORT"
echo ""
echo "📋 Access Points:"
printf "  • %-20s %s\n" "Supabase Studio:" "http://localhost:$VERIFIED_SUPABASE_STUDIO_PORT"
printf "  • %-20s %s\n" "Kong HTTP Gateway:" "http://localhost:$VERIFIED_KONG_HTTP_PORT"
printf "  • %-20s %s\n" "Kong HTTPS Gateway:" "https://localhost:$VERIFIED_KONG_HTTPS_PORT"
printf "  • %-20s %s\n" "Neo4j Browser:" "http://localhost:$VERIFIED_GRAPH_DB_DASHBOARD_PORT"
printf "  • %-20s %s\n" "Open Web UI:" "http://localhost:$VERIFIED_OPEN_WEB_UI_PORT"
printf "  • %-20s %s\n" "Backend API:" "http://localhost:$VERIFIED_BACKEND_PORT/docs"
echo ""

# Start the stack with the selected profile
echo "🔄 Starting the stack with profile: $PROFILE"

# Aggressively clean Docker environment to prevent caching issues
echo "  • Performing deep clean of Docker environment..."

if [[ "$PROFILE" == "default" ]]; then
  # Stop and remove containers from previous runs
  echo "    - Stopping and removing containers..."
  echo "      Command: $DOCKER_COMPOSE_CMD down --remove-orphans"
  $DOCKER_COMPOSE_CMD down --remove-orphans
  
  # Remove volumes if cold start is requested
  if [[ "$COLD_START" == "true" ]]; then
    echo "    - Removing volumes (cold start)..."
    echo "      Command: $DOCKER_COMPOSE_CMD down -v"
    $DOCKER_COMPOSE_CMD down -v

    # Add explicit network removal for cold start
    echo "    - Removing project network (cold start)..."
    echo "      Command: docker network rm ${PROJECT_NAME}_backend-bridge-network"
    docker network rm ${PROJECT_NAME}_backend-bridge-network || true # Use || true to prevent script from exiting if network doesn't exist

    # Add more aggressive system prune for cold start
    echo "    - Performing aggressive Docker system prune (cold start)..."
    echo "      Command: docker system prune --volumes -f"
    docker system prune --volumes -f
  fi
  
  # Prune Docker system to remove any cached configurations
  # This prune is less aggressive and runs even without --cold for general cleanup
  echo "    - Performing general Docker system prune..."
  echo "      Command: docker system prune -f"
  docker system prune -f
  
  # Small delay to ensure everything is cleaned up
  sleep 2
  
  # Start with a completely fresh build
  echo "  • Starting containers with new configuration..."
  echo "    - Building images without cache..."
  # Force Docker to use the updated environment file by explicitly passing it
  echo "      Command: $DOCKER_COMPOSE_CMD --env-file=.env build --no-cache"
  $DOCKER_COMPOSE_CMD --env-file=.env build --no-cache
  
  echo "    - Starting containers..."
  # Force Docker to use the updated environment file by explicitly passing it
  # Added --force-recreate to ensure containers are recreated with new port settings
  echo "      Command: $DOCKER_COMPOSE_CMD --env-file=.env up -d --force-recreate"
  $DOCKER_COMPOSE_CMD --env-file=.env up -d --force-recreate

  # Show the actual port mappings to verify
  echo ""
  echo "🔍 Verifying port mappings from Docker..."
  echo "  Command: $DOCKER_COMPOSE_CMD ps"
  $DOCKER_COMPOSE_CMD ps
  
  # Verify actual port mappings against expected values
  echo ""
  echo "🔍 Checking if Docker assigned the expected ports..."
  
  # Define services and their internal ports to check
  # Using simple arrays instead of associative arrays for better compatibility
  SERVICES=(
    "supabase-db:5432:$VERIFIED_SUPABASE_DB_PORT"
    "supabase-meta:8080:$VERIFIED_SUPABASE_META_PORT"
    "supabase-storage:5000:$VERIFIED_SUPABASE_STORAGE_PORT"
    "supabase-auth:9999:$VERIFIED_SUPABASE_AUTH_PORT"
    "supabase-api:3000:$VERIFIED_SUPABASE_API_PORT"
    "supabase-studio:3000:$VERIFIED_SUPABASE_STUDIO_PORT"
    "neo4j-graph-db:7687:$VERIFIED_GRAPH_DB_PORT"
    "open-web-ui:8080:$VERIFIED_OPEN_WEB_UI_PORT"
    "backend:8000:$VERIFIED_BACKEND_PORT"
    "kong-api-gateway:8000:$VERIFIED_KONG_HTTP_PORT"
    "kong-api-gateway:8443:$VERIFIED_KONG_HTTPS_PORT"
  )
  
  # If using default profile, Ollama is included
  if [[ "$PROFILE" == "default" ]]; then
    SERVICES+=("ollama:11434:$VERIFIED_OLLAMA_PORT")
  fi
  
  # Check each service
  for SERVICE_INFO in "${SERVICES[@]}"; do
    IFS=':' read -r SERVICE INTERNAL_PORT EXPECTED_PORT <<< "$SERVICE_INFO"
    
    # Get the actual port mapping from Docker - with improved error handling
    ACTUAL_PORT=$($DOCKER_COMPOSE_CMD port "$SERVICE" "$INTERNAL_PORT" 2>/dev/null | grep -oE '[0-9]+$' || echo "")
    
    if [[ -z "$ACTUAL_PORT" ]]; then
      echo "  • ❌ $SERVICE: Could not determine port mapping"
    elif [[ "$ACTUAL_PORT" == "$EXPECTED_PORT" ]]; then
      echo "  • ✅ $SERVICE: Using expected port $EXPECTED_PORT"
    else
      echo "  • ⚠️  $SERVICE: Expected port $EXPECTED_PORT but got $ACTUAL_PORT"
    fi
  done
  echo ""
  
  # Show logs
  echo ""
  echo "📋 Container logs (press Ctrl+C to exit):"
  echo "  Command: $DOCKER_COMPOSE_CMD logs -f"
  $DOCKER_COMPOSE_CMD logs -f
else
  # Stop and remove containers from previous runs
  echo "    - Stopping and removing containers..."
  $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE down --remove-orphans
  
  # Remove volumes if cold start is requested
  if [[ "$COLD_START" == "true" ]]; then
    echo "    - Removing volumes (cold start)..."
    $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE down -v

    # Add explicit network removal for cold start
    echo "    - Removing project network (cold start)..."
    echo "      Command: docker network rm ${PROJECT_NAME}_backend-bridge-network"
    docker network rm ${PROJECT_NAME}_backend-bridge-network || true # Use || true to prevent script from exiting if network doesn't exist

    # Add more aggressive system prune for cold start
    echo "    - Performing aggressive Docker system prune (cold start)..."
    echo "      Command: docker system prune --volumes -f"
    docker system prune --volumes -f
  fi
  
  # Prune Docker system to remove any cached configurations
  # This prune is less aggressive and runs even without --cold for general cleanup
  echo "    - Performing general Docker system prune..."
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
  # Added --force-recreate to ensure containers are recreated with new port settings
  $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file=.env up -d --force-recreate

  # Show the actual port mappings to verify
  echo ""
  echo "🔍 Verifying port mappings from Docker..."
  $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE ps
  
  # Verify actual port mappings against expected values
  echo ""
  echo "🔍 Checking if Docker assigned the expected ports..."
  
  # Define services and their internal ports to check
  # Using simple arrays instead of associative arrays for better compatibility
  SERVICES=(
    "supabase-db:5432:$VERIFIED_SUPABASE_DB_PORT"
    "supabase-meta:8080:$VERIFIED_SUPABASE_META_PORT"
    "supabase-storage:5000:$VERIFIED_SUPABASE_STORAGE_PORT"
    "supabase-auth:9999:$VERIFIED_SUPABASE_AUTH_PORT"
    "supabase-api:3000:$VERIFIED_SUPABASE_API_PORT"
    "supabase-studio:3000:$VERIFIED_SUPABASE_STUDIO_PORT"
    "neo4j-graph-db:7687:$VERIFIED_GRAPH_DB_PORT"
    "open-web-ui:8080:$VERIFIED_OPEN_WEB_UI_PORT"
    "backend:8000:$VERIFIED_BACKEND_PORT"
    "kong-api-gateway:8000:$VERIFIED_KONG_HTTP_PORT"
    "kong-api-gateway:8443:$VERIFIED_KONG_HTTPS_PORT"
  )
  
  # If using prod-gpu profile, Ollama is included
  if [[ "$PROFILE" == "prod-gpu" ]]; then
    SERVICES+=("ollama:11434:$VERIFIED_OLLAMA_PORT")
  fi
  
  # Check each service
  for SERVICE_INFO in "${SERVICES[@]}"; do
    IFS=':' read -r SERVICE INTERNAL_PORT EXPECTED_PORT <<< "$SERVICE_INFO"
    
    # Get the actual port mapping from Docker - with improved error handling
    ACTUAL_PORT=$($DOCKER_COMPOSE_CMD -f $COMPOSE_FILE port "$SERVICE" "$INTERNAL_PORT" 2>/dev/null | grep -oE '[0-9]+$' || echo "")
    
    if [[ -z "$ACTUAL_PORT" ]]; then
      echo "  • ❌ $SERVICE: Could not determine port mapping"
    elif [[ "$ACTUAL_PORT" == "$EXPECTED_PORT" ]]; then
      echo "  • ✅ $SERVICE: Using expected port $EXPECTED_PORT"
    else
      echo "  • ⚠️  $SERVICE: Expected port $EXPECTED_PORT but got $ACTUAL_PORT"
    fi
  done
  echo ""
  
  # Show logs
  echo ""
  echo "📋 Container logs (press Ctrl+C to exit):"
  $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE logs -f
fi
