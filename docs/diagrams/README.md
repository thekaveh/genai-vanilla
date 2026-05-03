# Architecture Diagrams

The current canonical architecture diagram is the richer static generated artifact:

- Browser view: `architecture.html`
- Static README/GitHub preview: `architecture.svg`

The old Mermaid-based architecture workflow has been removed. Do not regenerate the architecture diagram from Mermaid files.

For now, diagram updates are manual/skill-based: regenerate or edit the rich static diagram artifact directly using the architecture-diagram skill/workflow, then update the SVG preview to match. A future automation path may call Claude Code in headless mode with a diagram-generation skill, but that workflow is intentionally deferred.

Historical notes and old audit examples may still mention Mermaid; those are not current maintainer instructions.
