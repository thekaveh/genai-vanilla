#!/usr/bin/env python3
"""
Update README.md with the latest architecture diagram.
"""

import os
import re
import sys

# Get the script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
README_PATH = os.path.join(SCRIPT_DIR, "..", "..", "README.md")

def update_readme_with_diagram(diagram_path):
    """Update the README.md file with the architecture diagram."""
    with open(README_PATH, 'r') as file:
        content = file.read()
    
    # Define the regex pattern for the architecture diagram section
    diagram_pattern = r'## Architecture Diagram\s+!\[Architecture Diagram\]\([^)]+\)'
    diagram_replacement = f"## Architecture Diagram\n\n![Architecture Diagram](./{diagram_path})"
    
    # Check if the architecture diagram section exists
    if re.search(diagram_pattern, content):
        # Replace the existing diagram
        updated_content = re.sub(diagram_pattern, diagram_replacement, content)
    else:
        # Insert the diagram after the first heading (# Vanilla GenAI Stack)
        title_pattern = r'# Vanilla GenAI Stack\s+'
        updated_content = re.sub(title_pattern, f'# Vanilla GenAI Stack\n\n{diagram_replacement}\n\n', content)
    
    # Write the updated content back to the README
    with open(README_PATH, 'w') as file:
        file.write(updated_content)
    
    print(f"README.md updated with architecture diagram at {diagram_path}")

if __name__ == "__main__":
    # Get the diagram path from the command line or use default
    diagram_path = sys.argv[1] if len(sys.argv) > 1 else "docs/images/architecture.png"
    update_readme_with_diagram(diagram_path)