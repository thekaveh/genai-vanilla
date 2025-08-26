#!/bin/sh
set -e

echo "comfyui-init: Starting ComfyUI model download process..."

# Check required env vars
if [ -z "$PGHOST" ] || [ -z "$PGUSER" ] || [ -z "$PGPASSWORD" ] || [ -z "$PGDATABASE" ]; then
  echo "comfyui-init: Error: One or more required database environment variables are not set."
  echo "PGHOST=$PGHOST, PGUSER=$PGUSER, PGPASSWORD=[set], PGDATABASE=$PGDATABASE"
  exit 1
fi

if [ -z "$COMFYUI_MODELS_PATH" ]; then
  echo "comfyui-init: Error: COMFYUI_MODELS_PATH environment variable is not set."
  exit 1
fi

echo "comfyui-init: Installing required tools..."
apk add --no-cache curl postgresql-client wget bc

# Determine if we're working with local ComfyUI
if [ "$IS_LOCAL_COMFYUI" = "true" ]; then
  echo "comfyui-init: Running in LOCAL COMFYUI mode"
  echo "comfyui-init: Host ComfyUI URL: ${COMFYUI_HOST_URL:-http://host.docker.internal:8188}"
  echo "comfyui-init: Host models path: /host_models"
  
  # Check if local ComfyUI is accessible
  if curl -sf "${COMFYUI_HOST_URL:-http://host.docker.internal:8188}/system_stats" > /dev/null 2>&1; then
    echo "comfyui-init: ✓ Local ComfyUI is accessible"
  else
    echo "comfyui-init: ⚠ Warning: Cannot reach local ComfyUI at ${COMFYUI_HOST_URL:-http://host.docker.internal:8188}"
    echo "comfyui-init: Please ensure ComfyUI is running on your host machine"
  fi
  
  # For local ComfyUI, use the mounted host models directory
  TARGET_MODELS_PATH="/host_models"
else
  echo "comfyui-init: Running in CONTAINERIZED COMFYUI mode"
  TARGET_MODELS_PATH="$COMFYUI_MODELS_PATH"
fi

echo "comfyui-init: Creating model directories..."
mkdir -p "$TARGET_MODELS_PATH/checkpoints"
mkdir -p "$TARGET_MODELS_PATH/vae"
mkdir -p "$TARGET_MODELS_PATH/controlnet"
mkdir -p "$TARGET_MODELS_PATH/upscale_models"
mkdir -p "$TARGET_MODELS_PATH/clip"
mkdir -p "$TARGET_MODELS_PATH/embeddings"
mkdir -p "$TARGET_MODELS_PATH/loras"

# Also create directories in volume for reference
if [ "$IS_LOCAL_COMFYUI" = "true" ]; then
  mkdir -p "$COMFYUI_MODELS_PATH/checkpoints"
  mkdir -p "$COMFYUI_MODELS_PATH/vae"
  mkdir -p "$COMFYUI_MODELS_PATH/controlnet"
  mkdir -p "$COMFYUI_MODELS_PATH/upscale_models"
  mkdir -p "$COMFYUI_MODELS_PATH/clip"
  mkdir -p "$COMFYUI_MODELS_PATH/embeddings"
  mkdir -p "$COMFYUI_MODELS_PATH/loras"
fi

echo "comfyui-init: Model set: ${COMFYUI_MODEL_SET:-minimal}"
echo "comfyui-init: Fetching active ComfyUI models from database $PGDATABASE on $PGHOST..."

# Build SQL query based on model set configuration
case "${COMFYUI_MODEL_SET:-minimal}" in
  "minimal")
    # Only SD 1.5 checkpoint (no VAE for minimal)
    sql_query="SELECT name, type, filename, download_url, file_size_gb FROM public.comfyui_models WHERE active = true AND name = 'sd_v1-5_pruned_emaonly' ORDER BY type, name;"
    ;;
  "sd15")
    # SD 1.5 checkpoint + VAE
    sql_query="SELECT name, type, filename, download_url, file_size_gb FROM public.comfyui_models WHERE active = true AND (name = 'sd_v1-5_pruned_emaonly' OR name = 'vae_ft_mse_840000_ema_pruned') ORDER BY type, name;"
    ;;
  "sdxl")
    # SDXL checkpoint + VAE
    sql_query="SELECT name, type, filename, download_url, file_size_gb FROM public.comfyui_models WHERE active = true AND (name = 'sdxl_base_1.0' OR name = 'sdxl_vae') ORDER BY type, name;"
    ;;
  "full")
    # All active models (legacy behavior)
    sql_query="SELECT name, type, filename, download_url, file_size_gb FROM public.comfyui_models WHERE active = true ORDER BY type, name;"
    ;;
  *)
    echo "comfyui-init: Warning: Unknown COMFYUI_MODEL_SET '${COMFYUI_MODEL_SET}', defaulting to minimal"
    sql_query="SELECT name, type, filename, download_url, file_size_gb FROM public.comfyui_models WHERE active = true AND name = 'sd_v1-5_pruned_emaonly' ORDER BY type, name;"
    ;;
esac

psql_output=$(PGPASSWORD=$PGPASSWORD psql -h $PGHOST -p $PGPORT -d $PGDATABASE -U $PGUSER -t -c "$sql_query")

if [ -z "$psql_output" ]; then
  echo "comfyui-init: No ComfyUI models found for model set '${COMFYUI_MODEL_SET:-minimal}'."
  echo "comfyui-init: Please check your model set configuration or database content."
else
  echo "comfyui-init: Found models to download for '${COMFYUI_MODEL_SET:-minimal}' set:"
  echo "$psql_output"
  
  # Process each model
  echo "$psql_output" | while IFS='|' read -r name type filename download_url file_size_gb; do
    # Trim whitespace
    name=$(echo "$name" | xargs)
    type=$(echo "$type" | xargs)
    filename=$(echo "$filename" | xargs)
    download_url=$(echo "$download_url" | xargs)
    file_size_gb=$(echo "$file_size_gb" | xargs)
    
    if [ -n "$name" ] && [ -n "$type" ] && [ -n "$filename" ] && [ -n "$download_url" ]; then
      # Determine target directory based on type
      case "$type" in
        "checkpoint")
          target_dir="$TARGET_MODELS_PATH/checkpoints"
          ;;
        "vae")
          target_dir="$TARGET_MODELS_PATH/vae"
          ;;
        "controlnet")
          target_dir="$TARGET_MODELS_PATH/controlnet"
          ;;
        "upscaler")
          target_dir="$TARGET_MODELS_PATH/upscale_models"
          ;;
        "clip")
          target_dir="$TARGET_MODELS_PATH/clip"
          ;;
        "embeddings")
          target_dir="$TARGET_MODELS_PATH/embeddings"
          ;;
        "lora")
          target_dir="$TARGET_MODELS_PATH/loras"
          ;;
        *)
          echo "comfyui-init: Warning: Unknown model type '$type' for model '$name', skipping..."
          continue
          ;;
      esac
      
      target_file="$target_dir/$filename"
      
      # Check if file already exists
      if [ -f "$target_file" ]; then
        echo "comfyui-init: Model '$filename' already exists in $target_dir, skipping download..."
        continue
      fi
      
      echo "comfyui-init: Downloading $name ($type) - $filename (${file_size_gb}GB)..."
      echo "comfyui-init: Source: $download_url"
      echo "comfyui-init: Target: $target_file"
      
      # Download with progress indication and resume capability
      if wget --progress=bar:force:noscroll -c -O "$target_file" "$download_url"; then
        echo "comfyui-init: Successfully downloaded $filename"
        
        # Verify file size if we have the expected size
        if [ -n "$file_size_gb" ] && [ "$file_size_gb" != "null" ]; then
          actual_size=$(stat -c%s "$target_file" 2>/dev/null || echo "0")
          expected_size=$(echo "$file_size_gb * 1024 * 1024 * 1024" | bc 2>/dev/null || echo "0")
          
          if [ "$actual_size" -gt 0 ] && [ "$expected_size" -gt 0 ]; then
            size_diff=$(echo "scale=2; ($actual_size - $expected_size) / $expected_size * 100" | bc 2>/dev/null || echo "0")
            if [ "${size_diff%.*}" -gt 10 ] || [ "${size_diff%.*}" -lt -10 ]; then
              echo "comfyui-init: Warning: Downloaded file size ($actual_size bytes) differs significantly from expected size ($expected_size bytes)"
            fi
          fi
        fi
      else
        echo "comfyui-init: ERROR - Failed to download $filename from $download_url"
        echo "comfyui-init: Removing incomplete file if it exists..."
        rm -f "$target_file"
        # Continue with other models rather than failing completely
      fi
      
      echo # Newline for readability
    fi
  done
fi

# Create a simple status file to indicate completion
echo "comfyui-init: Creating completion marker..."
echo "$(date): ComfyUI model download completed" > "$TARGET_MODELS_PATH/.download_complete"
# Also create in volume directory for reference
if [ "$IS_LOCAL_COMFYUI" = "true" ]; then
  echo "$(date): ComfyUI model download completed (local mode)" > "$COMFYUI_MODELS_PATH/.download_complete"
fi

echo "comfyui-init: Model download process completed successfully."
if [ "$IS_LOCAL_COMFYUI" = "true" ]; then
  echo "comfyui-init: Models are available in: /host_models (mounted from $COMFYUI_LOCAL_MODELS_PATH)"
  echo "comfyui-init: Local ComfyUI should be able to access models at: $COMFYUI_LOCAL_MODELS_PATH"
else
  echo "comfyui-init: Models are available in: $COMFYUI_MODELS_PATH"
fi
echo "comfyui-init: Directory structure:"
find "$TARGET_MODELS_PATH" -type f -name "*.safetensors" -o -name "*.pt" -o -name "*.pth" -o -name "*.bin" | head -20