# Architecture Diagram

This directory contains the Mermaid diagram source for the project architecture.

## Generating the Architecture Diagram

The architecture diagram is defined in `architecture.mermaid` and can be generated as a PNG image using the provided script:

1. Make sure you have Node.js and npm installed
2. Run the generation script:
   ```
   cd docs/diagrams
   ./generate_diagram.sh
   ```
3. This will:
   - Install the Mermaid CLI tool if needed
   - Convert the Mermaid diagram to PNG
   - Save it as `docs/images/architecture.png`

The generated image will be automatically referenced in the main README.md file.

## Modifying the Architecture Diagram

To modify the architecture diagram:

1. Edit the `architecture.mermaid` file
2. Run the generation script to update the PNG image
3. The changes will be reflected in the README.md

## Mermaid Diagram Source

The diagram uses Mermaid syntax to define a clean, professional representation of the project architecture with:
- Logical grouping of services by category (Database, AI, API)
- Clear data flow visualization
- Consistent styling

You can also embed the Mermaid code directly in Markdown files for platforms that support Mermaid rendering (like GitHub).
