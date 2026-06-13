"""Assert hermes, n8n, backend declare lightrag in runtime_adaptive.adapts_to
AND that the env var actually reaches the rendered env."""
from __future__ import annotations

import yaml
import pytest
from pathlib import Path
from core.config_parser import ConfigParser
from services.service_config import ServiceConfig

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_yaml(name: str) -> dict:
    text = (REPO_ROOT / "services" / name / "service.yml").read_text(encoding="utf-8")
    return yaml.safe_load(text)


def _sc(env_path: Path) -> ServiceConfig:
    cp = ConfigParser(str(REPO_ROOT))
    cp.env_file_path = env_path
    sc = ServiceConfig(config_parser=cp)
    sc.localhost_host = "localhost"
    return sc


# --- Declarative checks ---

@pytest.mark.parametrize(
    "svc,container,expected_env_var",
    [
        ("hermes", "hermes-init", "LIGHTRAG_INTERNAL_URL"),
        ("n8n", "n8n", "LIGHTRAG_ENDPOINT"),
        ("backend", "backend", "LIGHTRAG_ENDPOINT"),
    ],
    ids=lambda item: item if isinstance(item, str) else None,
)
def test_adapts_to_includes_lightrag(svc, container, expected_env_var):
    data = _load_yaml(svc)
    block = data["runtime_adaptive"][container]
    assert "lightrag" in block["adapts_to"], \
        f"{svc}.{container}.runtime_adaptive.adapts_to missing 'lightrag'"
    assert expected_env_var in block["environment_adaptation"], \
        f"{svc}.{container} missing env var {expected_env_var}"


# --- Imperative checks (env actually rendered) ---


def test_hermes_init_gets_LIGHTRAG_INTERNAL_URL_when_lightrag_enabled(env_with_overrides):
    sc = _sc(env_with_overrides({
        "HERMES_SOURCE": "container",
        "LIGHTRAG_SOURCE": "container",
    }))
    env = sc.generate_service_environment()
    assert env.get("LIGHTRAG_INTERNAL_URL", "").startswith("http://"), \
        f"hermes-init missing LIGHTRAG_INTERNAL_URL; got {env.get('LIGHTRAG_INTERNAL_URL')!r}"


def test_n8n_gets_LIGHTRAG_ENDPOINT_when_lightrag_enabled(env_with_overrides):
    sc = _sc(env_with_overrides({
        "N8N_SOURCE": "container",
        "LIGHTRAG_SOURCE": "container",
    }))
    env = sc.generate_service_environment()
    assert env.get("LIGHTRAG_ENDPOINT", "").startswith("http://"), \
        f"n8n missing LIGHTRAG_ENDPOINT; got {env.get('LIGHTRAG_ENDPOINT')!r}"


def test_backend_gets_LIGHTRAG_ENDPOINT_when_lightrag_enabled(env_with_overrides):
    sc = _sc(env_with_overrides({
        "LIGHTRAG_SOURCE": "container",
    }))
    env = sc.generate_service_environment()
    assert env.get("LIGHTRAG_ENDPOINT", "").startswith("http://"), \
        f"backend missing LIGHTRAG_ENDPOINT; got {env.get('LIGHTRAG_ENDPOINT')!r}"


# --- Hermes-init *_INTERNAL_URL emissions (capability wiring) ---
#
# init-hermes.sh strips capability blocks whose URL env is empty
# (see services/hermes/init/scripts/init-hermes.sh strip_block). The
# runtime_adaptive.hermes-init.environment_adaptation block declares
# TTS_INTERNAL_URL / STT_INTERNAL_URL / COMFYUI_INTERNAL_URL /
# SEARXNG_INTERNAL_URL, but service_config.py used to only emit
# LIGHTRAG_INTERNAL_URL — silently disabling four capability blocks
# even when their upstream providers were enabled.


def test_hermes_init_gets_TTS_INTERNAL_URL_when_tts_enabled(env_with_overrides):
    sc = _sc(env_with_overrides({
        "HERMES_SOURCE": "container",
        "TTS_PROVIDER_SOURCE": "speaches-container-cpu",
    }))
    env = sc.generate_service_environment()
    assert env.get("TTS_INTERNAL_URL", "").startswith("http://"), \
        f"hermes-init missing TTS_INTERNAL_URL; got {env.get('TTS_INTERNAL_URL')!r}"


def test_hermes_init_gets_STT_INTERNAL_URL_when_stt_enabled(env_with_overrides):
    sc = _sc(env_with_overrides({
        "HERMES_SOURCE": "container",
        "STT_PROVIDER_SOURCE": "speaches-container-cpu",
    }))
    env = sc.generate_service_environment()
    assert env.get("STT_INTERNAL_URL", "").startswith("http://"), \
        f"hermes-init missing STT_INTERNAL_URL; got {env.get('STT_INTERNAL_URL')!r}"


def test_hermes_init_gets_COMFYUI_INTERNAL_URL_when_comfyui_enabled(env_with_overrides):
    sc = _sc(env_with_overrides({
        "HERMES_SOURCE": "container",
        "COMFYUI_SOURCE": "container-cpu",
    }))
    env = sc.generate_service_environment()
    assert env.get("COMFYUI_INTERNAL_URL", "").startswith("http://"), \
        f"hermes-init missing COMFYUI_INTERNAL_URL; got {env.get('COMFYUI_INTERNAL_URL')!r}"


def test_hermes_init_gets_SEARXNG_INTERNAL_URL_when_searxng_enabled(env_with_overrides):
    sc = _sc(env_with_overrides({
        "HERMES_SOURCE": "container",
        "SEARXNG_SOURCE": "container",
    }))
    env = sc.generate_service_environment()
    assert env.get("SEARXNG_INTERNAL_URL", "") == "http://searxng:8080", \
        f"hermes-init missing SEARXNG_INTERNAL_URL; got {env.get('SEARXNG_INTERNAL_URL')!r}"


def test_hermes_init_internal_urls_blank_when_hermes_disabled(env_with_overrides):
    sc = _sc(env_with_overrides({
        "HERMES_SOURCE": "disabled",
        "TTS_PROVIDER_SOURCE": "speaches-container-cpu",
        "STT_PROVIDER_SOURCE": "speaches-container-cpu",
        "COMFYUI_SOURCE": "container-cpu",
        "SEARXNG_SOURCE": "container",
    }))
    env = sc.generate_service_environment()
    # Hermes off = capability URLs blank (no point routing to a
    # non-existent init container).
    for var in (
        "TTS_INTERNAL_URL", "STT_INTERNAL_URL",
        "COMFYUI_INTERNAL_URL", "SEARXNG_INTERNAL_URL",
        "LIGHTRAG_INTERNAL_URL",
    ):
        assert env.get(var, "") == "", \
            f"{var} should be empty when HERMES_SOURCE=disabled; got {env.get(var)!r}"
