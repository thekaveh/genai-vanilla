#!/bin/bash
# Generate the architecture diagram and update the README

# Change to the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Install required packages
pip install -r requirements.txt

# Generate the architecture diagram
python architecture.py

# Update the README with the generated diagram
python update_readme.py

echo "Architecture diagram generated and README updated."