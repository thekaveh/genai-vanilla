#!/usr/bin/env sh
#
# GenAI Vanilla Stack - Supabase Key Generator Wrapper
#
# This is a thin wrapper that calls the Python implementation for full cross-platform compatibility.
# The original Bash implementation is available in bootstrapper/legacy_scripts/generate_supabase_keys.sh
#

# Change to the script directory
cd "$(dirname "$0")"

# Check if uv is available and use it for better dependency management
if command -v uv >/dev/null 2>&1; then
    echo "📦 Using uv for dependency management..."
    exec uv run --directory bootstrapper generate_supabase_keys.py "$@"
else
    # Fallback to system Python
    echo "📦 Using system Python (install uv for better dependency management)..."
    exec python3 bootstrapper/generate_supabase_keys.py "$@"
fi