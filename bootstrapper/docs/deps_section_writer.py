"""DepGraph → markdown deps section (simplified for data-flow model)."""

from __future__ import annotations

from .deps_resolver import DepEdge, DepGraph


def render_section(graph: DepGraph) -> str:
    """Render the canonical 'Dependencies & Integrations' section.

    Output is byte-deterministic for the same DepGraph. The Future-*
    subsections emit placeholders until Phase C populates them.
    """

    lines: list[str] = []
    lines.append("## Dependencies & Integrations")
    lines.append("")
    lines.append(
        "> Auto-generated section — the **Current** subsections are derived from "
        f"`services/{graph.focus}/service.yml`'s `data_flow.calls` field "
        f"(and inverse passes). Re-run "
        f"`python -m bootstrapper.docs.regen {graph.focus}` after manifest changes."
    )
    lines.append("")

    # Current — Upstream
    lines.append("### Current — Upstream (this service calls)")
    lines.append("")
    if graph.upstream:
        lines.append("| Service | Category |")
        lines.append("|---|---|")
        for e in graph.upstream:
            bidi = " ↔" if e.bidirectional else ""
            lines.append(f"| {e.other}{bidi} | {e.other_category} |")
    else:
        lines.append("_No upstream calls._")
    lines.append("")

    # Current — Downstream
    lines.append("### Current — Downstream (services that call this)")
    lines.append("")
    if graph.downstream:
        lines.append("| Service | Category |")
        lines.append("|---|---|")
        for e in graph.downstream:
            bidi = " ↔" if e.bidirectional else ""
            lines.append(f"| {e.other}{bidi} | {e.other_category} |")
    else:
        lines.append("_No downstream consumers._")
    lines.append("")

    # Diagram embed
    lines.append("### Architecture diagram")
    lines.append("")
    lines.append(f"![{graph.focus} architecture](./architecture.svg)")
    lines.append("")
    lines.append("[Open the interactive HTML diagram](./architecture.html) for a full-screen view.")
    lines.append("")

    # Future-* placeholders
    for heading in (
        "### Future — Missing pair integrations",
        "### Future — Candidate new services",
        "### Future — Unused features in this service",
    ):
        lines.append(heading)
        lines.append("")
        lines.append("_No high-confidence opportunities identified._")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
