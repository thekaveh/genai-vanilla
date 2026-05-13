#!/bin/sh
set -e

echo "n8n-init: Starting n8n community nodes installation..."

# Check required environment variables
if [ -z "$N8N_HOST" ] || [ -z "$N8N_PORT" ]; then
  echo "n8n-init: Error: N8N_HOST and N8N_PORT environment variables are required."
  echo "N8N_HOST=$N8N_HOST, N8N_PORT=$N8N_PORT"
  exit 1
fi

echo "n8n-init: Installing community nodes..."
# Run nodes installation script
if [ -f "/scripts/install-nodes.sh" ]; then
  /scripts/install-nodes.sh
else
  echo "n8n-init: ERROR - install-nodes.sh script not found!"
  exit 1
fi

echo "n8n-init: ✓ n8n community nodes installation completed successfully!"
echo "n8n-init: Your n8n instance now has:"
echo "n8n-init: - ComfyUI integration nodes"
echo "n8n-init: - Model Context Protocol (MCP) nodes"
echo "n8n-init:"
echo "n8n-init: 📋 Next Steps:"
echo "n8n-init: 1. Complete n8n user setup via the web UI"
echo "n8n-init: 2. Manually import workflow templates from /config/"
echo "n8n-init: 3. Set up PostgreSQL credentials for database access"