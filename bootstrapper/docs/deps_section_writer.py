"""DepGraph → markdown deps section (simplified for data-flow model)."""

from __future__ import annotations

from .deps_resolver import DepGraph, doc_folder_to_manifests


def render_section(graph: DepGraph, position: int = 5) -> str:
    """Render the canonical 'Dependencies & Integrations' section.

    Output is byte-deterministic for the same DepGraph and ``position``. The
    Future-* subsections emit placeholders; the regen tool splices in any
    user-authored Future content found in the existing README.

    The ``position`` parameter is the top-level section number (e.g. 5 in
    ``## 5. Dependencies & Integrations``). Subsections are numbered
    ``position.1`` through ``position.6``. Defaults to 5, the canonical slot
    in the standardized README layout.
    """

    lines: list[str] = []
    lines.append(f"## {position}. Dependencies & Integrations")
    lines.append("")
    if getattr(graph, "source", "") == "(aggregate)":
        # Aggregate doc-only folders (stt-provider, doc-processor):
        # their edges live in the MEMBER manifests, not a service.yml of
        # their own (tts-provider is the exception — it has a virtual
        # manifest — but the member citation is correct there too).
        members = ", ".join(
            f"`services/{m}/service.yml`"
            for m in doc_folder_to_manifests(graph.focus)
        ) or "the owning manifests"
        lines.append(
            "> Auto-generated section — the **Current** subsections are "
            f"derived from the member manifests' `data_flow.calls` "
            f"({members}). Re-run "
            f"`python -m bootstrapper.docs.regen {graph.focus}` after "
            "changing them."
        )
    elif getattr(graph, "source", "").startswith("(pointer doc"):
        # Doc-only folders (no service.yml of their own — e.g.
        # multi2vec-clip): citing `services/<focus>/service.yml` would
        # point at a file the same README says doesn't exist.
        lines.append(
            "> Auto-generated section — this is a doc-only folder (no "
            f"`services/{graph.focus}/service.yml`); its data-flow edges "
            "live in the owning family's manifest (see §4). Re-run "
            f"`python -m bootstrapper.docs.regen {graph.focus}` after "
            "changing them there."
        )
    else:
        lines.append(
            "> Auto-generated section — the **Current** subsections are derived from "
            f"`services/{graph.focus}/service.yml`'s `data_flow.calls` field "
            f"(and inverse passes). Re-run "
            f"`python -m bootstrapper.docs.regen {graph.focus}` after manifest changes."
        )
    lines.append("")

    # Current — Upstream
    lines.append(f"### {position}.1 Current — Upstream (this service calls)")
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
    lines.append(f"### {position}.2 Current — Downstream (services that call this)")
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
    lines.append(f"### {position}.3 Architecture diagram")
    lines.append("")
    lines.append(f"![{graph.focus} architecture](./architecture.svg)")
    lines.append("")
    lines.append("[Open the interactive HTML diagram](./architecture.html) for a full-screen view.")
    lines.append("")

    # Future-* placeholders
    for heading in (
        f"### {position}.4 Future — Missing pair integrations",
        f"### {position}.5 Future — Candidate new services",
        f"### {position}.6 Future — Unused features in this service",
    ):
        lines.append(heading)
        lines.append("")
        lines.append("_No high-confidence opportunities identified._")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
