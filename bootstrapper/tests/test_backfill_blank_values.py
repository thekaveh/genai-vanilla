"""Regression: backfill must fill blank values from .env.example.

When the manifest's secret-default policy changes (e.g.,
SUPABASE_DB_PASSWORD goes from `secret-blank` to
`default: password`), users with a pre-existing .env retain the
blank value. The stack then fails to start because supabase-db-init
can't authenticate.

The fix: backfill scans for `KEY=` (blank) entries and fills them
from the .env.example's non-blank value, preserving intentional
autogen blanks (those have an empty value in .env.example too).
"""

from __future__ import annotations

from pathlib import Path


def _make_starter(tmp_path: Path, env_body: str, example_body: str):
    """Build a GenAIStackStarter pointing at a synthetic tmp_path repo.

    The starter caches its env paths via ConfigParser at construction;
    we patch them post-construction to point at tmp_path so tests
    don't touch the real .env at repo root.
    """
    (tmp_path / ".env").write_text(env_body)
    (tmp_path / ".env.example").write_text(example_body)
    from start import GenAIStackStarter

    starter = GenAIStackStarter()
    starter.config_parser.root_dir = tmp_path
    starter.config_parser.env_file_path = tmp_path / ".env"
    starter.config_parser.env_example_path = tmp_path / ".env.example"
    return starter


def test_backfill_fills_blank_from_example_default(tmp_path):
    """Blank existing value gets filled from non-blank example value."""
    env_body = "SUPABASE_DB_PASSWORD=\nLITELLM_MASTER_KEY=\n"
    example_body = (
        "SUPABASE_DB_PASSWORD=password\n"  # placeholder
        "LITELLM_MASTER_KEY=\n"            # intentional autogen blank
    )
    starter = _make_starter(tmp_path, env_body, example_body)
    assert starter.backfill_missing_env_vars()
    out = (tmp_path / ".env").read_text()
    assert "SUPABASE_DB_PASSWORD=password" in out
    # LITELLM_MASTER_KEY stays blank — both sides are intentionally empty.
    assert "LITELLM_MASTER_KEY=password" not in out
    assert "LITELLM_MASTER_KEY=" in out


def test_backfill_preserves_existing_non_blank_values(tmp_path):
    """User-customized values are NEVER overwritten."""
    env_body = "SUPABASE_DB_PASSWORD=my-custom-secret\n"
    example_body = "SUPABASE_DB_PASSWORD=password\n"
    starter = _make_starter(tmp_path, env_body, example_body)
    assert starter.backfill_missing_env_vars()
    out = (tmp_path / ".env").read_text()
    assert "SUPABASE_DB_PASSWORD=my-custom-secret" in out
    assert "SUPABASE_DB_PASSWORD=password" not in out


def test_backfill_handles_inline_comments(tmp_path):
    """Inline comment (`# …`) after the blank value isn't mistaken for content."""
    env_body = "SUPABASE_DB_PASSWORD=  # autogen at runtime\n"
    example_body = "SUPABASE_DB_PASSWORD=password\n"
    starter = _make_starter(tmp_path, env_body, example_body)
    assert starter.backfill_missing_env_vars()
    out = (tmp_path / ".env").read_text()
    # Value is now `password` — the prior blank-with-comment was a blank.
    assert "SUPABASE_DB_PASSWORD=password" in out
