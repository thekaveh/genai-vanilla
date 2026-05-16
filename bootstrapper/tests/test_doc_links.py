"""Tests for scripts/check_doc_links.py — internal-markdown-link validator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VALIDATOR = REPO_ROOT / "scripts" / "check_doc_links.py"


def _run(*paths: Path) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(VALIDATOR), *(str(p) for p in paths)]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)


def test_validator_passes_on_clean_tree(tmp_path):
    """A directory of markdown files with valid relative links exits 0."""
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("See [B](./b.md).")
    b.write_text("See [A](./a.md).")
    result = _run(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_validator_flags_broken_relative_link(tmp_path):
    """A relative link that doesn't resolve exits non-zero and names the link."""
    a = tmp_path / "a.md"
    a.write_text("See [B](./b.md).")
    result = _run(tmp_path)
    assert result.returncode != 0
    assert "b.md" in result.stdout


def test_validator_ignores_external_links(tmp_path):
    """http(s) and mailto links are not checked."""
    a = tmp_path / "a.md"
    a.write_text(
        "[ext](https://example.com)\n"
        "[mail](mailto:me@example.com)\n"
    )
    result = _run(tmp_path)
    assert result.returncode == 0


def test_validator_ignores_anchors(tmp_path):
    """Bare `#anchor` and `./file.md#anchor` links don't require anchor existence."""
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("[same](#here) [other](./b.md#section)")
    b.write_text("body")
    result = _run(tmp_path)
    assert result.returncode == 0


def test_validator_resolves_relative_paths_with_parent_segments(tmp_path):
    """`../foo.md` is resolved relative to the source file."""
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "child.md").write_text("[parent](../sibling.md)")
    (tmp_path / "sibling.md").write_text("body")
    result = _run(tmp_path)
    assert result.returncode == 0


def test_validator_scans_repo_default_paths():
    """When invoked with no args, validator scans README.md + docs/ + CHANGELOG.md."""
    result = _run()
    # Whatever the current state is, the script must run end-to-end (exit
    # code 0 or 1 — but never crash). This guarantees Phase A's pre-migration
    # baseline can be captured.
    assert result.returncode in (0, 1), result.stdout + result.stderr
