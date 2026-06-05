"""
Source-permutation matrix.

For every SOURCE-configurable service, iterate every valid SOURCE value, write
it into a throwaway .env, and assert `docker compose config -q` succeeds. This
proves that:

  - Every declared source variant produces a parseable compose shape.
  - The `${VAR:-default}` patterns and `replicas: ${X_SCALE:-N}` fallbacks
    behave correctly when AUTO-MANAGED env vars are at their defaults.
  - No fragment hard-codes a source-specific value that breaks parse-time.

Skipped if `docker` is not on PATH or `.env.example` is missing.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
COMPOSE = REPO_ROOT / "docker-compose.yml"
ENV_EXAMPLE = REPO_ROOT / ".env.example"


def _docker_available() -> bool:
    return shutil.which("docker") is not None


pytestmark = pytest.mark.skipif(
    not _docker_available() or not ENV_EXAMPLE.is_file(),
    reason="docker not on PATH or .env.example missing",
)


# (source_var_name, [valid_values])
_PERMUTATIONS = [
    (
        "LLM_PROVIDER_SOURCE",
        [
            "ollama-container-cpu",
            "ollama-container-gpu",
            "ollama-localhost",
            "none",
        ],
    ),
    ("WEAVIATE_SOURCE", ["container", "localhost", "disabled"]),
    ("NEO4J_GRAPH_DB_SOURCE", ["container", "localhost", "disabled"]),
    ("COMFYUI_SOURCE", ["container-cpu", "container-gpu", "localhost", "disabled"]),
    (
        "STT_PROVIDER_SOURCE",
        [
            "speaches-container-cpu",
            "speaches-container-gpu",
            "parakeet-container-gpu",
            "parakeet-localhost",
            "whisper-cpp-localhost",
            "disabled",
        ],
    ),
    (
        "TTS_PROVIDER_SOURCE",
        [
            "speaches-container-cpu",
            "speaches-container-gpu",
            "chatterbox-container-gpu",
            "chatterbox-localhost",
            "disabled",
        ],
    ),
    ("DOC_PROCESSOR_SOURCE", ["disabled", "docling-container-gpu", "docling-localhost"]),
    ("OPENCLAW_SOURCE", ["disabled", "container", "localhost"]),
    ("HERMES_SOURCE", ["container", "localhost", "disabled"]),
    ("MINIO_SOURCE", ["container", "disabled"]),
    ("N8N_SOURCE", ["container", "disabled"]),
    ("SEARXNG_SOURCE", ["container", "disabled"]),
    ("OPEN_WEB_UI_SOURCE", ["container", "disabled"]),
    ("JUPYTERHUB_SOURCE", ["container", "disabled"]),
    ("LOCAL_DEEP_RESEARCHER_SOURCE", ["container", "disabled"]),
    ("CLOUD_OPENAI_SOURCE", ["enabled", "disabled"]),
    ("CLOUD_ANTHROPIC_SOURCE", ["enabled", "disabled"]),
    ("CLOUD_OPENROUTER_SOURCE", ["enabled", "disabled"]),
    # Ray was always Ray-disabled-by-default, but every SOURCE value must
    # still produce a clean `docker compose config`.
    ("RAY_SOURCE", ["ray-container-cpu", "ray-container-gpu", "disabled"]),
    # Observability bundle (added 2026-05-31). The matrix must exercise
    # both source values for each because PROMETHEUS_SOURCE is the gate
    # for FIVE cross-manifest scales (prometheus / node-exporter /
    # cadvisor / postgres-exporter / redis-exporter) and a wrong setting
    # would silently scale half the bundle to zero with no explicit
    # failure during compose rendering.
    ("PROMETHEUS_SOURCE", ["container", "disabled"]),
    ("GRAFANA_SOURCE", ["container", "disabled"]),
    # Compute tier (added 2026-06-04). Each is single-toggle (no source
    # variants beyond container/disabled). Spark gates Zeppelin's
    # `_generate_zeppelin_config` — exercising ZEPPELIN_SOURCE=container
    # here keeps SPARK_SOURCE at .env.example's default of `disabled`,
    # which would normally raise — but ServiceConfig isn't run during
    # `docker compose config` (it only validates compose-render syntax),
    # so the gate is invisible to this test. The real gate is exercised
    # by test_zeppelin_spark_gating.py.
    ("SPARK_SOURCE", ["container", "disabled"]),
    ("ZEPPELIN_SOURCE", ["container", "disabled"]),
    ("AIRFLOW_SOURCE", ["container", "disabled"]),
]


def _write_env_with_override(target: Path, var: str, value: str) -> None:
    """Copy .env.example to `target` with one variable overridden."""
    lines = ENV_EXAMPLE.read_text().splitlines()
    out = []
    found = False
    for line in lines:
        if line.startswith(f"{var}=") and not found:
            out.append(f"{var}={value}")
            found = True
        else:
            out.append(line)
    if not found:
        out.append(f"{var}={value}")
    target.write_text("\n".join(out) + "\n")


def _compose_config_ok(env_file: Path) -> tuple[bool, str]:
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            str(env_file),
            "-f",
            str(COMPOSE),
            "config",
            "-q",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    "var,value",
    [(v, val) for v, vals in _PERMUTATIONS for val in vals],
    ids=[f"{v}={val}" for v, vals in _PERMUTATIONS for val in vals],
)
def test_source_value_produces_valid_compose(var: str, value: str, tmp_path: Path):
    """Every source value, when written to .env, must produce a parseable
    compose shape via `docker compose -f docker-compose.yml config -q`."""
    env_file = tmp_path / ".env"
    _write_env_with_override(env_file, var, value)
    ok, stderr = _compose_config_ok(env_file)
    assert ok, f"{var}={value} produced invalid compose:\n{stderr}"
