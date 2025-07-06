#!/bin/bash

# Health check for Local Deep Researcher
# Check if the LangGraph server is responding

HEALTH_URL="http://localhost:2024"

# Try to connect to the server
if curl -s --max-time 5 --fail "$HEALTH_URL" > /dev/null 2>&1; then
    echo "Local Deep Researcher: Health check passed"
    exit 0
else
    echo "Local Deep Researcher: Health check failed"
    exit 1
fi
