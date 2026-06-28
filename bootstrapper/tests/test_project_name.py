"""Project-name override (--project / -p + PROJECT_NAME in .env + wizard step).

The container-family namespace is set by `docker compose -p <PROJECT_NAME>`.
start.sh and stop.sh must agree on it so stop tears down exactly what start
launched, and a submodule consumer must be able to isolate from a base Atlas
stack by setting their own name. These tests pin:

  * normalize_project_name() validation (Docker Compose project-name rules),
  * the persist→read loop (writing PROJECT_NAME to .env is what get_project_name
    — and therefore every `-p` and a later bare ./stop.sh — reads back),
  * the wizard's "Project name" step (default from .env, normalized on change,
    no-op when unchanged).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

# Repo root (parent of bootstrapper/) — so the wizard test finds services/
# regardless of the pytest working directory (CI runs from bootstrapper/).
REPO_ROOT = Path(__file__).resolve().parent.parent.parent

from core.config_parser import (
    ConfigParser,
    DEFAULT_PROJECT_NAME,
    normalize_project_name,
)


# ── normalize_project_name ───────────────────────────────────────────────────

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("atlas", "atlas"),
        ("MyShowcase", "myshowcase"),   # lower-cased like Docker Compose
        ("rag-showcase", "rag-showcase"),
        ("proj_1", "proj_1"),
        ("  Foo  ", "foo"),             # trimmed
    ],
)
def test_normalize_valid(raw, expected):
    assert normalize_project_name(raw) == expected


@pytest.mark.parametrize("bad", ["", "   ", "bad name", "has.dot", "-leading", "a/b", "x*y"])
def test_normalize_rejects_invalid(bad):
    with pytest.raises(ValueError):
        normalize_project_name(bad)


def test_default_project_name_constant():
    assert DEFAULT_PROJECT_NAME == "atlas"


# ── persist → read loop (the start/stop agreement mechanism) ─────────────────

def _cp(tmp_path, body: str) -> ConfigParser:
    env = tmp_path / ".env"
    env.write_text(body, encoding="utf-8")
    cp = ConfigParser(str(tmp_path))
    cp.env_file_path = env
    return cp


def test_get_project_name_reads_env(tmp_path):
    cp = _cp(tmp_path, "PROJECT_NAME=myshowcase\n")
    assert cp.get_project_name() == "myshowcase"


def test_get_project_name_defaults_to_atlas(tmp_path):
    cp = _cp(tmp_path, "BASE_PORT=63000\n")  # no PROJECT_NAME
    assert cp.get_project_name() == "atlas"


def test_persist_then_read_round_trip(tmp_path):
    """Writing PROJECT_NAME to .env (as --project does) is what every compose
    -p and a later bare ./stop.sh read back — this is the agreement guarantee."""
    from utils.source_override_manager import SourceOverrideManager

    cp = _cp(tmp_path, "PROJECT_NAME=atlas\n")
    assert cp.get_project_name() == "atlas"
    SourceOverrideManager(cp).update_env_file({"PROJECT_NAME": "myshowcase"})
    # A FRESH ConfigParser reading the same .env (mimicking the next process —
    # e.g. a later bare ./stop.sh) sees the persisted name.
    assert ConfigParser(str(tmp_path)).get_project_name() == "myshowcase"
    assert cp.get_project_name() == "myshowcase"


# ── stop.py override ─────────────────────────────────────────────────────────

def test_stop_show_configuration_info_honors_override(tmp_path, monkeypatch):
    import stop as stop_module

    monkeypatch.setenv("ATLAS_ENV_FILE", str(tmp_path / ".env"))
    (tmp_path / ".env").write_text("PROJECT_NAME=atlas\n", encoding="utf-8")
    stopper = stop_module.AtlasStopper()
    # No override → the .env value; override → wins.
    assert stopper.show_configuration_info(False, False) == "atlas"
    assert stopper.show_configuration_info(False, False,
                                           project_name_override="myshowcase") == "myshowcase"


# ── wizard "Project name" step ───────────────────────────────────────────────

def test_wizard_project_name_step_and_mapping(tmp_path, monkeypatch):
    monkeypatch.setenv("ATLAS_ENV_FILE", str(tmp_path / ".env"))
    (tmp_path / ".env").write_text("PROJECT_NAME=myshowcase\nBASE_PORT=63000\n", encoding="utf-8")

    from utils.hosts_manager import HostsManager
    from ui.textual.integration import _build_steps_and_rows, _selections_to_args

    # Repo root so service discovery finds services/ (CI runs from bootstrapper/);
    # ATLAS_ENV_FILE (set above) still points parse_env_file at the temp .env.
    cp = ConfigParser(str(REPO_ROOT))
    steps, _rows, info, cbp, _state, _cs = _build_steps_and_rows(cp, HostsManager())
    proj_steps = [s for s in steps if "Project name" in s.title]
    assert len(proj_steps) == 1, "expected exactly one Project name step"
    step = proj_steps[0]
    # Default pre-fills from the current .env value (not the hardcoded default).
    assert step.default_value == "myshowcase"
    assert step.kind == "text"

    env_vars = cp.parse_env_file()
    title = step.title
    # Changing the name → normalized value in stack_options.
    _, opts_changed = _selections_to_args({title: "NewName"}, info, cbp, env_vars=env_vars)
    assert opts_changed.get("project_name") == "newname"
    # Re-confirming the SAME name → no-op (None), so no spurious .env write.
    _, opts_same = _selections_to_args({title: "myshowcase"}, info, cbp, env_vars=env_vars)
    assert opts_same.get("project_name") is None
    # An invalid entry → no-op (None) rather than corrupting PROJECT_NAME.
    _, opts_bad = _selections_to_args({title: "bad name!"}, info, cbp, env_vars=env_vars)
    assert opts_bad.get("project_name") is None
