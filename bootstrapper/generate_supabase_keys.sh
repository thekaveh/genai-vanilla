#!/usr/bin/env sh
#
# GenAI Vanilla Stack - Supabase Key Generator Wrapper
#
# This is a thin wrapper that calls the Python implementation for full cross-platform compatibility.
# The original Bash implementation is available in legacy_scripts/generate_supabase_keys.sh
#

exec sh "$(dirname "$0")/_run.sh" generate_supabase_keys.py "$@"
