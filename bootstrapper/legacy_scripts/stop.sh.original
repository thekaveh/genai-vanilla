#!/usr/bin/env bash
# Cross-platform script to stop the GenAI Vanilla Stack

# Source hosts utilities from new location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config/scripts/hosts-utils.sh" 2>/dev/null || {
  echo "Warning: Could not load hosts-utils.sh"
}

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
COLD_STOP=false
CLEAN_HOSTS=false

# Function to show usage
show_usage() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --cold             Remove volumes (data will be lost)"
  echo "  --clean-hosts      Remove GenAI Stack hosts file entries (requires sudo/admin)"
  echo "  --help             Show this help message"
  echo ""
  echo "Examples:"
  echo "  $0                 # Stop all containers, preserve data"
  echo "  $0 --cold          # Stop all containers and remove all data volumes"
  echo "  $0 --clean-hosts   # Stop containers and clean up hosts file"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --cold)
      COLD_STOP=true
      shift
      ;;
    --clean-hosts)
      CLEAN_HOSTS=true
      shift
      ;;
    --help)
      show_usage
      exit 0
      ;;
    *)
      echo "❌ Unknown option: $1"
      show_usage
      exit 1
      ;;
  esac
done

echo "🛑 Stopping GenAI Vanilla Stack..."
echo ""

# Check if .env file exists and show detailed information
if [[ -f .env ]]; then
  echo "📋 Environment Configuration:"
  echo "  • Found .env file with timestamp: $(stat -c %y .env 2>/dev/null || stat -f %m .env 2>/dev/null)"
  
  # Get project name from .env file
  if grep -q "^PROJECT_NAME=" .env; then
    PROJECT_NAME=$(grep "^PROJECT_NAME=" .env | cut -d'=' -f2 | sed 's/[\"'\'']*//g')
    echo "  • Project name: $PROJECT_NAME"
  fi
else
  echo "⚠️ .env file not found. Using default configuration."
  PROJECT_NAME="genai"
fi

echo "  • Using Docker Compose command: $DOCKER_COMPOSE_CMD"
if [[ "$COLD_STOP" == true ]]; then
  echo "  • Cold Stop: Yes (removing volumes and aggressive cleanup)"
fi
if [[ "$CLEAN_HOSTS" == true ]]; then
  echo "  • Clean Hosts: Yes (will remove hosts file entries)"
fi
echo ""
# Function to execute compose command with proper error handling
execute_compose_cmd() {
  echo "      Command: $DOCKER_COMPOSE_CMD --env-file=.env $*"
  if [[ -f .env ]]; then
    $DOCKER_COMPOSE_CMD --env-file=.env "$@"
  else
    $DOCKER_COMPOSE_CMD "$@"
  fi
}

echo "🐳 Stopping Docker Compose services..."

# Stop containers and optionally remove volumes
if [[ "$COLD_STOP" == true ]]; then
  echo "🗑️ Performing cold stop (removing volumes and aggressive cleanup)..."
  echo "⚠️ WARNING: This will permanently delete all data!"
  echo ""
  
  # Stop and remove everything including volumes
  echo "    - Stopping containers and removing volumes..."
  execute_compose_cmd down --volumes --remove-orphans
  
  # Additional cleanup for cold stop
  echo "    - Removing project networks..."
  docker network rm ${PROJECT_NAME}_backend-bridge-network 2>/dev/null || true
  
  echo "    - Performing Docker system cleanup..."
  echo "      Command: docker system prune --volumes -f"
  docker system prune --volumes -f
  
  if [[ $? -eq 0 ]]; then
    echo "✅ Cold stop completed successfully - all containers stopped and data removed"
  else
    echo "⚠️ Some issues occurred during cold stop"
  fi
else
  echo "🔄 Performing standard stop (preserving volumes)..."
  execute_compose_cmd down --remove-orphans
  
  if [[ $? -eq 0 ]]; then
    echo "✅ All containers stopped successfully - data volumes preserved"
  else
    echo "⚠️ Some issues occurred while stopping containers"
  fi
fi

# Clean up hosts file entries if requested
if [[ "$CLEAN_HOSTS" == true ]]; then
  echo ""
  echo "🧹 Cleaning up hosts file entries..."
  
  # Check if hosts utilities are available
  if command -v detect_os &> /dev/null && command -v get_hosts_file &> /dev/null; then
    OS=$(detect_os)
    HOSTS_FILE=$(get_hosts_file)
    
    if [[ -z "$HOSTS_FILE" || ! -f "$HOSTS_FILE" ]]; then
      echo "⚠️  Could not locate hosts file for OS: $OS"
      echo "   Manual cleanup may be required for subdomain access"
    else
      # Check if we have elevated privileges
      if command -v is_elevated &> /dev/null && is_elevated; then
        if command -v remove_hosts_entries &> /dev/null; then
          echo "  • Removing GenAI Stack hosts file entries..."
          if remove_hosts_entries "$HOSTS_FILE"; then
            echo "✅ Hosts entries removed successfully"
            echo "   The following entries were removed:"
            if command -v get_genai_hosts &> /dev/null; then
              for host in $(get_genai_hosts); do
                echo "   127.0.0.1 $host"
              done
            fi
          else
            echo "❌ Failed to remove hosts entries"
          fi
        else
          echo "⚠️ remove_hosts_entries function not available"
        fi
      else
        echo "❌ --clean-hosts requires elevated privileges"
        if [[ "$OS" == "windows" ]]; then
          echo "   Please run as Administrator"
        else
          echo "   Please run with: sudo $0 --clean-hosts"
        fi
        echo "   Or manually remove these entries from $HOSTS_FILE:"
        if command -v get_genai_hosts &> /dev/null; then
          for host in $(get_genai_hosts); do
            echo "   127.0.0.1 $host"
          done
        fi
      fi
    fi
  else
    echo "⚠️ Hosts utilities not available (hosts-utils.sh not loaded)"
    echo "   Manual cleanup may be required in your hosts file for:"
    echo "   - api.localhost"
    echo "   - n8n.localhost" 
    echo "   - comfyui.localhost"
    echo "   And other GenAI Stack subdomains"
  fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ "$COLD_STOP" == true ]]; then
  echo "🎯 GenAI Vanilla Stack stopped with complete data cleanup"
  echo "   ✅ All containers stopped and removed"
  echo "   ✅ All data volumes removed"
  echo "   ✅ Project networks cleaned up"
  echo "   ✅ Docker system pruned"
else
  echo "🎯 GenAI Vanilla Stack stopped successfully"
  echo "   ✅ All containers stopped and removed"
  echo "   ✅ Data volumes preserved"
fi

if [[ "$CLEAN_HOSTS" == true ]]; then
  echo "   ✅ Hosts file entries cleaned up"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔄 To restart the stack, run:"
echo "   ./start.sh                    # Start with default settings"
echo "   ./start.sh --base-port 64567  # Start with custom base port" 
if [[ "$COLD_STOP" == true ]]; then
  echo "   ./start.sh --cold             # Recommended after cold stop"
fi
echo ""
echo "📚 For more information, check the README.md file"