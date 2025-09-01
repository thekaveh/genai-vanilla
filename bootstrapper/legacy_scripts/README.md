# Legacy Scripts

This directory contains the original Bash implementations and legacy utilities from the GenAI Vanilla Stack migration to Python.

## Files

### Original Implementations (Reference Only)
- **`start.sh.original`** - Original 1,332-line Bash implementation of the start script
- **`stop.sh.original`** - Original 226-line Bash implementation of the stop script

These scripts have been **fully migrated to Python** and are kept here for reference only.

### Legacy Utilities (All Migrated)
- **`hosts-utils.sh`** - Bash utilities for hosts file management
  - ✅ **MIGRATED**: Functionality fully implemented in `../utils/hosts_manager.py`
  - Kept for reference and compatibility with other scripts
  
- **`generate_supabase_keys.sh`** - Standalone utility for generating Supabase JWT keys
  - ✅ **MIGRATED**: Functionality fully implemented in `../utils/supabase_keys.py` and `../generate_supabase_keys.py`
  - Use the new Python version: `../../generate_supabase_keys.sh` (wrapper script)
  - Cross-platform script for generating SUPABASE_JWT_SECRET, SUPABASE_ANON_KEY, and SUPABASE_SERVICE_KEY

## Migration Status

The main start/stop functionality has been completely migrated to Python with full feature parity:
- 🎯 **Python Implementation**: `../start.py` and `../stop.py`
- 🔧 **Wrapper Scripts**: `../../start.sh` and `../../stop.sh` (thin wrappers)
- 🌍 **Cross-Platform**: Works on Windows, macOS, and Linux without shell compatibility issues

## Usage

For the current system, use the wrapper scripts in the root directory:
```bash
./start.sh --help
./stop.sh --help
```

These automatically use the Python implementations with full cross-platform compatibility.