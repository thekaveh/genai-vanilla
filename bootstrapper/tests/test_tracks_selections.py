"""Tests for the _selections_to_args track-disable synthesis pass.

When the user picks a track, every source-configurable service that is
out-of-track AND not explicitly overridden must end up with its
``*_SOURCE=disabled`` written to .env — even though its wizard step
was skipped and the selections dict never carried a value for it.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from ui.textual.integration import _selections_to_args, PICKER_STEP_TITLE


def _svc(key: str, display_name: str, options=("container", "disabled")):
    return SimpleNamespace(
        key=key,
        display_name=display_name,
        options=list(options),
        current_value="container",
    )


def test_off_track_service_force_disabled():
    """gen-ai-rag excludes comfyui → COMFYUI_SOURCE force-written as
    disabled in the source_args dict."""
    services_info = [
        _svc("comfyui", "ComfyUI"),
        _svc("weaviate", "Weaviate"),
    ]
    selections = {
        PICKER_STEP_TITLE: "gen-ai-rag",
        # User didn't visit the comfyui step (it was skipped).
        # User visited the weaviate step:
        "Weaviate  ·  source": "container",
    }
    source_args, _ = _selections_to_args(
        selections, services_info, current_base_port=63000, env_vars={},
    )
    assert source_args.get("comfyui_source") == "disabled", (
        f"comfyui must be force-disabled (off-track); got {source_args!r}"
    )
    assert source_args.get("weaviate_source") == "container"


def test_in_track_service_not_force_disabled():
    """weaviate is in gen-ai-rag → no synthesis. User's actual selection
    (or absence) governs the value."""
    services_info = [_svc("weaviate", "Weaviate")]
    selections = {
        PICKER_STEP_TITLE: "gen-ai-rag",
        "Weaviate  ·  source": "localhost",
    }
    source_args, _ = _selections_to_args(
        selections, services_info, current_base_port=63000, env_vars={},
    )
    assert source_args["weaviate_source"] == "localhost"


def test_all_track_no_synthesis():
    """'all' track → no service is force-disabled."""
    services_info = [_svc("comfyui", "ComfyUI"), _svc("weaviate", "Weaviate")]
    selections = {
        PICKER_STEP_TITLE: "all",
        # Neither step visited:
    }
    source_args, _ = _selections_to_args(
        selections, services_info, current_base_port=63000, env_vars={},
    )
    assert "comfyui_source" not in source_args
    assert "weaviate_source" not in source_args


def test_always_on_service_not_force_disabled():
    """LLM Engine is always-on; even if its step value is absent we
    must NOT force-write disabled."""
    services_info = [_svc("llm-provider", "LLM Engine",
                          options=("ollama-container-gpu", "none"))]
    selections = {
        PICKER_STEP_TITLE: "gen-ai-rag",
        # No "LLM Engine  ·  source" key — user skipped past it.
    }
    source_args, _ = _selections_to_args(
        selections, services_info, current_base_port=63000, env_vars={},
    )
    assert "llm_provider_source" not in source_args, (
        "Always-on LLM Engine must never get force-written; "
        f"got {source_args!r}"
    )


def test_no_picker_selection_no_synthesis():
    """If the picker step itself was skipped (e.g. no track), nothing
    is force-disabled. User's explicit selection on a service step is
    still passed through."""
    services_info = [_svc("comfyui", "ComfyUI")]
    selections = {"ComfyUI  ·  source": "container"}  # no picker, but service step visited
    source_args, _ = _selections_to_args(
        selections, services_info, current_base_port=63000, env_vars={},
    )
    assert source_args.get("comfyui_source") == "container", (
        "Service-step value must be preserved when no picker selection"
    )
    assert len(source_args) == 1, (
        f"No extra synthesis writes expected; got {source_args!r}"
    )
