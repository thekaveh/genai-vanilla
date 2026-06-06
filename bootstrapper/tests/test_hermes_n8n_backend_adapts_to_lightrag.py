"""Assert hermes, n8n, backend declare lightrag in runtime_adaptive.adapts_to
AND that the env var actually reaches the rendered env."""
from __future__ import annotations

import shutil
import yaml
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_yaml(name: str) -> dict:
    text = (REPO_ROOT / "services" / name / "service.yml").read_text(encoding="utf-8")
    return yaml.safe_load(text)


def _make(env_path, sources):
    """Build a ServiceConfig with sources patched into the env file."""
    from core.config_parser import ConfigParser
    from services.service_config import ServiceConfig

    text = env_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    out = []
    replaced = set()
    for line in lines:
        matched = False
        for var, val in sources.items():
            if line.startswith(f"{var}=") and var not in replaced:
                out.append(f"{var}={val}")
                replaced.add(var)
                matched = True
                break
        if not matched:
            out.append(line)
    for var, val in sources.items():
        if var not in replaced:
            out.append(f"{var}={val}")
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")

    cp = ConfigParser(str(REPO_ROOT))
    cp.env_file_path = env_path
    sc = ServiceConfig(config_parser=cp)
    sc.localhost_host = "localhost"
    return sc


# --- Declarative checks ---

@pytest.mark.parametrize("svc,container,expected_env_var", [
    ("hermes", "hermes-init", "LIGHTRAG_INTERNAL_URL"),
    ("n8n", "n8n", "LIGHTRAG_ENDPOINT"),
    ("backend", "backend", "LIGHTRAG_ENDPOINT"),
])
def test_adapts_to_includes_lightrag(svc, container, expected_env_var):
    data = _load_yaml(svc)
    block = data["runtime_adaptive"][container]
    assert "lightrag" in block["adapts_to"], \
        f"{svc}.{container}.runtime_adaptive.adapts_to missing 'lightrag'"
    assert expected_env_var in block["environment_adaptation"], \
        f"{svc}.{container} missing env var {expected_env_var}"


# --- Imperative checks (env actually rendered) ---

@pytest.fixture
def env_copy(tmp_path):
    env = tmp_path / ".env"
    shutil.copy(REPO_ROOT / ".env.example", env)
    return env


def test_hermes_init_gets_LIGHTRAG_INTERNAL_URL_when_lightrag_enabled(env_copy):
    sc = _make(env_copy, {
        "HERMES_SOURCE": "container",
        "LIGHTRAG_SOURCE": "container",
    })
    env = sc.generate_service_environment()
    assert env.get("LIGHTRAG_INTERNAL_URL", "").startswith("http://"), \
        f"hermes-init missing LIGHTRAG_INTERNAL_URL; got {env.get('LIGHTRAG_INTERNAL_URL')!r}"


def test_n8n_gets_LIGHTRAG_ENDPOINT_when_lightrag_enabled(env_copy):
    sc = _make(env_copy, {
        "N8N_SOURCE": "container",
        "LIGHTRAG_SOURCE": "container",
    })
    env = sc.generate_service_environment()
    assert env.get("LIGHTRAG_ENDPOINT", "").startswith("http://"), \
        f"n8n missing LIGHTRAG_ENDPOINT; got {env.get('LIGHTRAG_ENDPOINT')!r}"


def test_backend_gets_LIGHTRAG_ENDPOINT_when_lightrag_enabled(env_copy):
    sc = _make(env_copy, {
        "LIGHTRAG_SOURCE": "container",
    })
    env = sc.generate_service_environment()
    assert env.get("LIGHTRAG_ENDPOINT", "").startswith("http://"), \
        f"backend missing LIGHTRAG_ENDPOINT; got {env.get('LIGHTRAG_ENDPOINT')!r}"
