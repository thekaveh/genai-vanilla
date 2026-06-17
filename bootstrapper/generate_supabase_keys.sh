#!/usr/bin/env sh
#
# Atlas - Supabase Key Generator Wrapper
#
# This is a thin wrapper that calls the Python implementation for full cross-platform compatibility.
#

exec sh "$(dirname "$0")/_run.sh" generate_supabase_keys.py "$@"
