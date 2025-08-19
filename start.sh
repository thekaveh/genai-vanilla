#!/usr/bin/env bash
# Cross-platform script to start the GenAI Vanilla Stack with configurable ports and profile

# Source hosts utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/hosts-utils.sh" 2>/dev/null || {
  echo "Warning: Could not load hosts-utils.sh"
  SKIP_HOSTS=true
}

# Function to apply rich multi-color gradient with multiple colors per character
apply_enhanced_gradient() {
  local text="$1"
  local length=${#text}
  
  # Rich blue hue palette based on the screenshot - comprehensive gradient colors
  # From dark blue through bright cyan, covering all blue spectrum
  local blue_palette=(
    17   # Dark Navy Blue
    18   # Dark Blue  
    19   # Medium Dark Blue
    20   # Royal Blue
    21   # Bright Blue
    26   # Blue-Cyan
    27   # Cyan-Blue
    33   # Bright Cyan-Blue
    39   # Electric Blue
    45   # Bright Electric Blue
    51   # Cyan
    87   # Light Cyan-Blue
    123  # Bright Light Blue
    159  # Very Light Blue
    195  # Pale Blue
  )
  
  local palette_size=${#blue_palette[@]}
  
  # Calculate how many colors to use per character (minimum 2, maximum 4)
  local colors_per_char=2
  if [[ $length -le 5 ]]; then
    colors_per_char=2  # For GENAI (5 chars) = 10 colors minimum
  elif [[ $length -le 7 ]]; then
    colors_per_char=3  # For Vanilla (7 chars) = 21 colors
  else
    colors_per_char=2  # Default fallback
  fi
  
  for (( i=0; i<length; i++ )); do
    local char="${text:$i:1}"
    
    if [[ "$char" == " " ]]; then
      printf " "
    else
      # Calculate which section of the palette this character should use
      local char_section_start=$(( (i * palette_size) / length ))
      local char_section_size=$(( palette_size / length + 1 ))
      
      # Apply multiple colors within each character using subshells for gradient effect
      local color_step=$(( char_section_size / colors_per_char ))
      if [[ $color_step -lt 1 ]]; then
        color_step=1
      fi
      
      # For each character, create a smooth transition through multiple colors
      for (( color_idx=0; color_idx<colors_per_char; color_idx++ )); do
        local palette_idx=$(( char_section_start + (color_idx * color_step) ))
        
        # Ensure we don't exceed palette bounds
        if [[ $palette_idx -ge $palette_size ]]; then
          palette_idx=$((palette_size - 1))
        fi
        
        local color=${blue_palette[$palette_idx]}
        
        # Create a visual effect by printing portions of the character with different colors
        # This simulates multiple colors per character through rapid color transitions
        if [[ $color_idx -eq 0 ]]; then
          # First color - main character display
          printf "\e[1;38;5;${color}m%s\e[0m" "$char"
        else
          # Additional colors - create subtle overlay effect with zero-width characters
          printf "\e[1;38;5;${color}m\b%s\e[0m" "$char"
        fi
      done
    fi
  done
  
  printf "\n"
}

# Function to center text based on terminal width
center_text() {
  local text="$1"
  local term_width=${COLUMNS:-$(tput cols 2>/dev/null || echo 80)}
  local text_length=${#text}
  local padding=$(( (term_width - text_length) / 2 ))
  
  if [[ $padding -gt 0 ]]; then
    printf "%*s" $padding ""
  fi
  echo "$text"
}

# Function to display the branded ASCII banner with responsive sizing
show_banner() {
  # Get terminal width
  local term_width=${COLUMNS:-$(tput cols 2>/dev/null || echo 80)}
  
  # Choose logo size based on terminal width
  if [[ $term_width -lt 70 ]]; then
    show_compact_banner
  else
    show_full_banner
  fi
}

# Function to display the full branded ASCII banner - bold and prominent with centering
show_full_banner() {
  # Get terminal width for centering
  local term_width=${COLUMNS:-$(tput cols 2>/dev/null || echo 80)}
  
  # Filled block ASCII art for GenAI Vanilla - bold and prominent
  local line1='  ██████╗  ███████╗ ███╗   ██╗  █████╗  ██╗'
  local line2=' ██╔════╝  ██╔════╝ ████╗  ██║ ██╔══██╗ ██║'
  local line3=' ██║  ███╗ █████╗   ██╔██╗ ██║ ███████║ ██║'
  local line4=' ██║   ██║ ██╔══╝   ██║╚██╗██║ ██╔══██║ ██║'
  local line5=' ╚██████╔╝ ███████╗ ██║ ╚████║ ██║  ██║ ██║'
  local line6='  ╚═════╝  ╚══════╝ ╚═╝  ╚═══╝ ╚═╝  ╚═╝ ╚═╝'
  
  local line8=' ██╗   ██╗  █████╗  ███╗   ██╗ ██╗ ██╗      ██╗       █████╗'
  local line9=' ██║   ██║ ██╔══██╗ ████╗  ██║ ██║ ██║      ██║      ██╔══██╗'
  local line10=' ██║   ██║ ███████║ ██╔██╗ ██║ ██║ ██║      ██║      ███████║'
  local line11=' ╚██╗ ██╔╝ ██╔══██║ ██║╚██╗██║ ██║ ██║      ██║      ██╔══██║'
  local line12='  ╚████╔╝  ██║  ██║ ██║ ╚████║ ██║ ███████╗ ███████╗ ██║  ██║'
  local line13='   ╚═══╝   ╚═╝  ╚═╝ ╚═╝  ╚═══╝ ╚═╝ ╚══════╝ ╚══════╝ ╚═╝  ╚═╝'
  
  # Calculate centering for GenAI (first part)
  local genai_width=${#line1}
  local genai_padding=$(( (term_width - genai_width) / 2 ))
  
  # Calculate centering for Vanilla (second part)  
  local vanilla_width=${#line8}
  local vanilla_padding=$(( (term_width - vanilla_width) / 2 ))
  
  # Apply enhanced gradient to each line with proper centering
  printf "%*s" $genai_padding ""
  apply_enhanced_gradient "$line1"
  printf "%*s" $genai_padding ""
  apply_enhanced_gradient "$line2"
  printf "%*s" $genai_padding ""
  apply_enhanced_gradient "$line3"
  printf "%*s" $genai_padding ""
  apply_enhanced_gradient "$line4"
  printf "%*s" $genai_padding ""
  apply_enhanced_gradient "$line5"
  printf "%*s" $genai_padding ""
  apply_enhanced_gradient "$line6"
  printf "\n"
  printf "%*s" $vanilla_padding ""
  apply_enhanced_gradient "$line8"
  printf "%*s" $vanilla_padding ""
  apply_enhanced_gradient "$line9"
  printf "%*s" $vanilla_padding ""
  apply_enhanced_gradient "$line10"
  printf "%*s" $vanilla_padding ""
  apply_enhanced_gradient "$line11"
  printf "%*s" $vanilla_padding ""
  apply_enhanced_gradient "$line12"
  printf "%*s" $vanilla_padding ""
  apply_enhanced_gradient "$line13"
  
  printf "\n"
  # Center the credit information dynamically
  local credit_padding=$(( (term_width - 25) / 2 ))
  printf "%*s" $credit_padding ""
  printf "\e[1;94mDeveloped by Kaveh Razavi\e[0m\n"
  local url_padding=$(( (term_width - 45) / 2 ))
  printf "%*s" $url_padding ""
  printf "\e[1;96mhttps://github.com/thekaveh/genai-vanilla\e[0m\n"
  local license_padding=$(( (term_width - 17) / 2 ))
  printf "%*s" $license_padding ""
  printf "\e[1;93mApache License 2.0\e[0m\n"
  printf "\n"
}

# Function to display a compact banner for narrow terminals
show_compact_banner() {
  # Get terminal width for centering
  local term_width=${COLUMNS:-$(tput cols 2>/dev/null || echo 80)}
  
  # Compact filled block ASCII art for GenAI only
  local line1='  ██████╗  ███████╗ ███╗   ██╗  █████╗  ██╗'
  local line2=' ██╔════╝  ██╔════╝ ████╗  ██║ ██╔══██╗ ██║'
  local line3=' ██║  ███╗ █████╗   ██╔██╗ ██║ ███████║ ██║'
  local line4=' ██║   ██║ ██╔══╝   ██║╚██╗██║ ██╔══██║ ██║'
  local line5=' ╚██████╔╝ ███████╗ ██║ ╚████║ ██║  ██║ ██║'
  local line6='  ╚═════╝  ╚══════╝ ╚═╝  ╚═══╝ ╚═╝  ╚═╝ ╚═╝'
  
  local line8='  ██╗   ██╗  █████╗  ███╗   ██╗ ██╗ ██╗      ██╗       █████╗'
  local line9='  ██║   ██║ ██╔══██╗ ████╗  ██║ ██║ ██║      ██║      ██╔══██╗'
  local line10=' ██║   ██║ ███████║ ██╔██╗ ██║ ██║ ██║      ██║      ███████║'
  local line11=' ╚██╗ ██╔╝ ██╔══██║ ██║╚██╗██║ ██║ ██║      ██║      ██╔══██║'
  local line12='  ╚████╔╝  ██║  ██║ ██║ ╚████║ ██║ ███████╗ ███████╗ ██║  ██║'
  local line13='   ╚═══╝   ╚═╝  ╚═╝ ╚═╝  ╚═══╝ ╚═╝ ╚══════╝ ╚══════╝ ╚═╝  ╚═╝'
  
  # Calculate centering for GenAI (first part)
  local genai_width=${#line1}
  local genai_padding=$(( (term_width - genai_width) / 2 ))
  
  # Calculate centering for Vanilla (second part)  
  local vanilla_width=${#line8}
  local vanilla_padding=$(( (term_width - vanilla_width) / 2 ))
  
  # Apply enhanced gradient to each line with proper centering
  printf "%*s" $genai_padding ""
  apply_enhanced_gradient "$line1"
  printf "%*s" $genai_padding ""
  apply_enhanced_gradient "$line2"
  printf "%*s" $genai_padding ""
  apply_enhanced_gradient "$line3"
  printf "%*s" $genai_padding ""
  apply_enhanced_gradient "$line4"
  printf "%*s" $genai_padding ""
  apply_enhanced_gradient "$line5"
  printf "%*s" $genai_padding ""
  apply_enhanced_gradient "$line6"
  printf "\n"
  printf "%*s" $vanilla_padding ""
  apply_enhanced_gradient "$line8"
  printf "%*s" $vanilla_padding ""
  apply_enhanced_gradient "$line9"
  printf "%*s" $vanilla_padding ""
  apply_enhanced_gradient "$line10"
  printf "%*s" $vanilla_padding ""
  apply_enhanced_gradient "$line11"
  printf "%*s" $vanilla_padding ""
  apply_enhanced_gradient "$line12"
  printf "%*s" $vanilla_padding ""
  apply_enhanced_gradient "$line13"
  
  printf "\n"
  # Center the credit information dynamically for compact banner
  local credit_padding=$(( (term_width - 25) / 2 ))
  printf "%*s" $credit_padding ""
  printf "\e[1;94mDeveloped by Kaveh Razavi\e[0m\n"
  local url_padding=$(( (term_width - 45) / 2 ))
  printf "%*s" $url_padding ""
  printf "\e[1;96mhttps://github.com/thekaveh/genai-vanilla\e[0m\n"
  local license_padding=$(( (term_width - 17) / 2 ))
  printf "%*s" $license_padding ""
  printf "\e[1;93mApache License 2.0\e[0m\n"
  printf "\n"
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

# Function to execute docker compose with multiple files
execute_compose_cmd() {
  local cmd_args=""
  IFS=':' read -ra FILES <<< "$COMPOSE_FILES"
  for file in "${FILES[@]}"; do
    cmd_args="$cmd_args -f $file"
  done
  echo "      Command: $DOCKER_COMPOSE_CMD $cmd_args --env-file=.env $@"
  $DOCKER_COMPOSE_CMD $cmd_args --env-file=.env "$@"
}

# Default values
DEFAULT_BASE_PORT=63000
DEFAULT_PROFILE="default"
COLD_START=false
SETUP_HOSTS=false
SKIP_HOSTS=false

# Function to show usage
show_usage() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --base-port PORT   Set the base port number (default: $DEFAULT_BASE_PORT)"
  echo "  --profile PROFILE  Set the deployment profile (default: $DEFAULT_PROFILE)"
  echo "                     Supported profiles: default, ai-local, ai-gpu, fixed"
  echo "  --cold             Force creation of new .env file and generate new keys"
  echo "  --setup-hosts      Setup required hosts file entries (requires sudo/admin)"
  echo "  --skip-hosts       Skip hosts file check and setup"
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
      if [[ -n "$2" && "$2" =~ ^(default|ai-local|ai-gpu|fixed)$ ]]; then
        PROFILE=$2
        shift 2
      else
        echo "Error: --profile must be one of: default, ai-local, ai-gpu, fixed"
        show_usage
        exit 1
      fi
      ;;
    --cold)
      COLD_START=true
      shift
      ;;
    --setup-hosts)
      SETUP_HOSTS=true
      shift
      ;;
    --skip-hosts)
      SKIP_HOSTS=true
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
  unset REDIS_PORT
  unset KONG_HTTP_PORT
  unset KONG_HTTPS_PORT
  unset SUPABASE_META_PORT
  unset SUPABASE_STORAGE_PORT
  unset SUPABASE_AUTH_PORT
  unset SUPABASE_API_PORT
  unset SUPABASE_REALTIME_PORT
  unset SUPABASE_STUDIO_PORT
  unset GRAPH_DB_PORT
  unset GRAPH_DB_DASHBOARD_PORT
  unset OLLAMA_PORT
  unset LOCAL_DEEP_RESEARCHER_PORT
  unset SEARXNG_PORT
  unset OPEN_WEB_UI_PORT
  unset BACKEND_PORT
  unset N8N_PORT
  unset COMFYUI_PORT
fi


# Since port issues can sometimes persist due to Docker's caching, let's
# explicitly verify and indicate the env file is being used
if [[ -f .env ]]; then
  echo "• Found .env file with timestamp: $(stat -c %y .env 2>/dev/null || stat -f %m .env 2>/dev/null)"
fi

echo "• Using Docker Compose command: $DOCKER_COMPOSE_CMD"

# Determine Docker Compose files based on profile
COMPOSE_FILES="docker-compose.yml:compose-profiles/data.yml"
if [[ "$PROFILE" == "default" ]]; then
  COMPOSE_FILES="$COMPOSE_FILES:compose-profiles/ai.yml:compose-profiles/apps.yml:compose-profiles/vector.yml"
elif [[ "$PROFILE" == "ai-local" ]]; then
  COMPOSE_FILES="$COMPOSE_FILES:compose-profiles/ai-local.yml:compose-profiles/apps-local.yml:compose-profiles/vector-local.yml"
elif [[ "$PROFILE" == "ai-gpu" ]]; then
  COMPOSE_FILES="$COMPOSE_FILES:compose-profiles/ai-gpu.yml:compose-profiles/apps-gpu.yml:compose-profiles/vector-gpu.yml"
elif [[ "$PROFILE" == "fixed" ]]; then
  COMPOSE_FILES="$COMPOSE_FILES:compose-profiles/ai.yml:compose-profiles/apps.yml:compose-profiles/vector.yml"
fi

# Display the branded banner
show_banner

echo "🚀 Starting GenAI Vanilla Stack with:"
echo "  • Base Port: $BASE_PORT"
echo "  • Profile: $PROFILE"
echo "  • Compose Files: $COMPOSE_FILES"
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
  
  # Generate N8N_ENCRYPTION_KEY for cold start
  if [[ "$COLD_START" == "true" ]]; then
    echo "  • Generating n8n encryption key..."
    N8N_ENCRYPTION_KEY=$(openssl rand -hex 24)
    # Update the .env file with the new encryption key
    if grep -q "^N8N_ENCRYPTION_KEY=" .env; then
      # Replace existing key
      sed -i.bak "s/^N8N_ENCRYPTION_KEY=.*/N8N_ENCRYPTION_KEY=$N8N_ENCRYPTION_KEY/" .env
      rm .env.bak 2>/dev/null || true  # Remove backup file if created by sed
    else
      # Add new key if it doesn't exist
      echo "N8N_ENCRYPTION_KEY=$N8N_ENCRYPTION_KEY" >> .env
    fi
    echo "  • n8n encryption key generated successfully"
  fi
  
  # Generate SEARXNG_SECRET if missing or for cold start
  SEARXNG_SECRET_VALUE=$(grep "^SEARXNG_SECRET=" .env 2>/dev/null | cut -d '=' -f2 || echo "")
  if [[ "$COLD_START" == "true" || -z "$SEARXNG_SECRET_VALUE" ]]; then
    echo "  • Generating SearxNG secret key..."
    SEARXNG_SECRET=$(openssl rand -hex 32)
    # Update the .env file with the new secret
    if grep -q "^SEARXNG_SECRET=" .env; then
      # Replace existing secret
      sed -i.bak "s/^SEARXNG_SECRET=.*/SEARXNG_SECRET=$SEARXNG_SECRET/" .env
      rm .env.bak 2>/dev/null || true  # Remove backup file if created by sed
    else
      # Add new secret if it doesn't exist
      echo "SEARXNG_SECRET=$SEARXNG_SECRET" >> .env
    fi
    echo "  • SearxNG secret key generated successfully"
  fi
  
  ENV_SOURCE=".env"
else
  echo "📝 Updating .env file with base port $BASE_PORT..."
  
  # Backup existing .env with timestamp
  BACKUP_FILE=".env.backup.$(date +%Y%m%d%H%M%S)"
  cp .env "$BACKUP_FILE"
  echo "  • Backed up existing .env to $BACKUP_FILE"
  
  # Generate SEARXNG_SECRET if missing from existing .env file
  SEARXNG_SECRET_VALUE=$(grep "^SEARXNG_SECRET=" .env 2>/dev/null | cut -d '=' -f2 || echo "")
  if [[ -z "$SEARXNG_SECRET_VALUE" ]]; then
    echo "  • Generating missing SearxNG secret key..."
    SEARXNG_SECRET=$(openssl rand -hex 32)
    # Update the .env file with the new secret
    if grep -q "^SEARXNG_SECRET=" .env; then
      # Replace existing empty secret
      sed -i.bak "s/^SEARXNG_SECRET=.*/SEARXNG_SECRET=$SEARXNG_SECRET/" .env
      rm .env.bak 2>/dev/null || true  # Remove backup file if created by sed
    else
      # Add new secret if it doesn't exist
      echo "SEARXNG_SECRET=$SEARXNG_SECRET" >> .env
    fi
    echo "  • SearxNG secret key generated successfully"
  fi
  
  ENV_SOURCE=".env"
fi

# Define port variables that need calculation
PORT_VARS=(
  "SUPABASE_DB_PORT"
  "REDIS_PORT"
  "KONG_HTTP_PORT"
  "KONG_HTTPS_PORT"
  "SUPABASE_META_PORT"
  "SUPABASE_STORAGE_PORT"
  "SUPABASE_AUTH_PORT"
  "SUPABASE_API_PORT"
  "SUPABASE_REALTIME_PORT"
  "SUPABASE_STUDIO_PORT"
  "GRAPH_DB_PORT"
  "GRAPH_DB_DASHBOARD_PORT"
  "OLLAMA_PORT"
  "LOCAL_DEEP_RESEARCHER_PORT"
  "SEARXNG_PORT"
  "OPEN_WEB_UI_PORT"
  "BACKEND_PORT"
  "N8N_PORT"
  "COMFYUI_PORT"
  "WEAVIATE_PORT"
  "WEAVIATE_GRPC_PORT"
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
REDIS_PORT=$(($BASE_PORT + 1))
KONG_HTTP_PORT=$(($BASE_PORT + 2))
KONG_HTTPS_PORT=$(($BASE_PORT + 3))
SUPABASE_META_PORT=$(($BASE_PORT + 4))
SUPABASE_STORAGE_PORT=$(($BASE_PORT + 5))
SUPABASE_AUTH_PORT=$(($BASE_PORT + 6))
SUPABASE_API_PORT=$(($BASE_PORT + 7))
SUPABASE_REALTIME_PORT=$(($BASE_PORT + 8))
SUPABASE_STUDIO_PORT=$(($BASE_PORT + 9))
GRAPH_DB_PORT=$(($BASE_PORT + 10))
GRAPH_DB_DASHBOARD_PORT=$(($BASE_PORT + 11))
OLLAMA_PORT=$(($BASE_PORT + 12))
LOCAL_DEEP_RESEARCHER_PORT=$(($BASE_PORT + 13))
SEARXNG_PORT=$(($BASE_PORT + 14))
OPEN_WEB_UI_PORT=$(($BASE_PORT + 15))
BACKEND_PORT=$(($BASE_PORT + 16))
N8N_PORT=$(($BASE_PORT + 17))
COMFYUI_PORT=$(($BASE_PORT + 18))
WEAVIATE_PORT=$(($BASE_PORT + 19))
WEAVIATE_GRPC_PORT=$(($BASE_PORT + 20))
EOF

# Add profile-specific environment variables
if [[ "$PROFILE" == "ai-local" ]]; then
  # For ai-local profile, ComfyUI runs on the host machine
  # First check if COMFYUI_BASE_URL already exists and remove it
  sed -i.bak '/^COMFYUI_BASE_URL=/d' .env
  rm -f .env.bak 2>/dev/null || true
  
  echo "" >> .env
  echo "# --- Profile-specific settings (ai-local) ---" >> .env
  echo "COMFYUI_BASE_URL=http://host.docker.internal:8000" >> .env
fi

echo "✅ .env file generated successfully!"

# Read back port values from the .env file to verify they were written correctly
echo "📋 Verifying port assignments from .env file..."
VERIFIED_SUPABASE_DB_PORT=$(grep "^SUPABASE_DB_PORT=" .env | cut -d '=' -f2)
VERIFIED_REDIS_PORT=$(grep "^REDIS_PORT=" .env | cut -d '=' -f2)
VERIFIED_KONG_HTTP_PORT=$(grep "^KONG_HTTP_PORT=" .env | cut -d '=' -f2)
VERIFIED_KONG_HTTPS_PORT=$(grep "^KONG_HTTPS_PORT=" .env | cut -d '=' -f2)
VERIFIED_SUPABASE_META_PORT=$(grep "^SUPABASE_META_PORT=" .env | cut -d '=' -f2)
VERIFIED_SUPABASE_STORAGE_PORT=$(grep "^SUPABASE_STORAGE_PORT=" .env | cut -d '=' -f2)
VERIFIED_SUPABASE_AUTH_PORT=$(grep "^SUPABASE_AUTH_PORT=" .env | cut -d '=' -f2)
VERIFIED_SUPABASE_API_PORT=$(grep "^SUPABASE_API_PORT=" .env | cut -d '=' -f2)
VERIFIED_SUPABASE_REALTIME_PORT=$(grep "^SUPABASE_REALTIME_PORT=" .env | cut -d '=' -f2)
VERIFIED_SUPABASE_STUDIO_PORT=$(grep "^SUPABASE_STUDIO_PORT=" .env | cut -d '=' -f2)
VERIFIED_GRAPH_DB_PORT=$(grep "^GRAPH_DB_PORT=" .env | cut -d '=' -f2)
VERIFIED_GRAPH_DB_DASHBOARD_PORT=$(grep "^GRAPH_DB_DASHBOARD_PORT=" .env | cut -d '=' -f2)
VERIFIED_OLLAMA_PORT=$(grep "^OLLAMA_PORT=" .env | cut -d '=' -f2)
VERIFIED_LOCAL_DEEP_RESEARCHER_PORT=$(grep "^LOCAL_DEEP_RESEARCHER_PORT=" .env | cut -d '=' -f2)
VERIFIED_SEARXNG_PORT=$(grep "^SEARXNG_PORT=" .env | cut -d '=' -f2)
VERIFIED_OPEN_WEB_UI_PORT=$(grep "^OPEN_WEB_UI_PORT=" .env | cut -d '=' -f2)
VERIFIED_BACKEND_PORT=$(grep "^BACKEND_PORT=" .env | cut -d '=' -f2)
VERIFIED_N8N_PORT=$(grep "^N8N_PORT=" .env | cut -d '=' -f2)
VERIFIED_COMFYUI_PORT=$(grep "^COMFYUI_PORT=" .env | cut -d '=' -f2)
VERIFIED_WEAVIATE_PORT=$(grep "^WEAVIATE_PORT=" .env | cut -d '=' -f2)
VERIFIED_WEAVIATE_GRPC_PORT=$(grep "^WEAVIATE_GRPC_PORT=" .env | cut -d '=' -f2)

# Display port assignments in a cleaner format with aligned port numbers
echo ""
echo "🚀 PORT ASSIGNMENTS (verified from .env file):"
printf "  • %-35s %s\n" "Supabase PostgreSQL Database:" "$VERIFIED_SUPABASE_DB_PORT"
printf "  • %-35s %s\n" "Redis:" "$VERIFIED_REDIS_PORT"
printf "  • %-35s %s\n" "Kong HTTP Gateway:" "$VERIFIED_KONG_HTTP_PORT"
printf "  • %-35s %s\n" "Kong HTTPS Gateway:" "$VERIFIED_KONG_HTTPS_PORT"
printf "  • %-35s %s\n" "Supabase Meta Service:" "$VERIFIED_SUPABASE_META_PORT"
printf "  • %-35s %s\n" "Supabase Storage Service:" "$VERIFIED_SUPABASE_STORAGE_PORT"
printf "  • %-35s %s\n" "Supabase Auth Service:" "$VERIFIED_SUPABASE_AUTH_PORT"
printf "  • %-35s %s\n" "Supabase API (PostgREST):" "$VERIFIED_SUPABASE_API_PORT"
printf "  • %-35s %s\n" "Supabase Realtime:" "$VERIFIED_SUPABASE_REALTIME_PORT"
printf "  • %-35s %s\n" "Supabase Studio Dashboard:" "$VERIFIED_SUPABASE_STUDIO_PORT"
printf "  • %-35s %s\n" "Neo4j Graph Database (Bolt):" "$VERIFIED_GRAPH_DB_PORT"
printf "  • %-35s %s\n" "Neo4j Graph Database (Dashboard):" "$VERIFIED_GRAPH_DB_DASHBOARD_PORT"
printf "  • %-35s %s\n" "Ollama API:" "$VERIFIED_OLLAMA_PORT"
printf "  • %-35s %s\n" "Local Deep Researcher:" "$VERIFIED_LOCAL_DEEP_RESEARCHER_PORT"
printf "  • %-35s %s\n" "SearxNG Privacy Search:" "$VERIFIED_SEARXNG_PORT"
printf "  • %-35s %s\n" "Open Web UI:" "$VERIFIED_OPEN_WEB_UI_PORT"
printf "  • %-35s %s\n" "Backend API:" "$VERIFIED_BACKEND_PORT"
printf "  • %-35s %s\n" "n8n Workflow Automation:" "$VERIFIED_N8N_PORT"
printf "  • %-35s %s\n" "ComfyUI Image Generation:" "$VERIFIED_COMFYUI_PORT"
printf "  • %-35s %s\n" "Weaviate Vector DB (HTTP):" "$VERIFIED_WEAVIATE_PORT"
printf "  • %-35s %s\n" "Weaviate Vector DB (gRPC):" "$VERIFIED_WEAVIATE_GRPC_PORT"
echo ""
echo "📋 Access Points:"
printf "  • %-20s %s\n" "Supabase Studio:" "http://localhost:$VERIFIED_SUPABASE_STUDIO_PORT"
printf "  • %-20s %s\n" "Kong HTTP Gateway:" "http://localhost:$VERIFIED_KONG_HTTP_PORT"
printf "  • %-20s %s\n" "Kong HTTPS Gateway:" "https://localhost:$VERIFIED_KONG_HTTPS_PORT"
printf "  • %-20s %s\n" "Neo4j Browser:" "http://localhost:$VERIFIED_GRAPH_DB_DASHBOARD_PORT"
printf "  • %-20s %s\n" "Local Deep Researcher:" "http://localhost:$VERIFIED_LOCAL_DEEP_RESEARCHER_PORT"
printf "  • %-20s %s\n" "SearxNG Search:" "http://localhost:$VERIFIED_SEARXNG_PORT"
printf "  • %-20s %s\n" "Open Web UI:" "http://localhost:$VERIFIED_OPEN_WEB_UI_PORT"
printf "  • %-20s %s\n" "Backend API:" "http://localhost:$VERIFIED_BACKEND_PORT/docs"
printf "  • %-20s %s\n" "n8n Dashboard:" "http://localhost:$VERIFIED_N8N_PORT"
printf "  • %-20s %s\n" "ComfyUI Interface:" "http://localhost:$VERIFIED_COMFYUI_PORT"
printf "  • %-20s %s\n" "Weaviate GraphQL:" "http://localhost:$VERIFIED_WEAVIATE_PORT/v1/graphql"
echo ""

# Hosts file management
if [[ "$SKIP_HOSTS" != "true" ]]; then
  echo "🔍 Checking hosts file configuration..."
  
  OS=$(detect_os)
  HOSTS_FILE=$(get_hosts_file)
  
  if [[ -z "$HOSTS_FILE" || ! -f "$HOSTS_FILE" ]]; then
    echo "⚠️  Could not locate hosts file for OS: $OS"
    echo "   Subdomain access requires these entries in your hosts file:"
    for host in $(get_genai_hosts); do
      echo "   127.0.0.1 $host"
    done
    echo ""
  else
    # Check for missing entries
    MISSING_HOSTS=($(check_missing_hosts "$HOSTS_FILE"))
    
    if [[ ${#MISSING_HOSTS[@]} -eq 0 ]]; then
      echo "✅ All required hosts entries are present"
    else
      echo "⚠️  Missing hosts file entries for subdomain access:"
      for host in "${MISSING_HOSTS[@]}"; do
        echo "   127.0.0.1 $host"
      done
      echo ""
      
      # If --setup-hosts was provided, try to add them
      if [[ "$SETUP_HOSTS" == "true" ]]; then
        if is_elevated; then
          echo "📝 Adding hosts entries..."
          if add_hosts_entries "$HOSTS_FILE"; then
            echo "✅ Hosts file updated successfully"
          else
            echo "❌ Failed to update hosts file"
            exit 1
          fi
        else
          echo "❌ --setup-hosts requires elevated privileges"
          if [[ "$OS" == "windows" ]]; then
            echo "   Please run as Administrator"
          else
            echo "   Please run with: sudo $0 --setup-hosts --profile $PROFILE"
          fi
          exit 1
        fi
      else
        # Offer to add them
        echo "To enable subdomain access (e.g., http://api.localhost:$VERIFIED_KONG_HTTP_PORT),"
        echo "these entries need to be added to your hosts file."
        echo ""
        echo "You can:"
        echo "1. Run with elevated privileges to add automatically:"
        if [[ "$OS" == "windows" ]]; then
          echo "   Run as Administrator: $0 --setup-hosts --profile $PROFILE"
        else
          echo "   sudo $0 --setup-hosts --profile $PROFILE"
        fi
        echo "2. Add them manually to $HOSTS_FILE"
        echo "3. Continue without subdomain access (use direct ports only)"
        echo ""
        read -p "Continue without hosts file setup? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
          echo "Exiting. Please run with --setup-hosts or add entries manually."
          exit 1
        fi
      fi
    fi
  fi
  echo ""
fi

# Start the stack with the selected profile
echo "🔄 Starting the stack with profile: $PROFILE"

# Aggressively clean Docker environment to prevent caching issues
echo "  • Performing deep clean of Docker environment..."

# Stop and remove containers from previous runs
echo "    - Stopping and removing containers..."
execute_compose_cmd down --remove-orphans

# Remove volumes if cold start is requested
if [[ "$COLD_START" == "true" ]]; then
  echo "    - Removing volumes (cold start)..."
  execute_compose_cmd down -v

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
execute_compose_cmd build --no-cache

echo "    - Starting containers..."
# Force Docker to use the updated environment file by explicitly passing it
# Added --force-recreate to ensure containers are recreated with new port settings
execute_compose_cmd up -d --force-recreate

# Check dynamic Weaviate embedding model configuration
echo ""
echo "🔍 Verifying Weaviate embedding model configuration..."
if [[ "$PROFILE" == *"vector"* ]] || [[ "$COMPOSE_FILES" == *"vector"* ]]; then
  # Wait a moment for weaviate-init to complete
  sleep 3
  
  # Check if weaviate-shared-config volume exists and has configuration
  SHARED_CONFIG_PATH=""
  if docker volume inspect "${PROJECT_NAME}_weaviate-shared-config" >/dev/null 2>&1; then
    # Get the volume mount path (this is Docker-specific and may vary)
    echo "  • weaviate-shared-config volume exists"
    
    # Try to read the configuration from the volume via a temporary container
    WEAVIATE_MODEL=$(docker run --rm -v "${PROJECT_NAME}_weaviate-shared-config:/shared" alpine:latest sh -c "if [ -f /shared/weaviate-config.env ]; then cat /shared/weaviate-config.env | grep WEAVIATE_OLLAMA_EMBEDDING_MODEL | cut -d'=' -f2; fi" 2>/dev/null || echo "")
    
    if [ -n "$WEAVIATE_MODEL" ]; then
      echo "  • ✅ Dynamic embedding model discovered: $WEAVIATE_MODEL"
    else
      echo "  • ⚠️  Warning: No embedding model configuration found, using default"
    fi
  else
    echo "  • ⚠️  Warning: weaviate-shared-config volume not found"
  fi
else
  echo "  • Skipped (vector services not included in profile: $PROFILE)"
fi

# Show the actual port mappings to verify
echo ""
echo "🔍 Verifying port mappings from Docker..."
execute_compose_cmd ps
  
# Verify actual port mappings against expected values
echo ""
echo "🔍 Checking if Docker assigned the expected ports..."

# Define services and their internal ports to check
# Using simple arrays instead of associative arrays for better compatibility
SERVICES=(
  "supabase-db:5432:$VERIFIED_SUPABASE_DB_PORT"
  "redis:6379:$VERIFIED_REDIS_PORT"
  "supabase-meta:8080:$VERIFIED_SUPABASE_META_PORT"
  "supabase-storage:5000:$VERIFIED_SUPABASE_STORAGE_PORT"
  "supabase-auth:9999:$VERIFIED_SUPABASE_AUTH_PORT"
  "supabase-api:3000:$VERIFIED_SUPABASE_API_PORT"
  "supabase-realtime:4000:$VERIFIED_SUPABASE_REALTIME_PORT"
  "supabase-studio:3000:$VERIFIED_SUPABASE_STUDIO_PORT"
  "neo4j-graph-db:7687:$VERIFIED_GRAPH_DB_PORT"
  "weaviate:8080:$VERIFIED_WEAVIATE_PORT"
  "local-deep-researcher:2024:$VERIFIED_LOCAL_DEEP_RESEARCHER_PORT"
  "open-web-ui:8080:$VERIFIED_OPEN_WEB_UI_PORT"
  "backend:8000:$VERIFIED_BACKEND_PORT"
  "kong-api-gateway:8000:$VERIFIED_KONG_HTTP_PORT"
  "kong-api-gateway:8443:$VERIFIED_KONG_HTTPS_PORT"
)

# If using default or ai-gpu profile, Ollama is included
if [[ "$PROFILE" == "default" || "$PROFILE" == "ai-gpu" ]]; then
  SERVICES+=("ollama:11434:$VERIFIED_OLLAMA_PORT")
fi

# ComfyUI health check for ai-local profile
if [[ "$PROFILE" == "ai-local" ]]; then
  echo "🔍 Checking local ComfyUI availability..."
  # Try port 8188 first (standard), then 8000 (common alternative)
  if curl -s --connect-timeout 5 "http://localhost:8188/system_stats" > /dev/null 2>&1; then
    echo "  • ✅ Local ComfyUI: Available at http://localhost:8188"
  elif curl -s --connect-timeout 5 "http://localhost:8000/system_stats" > /dev/null 2>&1; then
    echo "  • ✅ Local ComfyUI: Available at http://localhost:8000"
  else
    echo "  • ⚠️  Local ComfyUI: Not running on port 8188 or 8000"
    echo "    Please start ComfyUI locally with: python main.py --listen --port 8188"
    echo "    Or refer to the documentation for installation instructions."
  fi
  echo ""
fi

# Function to get actual port mapping
get_actual_port() {
  local service=$1
  local internal_port=$2
  local cmd_args=""
  IFS=':' read -ra FILES <<< "$COMPOSE_FILES"
  for file in "${FILES[@]}"; do
    cmd_args="$cmd_args -f $file"
  done
  $DOCKER_COMPOSE_CMD $cmd_args port "$service" "$internal_port" 2>/dev/null | grep -oE '[0-9]+$' || echo ""
}

# Check each service
for SERVICE_INFO in "${SERVICES[@]}"; do
  IFS=':' read -r SERVICE INTERNAL_PORT EXPECTED_PORT <<< "$SERVICE_INFO"
  
  # Get the actual port mapping from Docker - with improved error handling
  ACTUAL_PORT=$(get_actual_port "$SERVICE" "$INTERNAL_PORT")
  
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
execute_compose_cmd logs -f
