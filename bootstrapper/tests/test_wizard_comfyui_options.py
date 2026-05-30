"""Tests for _merged_comfyui_options() — the wizard step's option provider."""
from __future__ import annotations

from pathlib import Path

import pytest

from wizard.comfyui_steps import _merged_comfyui_options
from utils.comfyui_library import ComfyUILibraryEntry


def _entry(name: str, **over) -> ComfyUILibraryEntry:
    d = dict(
        name=name, family="X", category="checkpoint", size_gb=1.0,
        url=f"https://e.com/{name}.safetensors", sha256=None,
        target_dir="checkpoints", min_vram_gb=None, cpu_supported=True,
        requires_custom_node=(), popularity=10, source="curated", pulled=False,
    )
    d.update(over)
    return ComfyUILibraryEntry(**d)


def test_catalog_entries_appear_as_options():
    catalog = [_entry("sdxl-base-1.0"), _entry("sd15")]
    options = _merged_comfyui_options(
        catalog=catalog, sidecar=[], pulled_names=set(),
        default_selected=set(),
    )
    names = {o.value for o in options}
    assert {"sdxl-base-1.0", "sd15"} <= names


def test_pulled_flag_renders_badge():
    catalog = [_entry("a")]
    options = _merged_comfyui_options(
        catalog=catalog, sidecar=[], pulled_names={"a"},
        default_selected=set(),
    )
    o = next(o for o in options if o.value == "a")
    # The pulled badge surfaces in hint or in a badges list — check both.
    rendered = (o.hint or "") + " " + " ".join(getattr(o, "badges", ()) or [])
    assert "[pulled]" in rendered


def test_sidecar_entries_in_custom_group():
    catalog = [_entry("a")]
    sidecar = [_entry("custom-x", source="custom")]
    options = _merged_comfyui_options(
        catalog=catalog, sidecar=sidecar, pulled_names=set(),
        default_selected=set(),
    )
    custom_opt = next(o for o in options if o.value == "custom-x")
    assert getattr(custom_opt, "group", None) == "Custom"


def test_default_selected_entries_pre_checked():
    catalog = [_entry("a"), _entry("b")]
    options = _merged_comfyui_options(
        catalog=catalog, sidecar=[], pulled_names=set(),
        default_selected={"a"},
    )
    selected = {o.value for o in options if getattr(o, "checked", False)}
    assert selected == {"a"}


def test_unknown_default_selected_skipped_with_warning(capsys):
    catalog = [_entry("a")]
    _merged_comfyui_options(
        catalog=catalog, sidecar=[], pulled_names=set(),
        default_selected={"nonexistent"},
    )
    captured = capsys.readouterr()
    assert "nonexistent" in (captured.err + captured.out)


def test_requires_custom_node_renders_warning():
    catalog = [_entry("flux", requires_custom_node=("ComfyUI-GGUF",))]
    options = _merged_comfyui_options(
        catalog=catalog, sidecar=[], pulled_names=set(),
        default_selected=set(),
    )
    o = next(o for o in options if o.value == "flux")
    rendered = (o.hint or "") + " " + " ".join(getattr(o, "badges", ()) or [])
    assert "ComfyUI-GGUF" in rendered


def test_sorted_by_popularity():
    catalog = [_entry("low", popularity=1), _entry("hi", popularity=99)]
    options = _merged_comfyui_options(
        catalog=catalog, sidecar=[], pulled_names=set(),
        default_selected=set(),
    )
    values = [o.value for o in options]
    assert values.index("hi") < values.index("low")


def test_min_vram_badge_when_hardware_short():
    catalog = [_entry("big", min_vram_gb=12.0, cpu_supported=False)]
    options = _merged_comfyui_options(
        catalog=catalog, sidecar=[], pulled_names=set(),
        default_selected=set(), gpu_mem_gb=8.0,  # less than min
    )
    o = next(o for o in options if o.value == "big")
    rendered = (o.hint or "") + " " + " ".join(getattr(o, "badges", ()) or [])
    assert "12" in rendered  # the VRAM threshold appears somewhere


def test_cpu_only_badge_when_no_gpu():
    catalog = [_entry("gpu-only", cpu_supported=False)]
    options = _merged_comfyui_options(
        catalog=catalog, sidecar=[], pulled_names=set(),
        default_selected=set(), gpu_mem_gb=None,  # no GPU
    )
    o = next(o for o in options if o.value == "gpu-only")
    rendered = (o.hint or "") + " " + " ".join(getattr(o, "badges", ()) or [])
    assert "GPU" in rendered or "gpu" in rendered.lower()
