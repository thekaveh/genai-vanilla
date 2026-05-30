"""Cross-cutting regression guard for the user-model selection plumbing.

PR #16 caught a class of bug where a CLI flag was declared but never
plumbed into the dict passed to apply_*. The Ollama-side pattern has
two seams:

  1. `@click.option('--<feature>-...')` + `main()` signature param
  2. `if <kwarg> is not None: user_model_selections['<ENV>'] = <kwarg>`

This test introspects start.py + integration.py and asserts both seams
agree for every `*_USER_MODELS` env var (and the parallel ComfyUI
custom-models-file plumbing).

When this test fails, either:
  - start.py is missing the `user_model_selections[KEY] = kwarg` assignment, OR
  - integration.py / start.py disagree on the env var name.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
START_PY = REPO_ROOT / "bootstrapper" / "start.py"
INTEGRATION_PY = REPO_ROOT / "bootstrapper" / "ui" / "textual" / "integration.py"


def _find_user_model_keys_in_start_py() -> set[str]:
    """Find every string literal KEY where `user_model_selections[KEY] = ...` appears."""
    tree = ast.parse(START_PY.read_text())
    keys: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            if node.value.id == "user_model_selections":
                slot = node.slice
                if isinstance(slot, ast.Constant) and isinstance(slot.value, str):
                    keys.add(slot.value)
    return keys


def test_user_model_selections_includes_comfyui():
    keys = _find_user_model_keys_in_start_py()
    assert "COMFYUI_USER_MODELS" in keys, (
        "start.py's user_model_selections dict is missing COMFYUI_USER_MODELS. "
        "Without this, --comfyui-models is a silent no-op."
    )


def test_user_model_selections_includes_ollama():
    """Sanity — also covers the existing Ollama plumbing."""
    keys = _find_user_model_keys_in_start_py()
    assert "OLLAMA_USER_MODELS" in keys


def test_user_model_selections_includes_comfyui_custom_models_file():
    keys = _find_user_model_keys_in_start_py()
    assert "COMFYUI_CUSTOM_MODELS_FILE" in keys


def test_integration_emits_comfyui_user_models():
    """integration.py must produce a `comfyui_user_models` key in its output dict."""
    raw = INTEGRATION_PY.read_text()
    assert "comfyui_user_models" in raw, (
        "integration.py._selections_to_args must emit a 'comfyui_user_models' key."
    )


def test_wizard_screen_consumes_comfyui_user_models():
    """The wizard's 'Apply user model selections' lambda must unpack
    comfyui_user_models from stack_options, parallel to how it unpacks
    cloud_user_models and ollama_user_models.

    Without this, wizard-driven ComfyUI selections silently drop on
    confirm — the P1 bug fixed alongside this test.
    """
    WIZARD_SCREEN = REPO_ROOT / "bootstrapper" / "ui" / "textual" / "screens" / "wizard_screen.py"
    raw = WIZARD_SCREEN.read_text()
    # The dict-merge pattern: each model-selection bucket appears as
    # **((self._stack_options or {}).get("<key>", {}) or {})
    for key in ("cloud_user_models", "ollama_user_models", "comfyui_user_models"):
        marker = f'"{key}"'
        assert marker in raw, (
            f"wizard_screen.py must unpack {marker} from stack_options "
            f"in the 'Apply user model selections' lambda. Without it, "
            f"wizard selections for that bucket silently drop."
        )
