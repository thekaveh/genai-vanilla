#!/bin/sh
set -e

echo "n8n-init: Starting n8n community nodes installation process..."

# Check required environment variables
if [ -z "$N8N_HOST" ] || [ -z "$N8N_PORT" ]; then
  echo "n8n-init: Error: N8N_HOST and N8N_PORT environment variables are required."
  echo "N8N_HOST=$N8N_HOST, N8N_PORT=$N8N_PORT"
  exit 1
fi

echo "n8n-init: Installing required tools..."
apk add --no-cache curl jq nodejs npm

# Construct n8n API URL
N8N_API_URL="http://${N8N_HOST}:${N8N_PORT}"
echo "n8n-init: Using n8n API at $N8N_API_URL"

echo "n8n-init: Waiting for n8n to be ready..."
# Wait for n8n to be fully ready (check healthz endpoint or root endpoint)
timeout=300  # 5 minutes timeout
elapsed=0
while ! curl -s --fail --max-time 5 "$N8N_API_URL/" > /dev/null 2>&1; do
  if [ $elapsed -ge $timeout ]; then
    echo "n8n-init: ERROR - Timeout waiting for n8n to be ready after ${timeout}s"
    exit 1
  fi
  echo "n8n-init: Waiting for n8n API... (${elapsed}s elapsed)"
  sleep 10
  elapsed=$((elapsed + 10))
done
echo "n8n-init: n8n API is ready."

# Wait for the community-packages REST endpoint to come online. n8n's
# root / responds before the REST router is wired up, so a blanket
# `sleep 15` was previously used as a crude readiness gate. Polling the
# actual endpoint we depend on tightens the loop and removes the
# unconditional 15s startup tax on warm restarts.
echo "n8n-init: Waiting for n8n community-packages endpoint to be ready..."
pkg_timeout=120
pkg_elapsed=0
community_packages_response="/tmp/n8n-community-packages.json"
community_packages_status="000"
while true; do
  community_packages_status=$(curl -s -o "$community_packages_response" -w "%{http_code}" --max-time 5 "$N8N_API_URL/rest/community-packages" -H "Content-Type: application/json" 2>/dev/null || true)
  case "$community_packages_status" in
    2*)
      break
      ;;
    401|403)
      echo "n8n-init: /rest/community-packages requires an authenticated session."
      echo "n8n-init: Assuming owner setup already completed; skipping first-boot community-node init."
      exit 0
      ;;
  esac
  if [ $pkg_elapsed -ge $pkg_timeout ]; then
    echo "n8n-init: WARNING - /rest/community-packages still not ready after ${pkg_timeout}s; proceeding anyway."
    break
  fi
  sleep 2
  pkg_elapsed=$((pkg_elapsed + 2))
done

# Get nodes to install from environment variable or config file
if [ -n "$N8N_INIT_NODES" ]; then
  echo "n8n-init: Using nodes list from environment variable: $N8N_INIT_NODES"
  # Convert comma-separated list to array
  NODES_TO_INSTALL=$(echo "$N8N_INIT_NODES" | tr ',' '\n')
else
  echo "n8n-init: Reading nodes list from config file..."
  if [ -f "/config/nodes.json" ]; then
    NODES_TO_INSTALL=$(jq -r '.nodes[].name' /config/nodes.json)
  else
    echo "n8n-init: No config file found and no N8N_INIT_NODES environment variable set."
    echo "n8n-init: No nodes to install."
    exit 0
  fi
fi

if [ -z "$NODES_TO_INSTALL" ]; then
  echo "n8n-init: No nodes specified for installation."
  exit 0
fi

echo "n8n-init: Nodes to install:"
echo "$NODES_TO_INSTALL"

# Install each node
success_count=0
failure_count=0

# NOTE: do NOT pipe into the while loop. POSIX shells run the right-hand
# side of a pipeline in a subshell, so success_count / failure_count
# increments inside the loop body would be lost on exit. A here-doc
# (`done <<EOF ... EOF`) keeps the loop in the current shell.
while IFS= read -r node_name; do
  # Skip empty lines
  node_clean=$(echo "$node_name" | xargs)
  if [ -z "$node_clean" ]; then
    continue
  fi

  echo "n8n-init: Installing node: $node_clean"

  # Try to install the node via n8n REST API
  # First, check if the node is already installed. --fail makes curl exit
  # non-zero on HTTP 4xx/5xx so the `|| echo "[]"` fallback fires (matching
  # the readiness curls at lines 24 and 43); without it, an error-page body
  # would be fed to jq and silently fail to parse the same way.
  installed_response="/tmp/n8n-installed-packages.json"
  installed_status=$(curl -s -o "$installed_response" -w "%{http_code}" --max-time 15 -X GET "$N8N_API_URL/rest/community-packages" \
    -H "Content-Type: application/json" 2>/dev/null || true)
  case "$installed_status" in
    2*)
      installed_check=$(cat "$installed_response")
      ;;
    401|403)
      echo "n8n-init: /rest/community-packages now requires login; skipping first-boot community-node init."
      exit 0
      ;;
    *)
      installed_check="[]"
      ;;
  esac

  # Check if node is already installed. n8n's internal /rest API wraps
  # list payloads in a {"data": [...]} envelope — unwrap it, falling back
  # to a bare array for older shapes. (The old bare `.[]` indexed into
  # the envelope and errored, so every node looked "not installed" on
  # every boot.) NOTE: /rest/* needs a session cookie once an owner
  # account exists, so this init can only install nodes on a first-boot
  # stack; afterwards the calls 401 and are counted as failures below.
  if echo "$installed_check" | jq -e --arg name "$node_clean" '(.data? // .) | .[] | select(.packageName == $name)' > /dev/null 2>&1; then
    echo "n8n-init: Node $node_clean is already installed, skipping."
    success_count=$((success_count + 1))
    continue
  fi

  # Install the node. `set -e` above would abort on the first failed install
  # before the manual error-handling below runs, so we explicitly tolerate
  # non-zero exits here and rely on the if-check on $? instead. --fail
  # promotes HTTP 4xx/5xx to a non-zero curl exit; without it, n8n
  # responses lacking a .error field (e.g. `{"message": "Internal error"}`
  # on HTTP 500) are silently treated as success because the jq -e '.error'
  # check below only matches when that exact key exists.
  curl_exit_code=0
  install_response=$(curl -s --fail --max-time 120 -X POST "$N8N_API_URL/rest/community-packages" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$node_clean\"}" \
    2>&1) || curl_exit_code=$?

  if [ $curl_exit_code -eq 0 ]; then
    # Check if response contains error
    if echo "$install_response" | jq -e '.error' > /dev/null 2>&1; then
      error_msg=$(echo "$install_response" | jq -r '.error // .message // "Unknown error"')
      echo "n8n-init: ERROR - Failed to install $node_clean: $error_msg"
      failure_count=$((failure_count + 1))
    else
      echo "n8n-init: ✓ Successfully installed $node_clean"
      success_count=$((success_count + 1))
    fi
  else
    echo "n8n-init: ERROR - HTTP request failed for $node_clean (exit code: $curl_exit_code)"
    echo "n8n-init: Response: $install_response"
    failure_count=$((failure_count + 1))
  fi

  # Small delay between installations
  sleep 2
done <<EOF
$NODES_TO_INSTALL
EOF

echo "n8n-init: Installation summary:"
echo "n8n-init: - Successful installations: $success_count"
echo "n8n-init: - Failed installations: $failure_count"

if [ $failure_count -gt 0 ]; then
  echo "n8n-init: ERROR - Some node installations failed. Check logs above."
  exit 1
else
  echo "n8n-init: ✓ All nodes installed successfully!"
fi

echo "n8n-init: Community nodes installation process completed."
