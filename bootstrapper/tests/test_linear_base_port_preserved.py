"""Linear-flow port handling must preserve a previously configured BASE_PORT.

Regression guard: handle_port_configuration(None) used to fall straight to
DEFAULT_BASE_PORT, so any `--no-tui` / non-TTY run silently rewrote every
*_PORT in .env back to the 63000 layout for users who had configured a
custom base port (and left BASE_PORT itself inconsistent with the rewritten
ports). The TUI path already read BASE_PORT from .env; the linear path now
mirrors it.
"""
from __future__ import annotations

from core.config_parser import DEFAULT_BASE_PORT
from start import GenAIStackStarter


def _starter_with_env(tmp_path, monkeypatch, env_text: str):
    env = tmp_path / ".env"
    env.write_text(env_text, encoding="utf-8")
    starter = GenAIStackStarter()
    starter.config_parser.env_file_path = env
    monkeypatch.setattr(starter.port_manager, "get_port_conflicts", lambda bp: {})
    captured = {}

    def _capture(bp):
        captured["base_port"] = bp
        return True

    monkeypatch.setattr(starter.port_manager, "update_env_ports", _capture)
    return starter, captured


def test_none_base_port_preserves_env_value(tmp_path, monkeypatch):
    starter, captured = _starter_with_env(tmp_path, monkeypatch, "BASE_PORT=64000\n")
    assert starter.handle_port_configuration(None) is True
    assert captured["base_port"] == 64000


def test_none_base_port_falls_back_to_default_when_blank(tmp_path, monkeypatch):
    starter, captured = _starter_with_env(tmp_path, monkeypatch, "BASE_PORT=\n")
    assert starter.handle_port_configuration(None) is True
    assert captured["base_port"] == DEFAULT_BASE_PORT


def test_explicit_flag_still_wins(tmp_path, monkeypatch):
    starter, captured = _starter_with_env(tmp_path, monkeypatch, "BASE_PORT=64000\n")
    assert starter.handle_port_configuration(65000) is True
    assert captured["base_port"] == 65000
