"""Tests for bootstrapper.services.manifest_validator (cross-manifest checks)."""

from __future__ import annotations

import pytest

from services.manifests import load_manifests
from services.manifest_validator import (
    ValidationIssue,
    validate_manifests,
)


# ────────────────────────────────────────────────────────────────────────────
# Happy paths
# ────────────────────────────────────────────────────────────────────────────


def test_clean_pair_of_manifests_returns_no_issues(
    services_root, write_manifest, minimal_manifest_dict
):
    write_manifest("redis", minimal_manifest_dict("redis"))
    write_manifest("backend", minimal_manifest_dict("backend") | {"category": "app"})
    manifests = load_manifests(services_root)
    issues = validate_manifests(manifests)
    assert issues == []


def test_empty_manifest_list_returns_no_issues():
    assert validate_manifests([]) == []


def test_full_manifest_with_sources_is_clean(
    services_root, write_manifest, full_manifest_dict, minimal_manifest_dict
):
    write_manifest("ollama", full_manifest_dict("ollama"))
    # The ollama fixture exports OLLAMA_ENDPOINT to litellm + weaviate; provide stubs
    # so the consumer-closure rule has manifests to resolve against.
    write_manifest("litellm", minimal_manifest_dict("litellm") | {"category": "llm"})
    write_manifest("weaviate", minimal_manifest_dict("weaviate") | {"category": "ai"})
    manifests = load_manifests(services_root)
    assert validate_manifests(manifests) == []


# ────────────────────────────────────────────────────────────────────────────
# Cross-manifest violations
# ────────────────────────────────────────────────────────────────────────────


def test_duplicate_env_var_name_across_manifests_flagged(
    services_root, write_manifest, minimal_manifest_dict
):
    # Both redis and another service declare REDIS_PORT — exactly one owner allowed.
    write_manifest("redis", minimal_manifest_dict("redis"))
    other = minimal_manifest_dict("backend")
    other["category"] = "app"
    other["env"].append({"name": "REDIS_PORT", "default": 9999})
    write_manifest("backend", other)
    manifests = load_manifests(services_root)
    issues = validate_manifests(manifests)
    assert any("REDIS_PORT" in i.message for i in issues)
    assert any(i.kind == "duplicate_env_var" for i in issues)


def test_duplicate_container_across_manifests_flagged(
    services_root, write_manifest, minimal_manifest_dict
):
    write_manifest("redis", minimal_manifest_dict("redis"))
    other = minimal_manifest_dict("backend")
    other["category"] = "app"
    other["containers"] = ["redis"]  # collides with the redis manifest
    write_manifest("backend", other)
    manifests = load_manifests(services_root)
    issues = validate_manifests(manifests)
    assert any(i.kind == "duplicate_container" for i in issues)


def test_depends_on_pointing_to_unknown_manifest_flagged(
    services_root, write_manifest, minimal_manifest_dict
):
    bad = minimal_manifest_dict("backend")
    bad["category"] = "app"
    bad["depends_on"] = {"required": ["does-not-exist"], "optional": []}
    write_manifest("backend", bad)
    manifests = load_manifests(services_root)
    issues = validate_manifests(manifests)
    assert any(i.kind == "unknown_dependency" for i in issues)
    assert any("does-not-exist" in i.message for i in issues)


def test_export_must_be_declared_by_owning_manifest(
    services_root, write_manifest, full_manifest_dict
):
    bad = full_manifest_dict("ollama")
    # Add an export that isn't declared as env or in source effects.
    bad["exports"].append({"name": "UNDECLARED_VAR", "consumers": ["litellm"]})
    write_manifest("ollama", bad)
    manifests = load_manifests(services_root)
    issues = validate_manifests(manifests)
    assert any(i.kind == "undeclared_export" for i in issues)
    assert any("UNDECLARED_VAR" in i.message for i in issues)


# Removed: test_source_effects_target_must_be_declared — the
# `sources.options[].effects` field was dropped in favor of
# `runtime_sc.<key>.<source>.environment` (single source of truth). The
# `undeclared_effect` validator rule is gone with it. The closure check
# (every exported name produced by env[] OR runtime_sc) lives in
# test_export_must_be_declared_by_owning_manifest below.


def test_source_var_must_be_declared_as_env(
    services_root, write_manifest, full_manifest_dict
):
    """The SOURCE env var name itself (e.g. LLM_PROVIDER_SOURCE) must appear in env[]."""
    bad = full_manifest_dict("ollama")
    # Strip the LLM_PROVIDER_SOURCE entry so the source-var rule fires.
    bad["env"] = [e for e in bad["env"] if e["name"] != "LLM_PROVIDER_SOURCE"]
    write_manifest("ollama", bad)
    manifests = load_manifests(services_root)
    issues = validate_manifests(manifests)
    assert any(i.kind == "undeclared_source_var" for i in issues)


def test_export_consumers_must_be_known_manifests(
    services_root, write_manifest, full_manifest_dict, minimal_manifest_dict
):
    bad = full_manifest_dict("ollama")
    bad["exports"] = [{"name": "OLLAMA_ENDPOINT", "consumers": ["nonexistent-service"]}]
    write_manifest("ollama", bad)
    manifests = load_manifests(services_root)
    issues = validate_manifests(manifests)
    assert any(i.kind == "unknown_consumer" for i in issues)


def test_validation_issue_carries_manifest_name():
    """Each ValidationIssue should record which manifest produced the issue."""
    issue = ValidationIssue(kind="x", manifest="y", message="z")
    assert issue.manifest == "y"
    assert issue.kind == "x"
    assert issue.message == "z"
