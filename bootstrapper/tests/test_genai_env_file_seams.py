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
