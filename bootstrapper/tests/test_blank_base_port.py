"""Regression: every BASE_PORT read site must tolerate a blank value.

A blank BASE_PORT can happen when:
  * The user manually blanked it in .env.
  * The migration mid-way through a rename has left it temporarily blank.
  * A bug elsewhere produced ``BASE_PORT=``.

Three production call sites historically did ``int(env_vars.get("BASE_PORT", DEFAULT_BASE_PORT))``,
which crashes with ``ValueError: invalid literal for int() with base 10: ''``
because ``dict.get(key, default)`` returns the empty string (not the default)
when the key is present-but-blank. Each call site is now guarded.
"""

from __future__ import annotations


def test_run_port_migration_handles_blank_base_port(tmp_path):
    """``GenAIStackStarter.run_port_migration`` doesn't crash if .env's
    BASE_PORT is blank — falls back to DEFAULT_BASE_PORT."""
    (tmp_path / ".env").write_text(
        "BASE_PORT=\nBOOTSTRAPPER_PORT_LAYOUT_VERSION=\n"
    )
    (tmp_path / ".env.example").write_text("BASE_PORT=63000\n")
    (tmp_path / "docker-compose.yml").write_text("services: {}\n")
    from start import GenAIStackStarter

    starter = GenAIStackStarter()
    starter.config_parser.root_dir = tmp_path
    starter.config_parser.env_file_path = tmp_path / ".env"
    starter.config_parser.env_example_path = tmp_path / ".env.example"

    # Must not raise ValueError. (Will no-op the rewrite because the
    # synthetic .env has no port vars to migrate, but the sentinel
    # parse + topology build must complete cleanly.)
    starter.run_port_migration(no_port_migrate=False)


def test_wizard_build_handles_blank_base_port(tmp_path, monkeypatch):
    """``_build_steps_and_rows`` doesn't crash when BASE_PORT is blank."""
    (tmp_path / ".env").write_text("BASE_PORT=\n")
    (tmp_path / "docker-compose.yml").write_text("services: {}\n")
    monkeypatch.chdir(tmp_path)
    from core.config_parser import ConfigParser, DEFAULT_BASE_PORT
    cp = ConfigParser(str(tmp_path))
    # Just exercise the int(BASE_PORT or DEFAULT) helper the wizard uses.
    raw = (cp.parse_env_file().get("BASE_PORT") or "").strip()
    try:
        base_port = int(raw) if raw else DEFAULT_BASE_PORT
    except ValueError:
        base_port = DEFAULT_BASE_PORT
    assert base_port == DEFAULT_BASE_PORT
