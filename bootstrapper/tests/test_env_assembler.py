"""Tests for bootstrapper.services.env_assembler."""

from __future__ import annotations

from services.env_assembler import assemble_env_example
from services.manifests import load_manifests


def test_emits_generated_header(services_root, write_manifest, minimal_manifest_dict):
    write_manifest("redis", minimal_manifest_dict("redis"))
    manifests = load_manifests(services_root)
    out = assemble_env_example(manifests)
    assert "GENERATED" in out
    assert "service.yml" in out


def test_empty_manifest_list_still_emits_header():
    out = assemble_env_example([])
    assert "GENERATED" in out
    # Even with no manifests, the file should be a valid env-file (zero declarations).


def test_emits_env_var_with_default_and_description(
    services_root, write_manifest, minimal_manifest_dict
):
    m = minimal_manifest_dict("redis")
    m["env"] = [
        {
            "name": "REDIS_PORT",
            "default": 6379,
            "description": "Host port for Redis.",
        }
    ]
    write_manifest("redis", m)
    manifests = load_manifests(services_root)
    out = assemble_env_example(manifests)
    assert "REDIS_PORT=6379" in out
    assert "Host port for Redis." in out


def test_omits_default_for_auto_managed_vars(
    services_root, write_manifest, minimal_manifest_dict
):
    m = minimal_manifest_dict("ollama")
    m["category"] = "llm"
    m["env"] = [
        {"name": "OLLAMA_SCALE", "auto_managed": True, "description": "Computed."},
        {"name": "OLLAMA_PORT", "default": 11434},
    ]
    write_manifest("ollama", m)
    manifests = load_manifests(services_root)
    out = assemble_env_example(manifests)
    # auto_managed vars are documented but their value is left empty (no default shown).
    assert "OLLAMA_SCALE=" in out
    assert "auto_managed" in out.lower() or "auto-managed" in out.lower()
    # Non-auto-managed value still has its default.
    assert "OLLAMA_PORT=11434" in out


def test_emits_image_vars(services_root, write_manifest, full_manifest_dict):
    write_manifest("ollama", full_manifest_dict("ollama"))
    manifests = load_manifests(services_root)
    out = assemble_env_example(manifests)
    assert "LLM_PROVIDER_IMAGE=ollama/ollama:latest" in out
    assert "OLLAMA_PULL_IMAGE=alpine/curl:latest" in out


def test_emits_source_var_with_options_comment(
    services_root, write_manifest, full_manifest_dict
):
    write_manifest("ollama", full_manifest_dict("ollama"))
    manifests = load_manifests(services_root)
    out = assemble_env_example(manifests)
    assert "LLM_PROVIDER_SOURCE=ollama-container-cpu" in out
    # Comment lists every option id so users editing .env see their choices.
    assert "ollama-container-cpu" in out
    assert "ollama-external" in out


def test_per_manifest_banner_includes_label_and_path(
    services_root, write_manifest, minimal_manifest_dict
):
    write_manifest("redis", minimal_manifest_dict("redis"))
    manifests = load_manifests(services_root)
    out = assemble_env_example(manifests)
    assert "Redis service" in out
    assert "services/redis/service.yml" in out


def test_ordering_respects_provided_order(
    services_root, write_manifest, minimal_manifest_dict
):
    write_manifest("redis", minimal_manifest_dict("redis"))
    write_manifest("backend", minimal_manifest_dict("backend") | {"category": "apps"})
    write_manifest("ollama", minimal_manifest_dict("ollama") | {"category": "llm"})
    manifests = load_manifests(services_root)
    # Without an order arg, alphabetical by folder name.
    out_default = assemble_env_example(manifests)
    p_backend = out_default.index("services/backend/service.yml")
    p_ollama = out_default.index("services/ollama/service.yml")
    p_redis = out_default.index("services/redis/service.yml")
    assert p_backend < p_ollama < p_redis

    # With explicit order, output respects it.
    out_ordered = assemble_env_example(manifests, order=["ollama", "redis", "backend"])
    q_ollama = out_ordered.index("services/ollama/service.yml")
    q_redis = out_ordered.index("services/redis/service.yml")
    q_backend = out_ordered.index("services/backend/service.yml")
    assert q_ollama < q_redis < q_backend


def test_order_with_missing_service_falls_back_to_alphabetical(
    services_root, write_manifest, minimal_manifest_dict
):
    """Services not mentioned in `order` are appended at the end, alphabetically."""
    write_manifest("redis", minimal_manifest_dict("redis"))
    write_manifest("backend", minimal_manifest_dict("backend") | {"category": "apps"})
    manifests = load_manifests(services_root)
    out = assemble_env_example(manifests, order=["redis"])
    p_redis = out.index("services/redis/service.yml")
    p_backend = out.index("services/backend/service.yml")
    assert p_redis < p_backend


def test_secret_var_default_is_empty_in_output(
    services_root, write_manifest, minimal_manifest_dict
):
    m = minimal_manifest_dict("redis")
    m["env"] = [
        {"name": "REDIS_PASSWORD", "default": "should-not-leak", "secret": True},
    ]
    write_manifest("redis", m)
    manifests = load_manifests(services_root)
    out = assemble_env_example(manifests)
    # The default never appears in the generated example; the user provides it.
    assert "should-not-leak" not in out
    assert "REDIS_PASSWORD=" in out


def test_output_is_deterministic(services_root, write_manifest, minimal_manifest_dict):
    """Re-rendering the same manifests must produce byte-identical output."""
    write_manifest("redis", minimal_manifest_dict("redis"))
    write_manifest("backend", minimal_manifest_dict("backend") | {"category": "apps"})
    manifests = load_manifests(services_root)
    a = assemble_env_example(manifests)
    b = assemble_env_example(manifests)
    assert a == b
