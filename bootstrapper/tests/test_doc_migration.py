"""Tests for scripts/migrate_docs_to_folders.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "migrate_docs_to_folders.py"


def _run_migration(target_repo: Path, *flags: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), "--repo-root", str(target_repo), *flags]
    return subprocess.run(cmd, capture_output=True, text=True)


def _build_fake_repo(tmp_path: Path) -> Path:
    """Build a miniature repo: 2 service docs + 1 cross-doc + 1 top-level README."""
    repo = tmp_path / "repo"
    docs_services = repo / "docs" / "services"
    docs_services.mkdir(parents=True)
    (docs_services / "alpha.md").write_text("# Alpha\nBody.")
    (docs_services / "bravo.md").write_text("# Bravo\nBody.")

    (repo / "docs" / "other.md").write_text("See [Alpha](services/alpha.md).")
    (repo / "README.md").write_text("See [Bravo](docs/services/bravo.md).")
    return repo


def test_migration_moves_files_into_folders(tmp_path):
    repo = _build_fake_repo(tmp_path)
    result = _run_migration(repo)
    assert result.returncode == 0, result.stdout + result.stderr

    # Files moved to per-folder layout
    assert (repo / "docs" / "services" / "alpha" / "README.md").is_file()
    assert (repo / "docs" / "services" / "bravo" / "README.md").is_file()
    # Old flat files gone
    assert not (repo / "docs" / "services" / "alpha.md").exists()
    assert not (repo / "docs" / "services" / "bravo.md").exists()


def test_migration_rewrites_inbound_links(tmp_path):
    repo = _build_fake_repo(tmp_path)
    _run_migration(repo)

    other = (repo / "docs" / "other.md").read_text()
    readme = (repo / "README.md").read_text()
    assert "services/alpha/README.md" in other
    assert "services/alpha.md" not in other
    assert "docs/services/bravo/README.md" in readme
    assert "docs/services/bravo.md" not in readme


def test_migration_dry_run_makes_no_changes(tmp_path):
    repo = _build_fake_repo(tmp_path)
    result = _run_migration(repo, "--dry-run")
    assert result.returncode == 0

    # Files NOT moved
    assert (repo / "docs" / "services" / "alpha.md").is_file()
    assert not (repo / "docs" / "services" / "alpha").exists()
    # Links NOT rewritten
    assert "services/alpha.md" in (repo / "docs" / "other.md").read_text()


def test_migration_is_idempotent(tmp_path):
    repo = _build_fake_repo(tmp_path)
    r1 = _run_migration(repo)
    r2 = _run_migration(repo)
    assert r1.returncode == 0
    assert r2.returncode == 0
    # Re-running on already-migrated repo doesn't break or duplicate
    assert (repo / "docs" / "services" / "alpha" / "README.md").is_file()
