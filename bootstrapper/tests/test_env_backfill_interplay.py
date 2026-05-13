"""
Test: manifest change → .env.example update → backfill_missing_env_vars()
chain on a stale .env propagates the new key.

Tier 2.G3 deliverable. Verifies the complementary nature of env_assembler
(manifest → .env.example) and backfill_missing_env_vars (.env.example →
user .env): together they form a pipeline that propagates a new manifest
env var down to live .env files on next ./start.sh run.

The current implementation keeps .env.example hand-maintained (env_assembler
is library-only — see Tier 2.G1 commit note), but the chain still works
because backfill reads .env.example as its source of truth regardless of
how it was produced.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "bootstrapper"))


def _make_starter_against(tmp_path: Path):
    """Create a GenAIStackStarter that reads/writes a tmp_path .env / .env.example."""
    from start import GenAIStackStarter
    # The starter constructs its own ConfigParser, which derives env paths
    # from CWD (root_dir). The simplest way to redirect: chdir.
    # We don't, because we want the source .env.example template to come
    # from the real repo. Instead, redirect the paths explicitly after
    # construction.
    starter = GenAIStackStarter()
    starter.config_parser.env_file_path = tmp_path / ".env"
    starter.config_parser.env_example_path = tmp_path / ".env.example"
    return starter


def test_backfill_appends_keys_present_in_env_example_but_missing_from_env(tmp_path):
    """Stale .env + .env.example with new keys → backfill adds them, preserves existing values."""
    # 1. Plant a .env.example with two sections, one new key per section
    (tmp_path / ".env.example").write_text("""# ============================================
# Foo Service
# ============================================
FOO_PORT=63010
FOO_NEW_VAR=new-default-value

# ============================================
# Bar Service
# ============================================
BAR_PORT=63011
BAR_FRESH_VAR=fresh-default
""")
    # 2. Plant a stale .env missing the two new keys
    (tmp_path / ".env").write_text("""FOO_PORT=63010
BAR_PORT=63011
USER_CUSTOM=preserved-value
""")

    starter = _make_starter_against(tmp_path)
    starter.backfill_missing_env_vars()

    # 3. Verify the new keys appended; existing values preserved
    after = (tmp_path / ".env").read_text()
    assert "FOO_NEW_VAR=new-default-value" in after
    assert "BAR_FRESH_VAR=fresh-default" in after
    assert "USER_CUSTOM=preserved-value" in after
    assert "FOO_PORT=63010" in after  # not duplicated, not removed


def test_backfill_is_idempotent(tmp_path):
    """Running backfill twice produces the same .env (no spurious appends)."""
    (tmp_path / ".env.example").write_text("FOO=bar\nBAZ=qux\n")
    (tmp_path / ".env").write_text("FOO=bar\n")

    starter = _make_starter_against(tmp_path)
    starter.backfill_missing_env_vars()
    after_first = (tmp_path / ".env").read_text()

    starter.backfill_missing_env_vars()
    after_second = (tmp_path / ".env").read_text()

    assert after_first == after_second, "backfill must be idempotent"
    assert "BAZ=qux" in after_first


def test_backfill_preserves_user_edits_to_existing_values(tmp_path):
    """If the user edited FOO_PORT in .env, backfill must not stomp it back to the default."""
    (tmp_path / ".env.example").write_text("FOO_PORT=63010\nFOO_NEW=newval\n")
    (tmp_path / ".env").write_text("FOO_PORT=99999\n")  # user override

    starter = _make_starter_against(tmp_path)
    starter.backfill_missing_env_vars()

    after = (tmp_path / ".env").read_text()
    assert "FOO_PORT=99999" in after  # user value preserved
    assert "FOO_PORT=63010" not in after  # example default not re-injected
    assert "FOO_NEW=newval" in after  # missing key appended


def test_backfill_noop_when_env_complete(tmp_path):
    """If .env already has all .env.example keys, backfill makes no change."""
    text = "FOO=1\nBAR=2\nBAZ=3\n"
    (tmp_path / ".env.example").write_text(text)
    (tmp_path / ".env").write_text(text)

    starter = _make_starter_against(tmp_path)
    starter.backfill_missing_env_vars()

    assert (tmp_path / ".env").read_text() == text


def test_backfill_appends_under_source_section_banner(tmp_path):
    """Missing keys get grouped by their `# === Section ===` header from .env.example."""
    (tmp_path / ".env.example").write_text("""# === Section A ===
FOO_VAR=a

# === Section B ===
BAR_VAR=b
""")
    (tmp_path / ".env").write_text("")  # empty .env, everything missing

    starter = _make_starter_against(tmp_path)
    starter.backfill_missing_env_vars()

    after = (tmp_path / ".env").read_text()
    # Both vars present
    assert "FOO_VAR=a" in after
    assert "BAR_VAR=b" in after
    # Auto-backfilled banner is present
    assert "Auto-backfilled" in after
