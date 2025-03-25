#!/bin/bash
# Generate architecture diagram from Mermaid file

# Check if npx is installed
if ! command -v npx &> /dev/null; then
    echo "npx is not installed. Please install Node.js and npm first."
    exit 1
fi

# Install mermaid-cli if not already installed
echo "Installing @mermaid-js/mermaid-cli if not already installed..."
npm list -g @mermaid-js/mermaid-cli || npm install -g @mermaid-js/mermaid-cli

# Path to the mermaid file
MERMAID_FILE="architecture.mermaid"
OUTPUT_FILE="../images/architecture.png"

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
