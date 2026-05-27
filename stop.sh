#!/usr/bin/env sh
#
# GenAI Vanilla Stack - Stop Script Wrapper
#
# This is a thin wrapper that calls the Python implementation for full cross-platform compatibility.
#

# Change to the script directory
cd "$(dirname "$0")"

exec sh bootstrapper/_run.sh stop.py "$@"
