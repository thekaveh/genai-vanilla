"""
Byte-equivalence proof for the modular layout.

Phase D landed the cutover: `docker-compose.yml` is now the thin
`include:`-shell that pulls in services/<name>/compose.yml fragments. This
test renders that shell via `docker compose config` and diffs the output
against the golden baseline captured from the pre-refactor monolithic file
at `bootstrapper/tests/fixtures/rendered_config_baseline.yml`.

Skipped if `docker` is not on PATH (CI lint job) or `.env` is missing
(fresh checkout).
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
COMPOSE = REPO_ROOT / "docker-compose.yml"
ENV_FILE = REPO_ROOT / ".env"
BASELINE = (
    Path(__file__).resolve().parent / "fixtures" / "rendered_config_baseline.yml"
)


def _docker_available() -> bool:
    return shutil.which("docker") is not None


pytestmark = pytest.mark.skipif(
    not _docker_available(),
    reason="docker not on PATH",
)


def _render(compose_file: Path) -> dict:
    if not ENV_FILE.is_file():
        pytest.skip(
            f".env does not exist at {ENV_FILE}. Run `cp .env.example .env` "
            f"locally to enable this test."
        )
    result = subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            str(ENV_FILE),
            "-f",
            str(compose_file),
            "config",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"`docker compose config` failed for {compose_file}:\n{result.stderr}"
    )
    return yaml.safe_load(result.stdout)


def _load_baseline() -> dict:
    if not BASELINE.is_file():
        pytest.skip(f"baseline fixture missing at {BASELINE}")
    return yaml.safe_load(BASELINE.read_text())


def test_full_stack_matches_baseline():
    """The thin-shell modular compose must render byte-identically to the
    pre-refactor monolithic baseline (captured in fixtures/)."""
    rendered = _render(COMPOSE)
    baseline = _load_baseline()
    assert rendered == baseline, (
        "Rendered modular config diverges from the monolithic baseline. "
        "Run `docker compose -f docker-compose.yml config > /tmp/actual.yml && "
        f"diff bootstrapper/tests/fixtures/rendered_config_baseline.yml /tmp/actual.yml` to inspect."
    )


def test_full_stack_services_match():
    """Service-by-service equality (gives a cleaner error message when one
    service drifts)."""
    rendered = _render(COMPOSE)
    baseline = _load_baseline()
    rendered_services = set(rendered["services"].keys())
    baseline_services = set(baseline["services"].keys())
    assert rendered_services == baseline_services, (
        f"Service set drift.\n"
        f"  Only in rendered: {sorted(rendered_services - baseline_services)}\n"
        f"  Only in baseline: {sorted(baseline_services - rendered_services)}"
    )
    drifted = []
    for name in sorted(rendered_services):
        if rendered["services"][name] != baseline["services"][name]:
            drifted.append(name)
    assert not drifted, f"Services with shape drift: {drifted}"


def test_full_stack_volumes_match():
    rendered = _render(COMPOSE)
    baseline = _load_baseline()
    assert rendered.get("volumes", {}) == baseline.get("volumes", {})


def test_full_stack_networks_match():
    rendered = _render(COMPOSE)
    baseline = _load_baseline()
    assert rendered.get("networks", {}) == baseline.get("networks", {})
