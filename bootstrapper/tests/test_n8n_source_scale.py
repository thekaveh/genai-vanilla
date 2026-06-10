"""N8N_SCALE must derive from N8N_SOURCE, not from a stale .env value.

Regression guard: the generator used to read N8N_SCALE from .env with the
manifest value as a mere dict-default. Because the key always exists in a
bootstrapped .env, `N8N_SOURCE=disabled` never disabled anything, and a
dependency-manager auto-disable (N8N_SCALE=0) stuck forever even after the
violated dependency was re-enabled.
"""
from __future__ import annotations

import shutil
import pytest
from pathlib import Path
from core.config_parser import ConfigParser
from services.service_config import ServiceConfig


REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = REPO_ROOT / ".env.example"


def _make(tmp_path: Path, overrides: dict) -> ServiceConfig:
    env_path = tmp_path / ".env"
    shutil.copy(ENV_EXAMPLE, env_path)
    text = env_path.read_text(encoding="utf-8")
    out = []
    replaced = set()
    for line in text.splitlines():
        key = line.split("=", 1)[0] if "=" in line else None
        if key in overrides and key not in replaced:
            out.append(f"{key}={overrides[key]}")
            replaced.add(key)
        else:
            out.append(line)
    for var, val in overrides.items():
        if var not in replaced:
            out.append(f"{var}={val}")
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")

    cp = ConfigParser(str(REPO_ROOT))
    cp.env_file_path = env_path
    sc = ServiceConfig(config_parser=cp)
    sc.localhost_host = "localhost"
    return sc


@pytest.mark.parametrize("stale_scale", ["", "1"])
def test_disabled_source_zeroes_all_n8n_scales(tmp_path, stale_scale):
    sc = _make(tmp_path, {"N8N_SOURCE": "disabled", "N8N_SCALE": stale_scale})
    env = sc.generate_service_environment()
    assert env["N8N_SCALE"] == "0"
    assert env["N8N_WORKER_SCALE"] == "0"
    assert env["N8N_INIT_SCALE"] == "0"


def test_container_source_revives_after_auto_disable(tmp_path):
    """A dependency-manager N8N_SCALE=0 in .env must not stick once the
    source is (still) container — the dep manager re-evaluates after
    generation each run, so generation must not preserve its old verdict."""
    sc = _make(tmp_path, {"N8N_SOURCE": "container", "N8N_SCALE": "0"})
    env = sc.generate_service_environment()
    assert env["N8N_SCALE"] == "1"
    assert env["N8N_WORKER_SCALE"] == "1"
    assert env["N8N_INIT_SCALE"] == "1"
