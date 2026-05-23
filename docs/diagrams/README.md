# Architecture Diagrams

The canonical architecture diagram is generated from the live topology:

- Source: `architecture.dot` — produced by `bootstrapper/tools/generate_architecture_diagram.py` (reads `services/topology.py`).
- Static preview: `architecture.svg` — rendered from `architecture.dot` via Graphviz `dot -Tsvg`.

## Regenerating

**Prerequisite:** Graphviz must be installed to render the SVG from `.dot`.

- macOS: `brew install graphviz`
- Debian/Ubuntu: `sudo apt-get install graphviz`
- Windows: `choco install graphviz` (or download from https://graphviz.org/download/)

```bash
cd bootstrapper && uv run python -m tools.generate_architecture_diagram   # rewrites architecture.dot
dot -Tsvg docs/diagrams/architecture.dot > docs/diagrams/architecture.svg  # refreshes the SVG preview
```

The `.dot` regen lint is part of `validate_fragments`; the SVG is a downstream rendering artifact and is regenerated manually when a topology change actually moves something visually.

The old Mermaid-based workflow has been removed. Historical audit notes may still mention Mermaid; those are not current maintainer instructions.
