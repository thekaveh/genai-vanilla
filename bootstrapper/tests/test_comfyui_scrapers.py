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
