"""Tests for bootstrapper.docs.deps_section_writer."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "bootstrapper"))

SERVICES_DIR = REPO_ROOT / "services"
FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_section_for_hermes_matches_golden():
    """The deps section for Hermes is byte-stable against a committed fixture."""
    from docs.deps_section_writer import render_section
    from docs.deps_resolver import build_doc_graph

    g = build_doc_graph("hermes", SERVICES_DIR)
    rendered = render_section(g)

    golden = (FIXTURE_DIR / "hermes.deps_section.md").read_text()
    assert rendered == golden, (
        "Hermes deps section drift. To accept the new output:\n"
        f"  bootstrapper/tests/fixtures/hermes.deps_section.md\n"
        "Diff against current rendered text and update if intentional."
    )


def test_section_contains_canonical_headings():
    from docs.deps_section_writer import render_section
    from docs.deps_resolver import build_doc_graph

    g = build_doc_graph("hermes", SERVICES_DIR)
    text = render_section(g)
    for heading in (
        "## Dependencies & Integrations",
        "### Current — Upstream",
        "### Current — Downstream",
        "### Architecture diagram",
        "### Future — Missing pair integrations",
        "### Future — Candidate new services",
        "### Future — Unused features in this service",
    ):
        assert heading in text, f"missing heading: {heading}"


def test_section_emits_empty_table_placeholder():
    """A graph with no upstream emits an explicit `_No upstream dependencies._` line."""
    from docs.deps_section_writer import render_section
    from docs.deps_resolver import DepGraph

    g = DepGraph(focus="kong", category="infra", port_var=None, source="single")
    text = render_section(g)
    assert "_No upstream dependencies._" in text
    assert "_No downstream consumers._" in text


def test_section_emits_no_high_confidence_placeholder_in_future():
    """Future subsections render `_No high-confidence opportunities identified._`
    until Phase C populates them."""
    from docs.deps_section_writer import render_section
    from docs.deps_resolver import DepGraph

    g = DepGraph(focus="kong", category="infra", port_var=None, source="single")
    text = render_section(g)
    assert text.count("_No high-confidence opportunities identified._") >= 3
