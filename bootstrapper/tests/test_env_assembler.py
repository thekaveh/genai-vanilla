"""Tests for bootstrapper.services.env_assembler."""

from __future__ import annotations

from pathlib import Path

from services.env_assembler import assemble_env_example
from services.manifests import load_manifests


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


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
    out = assemble_env_example(manifests, services_root=services_root)
    # Port default comes from topology slot allocator (data category, first slot:
    # base_port=63000 + data_offset=10 + slot=0 → 63010), not the manifest default.
    assert "REDIS_PORT=63010" in out
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
    out = assemble_env_example(manifests, services_root=services_root)
    # auto_managed vars are documented but their value is left empty (no default shown).
    assert "OLLAMA_SCALE=" in out
    assert "auto_managed" in out.lower() or "auto-managed" in out.lower()
    # Non-auto-managed port value comes from topology slot allocator, not manifest default.
    # llm category, first slot: base_port=63000 + llm_offset=30 + slot=0 → 63030.
    assert "OLLAMA_PORT=63030" in out


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


def test_committed_env_example_matches_assembler_output():
    """The committed ``.env.example`` at the repo root must be byte-identical
    to ``assemble_env_example(load_manifests(services/))``.

    This catches the "someone hand-edited .env.example without regenerating
    it" failure mode. If this test fails, run:

        cd bootstrapper && uv run python -m services.env_assembler

    and commit the resulting .env.example.
    """
    env_example_path = _REPO_ROOT / ".env.example"
    if not env_example_path.is_file():
        import pytest as _pytest
        _pytest.skip(f"{env_example_path} missing")

    expected = assemble_env_example(load_manifests(_REPO_ROOT / "services"))
    actual = env_example_path.read_text()
    assert actual == expected, (
        ".env.example is out of sync with the manifests. "
        "Regenerate with: cd bootstrapper && uv run python -m services.env_assembler"
    )


def test_multiline_description_each_line_commented(tmp_path):
    """Multi-line description must have every line prefixed with '# '."""
    services_root = tmp_path / "services"
    (services_root / "demo").mkdir(parents=True)
    (services_root / "demo" / "service.yml").write_text(
        "name: demo\n"
        "label: Demo\n"
        "category: data\n"
        "env:\n"
        "  - name: DEMO_VAR\n"
        "    default: value\n"
        "    description: |\n"
        "      Line one.\n"
        "      Line two.\n"
        "      Line three.\n"
    )
    manifests = load_manifests(services_root)
    output = assemble_env_example(manifests, services_root=services_root)
    # Every line of the description must be commented.
    assert "# Line one." in output
    assert "# Line two." in output
    assert "# Line three." in output
    # Bare uncommented continuation lines must NOT appear.
    lines = output.splitlines()
    for line in lines:
        if "Line two" in line or "Line three" in line:
            assert line.startswith("#"), f"description line not commented: {line!r}"
