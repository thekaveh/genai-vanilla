"""CLI tests for --track and --list-tracks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
START_PY = REPO_ROOT / "bootstrapper" / "start.py"


def _run(*args: str) -> subprocess.CompletedProcess:
    """Invoke start.py with isolated env so we don't accidentally touch
    docker. We rely on --list-tracks / --track foo exiting BEFORE any
    side effect."""
    return subprocess.run(
        [sys.executable, str(START_PY), *args],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": str(REPO_ROOT / "bootstrapper")},
        timeout=30,
    )


def test_list_tracks_exits_zero():
    r = _run("--list-tracks")
    assert r.returncode == 0, f"--list-tracks should exit 0; stderr={r.stderr!r}"


def test_list_tracks_lists_every_track():
    r = _run("--list-tracks")
    for key in ("gen-ai-rag", "gen-ai-eng", "gen-ai-creative",
                "ml-eng", "data-eng", "all"):
        assert key in r.stdout, f"--list-tracks must mention {key}; stdout={r.stdout!r}"


def test_track_unknown_exits_two():
    r = _run("--track", "nonexistent-track")
    assert r.returncode == 2
    assert "unknown track" in r.stderr.lower()
    # Lists available tracks in the error message so the user can self-correct.
    assert "gen-ai-rag" in r.stderr
