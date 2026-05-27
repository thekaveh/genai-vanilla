#!/usr/bin/env sh
#
# GenAI Vanilla Stack - Start Script Wrapper
#
# This is a thin wrapper that calls the Python implementation for full cross-platform compatibility.
# The original Bash implementation is available in bootstrapper/legacy_scripts/start.sh.original
#

# Change to the script directory
cd "$(dirname "$0")"

exec sh bootstrapper/_run.sh start.py "$@"
