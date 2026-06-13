"""GENAI_ENV_FILE must be honored at every seam, not just validation.

Regression guards for the half-wired custom-env-path feature:
- docker compose argv used to hardcode `--env-file=.env` at all four
  construction sites, so compose silently ran against the repo-root .env
  (or failed) while the bootstrapper validated/migrated the custom file.
- KeyGenerator wrote generated secrets to repo-root .env regardless.
- A relative GENAI_ENV_FILE resolved against CWD, which differs between
  the uv launcher (bootstrapper/) and the system-python fallback (root).
"""
from __future__ import annotations

from pathlib import Path

from core.config_parser import ConfigParser
from core.docker_manager import DockerManager
from utils.key_generator import KeyGenerator


def _custom_env(tmp_path, monkeypatch) -> Path:
    env = tmp_path / "custom.env"
    env.write_text("PROJECT_NAME=genai\n", encoding="utf-8")
    monkeypatch.setenv("GENAI_ENV_FILE", str(env))
    return env


def test_build_compose_command_uses_resolved_env_file(tmp_path, monkeypatch):
    env = _custom_env(tmp_path, monkeypatch)
    dm = DockerManager()
    monkeypatch.setattr(dm, "detect_docker_compose_command", lambda: "docker compose")
    cmd = dm._build_compose_command(["up", "-d"])
    assert f"--env-file={env}" in cmd
    assert "--env-file=.env" not in cmd


def test_build_compose_command_default_env_file_is_root_anchored(monkeypatch):
    monkeypatch.delenv("GENAI_ENV_FILE", raising=False)
    dm = DockerManager()
    monkeypatch.setattr(dm, "detect_docker_compose_command", lambda: "docker compose")
    monkeypatch.setattr(dm.config_parser, "env_file_exists", lambda: True)
    cmd = dm._build_compose_command(["ps"])
    expected = f"--env-file={dm.root_dir / '.env'}"
    assert expected in cmd


def test_key_generator_targets_custom_env_file(tmp_path, monkeypatch):
    env = _custom_env(tmp_path, monkeypatch)
    kg = KeyGenerator()
    assert kg.env_file_path == env


def test_relative_genai_env_file_anchors_at_root_dir(tmp_path, monkeypatch):
    (tmp_path / "rel.env").write_text("", encoding="utf-8")
    monkeypatch.setenv("GENAI_ENV_FILE", "rel.env")
    cp = ConfigParser(str(tmp_path))
    assert cp.env_file_path == (tmp_path / "rel.env").resolve()


def test_update_env_file_preserves_backslashes_in_values(tmp_path, monkeypatch):
    """Backslash sequences in env values (legal in JWT/base64 secrets)
    must be written verbatim. A plain re.sub(pattern, replacement) would
    interpret \\1 / \\g<name> in the replacement and corrupt silently —
    the lambda-replacement form in
    SourceOverrideManager.update_env_file is the guard this test pins."""
    from utils.source_override_manager import SourceOverrideManager

    env = tmp_path / ".env"
    env.write_text("SOME_SECRET=old\n", encoding="utf-8")
    monkeypatch.setenv("GENAI_ENV_FILE", str(env))
    mgr = SourceOverrideManager(ConfigParser())
    tricky = r"abc\1def\g<name>\\end"
    assert mgr.update_env_file({"SOME_SECRET": tricky}) is True
    assert f"SOME_SECRET={tricky}\n" in env.read_text(encoding="utf-8")


def test_parse_env_file_quote_and_hash_semantics(tmp_path, monkeypatch):
    """Inline-comment stripping must be quote-aware: a `#` inside quotes
    is data (PASSWORD="ab#cd" was silently read as `ab`), an unquoted
    hash is a comment only when preceded by whitespace."""
    env = tmp_path / ".env"
    env.write_text(
        'QUOTED="ab#cd"\n'
        "SINGLE='x#y'\n"
        "UNQUOTED_HASH=ab#cd\n"
        "WITH_COMMENT=value  # trailing note\n"
        "PLAIN=simple\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("GENAI_ENV_FILE", str(env))
    parsed = ConfigParser().parse_env_file()
    assert parsed["QUOTED"] == "ab#cd"
    assert parsed["SINGLE"] == "x#y"
    assert parsed["UNQUOTED_HASH"] == "ab#cd"
    assert parsed["WITH_COMMENT"] == "value"
    assert parsed["PLAIN"] == "simple"
