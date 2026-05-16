"""Regression: dependency_manager must not crash on empty scale-var
values.

auto_managed: true scale vars (HERMES_SCALE, OPENCLAW_SCALE, etc.) are
emitted into `.env.example` as ``VAR=`` (blank) — service_config.py
fills them in at runtime. When dependency_manager runs before that,
calling ``int("")`` raised ``ValueError: invalid literal for int()``.
"""

from __future__ import annotations

from pathlib import Path


def _make_dependency_manager(tmp_path: Path, env_body: str):
    """Build a DependencyManager pointing at a synthetic .env in tmp_path."""
    from services.dependency_manager import DependencyManager
    from core.config_parser import ConfigParser

    (tmp_path / ".env").write_text(env_body)
    cp = ConfigParser(str(tmp_path))
    return DependencyManager(cp)


def test_get_service_scale_returns_default_for_blank(tmp_path):
    """Blank scale value falls back to the 'assume enabled' default (1)."""
    dm = _make_dependency_manager(tmp_path, "HERMES_SCALE=\n")
    assert dm.get_service_scale("hermes") == 1


def test_get_service_scale_handles_garbage(tmp_path):
    """Non-integer junk also falls back to 1 rather than crashing."""
    dm = _make_dependency_manager(tmp_path, "BACKEND_SCALE=junk\n")
    assert dm.get_service_scale("backend") == 1


def test_get_service_scale_parses_integer(tmp_path):
    """Sanity: a normal integer value still parses correctly."""
    dm = _make_dependency_manager(tmp_path, "N8N_SCALE=2\n")
    assert dm.get_service_scale("n8n") == 2
