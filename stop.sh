#!/usr/bin/env bash
# Cross-platform script to stop the GenAI Vanilla Stack

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

# Function to execute docker compose with multiple files
execute_compose_cmd() {
  local cmd_args=""
  IFS=':' read -ra FILES <<< "$COMPOSE_FILES"
  for file in "${FILES[@]}"; do
    cmd_args="$cmd_args -f $file"
  done
  $DOCKER_COMPOSE_CMD $cmd_args "$@"
}

# Default values
DEFAULT_PROFILE="default"
COLD_STOP=false

# Function to show usage
show_usage() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --profile PROFILE  Set the deployment profile (default: $DEFAULT_PROFILE)"
  echo "                     Supported profiles: default, ai-local, ai-gpu"
  echo "  --cold             Remove volumes (data will be lost)"
  echo "  --help             Show this help message"
}

# Parse command line arguments
PROFILE=$DEFAULT_PROFILE

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --profile)
      if [[ -n "$2" && "$2" =~ ^(default|ai-local|ai-gpu)$ ]]; then
        PROFILE=$2
        shift 2
      else
        echo "Error: --profile must be one of: default, ai-local, ai-gpu"
        show_usage
        exit 1
      fi
      ;;
    --cold)
      COLD_STOP=true
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

# Determine Docker Compose files based on profile
COMPOSE_FILES="docker-compose.yml:compose-profiles/data.yml"
if [[ "$PROFILE" == "default" ]]; then
  COMPOSE_FILES="$COMPOSE_FILES:compose-profiles/ai.yml:compose-profiles/apps.yml"
elif [[ "$PROFILE" == "ai-local" ]]; then
  COMPOSE_FILES="$COMPOSE_FILES:compose-profiles/ai-local.yml:compose-profiles/apps-local.yml"
elif [[ "$PROFILE" == "ai-gpu" ]]; then
  COMPOSE_FILES="$COMPOSE_FILES:compose-profiles/ai-gpu.yml:compose-profiles/apps-gpu.yml"
fi

echo "🛑 Stopping GenAI Vanilla Stack"
echo "  • Profile: $PROFILE"
echo "  • Compose Files: $COMPOSE_FILES"
if [[ "$COLD_STOP" == "true" ]]; then
  echo "  • Cold Stop: Yes (removing volumes)"
fi
echo ""

# Explicitly verify and indicate the env file is being used
if [[ -f .env ]]; then
  echo "• Found .env file with timestamp: $(stat -c %y .env 2>/dev/null || stat -f %m .env 2>/dev/null)"
fi

echo "• Using Docker Compose command: $DOCKER_COMPOSE_CMD"
echo ""

# Stop the stack with the selected profile
echo "🔄 Stopping containers..."
if [[ "$COLD_STOP" == "true" ]]; then
  echo "   and removing volumes (data will be lost)..."
  execute_compose_cmd --env-file=.env down --volumes --remove-orphans
  echo ""
  echo "✅ Stack stopped and volumes removed."
else
  execute_compose_cmd --env-file=.env down --remove-orphans
  echo ""
  echo "✅ Stack stopped. Data volumes preserved."
fi

echo ""
echo "📋 To restart the stack, run: ./start.sh [options]"
echo "   Example: ./start.sh --base-port 64567 --profile $PROFILE"
