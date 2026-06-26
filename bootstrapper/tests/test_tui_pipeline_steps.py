"""Regression guard for the TUI startup pipeline steps list.

Fix 1 (final review): the Textual TUI pipeline in wizard_screen.py must include
``generate_comfyui_manifest`` AFTER ``generate_litellm_configuration`` and BEFORE
the ``docker compose up`` call.  Without this, a fresh interactive install never
writes ``volumes/comfyui/active-models.tsv``, so comfyui-init downloads nothing
regardless of the user's wizard selection.

This test parses wizard_screen.py with the ``ast`` module to locate the ``steps``
list and verify:

  1. Both ``generate_litellm_configuration`` and ``generate_comfyui_manifest``
     appear as callable references in the steps list.
  2. ``generate_comfyui_manifest`` comes AFTER ``generate_litellm_configuration``
     (mirrors the ordering in start.py's linear path).
  3. Both entries appear BEFORE the ``_run_compose`` call that starts containers
     (i.e., both are pre-compose pipeline steps).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WIZARD_SCREEN = REPO_ROOT / "bootstrapper" / "ui" / "textual" / "screens" / "wizard_screen.py"


def _extract_steps_and_compose_region(src: str) -> tuple[list[str], int]:
    """Return (list_of_step_labels_and_attrs, line_of_first_run_compose).

    We scan for the ``steps = [`` assignment in wizard_screen.py and collect
    every string literal label and every attribute reference (e.g.
    ``starter.generate_litellm_configuration``) mentioned inside that list.
    We also find the line of the first ``_run_compose(["up"`` call so we can
    confirm the steps list precedes compose-up.
    """
    # Locate the `steps = [` assignment via AST
    tree = ast.parse(src)
    steps_node: ast.List | None = None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "steps"
            and isinstance(node.value, ast.List)
        ):
            steps_node = node.value
            break

    assert steps_node is not None, "Could not find `steps = [...]` in wizard_screen.py"

    # Collect all string constants and attribute names used inside the list
    tokens: list[str] = []
    for elt in ast.walk(steps_node):
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
            tokens.append(elt.value)
        if isinstance(elt, ast.Attribute):
            tokens.append(elt.attr)  # e.g. 'generate_litellm_configuration'

    # Find line of first `_run_compose(["up"` — heuristic via regex on source
    compose_up_line: int = -1
    for lineno, line in enumerate(src.splitlines(), start=1):
        if '_run_compose(["up"' in line or "_run_compose(['up'" in line:
            compose_up_line = lineno
            break

    return tokens, compose_up_line


def _step_index(tokens: list[str], attr: str) -> int:
    """Return the first index in *tokens* where *attr* appears, or -1."""
    try:
        return tokens.index(attr)
    except ValueError:
        return -1


def test_tui_steps_include_generate_litellm_configuration():
    """generate_litellm_configuration must be in the TUI pipeline steps."""
    src = WIZARD_SCREEN.read_text()
    tokens, _ = _extract_steps_and_compose_region(src)
    assert "generate_litellm_configuration" in tokens, (
        "wizard_screen.py steps list is missing 'generate_litellm_configuration'. "
        "The TUI pipeline must call starter.generate_litellm_configuration before compose-up."
    )


def test_tui_steps_include_generate_comfyui_manifest():
    """generate_comfyui_manifest must be in the TUI pipeline steps (Fix 1)."""
    src = WIZARD_SCREEN.read_text()
    tokens, _ = _extract_steps_and_compose_region(src)
    assert "generate_comfyui_manifest" in tokens, (
        "wizard_screen.py steps list is MISSING 'generate_comfyui_manifest'. "
        "Without this step the TUI path never writes volumes/comfyui/active-models.tsv, "
        "so comfyui-init silently skips all model downloads regardless of wizard selection."
    )


def test_tui_steps_comfyui_manifest_after_litellm():
    """generate_comfyui_manifest must appear AFTER generate_litellm_configuration."""
    src = WIZARD_SCREEN.read_text()
    tokens, _ = _extract_steps_and_compose_region(src)
    litellm_idx = _step_index(tokens, "generate_litellm_configuration")
    comfyui_idx = _step_index(tokens, "generate_comfyui_manifest")
    assert litellm_idx != -1, "generate_litellm_configuration not found in steps"
    assert comfyui_idx != -1, "generate_comfyui_manifest not found in steps"
    assert comfyui_idx > litellm_idx, (
        f"generate_comfyui_manifest (token index {comfyui_idx}) must come AFTER "
        f"generate_litellm_configuration (token index {litellm_idx}) to mirror "
        "the ordering in start.py's linear path."
    )


def test_tui_steps_both_precede_compose_up():
    """Both generator steps must appear in the steps list, which precedes _run_compose up."""
    src = WIZARD_SCREEN.read_text()
    tokens, compose_up_line = _extract_steps_and_compose_region(src)

    assert compose_up_line != -1, (
        "Could not locate `_run_compose([\"up\"` in wizard_screen.py — "
        "update the heuristic in this test if the compose call changed."
    )

    # Confirm steps list node ends before the compose-up line by checking
    # that the steps assignment (which contains our tokens) is found and
    # that the _run_compose line follows it in source order.
    tree = ast.parse(src)
    steps_end_line: int = -1
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "steps"
            and isinstance(node.value, ast.List)
        ):
            steps_end_line = node.end_lineno  # type: ignore[attr-defined]
            break

    assert steps_end_line != -1, "steps assignment not found"
    assert steps_end_line < compose_up_line, (
        f"steps list ends at line {steps_end_line} but _run_compose([\"up\"] "
        f"is at line {compose_up_line} — steps list must precede compose-up."
    )
    # Confirm both attrs are present
    assert "generate_litellm_configuration" in tokens
    assert "generate_comfyui_manifest" in tokens
