"""Tests for list_catalog() — merge, cache, partial-failure, fallback."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from utils.comfyui_library import (
    list_catalog,
    ComfyUILibraryEntry,
    CACHE_TTL_SECONDS,
)


def _fake_entry(name: str, source: str) -> ComfyUILibraryEntry:
    return ComfyUILibraryEntry(
        name=name, family="X", category="checkpoint", size_gb=1.0,
        url=f"https://e.com/{name}.safetensors", sha256=None,
        target_dir="checkpoints", min_vram_gb=None, cpu_supported=True,
        requires_custom_node=(), popularity=0, source=source, pulled=False,
    )


def test_list_catalog_merges_hf_civitai_curated(tmp_path, monkeypatch):
    monkeypatch.setattr("utils.comfyui_library._CACHE_DIR", tmp_path)
    with patch("utils.comfyui_library.list_huggingface_models") as mock_hf, \
         patch("utils.comfyui_library.list_civitai_loras") as mock_civ:
        mock_hf.return_value = [_fake_entry("hf-a", "huggingface")]
        mock_civ.return_value = [_fake_entry("civ-b", "civitai")]
        entries = list_catalog(force_refresh=True)

    names = {e.name for e in entries}
    assert "hf-a" in names
    assert "civ-b" in names
    # curated entries always merged in.
    assert any(e.source == "curated" for e in entries)


def test_cache_hits_within_ttl(tmp_path, monkeypatch):
    monkeypatch.setattr("utils.comfyui_library._CACHE_DIR", tmp_path)
    with patch("utils.comfyui_library.list_huggingface_models") as mock_hf, \
         patch("utils.comfyui_library.list_civitai_loras") as mock_civ:
        mock_hf.return_value = [_fake_entry("hf-a", "huggingface")]
        mock_civ.return_value = []
        list_catalog(force_refresh=True)
        assert mock_hf.call_count == 1
        list_catalog()  # within TTL, no re-scrape
        assert mock_hf.call_count == 1


def test_cache_miss_after_ttl(tmp_path, monkeypatch):
    monkeypatch.setattr("utils.comfyui_library._CACHE_DIR", tmp_path)
    cache_file = tmp_path / "comfyui_catalog.json"
    cache_file.write_text(json.dumps({
        "schema_version": 1,
        "fetched_at": "2020-01-01T00:00:00Z",  # ancient
        "ttl_seconds": CACHE_TTL_SECONDS,
        "huggingface_status": "ok",
        "civitai_status": "ok",
        "entries": [],
    }))
    with patch("utils.comfyui_library.list_huggingface_models") as mock_hf, \
         patch("utils.comfyui_library.list_civitai_loras") as mock_civ:
        mock_hf.return_value = []
        mock_civ.return_value = []
        list_catalog()
        assert mock_hf.called


def test_force_refresh_bypasses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("utils.comfyui_library._CACHE_DIR", tmp_path)
    cache_file = tmp_path / "comfyui_catalog.json"
    cache_file.write_text(json.dumps({
        "schema_version": 1,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ttl_seconds": CACHE_TTL_SECONDS,
        "huggingface_status": "ok",
        "civitai_status": "ok",
        "entries": [],
    }))
    with patch("utils.comfyui_library.list_huggingface_models") as mock_hf, \
         patch("utils.comfyui_library.list_civitai_loras") as mock_civ:
        mock_hf.return_value = []
        mock_civ.return_value = []
        list_catalog(force_refresh=True)
        assert mock_hf.called


def test_partial_failure_civitai_down(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("utils.comfyui_library._CACHE_DIR", tmp_path)
    with patch("utils.comfyui_library.list_huggingface_models") as mock_hf, \
         patch("utils.comfyui_library.list_civitai_loras",
               side_effect=ConnectionError("civitai 503")):
        mock_hf.return_value = [_fake_entry("hf-x", "huggingface")]
        entries = list_catalog(force_refresh=True)

    sources = {e.source for e in entries}
    assert "huggingface" in sources
    assert "curated" in sources  # curated always in
    cache = json.loads((tmp_path / "comfyui_catalog.json").read_text())
    assert cache["civitai_status"] == "error"
    assert cache["huggingface_status"] == "ok"


def test_full_failure_no_cache_loads_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr("utils.comfyui_library._CACHE_DIR", tmp_path)
    with patch("utils.comfyui_library.list_huggingface_models",
               side_effect=ConnectionError("hf 503")), \
         patch("utils.comfyui_library.list_civitai_loras",
               side_effect=ConnectionError("civ 503")):
        entries = list_catalog(force_refresh=True)
    assert any(e.source == "fallback" for e in entries)


def test_dedupe_curated_wins_over_huggingface(tmp_path, monkeypatch):
    """Name collision: curated must win — its metadata is hand-vetted."""
    monkeypatch.setattr("utils.comfyui_library._CACHE_DIR", tmp_path)
    with patch("utils.comfyui_library.list_huggingface_models") as mock_hf, \
         patch("utils.comfyui_library.list_civitai_loras") as mock_civ, \
         patch("utils.comfyui_library.list_curated") as mock_cur:
        mock_hf.return_value = [_fake_entry("clash", "huggingface")]
        mock_civ.return_value = []
        mock_cur.return_value = [_fake_entry("clash", "curated")]
        entries = list_catalog(force_refresh=True)
    clash = [e for e in entries if e.name == "clash"]
    assert len(clash) == 1
    assert clash[0].source == "curated"
