"""DepGraph → markdown deps section."""

from __future__ import annotations

from .deps_resolver import DepEdge, DepGraph


def render_section(graph: DepGraph) -> str:
    """Render the canonical 'Dependencies & Integrations' section for one
    service's README. Output is byte-deterministic for the same DepGraph.

    The Future-* subsections emit a placeholder line until Phase C
    populates them.
    """

    lines: list[str] = []
    lines.append("## Dependencies & Integrations")
    lines.append("")
    lines.append(
        "> Auto-generated section — the **Current** subsections are derived from "
        f"`services/{graph.focus}/service.yml`. Re-run "
        f"`python -m bootstrapper.docs.regen {graph.focus}` after manifest changes."
    )
    lines.append("")

    # Current — Upstream
    lines.append("### Current — Upstream (this service depends on)")
    lines.append("")
    if graph.upstream:
        lines.append("| Service | Type | Mechanism | Failure mode |")
        lines.append("|---|---|---|---|")
        for e in graph.upstream:
            lines.append(_upstream_row(e))
    else:
        lines.append("_No upstream dependencies._")
    lines.append("")

    # Current — Downstream
    lines.append("### Current — Downstream (services that depend on this)")
    lines.append("")
    if graph.downstream:
        lines.append("| Service | Type | Mechanism |")
        lines.append("|---|---|---|")
        for e in graph.downstream:
            lines.append(_downstream_row(e))
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


def _upstream_row(e: DepEdge) -> str:
    return (
        f"| {e.other} | {e.kind} | "
        f"`{_escape_mechanism(e.mechanism)}` | "
        f"{e.failure_mode or '_unspecified_'} |"
    )


def _downstream_row(e: DepEdge) -> str:
    return f"| {e.other} | {e.kind} | {_escape_mechanism(e.mechanism)} |"


def _escape_mechanism(s: str) -> str:
    # Pipe characters break markdown tables. The mechanism field rarely
    # contains pipes, but guard anyway.
    return (s or "").replace("|", r"\|")
