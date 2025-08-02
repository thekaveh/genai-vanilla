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
while ! curl -s --fail "$N8N_API_URL/" > /dev/null 2>&1; do
  if [ $elapsed -ge $timeout ]; then
    echo "n8n-init: ERROR - Timeout waiting for n8n to be ready after ${timeout}s"
    exit 1
  fi
  echo "n8n-init: Waiting for n8n API... (${elapsed}s elapsed)"
  sleep 10
  elapsed=$((elapsed + 10))
done
echo "n8n-init: n8n API is ready."

# Additional wait to ensure n8n is fully initialized
echo "n8n-init: Allowing additional time for n8n full initialization..."
sleep 15

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

echo "$NODES_TO_INSTALL" | while IFS= read -r node_name; do
  # Skip empty lines
  node_clean=$(echo "$node_name" | xargs)
  if [ -z "$node_clean" ]; then
    continue
  fi
  
  echo "n8n-init: Installing node: $node_clean"
  
  # Try to install the node via n8n REST API
  # First, check if the node is already installed
  installed_check=$(curl -s -X GET "$N8N_API_URL/rest/community-packages" \
    -H "Content-Type: application/json" 2>/dev/null || echo "[]")
  
  # Check if node is already installed
  if echo "$installed_check" | jq -e --arg name "$node_clean" '.[] | select(.packageName == $name)' > /dev/null 2>&1; then
    echo "n8n-init: Node $node_clean is already installed, skipping."
    success_count=$((success_count + 1))
    continue
  fi
  
  # Install the node
  install_response=$(curl -s -X POST "$N8N_API_URL/rest/community-packages" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$node_clean\"}" \
    2>&1)
  
  curl_exit_code=$?
  
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
done

echo "n8n-init: Installation summary:"
echo "n8n-init: - Successful installations: $success_count"
echo "n8n-init: - Failed installations: $failure_count"

if [ $failure_count -gt 0 ]; then
  echo "n8n-init: WARNING - Some node installations failed. Check logs above."
else
  echo "n8n-init: ✓ All nodes installed successfully!"
fi

echo "n8n-init: Community nodes installation process completed."