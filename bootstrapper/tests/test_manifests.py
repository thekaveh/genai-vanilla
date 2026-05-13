"""Tests for bootstrapper.services.manifests (loader)."""

from __future__ import annotations

import pytest

from services.manifests import (
    Manifest,
    ManifestLoadError,
    load_manifests,
)


# ────────────────────────────────────────────────────────────────────────────
# Happy paths
# ────────────────────────────────────────────────────────────────────────────


def test_load_minimal_manifest(services_root, write_manifest, minimal_manifest_dict):
    write_manifest("redis", minimal_manifest_dict("redis"))
    manifests = load_manifests(services_root)
    assert len(manifests) == 1
    m = manifests[0]
    assert isinstance(m, Manifest)
    assert m.name == "redis"
    assert m.label == "Redis service"
    assert m.category == "data"
    assert m.containers == ["redis"]
    assert m.sources is None  # optional, omitted
    assert m.images == []     # optional → empty list
    assert m.depends_on.required == []
    assert m.depends_on.optional == []
    assert m.exports == []
    assert m.hook is None
    assert len(m.env) == 1
    assert m.env[0].name == "REDIS_PORT"
    assert m.env[0].default == 6379
    assert m.env[0].auto_managed is False


def test_load_full_manifest(services_root, write_manifest, full_manifest_dict):
    write_manifest("ollama", full_manifest_dict("ollama"))
    manifests = load_manifests(services_root)
    assert len(manifests) == 1
    m = manifests[0]
    assert m.name == "ollama"
    assert m.docs == "docs/services/ollama.md"
    assert len(m.images) == 2
    assert m.images[0].var == "LLM_PROVIDER_IMAGE"
    assert m.sources is not None
    assert m.sources.var == "LLM_PROVIDER_SOURCE"
    assert m.sources.default == "ollama-container-cpu"
    assert len(m.sources.options) == 2
    assert m.sources.options[0].id == "ollama-container-cpu"
    assert m.sources.options[1].requires == ["LLM_PROVIDER_EXTERNAL_URL"]
    assert m.sources.options[0].effects == {
        "OLLAMA_SCALE": 1,
        "OLLAMA_ENDPOINT": "http://ollama:11434",
    }
    assert m.depends_on.optional == []
    assert m.exports[0].name == "OLLAMA_ENDPOINT"
    assert m.exports[0].consumers == ["litellm", "weaviate"]


def test_load_multiple_manifests_in_deterministic_order(
    services_root, write_manifest, minimal_manifest_dict
):
    # Written out of order; load order should be alphabetical by folder name.
    write_manifest("ollama", minimal_manifest_dict("ollama") | {"category": "llm"})
    write_manifest("redis", minimal_manifest_dict("redis"))
    write_manifest("backend", minimal_manifest_dict("backend") | {"category": "app"})
    manifests = load_manifests(services_root)
    assert [m.name for m in manifests] == ["backend", "ollama", "redis"]


def test_empty_services_dir_returns_empty_list(services_root):
    assert load_manifests(services_root) == []


def test_missing_services_dir_returns_empty_list(tmp_path):
    # Phase A: the services/ folder may not exist yet.
    assert load_manifests(tmp_path / "does-not-exist") == []


def test_underscore_prefixed_folders_are_ignored(
    services_root, write_manifest, minimal_manifest_dict
):
    # services/_order.yml lives at services/ root (a file, not a folder),
    # but downstream consumers can reserve services/_user/ as an overlay slot.
    # The loader should skip folders starting with `_` or `.`.
    write_manifest("redis", minimal_manifest_dict("redis"))
    (services_root / "_user").mkdir()
    (services_root / "_user" / "service.yml").write_text("name: should-be-ignored\n")
    (services_root / ".hidden").mkdir()
    manifests = load_manifests(services_root)
    assert [m.name for m in manifests] == ["redis"]


# ────────────────────────────────────────────────────────────────────────────
# Schema violations
# ────────────────────────────────────────────────────────────────────────────


def test_missing_required_field_rejected(services_root, write_manifest):
    write_manifest("redis", {"name": "redis", "label": "x", "category": "data"})
    # missing containers + env
    with pytest.raises(ManifestLoadError) as exc:
        load_manifests(services_root)
    msg = str(exc.value)
    assert "redis" in msg
    assert "containers" in msg or "required" in msg.lower()


def test_invalid_category_rejected(services_root, write_manifest, minimal_manifest_dict):
    bad = minimal_manifest_dict("redis")
    bad["category"] = "nonsense"
    write_manifest("redis", bad)
    with pytest.raises(ManifestLoadError):
        load_manifests(services_root)


def test_lowercase_env_var_name_rejected(services_root, write_manifest, minimal_manifest_dict):
    bad = minimal_manifest_dict("redis")
    bad["env"] = [{"name": "lower_case", "default": ""}]
    write_manifest("redis", bad)
    with pytest.raises(ManifestLoadError):
        load_manifests(services_root)


def test_unknown_field_rejected(services_root, write_manifest, minimal_manifest_dict):
    bad = minimal_manifest_dict("redis")
    bad["typo_field"] = "oops"
    write_manifest("redis", bad)
    with pytest.raises(ManifestLoadError):
        load_manifests(services_root)


def test_folder_name_must_match_manifest_name(
    services_root, write_manifest, minimal_manifest_dict
):
    # services/foo/service.yml declares name: bar → rejected.
    bad = minimal_manifest_dict("bar")
    write_manifest("bar", bad, folder_name="foo")
    with pytest.raises(ManifestLoadError) as exc:
        load_manifests(services_root)
    assert "folder" in str(exc.value).lower() or "name" in str(exc.value).lower()


def test_service_dir_missing_manifest_rejected(services_root):
    (services_root / "redis").mkdir()
    # no service.yml inside
    with pytest.raises(ManifestLoadError) as exc:
        load_manifests(services_root)
    assert "service.yml" in str(exc.value)


def test_malformed_yaml_rejected(services_root):
    (services_root / "redis").mkdir()
    (services_root / "redis" / "service.yml").write_text("this is: : not valid: yaml\n  -bad")
    with pytest.raises(ManifestLoadError):
        load_manifests(services_root)


def test_source_default_must_be_one_of_options(
    services_root, write_manifest, full_manifest_dict
):
    bad = full_manifest_dict("ollama")
    bad["sources"]["default"] = "no-such-source"
    write_manifest("ollama", bad)
    with pytest.raises(ManifestLoadError) as exc:
        load_manifests(services_root)
    assert "default" in str(exc.value).lower()


def test_image_container_must_appear_in_containers(
    services_root, write_manifest, full_manifest_dict
):
    bad = full_manifest_dict("ollama")
    bad["images"][0]["container"] = "not-in-containers"
    write_manifest("ollama", bad)
    with pytest.raises(ManifestLoadError) as exc:
        load_manifests(services_root)
    assert "container" in str(exc.value).lower()
