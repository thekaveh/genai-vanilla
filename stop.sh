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

# Default values
DEFAULT_PROFILE="default"
COLD_STOP=false

# Function to show usage
show_usage() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --profile PROFILE  Set the deployment profile (default: $DEFAULT_PROFILE)"
  echo "                     Supported profiles: default, dev-ollama-local, prod-gpu"
  echo "  --cold             Remove volumes (data will be lost)"
  echo "  --help             Show this help message"
}

# Parse command line arguments
PROFILE=$DEFAULT_PROFILE

while [[ "$#" -gt 0 ]]; do
  case $1 in
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

# Determine Docker Compose file based on profile
COMPOSE_FILE="docker-compose.yml"
if [[ "$PROFILE" != "default" ]]; then
  COMPOSE_FILE="docker-compose.$PROFILE.yml"
fi

echo "🛑 Stopping GenAI Vanilla Stack"
echo "  • Profile: $PROFILE"
echo "  • Compose File: $COMPOSE_FILE"
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
  if [[ "$PROFILE" == "default" ]]; then
    $DOCKER_COMPOSE_CMD --env-file=.env down --volumes --remove-orphans
  else
    $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file=.env down --volumes --remove-orphans
  fi
  echo ""
  echo "✅ Stack stopped and volumes removed."
else
  if [[ "$PROFILE" == "default" ]]; then
    $DOCKER_COMPOSE_CMD --env-file=.env down --remove-orphans
  else
    $DOCKER_COMPOSE_CMD -f $COMPOSE_FILE --env-file=.env down --remove-orphans
  fi
  echo ""
  echo "✅ Stack stopped. Data volumes preserved."
fi

echo ""
echo "📋 To restart the stack, run: ./start.sh [options]"
echo "   Example: ./start.sh --base-port 64567 --profile $PROFILE"
