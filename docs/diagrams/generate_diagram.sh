#!/usr/bin/env bash
# Generate architecture diagram from Mermaid file
# Cross-platform compatible version

# Check if npx is installed
if ! command -v npx &> /dev/null; then
    echo "npx is not installed. Please install Node.js and npm first."
    exit 1
fi

# Install mermaid-cli if not already installed
echo "Installing @mermaid-js/mermaid-cli if not already installed..."
npm list -g @mermaid-js/mermaid-cli || npm install -g @mermaid-js/mermaid-cli

# Get script directory in a cross-platform way
get_script_dir() {
  local SOURCE="${BASH_SOURCE[0]}"
  local DIR=""
  
  # Resolve $SOURCE until the file is no longer a symlink
  while [ -h "$SOURCE" ]; do 
    DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
    SOURCE="$(readlink "$SOURCE")"
    # If $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE"
  done
  
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  echo "$DIR"
}

SCRIPT_DIR="$(get_script_dir)"
MERMAID_FILE="${SCRIPT_DIR}/architecture.mermaid"
OUTPUT_FILE="${SCRIPT_DIR}/../images/architecture.png"

# Ensure output directory exists
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Check if the mermaid file exists
if [ ! -f "$MERMAID_FILE" ]; then
    echo "Mermaid file not found: $MERMAID_FILE"
    exit 1
fi

# Convert mermaid to PNG
echo "Converting $MERMAID_FILE to PNG..."
npx mmdc -i "$MERMAID_FILE" -o "$OUTPUT_FILE" -t neutral -b transparent

# Check if conversion was successful
if [ $? -eq 0 ]; then
    echo "Conversion successful! PNG file created at: $OUTPUT_FILE"
    echo "The architecture diagram has been updated in the README.md"
    echo "Done!"
else
    echo "Conversion failed."
    exit 1
fi

# Add Windows compatibility note
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
  echo ""
  echo "⚠️  Windows detected: If you encounter any issues, please run this script in Git Bash or WSL."
fi
