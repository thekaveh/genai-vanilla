#!/bin/bash

set -euo pipefail

ENV_FILE=".env"
ISSUER="supabase-local"
EXPIRY_SECONDS=$((60 * 60 * 24 * 365 * 10))  # 10 years

echo "🔐 Generating SUPABASE_JWT_SECRET..."
SUPABASE_JWT_SECRET=$(openssl rand -hex 32)

base64url_encode() {
  echo -n "$1" | base64 | tr -d '=' | tr '/+' '_-'
}

generate_jwt() {
  local ROLE="$1"
  local HEADER='{"alg":"HS256","typ":"JWT"}'
  local EXP=$(($(date +%s) + EXPIRY_SECONDS))
  local PAYLOAD="{\"role\":\"$ROLE\",\"iss\":\"$ISSUER\",\"exp\":$EXP}"

  local HEADER_B64=$(base64url_encode "$HEADER")
  local PAYLOAD_B64=$(base64url_encode "$PAYLOAD")
  local UNSIGNED="${HEADER_B64}.${PAYLOAD_B64}"
  local SIGNATURE=$(echo -n "$UNSIGNED" | openssl dgst -sha256 -hmac "$SUPABASE_JWT_SECRET" -binary | base64 | tr -d '=' | tr '/+' '_-')

  echo "${UNSIGNED}.${SIGNATURE}"
}

SUPABASE_ANON_KEY=$(generate_jwt "anon")
SUPABASE_SERVICE_KEY=$(generate_jwt "service_role")

echo "✅ Keys generated."

# Update or insert into .env
update_env() {
  local KEY="$1"
  local VALUE="$2"
  if grep -q "^${KEY}=" "$ENV_FILE" 2>/dev/null; then
    sed -i.bak "s|^${KEY}=.*|${KEY}=${VALUE}|" "$ENV_FILE"
  else
    echo "${KEY}=${VALUE}" >> "$ENV_FILE"
  fi
}

update_env "SUPABASE_JWT_SECRET" "$SUPABASE_JWT_SECRET"
update_env "SUPABASE_ANON_KEY" "$SUPABASE_ANON_KEY"
update_env "SUPABASE_SERVICE_KEY" "$SUPABASE_SERVICE_KEY"

echo "🔄 .env updated:"
echo "  - SUPABASE_JWT_SECRET"
echo "  - SUPABASE_ANON_KEY"
echo "  - SUPABASE_SERVICE_KEY"