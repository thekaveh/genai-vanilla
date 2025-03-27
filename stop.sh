#!/usr/bin/env bash
# Cross-platform script to stop the GenAI Vanilla Stack

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

# Stop the stack with the selected profile
echo "🔄 Stopping containers..."
if [[ "$COLD_STOP" == "true" ]]; then
  echo "   and removing volumes (data will be lost)..."
  if [[ "$PROFILE" == "default" ]]; then
    docker compose --env-file=.env down --volumes --remove-orphans
  else
    docker compose -f $COMPOSE_FILE --env-file=.env down --volumes --remove-orphans
  fi
  echo "✅ Stack stopped and volumes removed."
else
  if [[ "$PROFILE" == "default" ]]; then
    docker compose --env-file=.env down --remove-orphans
  else
    docker compose -f $COMPOSE_FILE --env-file=.env down --remove-orphans
  fi
  echo "✅ Stack stopped. Data volumes preserved."
fi

echo "   To restart the stack, run: ./start.sh [options]"
