"""CI gate: committed README deps sections + architecture artifacts must
match what `python -m docs.regen --all --check` would produce.

Parallels test_env_example_consistency. Fails if any manifest change leaves
generated artifacts stale.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_no_drift_between_manifests_and_committed_artifacts():
    cmd = [sys.executable, "-m", "docs.regen", "--all", "--check"]
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "bootstrapper")}
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, env=env)
    if result.returncode == 2:
        pytest.fail(
            "Drift between committed docs and current manifests. Run:\n"
            "  python -m bootstrapper.docs.regen --all\n"
            "and commit the result.\n\n" + result.stdout
        )
    assert result.returncode == 0, result.stdout + result.stderr
