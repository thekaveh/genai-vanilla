#!/bin/sh
# services/comfyui/init/scripts/download_models.sh
#
# Reads the bootstrapper-emitted snapshot at /catalog-snapshot.json plus
# the sidecar at /custom-models.yaml. Downloads each entry into the
# correct subdirectory of /opt/ComfyUI/models. Failures are non-fatal.
#
# Required apk packages on alpine: wget jq yq coreutils ca-certificates
# — installed inline below.
set -e

apk add --no-cache wget jq yq coreutils ca-certificates

SNAPSHOT="${COMFYUI_CATALOG_SNAPSHOT:-/catalog-snapshot.json}"
CUSTOM="${COMFYUI_CUSTOM_MODELS_FILE:-/custom-models.yaml}"
MODELS_ROOT="${COMFYUI_MODELS_PATH:-/models}"

# 1. Materialize per-category directories (idempotent on every run).
for d in checkpoints vae loras controlnet ipadapter instantid \
         upscale_models embeddings clip animatediff_models \
         animatediff_motion_lora voice audio mesh_models; do
  mkdir -p "$MODELS_ROOT/$d"
done

# Map sidecar category enum → directory. Snapshot entries carry target_dir
# directly so this is only used by the YAML branch below.
category_to_dir() {
  case "$1" in
    checkpoint)   echo "checkpoints" ;;
    vae)          echo "vae" ;;
    lora)         echo "loras" ;;
    controlnet)   echo "controlnet" ;;
    ipadapter)    echo "ipadapter" ;;
    instantid)    echo "instantid" ;;
    upscaler)     echo "upscale_models" ;;
    embedding)    echo "embeddings" ;;
    clip)         echo "clip" ;;
    animatediff)  echo "animatediff_models" ;;
    motion_lora)  echo "animatediff_motion_lora" ;;
    video_model)  echo "checkpoints" ;;
    voice_model)  echo "voice" ;;
    audio_model)  echo "audio" ;;
    mesh_model)   echo "mesh_models" ;;
    *)            echo "" ;;
  esac
}

# Counters for the summary line.
OK_COUNT=0
SKIP_COUNT=0
FAIL_COUNT=0

# download_one <name> <url> <dest_path> <sha256_or_empty>
# Skip if dest exists with non-zero size AND (no SHA OR SHA matches).
# Failure is non-fatal: log + increment FAIL_COUNT + return 0.
download_one() {
  name="$1"; url="$2"; dest="$3"; sha="$4"
  if [ -s "$dest" ]; then
    if [ -n "$sha" ]; then
      if echo "$sha  $dest" | sha256sum -c - >/dev/null 2>&1; then
        echo "= $name (cached, sha verified)"
        SKIP_COUNT=$((SKIP_COUNT + 1))
        return 0
      else
        echo "! $name (cached but sha mismatch — re-downloading)"
        rm -f "$dest"
      fi
    else
      echo "= $name (cached)"
      SKIP_COUNT=$((SKIP_COUNT + 1))
      return 0
    fi
  fi
  echo "+ $name → $dest"
  wget_rc=0
  wget_out=$(wget -c -O "$dest" "$url" 2>&1) || wget_rc=$?
  printf '%s\n' "$wget_out" | tail -1
  if [ $wget_rc -eq 0 ]; then
    OK_COUNT=$((OK_COUNT + 1))
  else
    echo "✗ $name failed (wget exit $wget_rc)"
    rm -f "$dest"  # clean up any partial file
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

# 2. Snapshot (jq parses).
# Use a tempfile rather than a pipe so the while-loop body runs in the
# current shell, not a subshell. A piped `cmd | while read` forks a
# subshell for the loop body on POSIX sh / Alpine ash, causing counter
# mutations (OK_COUNT etc.) to be lost when the loop exits.
if [ -s "$SNAPSHOT" ]; then
  echo "--- snapshot: $SNAPSHOT ---"
  jq -c '.entries // [] | .[]' "$SNAPSHOT" > /tmp/_snapshot_entries
  while IFS= read -r entry; do
    name=$(echo "$entry" | jq -r '.name')
    url=$(echo "$entry" | jq -r '.url')
    dir=$(echo "$entry" | jq -r '.target_dir')
    file=$(echo "$entry" | jq -r '.filename')
    sha=$(echo "$entry" | jq -r '.sha256 // empty')
    if [ -z "$url" ] || [ "$url" = "null" ] || [ -z "$name" ] || [ "$name" = "null" ]; then
      echo "✗ snapshot entry missing name or url; skipping"
      FAIL_COUNT=$((FAIL_COUNT + 1))
      continue
    fi
    download_one "$name" "$url" "$MODELS_ROOT/$dir/$file" "$sha"
  done < /tmp/_snapshot_entries
  rm -f /tmp/_snapshot_entries
else
  echo "(no snapshot at $SNAPSHOT — skipping catalog entries)"
fi

# 3. Sidecar YAML (yq → jq).
# Same tempfile pattern to preserve counter state across the loop.
if [ -s "$CUSTOM" ]; then
  echo "--- sidecar: $CUSTOM ---"
  yq -o=json '.models // [] | .[]' "$CUSTOM" 2>/dev/null | jq -c '.' > /tmp/_sidecar_entries || true
  while IFS= read -r entry; do
    name=$(echo "$entry" | jq -r '.name')
    url=$(echo "$entry" | jq -r '.url')
    category=$(echo "$entry" | jq -r '.category')
    sha=$(echo "$entry" | jq -r '.sha256 // empty')
    if [ -z "$url" ] || [ "$url" = "null" ] || [ -z "$name" ] || [ "$name" = "null" ]; then
      echo "✗ sidecar entry missing name or url; skipping"
      FAIL_COUNT=$((FAIL_COUNT + 1))
      continue
    fi
    dir=$(category_to_dir "$category")
    if [ -z "$dir" ]; then
      echo "✗ $name: unknown category '$category'; skipping"
      FAIL_COUNT=$((FAIL_COUNT + 1))
      continue
    fi
    file=$(basename "$url" | cut -d '?' -f 1)
    download_one "$name" "$url" "$MODELS_ROOT/$dir/$file" "$sha"
  done < /tmp/_sidecar_entries
  rm -f /tmp/_sidecar_entries
else
  echo "(no sidecar at $CUSTOM — skipping custom entries)"
fi

echo "--- summary: $OK_COUNT downloaded, $SKIP_COUNT cached, $FAIL_COUNT failed ---"
touch "$MODELS_ROOT/.download_complete"
exit 0
