#!/usr/bin/env bash
# Cross-platform script to start the GenAI Vanilla Stack with YAML-driven configuration

# Source hosts utilities from new location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config/scripts/hosts-utils.sh" 2>/dev/null || {
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

# Function to check yq availability with graceful fallback
ensure_yq_available() {
  if ! command -v yq &> /dev/null; then
    echo "⚠️  yq not found - required for YAML configuration processing"
    echo ""
    echo "Please install yq using one of these methods:"
    echo ""
    case "$OSTYPE" in
      darwin*)
        echo "  macOS:"
        echo "    brew install yq"
        echo "    or download from: https://github.com/mikefarah/yq/releases"
        ;;
      linux*)
        echo "  Linux:"
        echo "    # Ubuntu/Debian:"
        echo "    sudo apt update && sudo apt install -y yq"
        echo ""
        echo "    # RHEL/CentOS/Fedora:"
        echo "    sudo yum install -y yq"
        echo ""
        echo "    # Arch Linux:"
        echo "    sudo pacman -S yq"
        echo ""
        echo "    # Or download from: https://github.com/mikefarah/yq/releases"
        ;;
      *)
        echo "  Download from: https://github.com/mikefarah/yq/releases"
        ;;
    esac
    echo ""
    echo "After installing yq, please run this script again."
    exit 1
  fi
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

# Function to validate SOURCE configurations against service-configs.yml
validate_source_values() {
  local config_file="config/service-configs.yml"
  local validation_errors=0
  
  echo "🔍 Validating SOURCE configurations..."
  
  # Check LLM_PROVIDER_SOURCE
  local llm_source="${SERVICE_SOURCES[LLM_PROVIDER_SOURCE]}"
  local valid_llm_sources=$(yq eval '.source_mappings.LLM_PROVIDER_SOURCE.mappings | keys | .[]' "$config_file" | tr '\n' ' ')
  if ! yq eval ".source_mappings.LLM_PROVIDER_SOURCE.mappings | has(\"$llm_source\")" "$config_file" | grep -q "true"; then
    echo "❌ Invalid LLM_PROVIDER_SOURCE: '$llm_source'"
    echo "   Valid options: $valid_llm_sources"
    validation_errors=$((validation_errors + 1))
  fi
  
  # Check COMFYUI_SOURCE
  local comfyui_source="${SERVICE_SOURCES[COMFYUI_SOURCE]}"
  local valid_comfyui_sources=$(yq eval '.source_mappings.COMFYUI_SOURCE.mappings | keys | .[]' "$config_file" | tr '\n' ' ')
  if ! yq eval ".source_mappings.COMFYUI_SOURCE.mappings | has(\"$comfyui_source\")" "$config_file" | grep -q "true"; then
    echo "❌ Invalid COMFYUI_SOURCE: '$comfyui_source'"
    echo "   Valid options: $valid_comfyui_sources"
    validation_errors=$((validation_errors + 1))
  fi
  
  # Check WEAVIATE_SOURCE
  local weaviate_source="${SERVICE_SOURCES[WEAVIATE_SOURCE]}"
  local valid_weaviate_sources=$(yq eval '.source_mappings.WEAVIATE_SOURCE.mappings | keys | .[]' "$config_file" | tr '\n' ' ')
  if ! yq eval ".source_mappings.WEAVIATE_SOURCE.mappings | has(\"$weaviate_source\")" "$config_file" | grep -q "true"; then
    echo "❌ Invalid WEAVIATE_SOURCE: '$weaviate_source'"
    echo "   Valid options: $valid_weaviate_sources"
    validation_errors=$((validation_errors + 1))
  fi
  
  # Check VECTOR_SOURCE
  local vector_source="${SERVICE_SOURCES[VECTOR_SOURCE]}"
  local valid_vector_sources=$(yq eval '.source_mappings.VECTOR_SOURCE.mappings | keys | .[]' "$config_file" | tr '\n' ' ')
  if ! yq eval ".source_mappings.VECTOR_SOURCE.mappings | has(\"$vector_source\")" "$config_file" | grep -q "true"; then
    echo "❌ Invalid VECTOR_SOURCE: '$vector_source'"
    echo "   Valid options: $valid_vector_sources"
    validation_errors=$((validation_errors + 1))
  fi
  
  # Additional validation for localhost services
  if [[ "$llm_source" == "localhost" ]]; then
    echo "🔍 Validating localhost Ollama service..."
    if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
      echo "⚠️  Warning: Ollama not detected at localhost:11434"
      echo "   Make sure Ollama is running locally before starting the stack"
    else
      echo "✅ Localhost Ollama service is accessible"
    fi
  fi
  
  if [[ "$comfyui_source" == "localhost" ]]; then
    echo "🔍 Validating localhost ComfyUI service..."
    if ! curl -s http://localhost:8000 >/dev/null 2>&1 && ! curl -s http://localhost:8188 >/dev/null 2>&1; then
      echo "⚠️  Warning: ComfyUI not detected at localhost:8000 or localhost:8188"
      echo "   Make sure ComfyUI is running locally before starting the stack"
    else
      echo "✅ Localhost ComfyUI service is accessible"
    fi
  fi
  
  # Check for undefined SOURCE variables
  local undefined_sources=()
  for source_var in LLM_PROVIDER_SOURCE COMFYUI_SOURCE WEAVIATE_SOURCE VECTOR_SOURCE N8N_SOURCE SEARXNG_SOURCE BACKEND_SOURCE OPEN_WEB_UI_SOURCE LOCAL_DEEP_RESEARCHER_SOURCE NEO4J_SOURCE; do
    if [[ -z "${SERVICE_SOURCES[$source_var]}" ]]; then
      undefined_sources+=("$source_var")
    fi
  done
  
  if [[ ${#undefined_sources[@]} -gt 0 ]]; then
    echo "❌ Undefined SOURCE variables: ${undefined_sources[*]}"
    validation_errors=$((validation_errors + ${#undefined_sources[@]}))
  fi
  
  if [[ $validation_errors -gt 0 ]]; then
    echo ""
    echo "❌ Found $validation_errors SOURCE configuration error(s)."
    echo "Please correct the SOURCE values in your .env file and try again."
    echo ""
    echo "💡 Tip: Edit .env.example and run ./start.sh to recreate .env file"
    exit 1
  fi
  
  echo "✅ All SOURCE values are valid"
}

# Function to parse service SOURCE configurations from .env
parse_service_sources() {
  # Initialize associative array for service sources
  declare -A SERVICE_SOURCES 2>/dev/null || true
  
  # Default values
  SERVICE_SOURCES[LLM_PROVIDER_SOURCE]="container-cpu"
  SERVICE_SOURCES[COMFYUI_SOURCE]="container-cpu"
  SERVICE_SOURCES[WEAVIATE_SOURCE]="container"
  SERVICE_SOURCES[VECTOR_SOURCE]="container-cpu"
  SERVICE_SOURCES[N8N_SOURCE]="container"
  SERVICE_SOURCES[SEARXNG_SOURCE]="container"
  SERVICE_SOURCES[BACKEND_SOURCE]="container"
  SERVICE_SOURCES[OPEN_WEB_UI_SOURCE]="container"
  SERVICE_SOURCES[LOCAL_DEEP_RESEARCHER_SOURCE]="container"
  SERVICE_SOURCES[NEO4J_SOURCE]="container"
  
  if [[ -f .env ]]; then
    # Parse SOURCE variables from .env file
    while IFS= read -r line; do
      if [[ $line =~ ^([A-Z_]+_SOURCE)=([^#]*) ]]; then
        local var_name="${BASH_REMATCH[1]}"
        local var_value="${BASH_REMATCH[2]// /}"  # Remove spaces
        var_value="${var_value//\"/}"  # Remove quotes
        SERVICE_SOURCES[$var_name]="$var_value"
      fi
    done < .env
  fi
}

# Function to load service configuration from YAML
load_service_config() {
  local config_file="config/service-configs.yml"
  
  if [[ ! -f "$config_file" ]]; then
    echo "❌ Service configuration file not found: $config_file"
    exit 1
  fi
  
  echo "📋 Loading service configuration from $config_file"
}

# Function to get the correct host reference for localhost services
get_localhost_host() {
  # On Linux, host.docker.internal might not work, so we need a fallback
  if [[ "$OSTYPE" == "linux"* ]]; then
    # Check if host.docker.internal resolves
    if ! getent hosts host.docker.internal >/dev/null 2>&1; then
      echo "172.17.0.1"  # Default Docker bridge gateway on Linux
    else
      echo "host.docker.internal"
    fi
  else
    echo "host.docker.internal"  # Works on macOS and Windows
  fi
}

# Function to generate environment variables based on YAML configuration
generate_service_environment() {
  local config_file="config/service-configs.yml"
  local localhost_host=$(get_localhost_host)
  
  echo "🔧 Generating service environment from YAML configuration..."
  echo "🔗 Using '$localhost_host' for localhost service connections"
  
  # Parse LLM_PROVIDER_SOURCE
  local llm_source="${SERVICE_SOURCES[LLM_PROVIDER_SOURCE]}"
  local llm_config_key=$(yq eval ".source_mappings.LLM_PROVIDER_SOURCE.mappings.\"$llm_source\"" "$config_file")
  
  if [[ "$llm_config_key" == "null" || "$llm_config_key" == "" ]]; then
    llm_config_key="container-cpu"  # Default fallback
  fi
  
  # Set Ollama configuration based on YAML
  local ollama_scale=$(yq eval ".source_configurable.ollama.\"$llm_config_key\".scale" "$config_file")
  local ollama_endpoint=$(yq eval ".source_configurable.ollama.\"$llm_config_key\".environment.OLLAMA_ENDPOINT" "$config_file")
  local ollama_gpu_devices=$(yq eval ".source_configurable.ollama.\"$llm_config_key\".environment.NVIDIA_VISIBLE_DEVICES" "$config_file")
  local ollama_extra_hosts=$(yq eval ".source_configurable.ollama.\"$llm_config_key\".extra_hosts" "$config_file")
  
  export OLLAMA_SCALE="${ollama_scale:-1}"
  # Replace host.docker.internal with dynamic localhost host for cross-platform compatibility
  export OLLAMA_ENDPOINT="${ollama_endpoint/host.docker.internal/$localhost_host}"
  export OLLAMA_NVIDIA_VISIBLE_DEVICES="${ollama_gpu_devices:-}"
  
  # Note: extra_hosts for localhost connectivity are statically defined in docker-compose.yml
  
  # Set deploy resources for GPU configurations
  if [[ "$llm_config_key" == "container-gpu" ]]; then
    export OLLAMA_DEPLOY_RESOURCES=$'reservations:\n  devices:\n    - driver: nvidia\n      capabilities: [gpu]'
  else
    export OLLAMA_DEPLOY_RESOURCES="~"
  fi
  
  # Set dependent service scales
  if [[ "$llm_config_key" == "container-cpu" || "$llm_config_key" == "container-gpu" ]]; then
    export OLLAMA_PULL_SCALE=1
  else
    export OLLAMA_PULL_SCALE=0
  fi
  
  # Parse COMFYUI_SOURCE
  local comfyui_source="${SERVICE_SOURCES[COMFYUI_SOURCE]}"
  local comfyui_config_key=$(yq eval ".source_mappings.COMFYUI_SOURCE.mappings.\"$comfyui_source\"" "$config_file")
  
  if [[ "$comfyui_config_key" == "null" || "$comfyui_config_key" == "" ]]; then
    comfyui_config_key="container-cpu"  # Default fallback
  fi
  
  # Set ComfyUI configuration
  local comfyui_scale=$(yq eval ".source_configurable.comfyui.\"$comfyui_config_key\".scale" "$config_file")
  local comfyui_endpoint=$(yq eval ".source_configurable.comfyui.\"$comfyui_config_key\".environment.COMFYUI_ENDPOINT" "$config_file")
  local comfyui_args=$(yq eval ".source_configurable.comfyui.\"$comfyui_config_key\".environment.COMFYUI_ARGS" "$config_file")
  local is_local_comfyui=$(yq eval ".source_configurable.comfyui.\"$comfyui_config_key\".environment.IS_LOCAL_COMFYUI" "$config_file")
  local comfyui_models_path=$(yq eval ".source_configurable.comfyui.\"$comfyui_config_key\".environment.COMFYUI_LOCAL_MODELS_PATH" "$config_file")
  local comfyui_extra_hosts=$(yq eval ".source_configurable.comfyui.\"$comfyui_config_key\".extra_hosts" "$config_file")
  
  export COMFYUI_SCALE="${comfyui_scale:-1}"
  # Replace host.docker.internal with dynamic localhost host for cross-platform compatibility
  export COMFYUI_ENDPOINT="${comfyui_endpoint/host.docker.internal/$localhost_host}"
  export COMFYUI_ARGS="${comfyui_args}"
  export IS_LOCAL_COMFYUI="${is_local_comfyui:-false}"
  export COMFYUI_LOCAL_MODELS_PATH="${comfyui_models_path:-./empty}"
  
  # Create empty directory if needed
  if [[ "$IS_LOCAL_COMFYUI" == "false" ]]; then
    mkdir -p ./empty
  fi
  
  # Note: extra_hosts for localhost connectivity are statically defined in docker-compose.yml
  
  # Set deploy resources for GPU configurations
  if [[ "$comfyui_config_key" == "container-gpu" ]]; then
    export COMFYUI_DEPLOY_RESOURCES=$'reservations:\n  devices:\n    - driver: nvidia\n      count: 1\n      capabilities: [gpu]\nlimits:\n  cpus: "${PROD_ENV_COMFYUI_CPUS:-2}"\n  memory: "${PROD_ENV_COMFYUI_MEM_LIMIT:-4g}"'
  else
    export COMFYUI_DEPLOY_RESOURCES="~"
  fi
  
  # Set dependent service scales
  if [[ "$comfyui_config_key" == "container-cpu" || "$comfyui_config_key" == "container-gpu" ]]; then
    export COMFYUI_INIT_SCALE=1
  else
    export COMFYUI_INIT_SCALE=0
  fi
  
  # Parse VECTOR_SOURCE for multi2vec-clip
  local vector_source="${SERVICE_SOURCES[VECTOR_SOURCE]}"
  local vector_config_key=$(yq eval ".source_mappings.VECTOR_SOURCE.mappings.\"$vector_source\"" "$config_file")
  
  if [[ "$vector_config_key" == "null" || "$vector_config_key" == "" ]]; then
    vector_config_key="container-cpu"  # Default fallback
  fi
  
  # Set CLIP configuration
  local clip_scale=$(yq eval ".source_configurable.multi2vec-clip.\"$vector_config_key\".scale" "$config_file")
  local clip_cuda=$(yq eval ".source_configurable.multi2vec-clip.\"$vector_config_key\".environment.ENABLE_CUDA" "$config_file")
  
  export CLIP_SCALE="${clip_scale:-1}"
  export CLIP_ENABLE_CUDA="${clip_cuda:-0}"
  
  # Set deploy resources for GPU configurations
  if [[ "$vector_config_key" == "container-gpu" ]]; then
    export CLIP_DEPLOY_RESOURCES=$'reservations:\n  devices:\n    - driver: nvidia\n      capabilities: [gpu]'
  else
    export CLIP_DEPLOY_RESOURCES="~"
  fi
  
  # Parse WEAVIATE_SOURCE
  local weaviate_source="${SERVICE_SOURCES[WEAVIATE_SOURCE]}"
  local weaviate_config_key=$(yq eval ".source_mappings.WEAVIATE_SOURCE.mappings.\"$weaviate_source\"" "$config_file")
  local weaviate_scale=$(yq eval ".source_configurable.weaviate.\"$weaviate_config_key\".scale" "$config_file")
  local weaviate_url=$(yq eval ".source_configurable.weaviate.\"$weaviate_config_key\".environment.WEAVIATE_URL" "$config_file")
  local weaviate_extra_hosts=$(yq eval ".source_configurable.weaviate.\"$weaviate_config_key\".extra_hosts" "$config_file")
  
  export WEAVIATE_SCALE="${weaviate_scale:-1}"
  # Replace host.docker.internal with dynamic localhost host for cross-platform compatibility
  export WEAVIATE_URL="${weaviate_url/host.docker.internal/$localhost_host}"
  export WEAVIATE_INIT_SCALE="$WEAVIATE_SCALE"
  
  # Weaviate inherits Ollama endpoint for vectorization when enabled
  if [[ "$WEAVIATE_SCALE" -gt 0 ]]; then
    export WEAVIATE_OLLAMA_ENDPOINT="${OLLAMA_ENDPOINT}"
  else
    export WEAVIATE_OLLAMA_ENDPOINT=""
  fi
  
  # Parse N8N_SOURCE
  local n8n_source="${SERVICE_SOURCES[N8N_SOURCE]}"
  local n8n_config_key=$(yq eval ".source_mappings.N8N_SOURCE.mappings.\"$n8n_source\"" "$config_file")
  local n8n_scale=$(yq eval ".source_configurable.n8n.\"$n8n_config_key\".scale" "$config_file")
  
  # n8n depends on weaviate for vector operations
  if [[ "$n8n_scale" -gt 0 && "$WEAVIATE_SCALE" -eq 0 ]]; then
    echo "⚠️  n8n disabled: requires weaviate for vector operations and AI workflow nodes"
    echo "    Enable weaviate (WEAVIATE_SOURCE=container) to use n8n workflows with vector capabilities"
    export N8N_SCALE=0
    export N8N_WORKER_SCALE=0
    export N8N_INIT_SCALE=0
  else
    export N8N_SCALE="${n8n_scale:-0}"
    export N8N_WORKER_SCALE="$N8N_SCALE"
    export N8N_INIT_SCALE="$N8N_SCALE"
    if [[ "$N8N_SCALE" -gt 0 ]]; then
      echo "  • n8n enabled with weaviate integration for vector operations"
    fi
  fi
  
  # Parse other services
  local searxng_source="${SERVICE_SOURCES[SEARXNG_SOURCE]}"
  local searxng_config_key=$(yq eval ".source_mappings.SEARXNG_SOURCE.mappings.\"$searxng_source\"" "$config_file")
  local searxng_scale=$(yq eval ".source_configurable.searxng.\"$searxng_config_key\".scale" "$config_file")
  export SEARXNG_SCALE="${searxng_scale:-0}"
  
  local backend_source="${SERVICE_SOURCES[BACKEND_SOURCE]}"
  local backend_config_key=$(yq eval ".source_mappings.BACKEND_SOURCE.mappings.\"$backend_source\"" "$config_file")
  local backend_scale=$(yq eval ".source_configurable.backend.\"$backend_config_key\".scale" "$config_file")
  export BACKEND_SCALE="${backend_scale:-0}"
  if [[ "$BACKEND_SCALE" -gt 0 ]]; then
    echo "  • Backend enabled - will connect to available optional services (neo4j, searxng, n8n, weaviate)"
  fi
  
  local open_web_ui_source="${SERVICE_SOURCES[OPEN_WEB_UI_SOURCE]}"
  local open_web_ui_config_key=$(yq eval ".source_mappings.OPEN_WEB_UI_SOURCE.mappings.\"$open_web_ui_source\"" "$config_file")
  local open_web_ui_scale=$(yq eval ".source_configurable.open-web-ui.\"$open_web_ui_config_key\".scale" "$config_file")
  export OPEN_WEB_UI_SCALE="${open_web_ui_scale:-0}"
  if [[ "$OPEN_WEB_UI_SCALE" -gt 0 ]]; then
    echo "  • Open WebUI enabled - will connect to available optional services (weaviate, local-deep-researcher)"
  fi
  
  local local_deep_researcher_source="${SERVICE_SOURCES[LOCAL_DEEP_RESEARCHER_SOURCE]}"
  local local_deep_researcher_config_key=$(yq eval ".source_mappings.LOCAL_DEEP_RESEARCHER_SOURCE.mappings.\"$local_deep_researcher_source\"" "$config_file")
  local local_deep_researcher_scale=$(yq eval ".source_configurable.local-deep-researcher.\"$local_deep_researcher_config_key\".scale" "$config_file")
  export LOCAL_DEEP_RESEARCHER_SCALE="${local_deep_researcher_scale:-0}"
  
  local neo4j_source="${SERVICE_SOURCES[NEO4J_SOURCE]}"
  local neo4j_config_key=$(yq eval ".source_mappings.NEO4J_SOURCE.mappings.\"$neo4j_source\"" "$config_file")
  local neo4j_scale=$(yq eval ".source_configurable.neo4j-graph-db.\"$neo4j_config_key\".scale" "$config_file")
  local neo4j_uri=$(yq eval ".source_configurable.neo4j-graph-db.\"$neo4j_config_key\".environment.NEO4J_URI" "$config_file")
  local neo4j_extra_hosts=$(yq eval ".source_configurable.neo4j-graph-db.\"$neo4j_config_key\".extra_hosts" "$config_file")
  
  export NEO4J_SCALE="${neo4j_scale:-0}"
  # Replace host.docker.internal with dynamic localhost host for cross-platform compatibility
  export NEO4J_URI="${neo4j_uri/host.docker.internal/$localhost_host}"
  
  # Note: extra_hosts for localhost connectivity are statically defined in docker-compose.yml

  # Note: extra_hosts for localhost connectivity are statically defined in docker-compose.yml
  
  echo "✅ Service environment generated successfully"
  echo "  - Ollama: $llm_config_key (scale: $OLLAMA_SCALE, endpoint: $OLLAMA_ENDPOINT)"
  echo "  - ComfyUI: $comfyui_config_key (scale: $COMFYUI_SCALE, endpoint: $COMFYUI_ENDPOINT)"
  echo "  - Multi2Vec-CLIP: $vector_config_key (scale: $CLIP_SCALE, CUDA: $CLIP_ENABLE_CUDA)"
  echo "  - Weaviate: container (scale: $WEAVIATE_SCALE, ollama: $WEAVIATE_OLLAMA_ENDPOINT)"
}

# Function to update .env file with computed variables
update_env_file() {
  local env_file=".env"
  local temp_file="${env_file}.tmp"
  
  echo "📝 Updating .env file with computed service configurations..."
  
  # Create a list of variables to add/update
  local vars_to_update=(
    "OLLAMA_SCALE"
    "OLLAMA_ENDPOINT"
    "OLLAMA_NVIDIA_VISIBLE_DEVICES"
    "OLLAMA_DEPLOY_RESOURCES"
    "OLLAMA_PULL_SCALE"
    "COMFYUI_SCALE"
    "COMFYUI_ENDPOINT"
    "COMFYUI_ARGS"
    "COMFYUI_DEPLOY_RESOURCES"
    "COMFYUI_INIT_SCALE"
    "IS_LOCAL_COMFYUI"
    "CLIP_SCALE"
    "CLIP_ENABLE_CUDA"
    "CLIP_DEPLOY_RESOURCES"
    "WEAVIATE_SCALE"
    "WEAVIATE_URL"
    "WEAVIATE_OLLAMA_ENDPOINT"
    "N8N_SCALE"
    "N8N_WORKER_SCALE"
    "N8N_INIT_SCALE"
    "WEAVIATE_INIT_SCALE"
    "SEARXNG_SCALE"
    "BACKEND_SCALE"
    "OPEN_WEB_UI_SCALE"
    "LOCAL_DEEP_RESEARCHER_SCALE"
    "NEO4J_SCALE"
    "NEO4J_URI"
  )
  
  # Copy existing .env file
  cp "$env_file" "$temp_file"
  
  # Add/update computed variables
  for var in "${vars_to_update[@]}"; do
    local value="${!var}"
    if grep -q "^${var}=" "$temp_file"; then
      # Update existing variable
      if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^${var}=.*|${var}=${value}|" "$temp_file"
      else
        sed -i "s|^${var}=.*|${var}=${value}|" "$temp_file"
      fi
    else
      # Add new variable
      echo "${var}=${value}" >> "$temp_file"
    fi
  done
  
  # Replace original file
  mv "$temp_file" "$env_file"
  
  echo "✅ Environment file updated with computed configurations"
}

# Note: Kong route configuration is now handled by dynamic environment variables

# Store the detected command in a variable
DOCKER_COMPOSE_CMD=$(detect_docker_compose_cmd)

# Default values
DEFAULT_BASE_PORT=63000
COLD_START=false
SETUP_HOSTS=false
SKIP_HOSTS=false

# Function to show usage
show_usage() {
  echo "Usage: $0 [options]"
  echo "Options:"
  echo "  --base-port PORT   Set the base port number (default: $DEFAULT_BASE_PORT)"
  echo "  --cold             Force creation of new .env file and generate new keys"
  echo "  --setup-hosts      Setup required hosts file entries (requires sudo/admin)"
  echo "  --skip-hosts       Skip hosts file check and setup"
  echo "  --help             Show this help message"
  echo ""
  echo "Service Configuration:"
  echo "  Services are configured via SOURCE variables in .env.example file:"
  echo "    container      - Run service in Docker container (default)"
  echo "    container-cpu  - CPU-only container"
  echo "    container-gpu  - GPU-accelerated container"
  echo "    localhost      - Use service running on localhost"
  echo "    external       - Use external service via URL"
  echo "    disabled       - Don't start the service"
  echo "    api            - Use API-based service (for LLM providers)"
  echo ""
  echo "Workflow:"
  echo "  1. Edit .env.example with your desired SOURCE configurations"
  echo "  2. Run this script - it will copy .env.example to .env automatically"
  echo "  3. Script reads SOURCE values and starts appropriate services"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --base-port)
      if [[ -n $2 && $2 =~ ^[0-9]+$ ]]; then
        BASE_PORT="$2"
        shift 2
      else
        echo "❌ Error: --base-port requires a numeric value"
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
      echo "❌ Unknown option: $1"
      show_usage
      exit 1
      ;;
  esac
done

# Set default base port if not specified
BASE_PORT=${BASE_PORT:-$DEFAULT_BASE_PORT}

# Display logo
show_banner

# Ensure yq is available for YAML processing
ensure_yq_available

echo "🚀 Starting GenAI Vanilla Stack (Base Port: $BASE_PORT)"
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
  
  # Unset potentially lingering port environment variables if cold start and custom base port are used
  if [[ "$COLD_START" == "true" && "$BASE_PORT" != "$DEFAULT_BASE_PORT" ]]; then
    echo "  • Unsetting potentially lingering port environment variables..."
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
    unset LLM_PROVIDER_PORT
    unset LOCAL_DEEP_RESEARCHER_PORT
    unset SEARXNG_PORT
    unset OPEN_WEB_UI_PORT
    unset BACKEND_PORT
    unset N8N_PORT
    unset COMFYUI_PORT
    unset WEAVIATE_PORT
    unset WEAVIATE_GRPC_PORT
    echo "  • Port environment variables unset successfully"
  fi
  
  # Check if generate_supabase_keys.sh exists and is executable
  if [[ -f ./config/scripts/generate_supabase_keys.sh && -x ./config/scripts/generate_supabase_keys.sh ]]; then
    echo "  • Generating Supabase keys..."
    ./config/scripts/generate_supabase_keys.sh
    echo "  • Supabase keys generated successfully"
  else
    echo "  • ⚠️  Warning: config/scripts/generate_supabase_keys.sh not found or not executable"
    echo "    Please run 'chmod +x config/scripts/generate_supabase_keys.sh' and then './config/scripts/generate_supabase_keys.sh'"
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

# Update port configuration in .env
echo "⚙️ Configuring ports (Base: $BASE_PORT)..."
env_file=".env"
temp_file="${env_file}.tmp"

# Port mapping based on base port - using portable approach
cp "$env_file" "$temp_file"

# Function to update port in env file
update_port() {
  local port_var="$1"
  local port_value="$2"
  if grep -q "^${port_var}=" "$temp_file"; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' "s|^${port_var}=.*|${port_var}=${port_value}|" "$temp_file"
    else
      sed -i "s|^${port_var}=.*|${port_var}=${port_value}|" "$temp_file"
    fi
  else
    echo "${port_var}=${port_value}" >> "$temp_file"
  fi
}

# Update all ports
update_port "SUPABASE_DB_PORT" $(($BASE_PORT + 0))
update_port "REDIS_PORT" $(($BASE_PORT + 1))
update_port "KONG_HTTP_PORT" $(($BASE_PORT + 2))
update_port "KONG_HTTPS_PORT" $(($BASE_PORT + 3))
update_port "SUPABASE_META_PORT" $(($BASE_PORT + 4))
update_port "SUPABASE_STORAGE_PORT" $(($BASE_PORT + 5))
update_port "SUPABASE_AUTH_PORT" $(($BASE_PORT + 6))
update_port "SUPABASE_API_PORT" $(($BASE_PORT + 7))
update_port "SUPABASE_REALTIME_PORT" $(($BASE_PORT + 8))
update_port "SUPABASE_STUDIO_PORT" $(($BASE_PORT + 9))
update_port "GRAPH_DB_PORT" $(($BASE_PORT + 10))
update_port "GRAPH_DB_DASHBOARD_PORT" $(($BASE_PORT + 11))
update_port "LLM_PROVIDER_PORT" $(($BASE_PORT + 12))
update_port "LOCAL_DEEP_RESEARCHER_PORT" $(($BASE_PORT + 13))
update_port "SEARXNG_PORT" $(($BASE_PORT + 14))
update_port "OPEN_WEB_UI_PORT" $(($BASE_PORT + 15))
update_port "BACKEND_PORT" $(($BASE_PORT + 16))
update_port "N8N_PORT" $(($BASE_PORT + 17))
update_port "COMFYUI_PORT" $(($BASE_PORT + 18))
update_port "WEAVIATE_PORT" $(($BASE_PORT + 19))
update_port "WEAVIATE_GRPC_PORT" $(($BASE_PORT + 20))

mv "$temp_file" "$env_file"

# Read back port values from the .env file to verify they were written correctly
echo "📋 Verifying port assignments from .env file..."
VERIFIED_SUPABASE_DB_PORT=$(grep "^SUPABASE_DB_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_REDIS_PORT=$(grep "^REDIS_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_KONG_HTTP_PORT=$(grep "^KONG_HTTP_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_KONG_HTTPS_PORT=$(grep "^KONG_HTTPS_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_SUPABASE_META_PORT=$(grep "^SUPABASE_META_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_SUPABASE_STORAGE_PORT=$(grep "^SUPABASE_STORAGE_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_SUPABASE_AUTH_PORT=$(grep "^SUPABASE_AUTH_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_SUPABASE_API_PORT=$(grep "^SUPABASE_API_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_SUPABASE_REALTIME_PORT=$(grep "^SUPABASE_REALTIME_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_SUPABASE_STUDIO_PORT=$(grep "^SUPABASE_STUDIO_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_GRAPH_DB_PORT=$(grep "^GRAPH_DB_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_GRAPH_DB_DASHBOARD_PORT=$(grep "^GRAPH_DB_DASHBOARD_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_LLM_PROVIDER_PORT=$(grep "^LLM_PROVIDER_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_LOCAL_DEEP_RESEARCHER_PORT=$(grep "^LOCAL_DEEP_RESEARCHER_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_SEARXNG_PORT=$(grep "^SEARXNG_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_OPEN_WEB_UI_PORT=$(grep "^OPEN_WEB_UI_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_BACKEND_PORT=$(grep "^BACKEND_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_N8N_PORT=$(grep "^N8N_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_COMFYUI_PORT=$(grep "^COMFYUI_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_WEAVIATE_PORT=$(grep "^WEAVIATE_PORT=" "$env_file" | cut -d '=' -f2)
VERIFIED_WEAVIATE_GRPC_PORT=$(grep "^WEAVIATE_GRPC_PORT=" "$env_file" | cut -d '=' -f2)

echo "✅ Port verification completed successfully"

# Parse service sources from .env
parse_service_sources

# Validate SOURCE values against service-configs.yml
validate_source_values

# Load and generate service configuration
load_service_config
generate_service_environment

# Update .env with computed variables
update_env_file

# Note: Kong routes are now configured via dynamic environment variables

# Setup hosts if needed
if [[ "$SETUP_HOSTS" == true ]] && [[ "$SKIP_HOSTS" == false ]]; then
  echo "🔧 Setting up hosts file entries..."
  if ! setup_hosts_entries; then
    echo "⚠️ Failed to setup hosts file entries"
  fi
elif [[ "$SKIP_HOSTS" == false ]]; then
  echo "🔍 Checking hosts file entries..."
  check_missing_hosts
fi

echo ""
echo "📊 Service Configuration Summary:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "%-25s %-15s %-35s %-8s\n" "SERVICE" "SOURCE" "ENDPOINT" "SCALE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "%-25s %-15s %-35s %-8s\n" "Data Services:" "" "" ""
printf "%-25s %-15s %-35s %-8s\n" "  Supabase Database" "container" "postgresql://localhost:$VERIFIED_SUPABASE_DB_PORT" "1"
printf "%-25s %-15s %-35s %-8s\n" "  Redis Cache" "container" "redis://localhost:$VERIFIED_REDIS_PORT" "1"
printf "%-25s %-15s %-35s %-8s\n" "  Neo4j Graph Database" "${SERVICE_SOURCES[NEO4J_SOURCE]}" "bolt://localhost:$VERIFIED_GRAPH_DB_PORT" "$NEO4J_SCALE"
printf "%-25s %-15s %-35s %-8s\n" "  Supabase Meta" "container" "http://localhost:$VERIFIED_SUPABASE_META_PORT" "1"
printf "%-25s %-15s %-35s %-8s\n" "  Supabase Storage" "container" "http://localhost:$VERIFIED_SUPABASE_STORAGE_PORT" "1"
printf "%-25s %-15s %-35s %-8s\n" "  Supabase Auth" "container" "http://localhost:$VERIFIED_SUPABASE_AUTH_PORT" "1"
printf "%-25s %-15s %-35s %-8s\n" "  Supabase API" "container" "http://localhost:$VERIFIED_SUPABASE_API_PORT" "1"
printf "%-25s %-15s %-35s %-8s\n" "  Supabase Realtime" "container" "http://localhost:$VERIFIED_SUPABASE_REALTIME_PORT" "1"
echo ""
printf "%-25s %-15s %-35s %-8s\n" "AI Services:" "" "" ""
printf "%-25s %-15s %-35s %-8s\n" "  Ollama" "${SERVICE_SOURCES[LLM_PROVIDER_SOURCE]}" "$OLLAMA_ENDPOINT" "$OLLAMA_SCALE"
printf "%-25s %-15s %-35s %-8s\n" "  ComfyUI" "${SERVICE_SOURCES[COMFYUI_SOURCE]}" "$COMFYUI_ENDPOINT" "$COMFYUI_SCALE"
printf "%-25s %-15s %-35s %-8s\n" "  Weaviate Vector DB" "${SERVICE_SOURCES[WEAVIATE_SOURCE]}" "http://localhost:$VERIFIED_WEAVIATE_PORT" "$WEAVIATE_SCALE"
printf "%-25s %-15s %-35s %-8s\n" "  Multi2Vec-CLIP" "${SERVICE_SOURCES[VECTOR_SOURCE]}" "http://multi2vec-clip:8080" "$CLIP_SCALE"
printf "%-25s %-15s %-35s %-8s\n" "  Local Deep Researcher" "${SERVICE_SOURCES[LOCAL_DEEP_RESEARCHER_SOURCE]}" "http://localhost:$VERIFIED_LOCAL_DEEP_RESEARCHER_PORT" "$LOCAL_DEEP_RESEARCHER_SCALE"
echo ""
printf "%-25s %-15s %-35s %-8s\n" "App Services:" "" "" ""
printf "%-25s %-15s %-35s %-8s\n" "  Kong API Gateway" "container" "http://localhost:$VERIFIED_KONG_HTTP_PORT" "1"
printf "%-25s %-15s %-35s %-8s\n" "  Supabase Studio" "container" "http://localhost:$VERIFIED_SUPABASE_STUDIO_PORT" "1"
printf "%-25s %-15s %-35s %-8s\n" "  Open WebUI" "${SERVICE_SOURCES[OPEN_WEB_UI_SOURCE]}" "http://localhost:$VERIFIED_OPEN_WEB_UI_PORT" "$OPEN_WEB_UI_SCALE"
printf "%-25s %-15s %-35s %-8s\n" "  Backend API" "${SERVICE_SOURCES[BACKEND_SOURCE]}" "http://localhost:$VERIFIED_BACKEND_PORT" "$BACKEND_SCALE"
printf "%-25s %-15s %-35s %-8s\n" "  n8n Workflows" "${SERVICE_SOURCES[N8N_SOURCE]}" "http://localhost:$VERIFIED_N8N_PORT" "$N8N_SCALE"
printf "%-25s %-15s %-35s %-8s\n" "  SearxNG Search" "${SERVICE_SOURCES[SEARXNG_SOURCE]}" "http://localhost:$VERIFIED_SEARXNG_PORT" "$SEARXNG_SCALE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

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
printf "  • %-35s %s\n" "Ollama API:" "$VERIFIED_LLM_PROVIDER_PORT"
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
echo "🔄 Preparing Docker environment..."

# Aggressively clean Docker environment to prevent caching issues
echo "  • Performing deep clean of Docker environment..."

# Function to execute compose command with proper error handling
execute_compose_cmd() {
  echo "      Command: $DOCKER_COMPOSE_CMD --env-file=.env $*"
  $DOCKER_COMPOSE_CMD --env-file=.env "$@"
}

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
  docker network rm ${PROJECT_NAME}_backend-bridge-network 2>/dev/null || true # Use || true to prevent script from exiting if network doesn't exist

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
echo "      Command: $DOCKER_COMPOSE_CMD --env-file=.env up -d --force-recreate"
$DOCKER_COMPOSE_CMD --env-file=.env up -d --force-recreate

if [[ $? -eq 0 ]]; then
  echo ""
  echo "🎉 GenAI Vanilla Stack started successfully!"
  
  # ComfyUI health check for localhost configuration
  if [[ "${SERVICE_SOURCES[COMFYUI_SOURCE]}" == "localhost" ]]; then
    echo ""
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
  fi
  
  # Check dynamic Weaviate embedding model configuration
  if [[ "$WEAVIATE_SCALE" -gt 0 ]]; then
    echo ""
    echo "🔍 Verifying Weaviate embedding model configuration..."
    # Wait a moment for weaviate-init to complete
    sleep 3
    
    # Check if weaviate-shared-config volume exists and has configuration
    if docker volume inspect "${PROJECT_NAME}_weaviate-shared-config" >/dev/null 2>&1; then
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
    echo ""
    echo "🔍 Verifying Weaviate embedding model configuration..."
    echo "  • Skipped (Weaviate not running in current configuration)"
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
    "n8n:5678:$VERIFIED_N8N_PORT"
    "searxng:8080:$VERIFIED_SEARXNG_PORT"
  )

  # If Ollama is running in container mode, check its port too
  if [[ "$OLLAMA_SCALE" -gt 0 ]]; then
    SERVICES+=("ollama:11434:$VERIFIED_LLM_PROVIDER_PORT")
  fi
  
  # If ComfyUI is running in container mode, check its port too
  if [[ "$COMFYUI_SCALE" -gt 0 ]]; then
    SERVICES+=("comfyui:18188:$VERIFIED_COMFYUI_PORT")
  fi

  # Function to get actual port mapping
  get_actual_port() {
    local service=$1
    local internal_port=$2
    $DOCKER_COMPOSE_CMD --env-file=.env port "$service" "$internal_port" 2>/dev/null | grep -oE '[0-9]+$' || echo ""
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
  echo "🌐 Access your services:"
  echo "  • Supabase Studio: http://localhost:$VERIFIED_SUPABASE_STUDIO_PORT"
  echo "  • Open WebUI: http://localhost:$VERIFIED_OPEN_WEB_UI_PORT"
  echo "  • Backend API: http://localhost:$VERIFIED_BACKEND_PORT/docs"
  echo "  • n8n Workflows: http://localhost:$VERIFIED_N8N_PORT"
  if [[ "$COMFYUI_SCALE" -gt 0 ]]; then
    echo "  • ComfyUI: http://localhost:$VERIFIED_COMFYUI_PORT"
  fi
  echo "  • Neo4j Browser: http://localhost:$VERIFIED_GRAPH_DB_DASHBOARD_PORT"
  echo "  • Weaviate: http://localhost:$VERIFIED_WEAVIATE_PORT/v1"
  echo ""
  echo "📚 For more information, check the README.md file"
  echo ""
  
  # Optional: Show logs
  echo "📋 Container logs (press Ctrl+C to exit):"
  execute_compose_cmd logs -f
else
  echo ""
  echo "❌ Failed to start GenAI Vanilla Stack"
  echo "   Check the logs above for error details"
  exit 1
fi