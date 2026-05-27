"""Regression: Kong must have explicit host-routed services for every
alias declared by manifests. Otherwise the dashboard catch-all swallows
``graph.localhost``, ``weaviate.localhost``, etc. → Supabase Studio.
"""

from __future__ import annotations

from pathlib import Path


def _generate(env_body: str) -> dict:
    """Render Kong config against a synthetic env override.

    The generator's ``generate_kong_config`` calls
    ``load_environment_variables`` first, which would otherwise reset
    ``env_vars`` from disk. We stub that loader so it starts from the
    real .env (unrelated vars resolve normally) and applies the test
    overrides on top.
    """
    from core.config_parser import ConfigParser
    from utils.kong_config_generator import KongConfigGenerator

    repo_root = Path(__file__).resolve().parent.parent.parent
    cp = ConfigParser(str(repo_root))
    g = KongConfigGenerator(cp)
    overrides: dict[str, str] = {}
    for line in env_body.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            overrides[k.strip()] = v.strip()

    def _stub_load():
        g.env_vars = cp.parse_env_file()
        g.env_vars.update(overrides)
    g.load_environment_variables = _stub_load  # type: ignore[method-assign]
    return g.generate_kong_config()


def _hosts_to_service(config: dict) -> dict[str, str]:
    """Build a {hostname: kong_service_name} index from the config."""
    index: dict[str, str] = {}
    for svc in config["services"]:
        for route in svc.get("routes", []):
            for host in route.get("hosts") or []:
                index[host] = svc["name"]
    return index


def test_dashboard_catch_all_is_restricted_to_studio_and_bare_localhost():
    """The Studio dashboard route must not be a global wildcard.

    Regression: it used to match ``paths: ['/']`` with no host filter,
    so every unaliased *.localhost request fell through to Studio.
    """
    config = _generate("")
    dashboard = next(
        svc for svc in config["services"] if svc["name"] == "dashboard"
    )
    dashboard_routes = dashboard["routes"]
    assert len(dashboard_routes) == 1
    hosts = set(dashboard_routes[0].get("hosts") or [])
    assert hosts == {"studio.localhost", "localhost"}, (
        f"dashboard route should be locked to studio.localhost + localhost, "
        f"got {hosts}"
    )


def test_alias_only_services_route_to_expected_containers():
    """Container-mode sources produce a Kong route per alias, pointing
    at the right internal container URL."""
    config = _generate(
        "NEO4J_GRAPH_DB_SOURCE=container\n"
        "WEAVIATE_SOURCE=container\n"
        "LLM_PROVIDER_SOURCE=ollama-container-cpu\n"
        "DOC_PROCESSOR_SOURCE=docling-container-gpu\n"
        "LOCAL_DEEP_RESEARCHER_SOURCE=container\n"
        "STT_PROVIDER_SOURCE=speaches-container-cpu\n"
        "TTS_PROVIDER_SOURCE=speaches-container-cpu\n"
    )
    by_host = _hosts_to_service(config)
    for alias in [
        "graph.localhost", "weaviate.localhost", "ollama.localhost",
        "docling.localhost", "research.localhost",
        "stt.localhost", "tts.localhost",
    ]:
        assert alias in by_host, f"missing Kong route for {alias}: {sorted(by_host)}"


def test_localhost_source_routes_via_host_docker_internal():
    """Host-install ('localhost') sources still get a Kong alias — the
    route proxies through ``host.docker.internal`` to the user's host
    port. Mirrors the existing ComfyUI/OpenClaw/Hermes pattern so a
    single entry point (``ollama.localhost``, ``graph.localhost``, etc.)
    works in both container and host-install modes.

    Test exercises the *fallback* URLs (no ``<SVC>_LOCALHOST_URL``
    override). The dev's real .env may already define those overrides
    against a non-default BASE_PORT, so we explicitly blank them.
    """
    config = _generate(
        "NEO4J_GRAPH_DB_SOURCE=localhost\n"
        "WEAVIATE_SOURCE=localhost\n"
        "LLM_PROVIDER_SOURCE=ollama-localhost\n"
        "DOC_PROCESSOR_SOURCE=docling-localhost\n"
        "DOCLING_LOCALHOST_URL=\n"
        "STT_PROVIDER_SOURCE=parakeet-localhost\n"
        "PARAKEET_LOCALHOST_URL=\n"
        "TTS_PROVIDER_SOURCE=chatterbox-localhost\n"
        "CHATTERBOX_LOCALHOST_URL=\n"
    )
    by_host = _hosts_to_service(config)
    # Every alias still resolves.
    expected_urls = {
        "graph.localhost":    "http://host.docker.internal:7474/",
        "weaviate.localhost": "http://host.docker.internal:8080/",
        "ollama.localhost":   "http://host.docker.internal:11434/",
        # docling-localhost default port from manifest fallback
        "docling.localhost":  "http://host.docker.internal:63021/",
        "stt.localhost":      "http://host.docker.internal:63022/",
        "tts.localhost":      "http://host.docker.internal:63027/",
    }
    by_host_with_url = {
        host: svc
        for svc in config["services"]
        for route in svc.get("routes", [])
        for host in route.get("hosts") or []
    }
    for alias, expected in expected_urls.items():
        assert alias in by_host, (
            f"localhost-mode alias {alias} should still be Kong-routed: "
            f"{sorted(by_host)}"
        )
        assert by_host_with_url[alias]["url"] == expected, (
            f"localhost-mode alias {alias} should target {expected}, "
            f"got {by_host_with_url[alias]['url']}"
        )


def test_localhost_port_env_override_is_honored():
    """Users can override the localhost target via ``<SVC>_LOCALHOST_PORT``
    env vars. Kong's route URL is built by the ``_localhost_url`` helper,
    which reads the same PORT var compose's runtime_sc consumes — so
    Kong and the in-container clients always agree.
    """
    config = _generate(
        "STT_PROVIDER_SOURCE=whisper-cpp-localhost\n"
        "WHISPER_CPP_LOCALHOST_PORT=7777\n"
        "DOC_PROCESSOR_SOURCE=docling-localhost\n"
        "DOCLING_LOCALHOST_PORT=8888\n"
        "TTS_PROVIDER_SOURCE=chatterbox-localhost\n"
        "CHATTERBOX_LOCALHOST_PORT=6666\n"
    )
    by_host_with_url = {
        host: svc["url"]
        for svc in config["services"]
        for route in svc.get("routes", [])
        for host in route.get("hosts") or []
    }
    assert by_host_with_url["stt.localhost"] == "http://host.docker.internal:7777/"
    assert by_host_with_url["docling.localhost"] == "http://host.docker.internal:8888/"
    assert by_host_with_url["tts.localhost"] == "http://host.docker.internal:6666/"


def test_external_source_skips_kong_route():
    """``*-external`` sources target a remote URL outside our network —
    we don't add a Kong route for those (LiteLLM forwards via its own
    config). Disabled handled separately below.
    """
    config = _generate("LLM_PROVIDER_SOURCE=ollama-external\n")
    by_host = _hosts_to_service(config)
    assert "ollama.localhost" not in by_host


def test_disabled_source_skips_kong_route():
    """Disabled service: no Kong route."""
    config = _generate(
        "WEAVIATE_SOURCE=disabled\nDOC_PROCESSOR_SOURCE=disabled\n"
    )
    by_host = _hosts_to_service(config)
    assert "weaviate.localhost" not in by_host
    assert "docling.localhost" not in by_host


def test_tts_route_picks_correct_container_for_chatterbox():
    """TTS engine container varies by source-id prefix."""
    config = _generate("TTS_PROVIDER_SOURCE=chatterbox-container-gpu\n")
    tts_svc = next(
        (svc for svc in config["services"] if svc["name"] == "tts-api"),
        None,
    )
    assert tts_svc is not None
    assert tts_svc["url"] == "http://chatterbox:4123/"


def test_stt_and_tts_container_urls_match_compose_listen_ports():
    """STT/TTS engine containers expose specific listen ports — the
    Kong upstream URL must point at the right one (regression: an
    earlier version mistakenly routed chatterbox-container to :8000
    when the container actually listens on :4123).
    """
    cases = [
        ("STT_PROVIDER_SOURCE=parakeet-container-gpu\n", "stt-api",
         "http://parakeet-gpu:8000/"),
        ("STT_PROVIDER_SOURCE=speaches-container-cpu\n", "stt-api",
         "http://speaches:8000/"),
        ("STT_PROVIDER_SOURCE=speaches-container-gpu\n", "stt-api",
         "http://speaches:8000/"),
        ("TTS_PROVIDER_SOURCE=speaches-container-cpu\n", "tts-api",
         "http://speaches:8000/"),
    ]
    for env, name, expected in cases:
        config = _generate(env)
        svc = next((s for s in config["services"] if s["name"] == name), None)
        assert svc is not None, f"{name} missing for env={env!r}"
        assert svc["url"] == expected, (
            f"{name} should route to {expected} for env={env!r}, got {svc['url']}"
        )


import pytest


@pytest.mark.parametrize("env_var,svc_source_var,svc_source_value,expected_port", [
    ("COMFYUI_LOCALHOST_PORT",      "COMFYUI_SOURCE",            "localhost",              "9999"),
    ("DOCLING_LOCALHOST_PORT",      "DOC_PROCESSOR_SOURCE",      "docling-localhost",      "9999"),
    # Hermes Kong route fronts the DASHBOARD (browser UI), not the API.
    # HERMES_LOCALHOST_PORT drives the API (consumed by runtime_sc's
    # HERMES_ENDPOINT); HERMES_LOCALHOST_DASHBOARD_PORT is the separate
    # host port the Kong route targets — same split as Neo4j HTTP/Bolt.
    ("HERMES_LOCALHOST_DASHBOARD_PORT", "HERMES_SOURCE",          "localhost",              "9999"),
    ("OPENCLAW_LOCALHOST_PORT",     "OPENCLAW_SOURCE",           "localhost",              "9999"),
    ("PARAKEET_LOCALHOST_PORT",     "STT_PROVIDER_SOURCE",       "parakeet-localhost",     "9999"),
    ("WHISPER_CPP_LOCALHOST_PORT",  "STT_PROVIDER_SOURCE",       "whisper-cpp-localhost",  "9999"),
    ("CHATTERBOX_LOCALHOST_PORT",   "TTS_PROVIDER_SOURCE",       "chatterbox-localhost",   "9999"),
    ("OLLAMA_LOCALHOST_PORT",       "LLM_PROVIDER_SOURCE",       "ollama-localhost",       "9999"),
    ("NEO4J_LOCALHOST_HTTP_PORT",   "NEO4J_GRAPH_DB_SOURCE",     "localhost",              "9999"),
    ("WEAVIATE_LOCALHOST_PORT",     "WEAVIATE_SOURCE",           "localhost",              "9999"),
])
def test_kong_localhost_route_reads_port_var(
    env_var, svc_source_var, svc_source_value, expected_port, tmp_path
):
    """Each localhost-mode route's `url` is derived from the matching
    LOCALHOST_PORT env var. Sets a non-default port and asserts the
    generated route URL reflects it."""
    from utils.kong_config_generator import KongConfigGenerator
    from core.config_parser import ConfigParser

    env_path = tmp_path / ".env"
    env_path.write_text(
        f"{svc_source_var}={svc_source_value}\n"
        f"{env_var}={expected_port}\n"
        "DASHBOARD_USERNAME=u\nDASHBOARD_PASSWORD=p\n",
        encoding="utf-8",
    )
    cp = ConfigParser(str(tmp_path))
    cp.env_file_path = env_path
    cp.parse_env_file()
    gen = KongConfigGenerator(cp)
    gen.load_environment_variables()
    cfg = gen.generate_kong_config()
    found = []
    for svc in cfg["services"]:
        url = svc.get("url", "") or ""
        if f":{expected_port}" in url and "host.docker.internal" in url:
            found.append((svc["name"], url))
    assert found, (
        f"Expected at least one Kong service route to target "
        f"host.docker.internal:{expected_port} (matching {env_var}). "
        f"Got services: {[(s['name'], s.get('url')) for s in cfg['services']]}"
    )
