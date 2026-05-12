#!/usr/bin/env bash
# init-hermes.sh — render /opt/data/config.yaml (and supporting files)
# from environment, then exit. Runs before the hermes service starts
# (see docker-compose.yml depends_on).
#
# Idempotent: re-running overwrites the GENERATED files but leaves
# user-edited files (sessions/, memories/MEMORY.md, etc.) intact.
#
# Three responsibilities:
#   1. Ensure /opt/data exists and is owned by HERMES_UID:HERMES_GID
#      (the hermes container runs as that user).
#   2. Render /opt/data/config.yaml from /templates/config.yaml.tmpl
#      via envsubst, surgically dropping provider blocks whose
#      *_INTERNAL_URL is empty (i.e. the underlying stack service is
#      disabled).
#   3. Drop a comfyui-host override file under /opt/data/skills/ so
#      Hermes's bundled creative-comfyui skill targets our internal
#      comfyui:18188 instead of its hardcoded 127.0.0.1:8188.
#
# Exits non-zero on any unexpected condition so docker compose surfaces
# the failure instead of letting hermes start with a broken config.

set -euo pipefail

DATA_DIR=/opt/data
CONFIG_OUT="${DATA_DIR}/config.yaml"
SKILLS_DIR="${DATA_DIR}/skills"
TEMPLATE_DIR=/templates

HERMES_UID="${HERMES_UID:-10000}"
HERMES_GID="${HERMES_GID:-10000}"

log() { printf '[hermes-init] %s\n' "$*"; }

log "starting"
log "  DATA_DIR=${DATA_DIR}"
log "  CONFIG_OUT=${CONFIG_OUT}"
log "  HERMES_UID:HERMES_GID=${HERMES_UID}:${HERMES_GID}"

mkdir -p "${DATA_DIR}" "${SKILLS_DIR}"

# ─── render config.yaml ────────────────────────────────────────────
# envsubst replaces ${VAR}; the template references only the env vars
# we explicitly export below so unrelated env vars (LITELLM_MASTER_KEY
# etc.) don't accidentally land in config.yaml in plain text via
# stray ${...} occurrences.

# Defaults so envsubst never emits a literal "/v1" with no host.
export HERMES_DEFAULT_MODEL="${HERMES_DEFAULT_MODEL:-}"
export HERMES_CONTEXT_LENGTH="${HERMES_CONTEXT_LENGTH:-65536}"
export LITELLM_MASTER_KEY="${LITELLM_MASTER_KEY:-}"
export XTTS_INTERNAL_URL="${XTTS_INTERNAL_URL:-}"
export PARAKEET_INTERNAL_URL="${PARAKEET_INTERNAL_URL:-}"
export COMFYUI_INTERNAL_URL="${COMFYUI_INTERNAL_URL:-}"
export SEARXNG_INTERNAL_URL="${SEARXNG_INTERNAL_URL:-}"

# Build the variable list explicitly so envsubst only touches the
# ones we know about.
VARS='${HERMES_DEFAULT_MODEL} ${HERMES_CONTEXT_LENGTH} ${LITELLM_MASTER_KEY}
${XTTS_INTERNAL_URL} ${PARAKEET_INTERNAL_URL} ${COMFYUI_INTERNAL_URL}
${SEARXNG_INTERNAL_URL}'

if [[ ! -f "${TEMPLATE_DIR}/config.yaml.tmpl" ]]; then
  log "❌ template ${TEMPLATE_DIR}/config.yaml.tmpl is missing — check the bind mount"
  exit 1
fi

rendered=$(envsubst "$VARS" < "${TEMPLATE_DIR}/config.yaml.tmpl")

# Strip provider blocks whose URL came out empty. The template uses
# sentinel comment lines `# BEGIN-TTS / # END-TTS` etc. so we can
# safely delete a multi-line block when its URL didn't resolve.
strip_block() {
  local tag="$1" url_var="$2"
  if [[ -z "${!url_var:-}" ]]; then
    rendered=$(printf '%s\n' "$rendered" \
      | awk -v t="$tag" '
          $0 ~ "# BEGIN-"t"$" {skip=1; next}
          $0 ~ "# END-"t"$"   {skip=0; next}
          !skip {print}
        ')
    log "  dropped ${tag} block (no ${url_var})"
  fi
}

strip_block TTS    XTTS_INTERNAL_URL
strip_block STT    PARAKEET_INTERNAL_URL
strip_block SEARCH SEARXNG_INTERNAL_URL

# Atomic write so a crash mid-write doesn't leave a partial config.
tmp="${CONFIG_OUT}.tmp"
printf '%s\n' "$rendered" > "$tmp"
mv "$tmp" "$CONFIG_OUT"
log "wrote ${CONFIG_OUT}"

# ─── ComfyUI host override ─────────────────────────────────────────
# Drop a skill-override that pins comfyui-host to our internal URL,
# bypassing the bundled skill's hardcoded 127.0.0.1:8188.
if [[ -n "${COMFYUI_INTERNAL_URL:-}" && -f "${TEMPLATE_DIR}/comfyui-host-override.md" ]]; then
  out="${SKILLS_DIR}/creative-comfyui-host-override.md"
  COMFYUI_INTERNAL_URL="${COMFYUI_INTERNAL_URL}" \
    envsubst '${COMFYUI_INTERNAL_URL}' < "${TEMPLATE_DIR}/comfyui-host-override.md" > "${out}.tmp"
  mv "${out}.tmp" "${out}"
  log "wrote ${out}"
else
  log "skipped ComfyUI host override (COMFYUI_INTERNAL_URL empty or template missing)"
fi

# ─── ownership ─────────────────────────────────────────────────────
chown -R "${HERMES_UID}:${HERMES_GID}" "${DATA_DIR}" 2>/dev/null || {
  log "⚠ chown failed (running rootless?) — hermes container may need to fix perms itself"
}

log "done"
