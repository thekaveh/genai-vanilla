"""Tests for _make_track_skip — the per-service skip_if_prev predicate
generator wired into bootstrapper/ui/textual/integration.py.

The predicate reads the picker selection (under
``PICKER_STEP_TITLE``) and returns True (skip) when the service is
neither in the chosen track's services nor in the always-on tier nor
in the explicit-override set.
"""

from __future__ import annotations

import pytest

from tracks import load_tracks, normalize_service_key
from ui.textual.integration import _make_track_skip, PICKER_STEP_TITLE


def test_make_track_skip_returns_callable():
    reg = load_tracks()
    skip = _make_track_skip(
        "comfyui",
        always_on=reg.always_on,
        overridden=frozenset(),
    )
    assert callable(skip)


def test_predicate_skips_off_track_service():
    """comfyui is NOT in gen-ai-rag's services list → skip = True."""
    reg = load_tracks()
    skip = _make_track_skip(
        "comfyui",
        always_on=reg.always_on,
        overridden=frozenset(),
    )
    assert skip({PICKER_STEP_TITLE: "gen-ai-rag"}) is True


def test_predicate_does_not_skip_in_track_service():
    """weaviate IS in gen-ai-rag → skip = False."""
    reg = load_tracks()
    skip = _make_track_skip(
        "weaviate",
        always_on=reg.always_on,
        overridden=frozenset(),
    )
    assert skip({PICKER_STEP_TITLE: "gen-ai-rag"}) is False


def test_predicate_does_not_skip_always_on_service():
    """LLM Engine is always-on → skip = False for every track."""
    reg = load_tracks()
    skip = _make_track_skip(
        "llm-provider",
        always_on=reg.always_on,
        overridden=frozenset(),
    )
    for t in reg.tracks:
        assert skip({PICKER_STEP_TITLE: t.key}) is False, \
            f"llm-provider must NEVER be skipped (track={t.key})"


def test_predicate_does_not_skip_overridden_service():
    """An off-track service that was explicitly overridden via
    --comfyui-source must still appear in the wizard."""
    reg = load_tracks()
    skip = _make_track_skip(
        "comfyui",
        always_on=reg.always_on,
        overridden=frozenset({"comfyui"}),
    )
    assert skip({PICKER_STEP_TITLE: "gen-ai-rag"}) is False


def test_predicate_handles_all_sentinel():
    """The 'all' track has services=None → no service ever skipped."""
    reg = load_tracks()
    for svc_key in ("comfyui", "spark", "ray-head", "weaviate"):
        skip = _make_track_skip(
            svc_key, always_on=reg.always_on, overridden=frozenset(),
        )
        assert skip({PICKER_STEP_TITLE: "all"}) is False


def test_predicate_normalizes_family_aliases():
    """ml-eng lists 'ray' in tracks.yml; the wizard hands the predicate
    'ray-head'. The predicate must normalize before lookup."""
    reg = load_tracks()
    skip = _make_track_skip(
        "ray-head",
        always_on=reg.always_on,
        overridden=frozenset(),
    )
    assert skip({PICKER_STEP_TITLE: "ml-eng"}) is False


def test_predicate_normalizes_runtime_sc_divergence():
    """Single-container svc.keys that diverge from folder names normalize
    too (open-web-ui→open-webui, neo4j-graph-db→neo4j)."""
    reg = load_tracks()
    # open-web-ui is in gen-ai-rag (which lists 'open-webui' in YAML).
    skip_owui = _make_track_skip(
        "open-web-ui",
        always_on=reg.always_on,
        overridden=frozenset(),
    )
    assert skip_owui({PICKER_STEP_TITLE: "gen-ai-rag"}) is False
    # neo4j-graph-db is in data-eng (which lists 'neo4j' in YAML).
    skip_neo = _make_track_skip(
        "neo4j-graph-db",
        always_on=reg.always_on,
        overridden=frozenset(),
    )
    assert skip_neo({PICKER_STEP_TITLE: "data-eng"}) is False


def test_predicate_missing_selection_does_not_skip():
    """Before the user has visited the picker, the predicate must
    return False (don't pre-emptively skip)."""
    reg = load_tracks()
    skip = _make_track_skip(
        "comfyui",
        always_on=reg.always_on,
        overridden=frozenset(),
    )
    assert skip({}) is False


def test_predicate_unknown_track_does_not_skip():
    """If somehow the picker selection is garbage, fail open (don't
    skip) — a buggy predicate must not eat user prompts."""
    reg = load_tracks()
    skip = _make_track_skip(
        "comfyui",
        always_on=reg.always_on,
        overridden=frozenset(),
    )
    assert skip({PICKER_STEP_TITLE: "bogus-track"}) is False


# ─── Matrix: every track × every wizard svc.key the spec lists ─────
#
# IMPORTANT — the values below are wizard svc.keys (what
# ServiceDiscovery surfaces in services_info.key), NOT folder names.
# Some diverge:
#   - 'open-web-ui' is the runtime_sc key for the services/open-webui family.
#   - 'neo4j-graph-db' is the runtime_sc key for the services/neo4j family.
# Family heads like 'ray-head', 'spark-master', 'airflow-webserver' are
# also wizard svc.keys, not folder names.

EXPECTED_IN_TRACK: dict[str, set[str]] = {
    "gen-ai-rag": {
        "open-web-ui", "weaviate", "neo4j-graph-db", "lightrag",
        "doc-processor", "tei-reranker", "searxng", "local-deep-researcher",
        # always-on:
        "llm-provider", "prometheus", "grafana",
    },
    "gen-ai-eng": {
        "open-web-ui", "n8n", "hermes", "openclaw", "jupyterhub", "comfyui",
        "stt-provider", "tts-provider", "searxng", "local-deep-researcher",
        "llm-provider", "prometheus", "grafana",
    },
    "gen-ai-creative": {
        "open-web-ui", "comfyui", "stt-provider", "tts-provider",
        "multi2vec-clip", "doc-processor",
        "llm-provider", "prometheus", "grafana",
    },
    "ml-eng": {
        "spark-master", "ray-head", "jupyterhub", "zeppelin",
        "open-web-ui", "minio", "tei-reranker",
        "llm-provider", "prometheus", "grafana",
    },
    "data-eng": {
        "spark-master", "airflow-webserver", "jupyterhub", "zeppelin",
        "minio", "weaviate", "neo4j-graph-db",
        "llm-provider", "prometheus", "grafana",
    },
}

ALL_DISCOVERED: set[str] = set().union(*EXPECTED_IN_TRACK.values())


@pytest.mark.parametrize("track_key", list(EXPECTED_IN_TRACK.keys()))
def test_track_membership_matrix(track_key: str):
    """For every (track, service) pair: predicate matches the spec table."""
    reg = load_tracks()
    expected = EXPECTED_IN_TRACK[track_key]
    for svc in ALL_DISCOVERED:
        skip = _make_track_skip(
            svc, always_on=reg.always_on, overridden=frozenset(),
        )
        is_skipped = skip({PICKER_STEP_TITLE: track_key})
        is_in_expected = svc in expected
        assert is_skipped != is_in_expected, (
            f"track={track_key} svc={svc}: "
            f"expected in_track={is_in_expected} but predicate "
            f"says skip={is_skipped}"
        )
