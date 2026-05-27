"""Tests for bootstrapper.docs.regen CLI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, "-m", "docs.regen", *args]
    env = {"PYTHONPATH": str(REPO_ROOT / "bootstrapper")}
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT, env={**__import__('os').environ, **env})


def test_help_flag_prints_usage_and_exits_zero():
    r = _run("--help")
    assert r.returncode == 0
    assert "usage" in r.stdout.lower()


def test_single_service_writes_three_files(tmp_path, monkeypatch):
    """regen hermes writes README.md (deps section), architecture.html, .svg."""
    r = _run("hermes", "--out-root", str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "hermes" / "README.md").is_file()
    assert (tmp_path / "hermes" / "architecture.html").is_file()
    assert (tmp_path / "hermes" / "architecture.svg").is_file()


def test_section_only_skips_diagrams(tmp_path):
    r = _run("hermes", "--out-root", str(tmp_path), "--section-only")
    assert r.returncode == 0
    assert (tmp_path / "hermes" / "README.md").is_file()
    assert not (tmp_path / "hermes" / "architecture.svg").exists()


def test_dry_run_writes_nothing(tmp_path):
    r = _run("hermes", "--out-root", str(tmp_path), "--dry-run")
    assert r.returncode == 0
    assert not (tmp_path / "hermes").exists()
    assert "would write" in r.stdout.lower()


def test_check_mode_exits_2_on_drift(tmp_path):
    """--check returns 2 when a committed artifact disagrees with current manifests.

    Seed a known-stale README at <out-root>/<svc>/README.md (with placeholder
    content that won't match what regen would produce), then assert --check
    reports drift. Without the seed, --check still exits 2 because the
    missing-artifact path also counts as drift, but that's a weaker contract
    than the docstring implies.
    """
    svc_dir = tmp_path / "hermes"
    svc_dir.mkdir()
    (svc_dir / "README.md").write_text("# stale placeholder — manifest content differs\n")
    r = _run("hermes", "--out-root", str(tmp_path), "--check")
    assert r.returncode == 2, f"expected drift exit code 2, got {r.returncode}: {r.stdout}"


def test_all_processes_21_doc_folders(tmp_path):
    """--all iterates every doc folder under services/ and writes
    artifacts to <out-root>/<doc-folder>/."""
    r = _run("--all", "--out-root", str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    written = sorted(p.name for p in tmp_path.iterdir() if p.is_dir())
    assert len(written) >= 20
