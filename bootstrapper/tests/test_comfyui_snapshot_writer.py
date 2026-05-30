"""Tests for the snapshot writer that materializes the init container's
input: a JSON file with the denormalized entries the user picked.
"""
from __future__ import annotations

import json
from pathlib import Path

from utils.comfyui_library import ComfyUILibraryEntry
from utils.comfyui_snapshot_writer import write_snapshot


def _entry(name: str, **over) -> ComfyUILibraryEntry:
    d = dict(
        name=name, family="X", category="checkpoint", size_gb=1.0,
        url=f"https://e.com/{name}.safetensors", sha256=None,
        target_dir="checkpoints", min_vram_gb=None, cpu_supported=True,
        requires_custom_node=(), popularity=0, source="curated", pulled=False,
    )
    d.update(over)
    return ComfyUILibraryEntry(**d)


def test_writes_resolved_entries(tmp_path):
    catalog = [
        _entry("sdxl-base-1.0"),
        _entry("sdxl-vae", category="vae", target_dir="vae",
               url="https://e.com/sdxl-vae.safetensors"),
    ]
    sidecar = [
        _entry("my-lora", category="lora", target_dir="loras",
               url="https://e.com/my-lora.safetensors", source="custom"),
    ]
    out_path = tmp_path / "snapshot.json"
    write_snapshot(
        selection_csv="sdxl-base-1.0,sdxl-vae",
        catalog=catalog,
        sidecar_entries=sidecar,
        out_path=out_path,
    )
    payload = json.loads(out_path.read_text())
    assert payload["schema_version"] == 1
    names = {e["name"] for e in payload["entries"]}
    assert names == {"sdxl-base-1.0", "sdxl-vae", "my-lora"}


def test_unknown_csv_name_skipped_with_warning(tmp_path, capsys):
    catalog = [_entry("sdxl-base-1.0")]
    out_path = tmp_path / "snapshot.json"
    write_snapshot(
        selection_csv="sdxl-base-1.0,nonexistent-foo",
        catalog=catalog,
        sidecar_entries=[],
        out_path=out_path,
    )
    captured = capsys.readouterr()
    assert "nonexistent-foo" in captured.err
    payload = json.loads(out_path.read_text())
    assert len(payload["entries"]) == 1


def test_empty_csv_emits_empty_entries(tmp_path):
    out_path = tmp_path / "snapshot.json"
    write_snapshot(
        selection_csv="",
        catalog=[_entry("a")],
        sidecar_entries=[],
        out_path=out_path,
    )
    payload = json.loads(out_path.read_text())
    assert payload["entries"] == []


def test_denormalized_fields_only(tmp_path):
    """Snapshot must NOT carry wizard-side fields — only what init needs."""
    catalog = [_entry("a")]
    out_path = tmp_path / "snapshot.json"
    write_snapshot(
        selection_csv="a",
        catalog=catalog,
        sidecar_entries=[],
        out_path=out_path,
    )
    entry = json.loads(out_path.read_text())["entries"][0]
    assert set(entry.keys()) == {
        "name", "url", "target_dir", "filename", "size_gb", "sha256"
    }


def test_filename_extracted_from_url(tmp_path):
    catalog = [_entry("x", url="https://huggingface.co/Org/m/resolve/main/weights.safetensors")]
    out_path = tmp_path / "snapshot.json"
    write_snapshot(
        selection_csv="x",
        catalog=catalog,
        sidecar_entries=[],
        out_path=out_path,
    )
    payload = json.loads(out_path.read_text())
    assert payload["entries"][0]["filename"] == "weights.safetensors"


def test_filename_strips_query_string(tmp_path):
    """civitai download URLs often have ?token=... query strings; strip them.

    Note: civitai's opaque IDs produce an extension-less stem (e.g. "12345").
    The init container's download script (T11) must tolerate this; see the
    download_models.sh wget invocation for handling.
    """
    catalog = [_entry("c", url="https://civitai.com/api/download/models/12345?token=abc.def")]
    out_path = tmp_path / "snapshot.json"
    write_snapshot(
        selection_csv="c",
        catalog=catalog,
        sidecar_entries=[],
        out_path=out_path,
    )
    payload = json.loads(out_path.read_text())
    fn = payload["entries"][0]["filename"]
    assert fn == "12345"  # extension-less, query stripped


def test_filename_falls_back_to_model_bin(tmp_path):
    """When the URL has no path component (bare host), fall back to model.bin."""
    catalog = [_entry("x", url="https://example.com")]
    out_path = tmp_path / "snap.json"
    write_snapshot(
        selection_csv="x",
        catalog=catalog,
        sidecar_entries=[],
        out_path=out_path,
    )
    assert json.loads(out_path.read_text())["entries"][0]["filename"] == "model.bin"


def test_creates_parent_dir(tmp_path):
    """When out_path's parent doesn't exist, writer creates it."""
    out_path = tmp_path / "nested" / "deep" / "snap.json"
    write_snapshot(
        selection_csv="",
        catalog=[],
        sidecar_entries=[],
        out_path=out_path,
    )
    assert out_path.is_file()


def test_sidecar_always_included(tmp_path):
    """Sidecar entries land in the snapshot regardless of the CSV."""
    sidecar = [_entry("custom-only", source="custom")]
    out_path = tmp_path / "snap.json"
    write_snapshot(
        selection_csv="",
        catalog=[],
        sidecar_entries=sidecar,
        out_path=out_path,
    )
    payload = json.loads(out_path.read_text())
    names = {e["name"] for e in payload["entries"]}
    assert "custom-only" in names
