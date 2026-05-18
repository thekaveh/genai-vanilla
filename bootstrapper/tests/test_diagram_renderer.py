"""Tests for bootstrapper.docs.diagram_renderer."""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "bootstrapper"))

SERVICES_DIR = REPO_ROOT / "services"
FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_renders_svg_with_focus_label():
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg
    g = build_doc_graph("hermes", SERVICES_DIR)
    svg = render_svg(g)
    assert svg.startswith("<svg")
    assert "hermes" in svg.lower()


def test_renders_html_includes_jetbrains_mono():
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_html
    g = build_doc_graph("hermes", SERVICES_DIR)
    html = render_html(g)
    assert "JetBrains+Mono" in html
    assert "<svg" in html


def test_svg_has_no_volatile_content():
    """The SVG body must NOT contain a generation timestamp (HTML footer only)."""
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg
    g = build_doc_graph("hermes", SERVICES_DIR)
    svg = render_svg(g)
    assert not re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", svg)
    assert "generated:" not in svg.lower()


def test_svg_byte_deterministic():
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg
    g = build_doc_graph("hermes", SERVICES_DIR)
    a = render_svg(g)
    b = render_svg(g)
    assert a == b


def test_svg_matches_golden_snapshot():
    """Hermes is the snapshot — most complex graph. Fixture lives at
    bootstrapper/tests/fixtures/hermes.architecture.svg."""
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg

    g = build_doc_graph("hermes", SERVICES_DIR)
    rendered = render_svg(g)
    golden = (FIXTURE_DIR / "hermes.architecture.svg").read_text()
    assert rendered == golden, (
        "Hermes SVG drift. To accept the new output:\n"
        "  PYTHONPATH=bootstrapper python -c \"from docs.deps_resolver "
        "import build_doc_graph; from docs.diagram_renderer import render_svg; "
        "from pathlib import Path; "
        "Path('bootstrapper/tests/fixtures/hermes.architecture.svg').write_text("
        "render_svg(build_doc_graph('hermes', Path('services'))))\"\n"
    )


def test_empty_lanes_drawn_explicitly():
    """A focus with empty upstream/downstream gets explicit 'no deps' placeholders."""
    from docs.deps_resolver import DepGraph
    from docs.diagram_renderer import render_svg

    g = DepGraph(focus="kong", category="infra", port_var=None, source="single")
    svg = render_svg(g)
    assert "no upstream" in svg.lower() or "no upstream deps" in svg.lower()
    assert "no downstream" in svg.lower() or "no downstream consumers" in svg.lower()


def test_aggregate_focus_renders_parent_box():
    """Aggregate doc folders (stt-provider, tts-provider) render a parent
    boundary rectangle wrapping inner member boxes."""
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg

    g = build_doc_graph("stt-provider", SERVICES_DIR)
    svg = render_svg(g)
    assert "#fb7185" in svg
    assert "stroke-dasharray=\"4,4\"" in svg


def test_non_aggregate_has_no_rose_boundary():
    """Singleton focus (e.g. hermes) does NOT emit the rose aggregate boundary."""
    from docs.deps_resolver import build_doc_graph
    from docs.diagram_renderer import render_svg

    g = build_doc_graph("hermes", SERVICES_DIR)
    svg = render_svg(g)
    assert "#fb7185" not in svg
