"""COMPOSE_PROFILES stacking across STT/TTS/doc-processor generators.

Regression guard for the doc-processor clobber bug: the docling-gpu branch
used to rebuild COMPOSE_PROFILES from service_sources (which never holds
that key) instead of stacking onto the shared running tally, wiping any
speaches/parakeet/chatterbox profile added before it. Also pins the
stale-clearing contract: the pipeline always emits COMPOSE_PROFILES (empty
when no profile-gated source is active) so update_env_file() can't preserve
a profile from a since-disabled source.
"""
from __future__ import annotations

import shutil
import pytest
from pathlib import Path
from core.config_parser import ConfigParser
from services.service_config import ServiceConfig


REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = REPO_ROOT / ".env.example"


@pytest.fixture
def env_copy(tmp_path):
    env = tmp_path / ".env"
    shutil.copy(ENV_EXAMPLE, env)
    return env


def _make(env_path: Path, sources: dict) -> ServiceConfig:
    text = env_path.read_text(encoding="utf-8")
    out = []
    replaced = set()
    for line in text.splitlines():
        key = line.split("=", 1)[0] if "=" in line else None
        if key in sources and key not in replaced:
            out.append(f"{key}={sources[key]}")
            replaced.add(key)
        else:
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


def _profiles(env: dict) -> set:
    return {p for p in env["COMPOSE_PROFILES"].split(",") if p}


def test_docling_gpu_stacks_on_stt_profile(env_copy):
    sc = _make(env_copy, {
        "STT_PROVIDER_SOURCE": "speaches-container-cpu",
        "TTS_PROVIDER_SOURCE": "disabled",
        "DOC_PROCESSOR_SOURCE": "docling-container-gpu",
    })
    env = sc.generate_service_environment()
    assert _profiles(env) == {"speaches-cpu", "docling-gpu", "doc-gpu"}


def test_docling_gpu_stacks_on_stt_and_tts_profiles(env_copy):
    sc = _make(env_copy, {
        "STT_PROVIDER_SOURCE": "parakeet-container-gpu",
        "TTS_PROVIDER_SOURCE": "chatterbox-container-gpu",
        "DOC_PROCESSOR_SOURCE": "docling-container-gpu",
    })
    env = sc.generate_service_environment()
    assert _profiles(env) == {
        "parakeet-gpu", "chatterbox-gpu", "docling-gpu", "doc-gpu",
    }


def test_docling_gpu_alone(env_copy):
    sc = _make(env_copy, {
        "STT_PROVIDER_SOURCE": "disabled",
        "TTS_PROVIDER_SOURCE": "disabled",
        "DOC_PROCESSOR_SOURCE": "docling-container-gpu",
    })
    env = sc.generate_service_environment()
    assert _profiles(env) == {"docling-gpu", "doc-gpu"}


def test_all_disabled_emits_empty_profiles_key(env_copy):
    """The key must be present (and empty) so stale .env values get cleared."""
    sc = _make(env_copy, {
        "STT_PROVIDER_SOURCE": "disabled",
        "TTS_PROVIDER_SOURCE": "disabled",
        "DOC_PROCESSOR_SOURCE": "disabled",
    })
    env = sc.generate_service_environment()
    assert env["COMPOSE_PROFILES"] == ""


def test_speaches_shared_by_stt_and_tts_not_duplicated(env_copy):
    sc = _make(env_copy, {
        "STT_PROVIDER_SOURCE": "speaches-container-cpu",
        "TTS_PROVIDER_SOURCE": "speaches-container-cpu",
        "DOC_PROCESSOR_SOURCE": "disabled",
    })
    env = sc.generate_service_environment()
    assert env["COMPOSE_PROFILES"].split(",").count("speaches-cpu") == 1
