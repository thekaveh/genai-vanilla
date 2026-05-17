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


def test_doc_folder_to_manifests_mapping():
    """Aggregate doc folders are recognized and map to underlying manifests."""
    from docs.deps_resolver import doc_folder_to_manifests
    assert doc_folder_to_manifests("hermes") == ("hermes",)
    # Aggregates fold:
    assert set(doc_folder_to_manifests("stt-provider")) >= {"parakeet", "speaches"}
    assert set(doc_folder_to_manifests("tts-provider")) >= {"chatterbox", "speaches"}
    assert set(doc_folder_to_manifests("doc-processor")) >= {"docling"}
    # multi2vec-clip has no manifest — empty tuple
    assert doc_folder_to_manifests("multi2vec-clip") == ()


def test_build_doc_graph_aggregates_edges():
    """build_doc_graph('stt-provider') unions parakeet + speaches edges and
    suppresses intra-aggregate edges."""
    from docs.deps_resolver import build_doc_graph
    g = build_doc_graph("stt-provider", SERVICES_DIR)
    assert g.focus == "stt-provider"
    # Hermes adapts_to stt_provider, so stt-provider has Hermes downstream
    assert any(e.other == "hermes" for e in g.downstream)
    # Internal edge: parakeet ↔ speaches must NOT appear (intra-aggregate
    # suppression)
    edge_others = {e.other for e in g.upstream} | {e.other for e in g.downstream}
    assert "parakeet" not in edge_others
    assert "speaches" not in edge_others


def test_build_doc_graph_singleton_passes_through():
    """Singleton doc folders (1:1 with manifest) behave like build_graph()."""
    from docs.deps_resolver import build_doc_graph, build_graph
    g1 = build_doc_graph("hermes", SERVICES_DIR)
    g2 = build_graph("hermes", SERVICES_DIR)
    assert g1.upstream == g2.upstream
    assert g1.downstream == g2.downstream


def test_build_doc_graph_multi2vec_clip_is_pointer_only():
    """multi2vec-clip has no manifest — build_doc_graph returns a sentinel
    DepGraph that signals 'no diagram, see weaviate'."""
    from docs.deps_resolver import build_doc_graph, DepGraph
    g = build_doc_graph("multi2vec-clip", SERVICES_DIR)
    assert isinstance(g, DepGraph)
    assert g.focus == "multi2vec-clip"
    assert g.upstream == ()
    assert g.downstream == ()
    assert g.init_containers == ()
