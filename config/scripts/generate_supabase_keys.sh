#!/usr/bin/env bash

# More portable shebang that works across different Unix-like systems

# Set error handling, but in a more compatible way
set -e
set -u

ENV_FILE=".env"
ISSUER="supabase-local"
EXPIRY_SECONDS=$((60 * 60 * 24 * 365 * 10))  # 10 years

echo "🔐 Generating SUPABASE_JWT_SECRET..."
SUPABASE_JWT_SECRET=$(openssl rand -hex 32)

# Cross-platform base64url encoding function
base64url_encode() {
  # Different base64 options for different platforms
  if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo -n "$1" | base64 | tr -d '\n' | tr -d '=' | tr '+/' '-_'
  else
    # Linux and others
    echo -n "$1" | base64 -w 0 | tr -d '=' | tr '+/' '-_'
  fi
}

generate_jwt() {
  local ROLE="$1"
  local HEADER='{"alg":"HS256","typ":"JWT"}'
  local EXP=$(($(date +%s) + EXPIRY_SECONDS))
  local PAYLOAD="{\"role\":\"$ROLE\",\"iss\":\"$ISSUER\",\"exp\":$EXP}"

  local HEADER_B64=$(base64url_encode "$HEADER")
  local PAYLOAD_B64=$(base64url_encode "$PAYLOAD")
  local UNSIGNED="${HEADER_B64}.${PAYLOAD_B64}"
  
  # Cross-platform way to generate signature
  if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    local SIGNATURE=$(echo -n "$UNSIGNED" | openssl dgst -sha256 -hmac "$SUPABASE_JWT_SECRET" -binary | base64 | tr -d '\n' | tr -d '=' | tr '+/' '-_')
  else
    # Linux and others
    local SIGNATURE=$(echo -n "$UNSIGNED" | openssl dgst -sha256 -hmac "$SUPABASE_JWT_SECRET" -binary | base64 -w 0 | tr -d '=' | tr '+/' '-_')
  fi

  echo "${UNSIGNED}.${SIGNATURE}"
}

SUPABASE_ANON_KEY=$(generate_jwt "anon")
SUPABASE_SERVICE_KEY=$(generate_jwt "service_role")

echo "✅ Keys generated."

# Cross-platform way to update environment variables
update_env() {
  local KEY="$1"
  local VALUE="$2"
  local TEMP_FILE="${ENV_FILE}.tmp"
  
  # Check if file exists
  if [ ! -f "$ENV_FILE" ]; then
    touch "$ENV_FILE"
  fi
  
  # Check if key exists
  if grep -q "^${KEY}=" "$ENV_FILE" 2>/dev/null; then
    # Different sed syntax for different platforms
    if [[ "$OSTYPE" == "darwin"* ]]; then
      # macOS requires an extension with -i
      sed -i '' "s|^${KEY}=.*|${KEY}=${VALUE}|" "$ENV_FILE"
    else
      # Linux
      sed -i "s|^${KEY}=.*|${KEY}=${VALUE}|" "$ENV_FILE"
    fi
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

# Add Windows compatibility note
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
  echo ""
  echo "⚠️  Windows detected: If you encounter any issues, please run this script in Git Bash or WSL."
fi
