#!/bin/sh
# services/comfyui/init/scripts/download_models.sh
#
# Queries public.comfyui_models (UPSERTed by comfyui-catalog-init) for
# every active row and downloads the file into the correct subdirectory
# of /opt/ComfyUI/models. Mirrors services/ollama/pull/scripts/pull.sh's
# structure: psql tab-separated SELECT + tempfile loop + wget.
#
# Failures are non-fatal: bad rows / failed wgets increment FAIL_COUNT
# and the script still exits 0 + writes the .download_complete marker
# so ComfyUI can start (workflows referencing missing models just fail
# at render time — the historical behavior).
#
# Required apk packages on alpine: wget ca-certificates postgresql-client
# — installed inline below.
set -e

apk add --no-cache wget ca-certificates postgresql-client

MODELS_ROOT="${COMFYUI_MODELS_PATH:-/models}"

# Required env vars — same shape as services/ollama/pull/scripts/pull.sh.
if [ -z "$PGHOST" ] || [ -z "$PGUSER" ] || [ -z "$PGPASSWORD" ] || [ -z "$PGDATABASE" ]; then
  echo "comfyui-init: Error: One or more required PG env vars are not set."
  echo "PGHOST=$PGHOST, PGUSER=$PGUSER, PGPASSWORD=[set], PGDATABASE=$PGDATABASE"
  exit 1
fi

# 1. Materialize per-category directories (idempotent on every run).
for d in checkpoints vae loras controlnet ipadapter instantid \
         upscale_models embeddings clip animatediff_models \
         animatediff_motion_lora voice audio mesh_models; do
  mkdir -p "$MODELS_ROOT/$d"
done

# Map category enum → directory. Mirrors CATEGORY_TARGET_DIR in
# bootstrapper/utils/comfyui_library.py. Keep in sync with that dict
# when adding new categories.
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

# 2. Pull the active set from Postgres.
# Tab-separated, header-less, tuples-only — mirrors ollama-pull's pattern.
# Use a tempfile rather than a pipe so the while-loop body runs in the
# current shell, not a subshell. A piped `cmd | while read` forks a
# subshell for the loop body on POSIX sh / Alpine ash, causing counter
# mutations (OK_COUNT etc.) to be lost when the loop exits.
echo "comfyui-init: Fetching active ComfyUI models from $PGDATABASE on $PGHOST..."
PGPASSWORD="$PGPASSWORD" psql \
  -h "$PGHOST" -p "${PGPORT:-5432}" -d "$PGDATABASE" -U "$PGUSER" \
  -A -F $'\t' -t \
  -c "SELECT name, type, filename, download_url, COALESCE(sha256, '') FROM public.comfyui_models WHERE active = true ORDER BY name;" \
  > /tmp/_comfy_active 2>/tmp/_comfy_psql_err \
  || { echo "✗ psql query failed:"; cat /tmp/_comfy_psql_err; FAIL_COUNT=$((FAIL_COUNT + 1)); > /tmp/_comfy_active; }

if [ ! -s /tmp/_comfy_active ]; then
  echo "(no active comfyui_models rows — nothing to download)"
else
  row_count=$(wc -l < /tmp/_comfy_active | tr -d ' ')
  echo "--- found $row_count active row(s) ---"
  while IFS=$'\t' read -r name category filename url sha; do
    # Skip blank lines (defensive against trailing newline-only chunks).
    if [ -z "$name" ] || [ -z "$url" ]; then
      echo "✗ row with missing name or url; skipping"
      FAIL_COUNT=$((FAIL_COUNT + 1))
      continue
    fi
    dir=$(category_to_dir "$category")
    if [ -z "$dir" ]; then
      echo "✗ $name: unknown category '$category'; skipping"
      FAIL_COUNT=$((FAIL_COUNT + 1))
      continue
    fi
    # Filename column is authoritative; fall back to a URL-derived
    # basename only if the DB row is empty.
    if [ -z "$filename" ]; then
      filename=$(basename "$url" | cut -d '?' -f 1)
    fi
    download_one "$name" "$url" "$MODELS_ROOT/$dir/$filename" "$sha"
  done < /tmp/_comfy_active
fi
rm -f /tmp/_comfy_active /tmp/_comfy_psql_err

echo "--- summary: $OK_COUNT downloaded, $SKIP_COUNT cached, $FAIL_COUNT failed ---"
touch "$MODELS_ROOT/.download_complete"
exit 0
