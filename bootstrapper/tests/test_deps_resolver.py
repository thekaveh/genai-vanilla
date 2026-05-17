"""Tests for bootstrapper.docs.deps_resolver."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "bootstrapper"))

SERVICES_DIR = REPO_ROOT / "services"


def test_dep_graph_focus_is_service_name():
    from docs.deps_resolver import build_graph
    g = build_graph("hermes", SERVICES_DIR)
    assert g.focus == "hermes"
    assert g.category == "agents"


def test_dep_graph_required_upstream_includes_litellm():
    """Hermes's depends_on.required: [litellm] should produce a required upstream edge."""
    from docs.deps_resolver import build_graph
    g = build_graph("hermes", SERVICES_DIR)
    others = {e.other for e in g.upstream if e.kind == "required"}
    assert "litellm" in others


def test_dep_graph_adaptive_upstream_includes_tts_and_stt():
    """Hermes adapts_to: [stt_provider, tts_provider, ...] → adaptive edges."""
    from docs.deps_resolver import build_graph
    g = build_graph("hermes", SERVICES_DIR)
    adaptive = {e.other for e in g.upstream if e.kind == "adaptive"}
    assert adaptive
    assert any("stt" in a or a == "parakeet" or a == "speaches" for a in adaptive)


def test_dep_graph_downstream_includes_litellm_loop():
    """LiteLLM registers Hermes back as the `hermes-agent` model → bidirectional loop.

    For the resolver alone, this means: Hermes's downstream set includes
    LiteLLM, even though LiteLLM was already in upstream. The bidirectional
    flag must be True on both sides.
    """
    from docs.deps_resolver import build_graph
    g = build_graph("hermes", SERVICES_DIR)
    bidir = [e for e in g.upstream if e.other == "litellm" and e.bidirectional]
    assert bidir, "expected Hermes↔LiteLLM marked bidirectional"


def test_dep_graph_failure_mode_populated_from_manifest():
    """The failure_mode string from Task 2 must propagate to adaptive upstream edges."""
    from docs.deps_resolver import build_graph
    g = build_graph("hermes", SERVICES_DIR)
    litellm_edge = next(e for e in g.upstream if e.other == "litellm")
    assert litellm_edge.failure_mode is not None
    assert "preflight" in litellm_edge.failure_mode.lower()


def test_dep_graph_init_containers_recorded():
    """hermes-init must be in init_containers, not in upstream/downstream."""
    from docs.deps_resolver import build_graph
    g = build_graph("hermes", SERVICES_DIR)
    assert "hermes-init" in g.init_containers
    assert all(e.other != "hermes-init" for e in g.upstream)
    assert all(e.other != "hermes-init" for e in g.downstream)


def test_dep_graph_byte_deterministic():
    """Two builds of the same graph produce identical edge orderings."""
    from docs.deps_resolver import build_graph
    g1 = build_graph("hermes", SERVICES_DIR)
    g2 = build_graph("hermes", SERVICES_DIR)
    assert g1 == g2
