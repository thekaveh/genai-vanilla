"""Tests for HF + civitai scrapers in comfyui_library.

Uses fixture JSON committed at bootstrapper/tests/fixtures/comfyui/ so
tests are hermetic. The live integration test (skip-if-no-network) lives
in test_live_comfyui_catalog.py (added later, separate task).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from utils.comfyui_library import (
    ComfyUILibraryEntry,
    _parse_hf_response,
    _parse_civitai_response,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "comfyui"


def _load(name: str) -> list[dict]:
    return json.loads((FIXTURE_DIR / name).read_text())


def test_parse_hf_text2image():
    raw = _load("hf_text2image_search.json")
    entries = _parse_hf_response(raw, category="checkpoint")
    assert len(entries) >= 5, "fixture should have at least 5 checkpoint entries"
    for e in entries:
        assert isinstance(e, ComfyUILibraryEntry)
        assert e.category == "checkpoint"
        assert e.source == "huggingface"
        assert e.url.startswith("https://huggingface.co/")
        assert e.url.endswith((".safetensors", ".ckpt", ".bin", ".gguf"))
        assert e.target_dir == "checkpoints"


def test_parse_hf_text2video():
    raw = _load("hf_text2video_search.json")
    entries = _parse_hf_response(raw, category="video_model")
    assert len(entries) >= 3
    for e in entries:
        assert e.category == "video_model"
        assert e.target_dir == "checkpoints"  # upstream convention


def test_parse_hf_text2speech():
    raw = _load("hf_text2speech_search.json")
    entries = _parse_hf_response(raw, category="voice_model")
    for e in entries:
        assert e.category == "voice_model"
        assert e.target_dir == "voice"


def test_parse_hf_text2mesh():
    raw = _load("hf_text2mesh_search.json")
    entries = _parse_hf_response(raw, category="mesh_model")
    for e in entries:
        assert e.category == "mesh_model"
    # All 3D models today require a custom node — at least one entry
    # surfaces the badge so the wizard renders it.
    assert any(e.requires_custom_node for e in entries), \
        "at least one mesh_model fixture should require a custom node"


def test_parse_civitai_lora():
    raw = _load("civitai_models.json")
    entries = _parse_civitai_response(raw, category="lora")
    for e in entries:
        assert e.category == "lora"
        assert e.source == "civitai"
        assert e.target_dir == "loras"


def test_parse_hf_skips_malformed_entry():
    """A fixture with a missing siblings array shouldn't crash; skips entry."""
    raw = [{"id": "broken/model", "downloads": 100}]  # no siblings array
    entries = _parse_hf_response(raw, category="checkpoint")
    assert entries == []


def test_parse_hf_skips_entry_with_no_safetensors_or_compatible():
    """Models with only .ipynb / .txt files aren't useful — skip."""
    raw = [{
        "id": "fake/onlytext",
        "downloads": 1000,
        "siblings": [{"rfilename": "README.md"}, {"rfilename": "config.json"}],
    }]
    entries = _parse_hf_response(raw, category="checkpoint")
    assert entries == []


def test_parse_hf_unknown_category_raises():
    """Defense: parser must validate the category argument."""
    with pytest.raises(ValueError):
        _parse_hf_response([], category="not-a-category")


def test_parse_civitai_unknown_category_raises():
    with pytest.raises(ValueError):
        _parse_civitai_response({"items": []}, category="not-a-category")


# ─── Live-API request shape ───────────────────────────────────────────
# HF's /api/models endpoint returns lightweight model cards WITHOUT a
# ``siblings[]`` array unless the request asks for full metadata via
# ``full=true``. Without siblings, ``_pick_primary_file`` returns None
# for every entry and the entire HF tier of the catalog silently
# collapses to zero entries — which is exactly what was happening in
# production until the post-PR-#20 wizard screenshot exposed it.
# This test pins the request shape so the regression class can't recur.

def test_list_huggingface_models_requests_full_metadata(monkeypatch):
    """list_huggingface_models() must pass ``full=true`` (or boolean True)
    on every HF API call. Without it, the response carries no siblings
    array and ``_pick_primary_file`` drops every entry — silently."""
    from utils import comfyui_library

    captured_params: list[dict] = []

    class _FakeResp:
        def __init__(self) -> None:
            self._json: list = []

        def raise_for_status(self) -> None:
            return None

        def json(self) -> list:
            return self._json

    def _fake_get(_url, params=None, timeout=None):  # noqa: ARG001
        captured_params.append(dict(params or {}))
        return _FakeResp()

    monkeypatch.setattr(comfyui_library._requests, "get", _fake_get)
    comfyui_library.list_huggingface_models()

    assert captured_params, "list_huggingface_models made zero HTTP calls"
    for params in captured_params:
        full = params.get("full")
        assert full in (True, "true", "True"), (
            f"HF request missing `full=true`: {params!r}. "
            f"Without it the siblings[] array is empty and _pick_primary_file "
            f"drops every entry."
        )
