#!/usr/bin/env sh
#
# GenAI Vanilla Stack - Start Script Wrapper
#
# This is a thin wrapper that calls the Python implementation for full cross-platform compatibility.
#

# Change to the script directory
cd "$(dirname "$0")" || { echo "start.sh: failed to enter script directory" >&2; exit 1; }

exec sh bootstrapper/_run.sh start.py "$@"
