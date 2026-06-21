"""
Tests for declarative source-option profile metadata (Task 3, Plan B).

Verifies that:
- localhost-flavored source options are dev-only (in "default" but NOT "prod").
- Unannotated options (container, disabled, external, api) are available in all profiles.
- option_in_profile() returns True for unknown service/option ids (permissive fallback).
- The cross-manifest lint detects a service that accidentally marks all options dev-only.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from services.manifests import load_manifests, option_in_profile
from services.manifest_validator import validate_manifests, ValidationIssue

REPO = pathlib.Path(__file__).resolve().parents[2]
SERVICES = REPO / "services"


# ─────────────────────────────────────────────────────────────────────────────
# Fixture
# ─────────────────────────────────────────────────────────────────────────────

def _manifests():
    return load_manifests(SERVICES)


# ─────────────────────────────────────────────────────────────────────────────
# Localhost options must be dev-only (profiles: [default])
# ─────────────────────────────────────────────────────────────────────────────

def test_localhost_options_are_dev_only():
    m = _manifests()
    # comfyui localhost
    assert option_in_profile(m, "comfyui", "localhost", "default") is True
    assert option_in_profile(m, "comfyui", "localhost", "prod") is False
    # ollama localhost
    assert option_in_profile(m, "ollama", "ollama-localhost", "default") is True
    assert option_in_profile(m, "ollama", "ollama-localhost", "prod") is False
    # parakeet localhost variants
    assert option_in_profile(m, "parakeet", "parakeet-localhost", "prod") is False
    assert option_in_profile(m, "parakeet", "whisper-cpp-localhost", "prod") is False
    # tts-provider chatterbox localhost
    assert option_in_profile(m, "tts-provider", "chatterbox-localhost", "prod") is False
    # docling localhost
    assert option_in_profile(m, "docling", "docling-localhost", "prod") is False
    # remaining services
    assert option_in_profile(m, "hermes", "localhost", "prod") is False
    assert option_in_profile(m, "lightrag", "localhost", "prod") is False
    assert option_in_profile(m, "neo4j", "localhost", "prod") is False
    assert option_in_profile(m, "openclaw", "localhost", "prod") is False
    assert option_in_profile(m, "tei-reranker", "localhost", "prod") is False
    assert option_in_profile(m, "weaviate", "localhost", "prod") is False


# ─────────────────────────────────────────────────────────────────────────────
# Unannotated options are available in all profiles
# ─────────────────────────────────────────────────────────────────────────────

def test_unannotated_option_in_all_profiles():
    m = _manifests()
    # container-cpu and disabled are unannotated on comfyui
    assert option_in_profile(m, "comfyui", "container-cpu", "prod") is True
    assert option_in_profile(m, "comfyui", "container-cpu", "default") is True
    assert option_in_profile(m, "comfyui", "disabled", "prod") is True
    # ollama container options
    assert option_in_profile(m, "ollama", "ollama-container-cpu", "prod") is True
    assert option_in_profile(m, "ollama", "ollama-container-gpu", "prod") is True
    # weaviate container
    assert option_in_profile(m, "weaviate", "container", "prod") is True


# ─────────────────────────────────────────────────────────────────────────────
# Permissive fallback for unknown service/option
# ─────────────────────────────────────────────────────────────────────────────

def test_unknown_service_returns_true():
    m = _manifests()
    assert option_in_profile(m, "nonexistent-service", "container", "prod") is True


def test_unknown_option_id_returns_true():
    m = _manifests()
    assert option_in_profile(m, "comfyui", "nonexistent-option", "prod") is True


# ─────────────────────────────────────────────────────────────────────────────
# Cross-manifest lint: no_prod_option
# ─────────────────────────────────────────────────────────────────────────────

def test_real_manifests_have_no_prod_option_violations():
    """None of the real service manifests should trigger the no_prod_option lint."""
    m = _manifests()
    issues = validate_manifests(m)
    prod_violations = [i for i in issues if i.kind == "no_prod_option"]
    assert prod_violations == [], (
        f"Unexpected no_prod_option violations: {prod_violations}"
    )


def test_lint_detects_all_dev_only_service():
    """Synthetic manifest with all options dev-only triggers no_prod_option."""
    from services.manifests import (
        Manifest, EnvVarDecl, SourcesBlock, SourceOption
    )
    from services.manifest_validator import validate_manifests as vm

    bad = Manifest(
        name="bad-svc",
        label="Bad Service",
        category="apps",
        env=[EnvVarDecl(name="BAD_SVC_SOURCE", default="container")],
        sources=SourcesBlock(
            var="BAD_SVC_SOURCE",
            default="container",
            options=[
                SourceOption(id="container", label="Container", profiles=["default"]),
                SourceOption(id="disabled", label="Disabled", profiles=["default"]),
            ],
        ),
    )
    issues = vm([bad])
    assert any(i.kind == "no_prod_option" and i.manifest == "bad-svc" for i in issues), (
        f"Expected no_prod_option for bad-svc, got: {issues}"
    )


def test_lint_passes_for_single_option_service():
    """A service with only one source option is exempt from the prod lint."""
    from services.manifests import (
        Manifest, EnvVarDecl, SourcesBlock, SourceOption
    )
    from services.manifest_validator import validate_manifests as vm

    single = Manifest(
        name="single-svc",
        label="Single Option Service",
        category="apps",
        env=[EnvVarDecl(name="SINGLE_SVC_SOURCE", default="localhost")],
        sources=SourcesBlock(
            var="SINGLE_SVC_SOURCE",
            default="localhost",
            options=[
                SourceOption(id="localhost", label="Localhost only", profiles=["default"]),
            ],
        ),
    )
    issues = vm([single])
    prod_violations = [i for i in issues if i.kind == "no_prod_option"]
    assert prod_violations == [], (
        f"Single-option service should be exempt, got: {prod_violations}"
    )
