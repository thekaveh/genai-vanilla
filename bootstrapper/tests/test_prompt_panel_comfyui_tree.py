"""Panel-side variant-tree behavior for ComfyUI parents.

Three panel-level concerns covered:
  1. _rebuild_visible skips the synthetic _LATEST_TAG leaf for
     ComfyUI parents (the leaf would have no meaning — every variant
     in opt.sizes is already a full catalog name).
  2. _leaf_render_data returns the per-leaf (label, badges) from
     opt.leaf_details rather than the Ollama parent:tag format.
  3. _row_is_checked_comfyui aggregates parent-checked state over
     opt.sizes membership in _checked_values (the synthetic parent
     value doesn't appear in the selection set so the Ollama
     prefix-match never matches).
"""
from __future__ import annotations

from ui.textual.widgets.prompt_panel import (
    PromptOption,
    PromptPanel,
    _VisibleRow,
    _row_is_checked_comfyui,
)


class _PanelStub:
    """Minimal stand-in exposing the state ``_rebuild_visible`` reads."""
    _rebuild_visible = PromptPanel._rebuild_visible

    def __init__(self, *, options, expanded=None):
        class _Step: pass
        self._step = _Step()
        self._step.options = options
        self._filter_tag = "all"
        self._search_query = ""
        self._expanded = set(expanded or [])
        self._variant_cache = {}
        self._variant_loading = set()


def _comfyui_parent():
    """A 3-variant ComfyUI family parent option."""
    return PromptOption(
        value="family:TRELLIS",
        label="TRELLIS  ·  3 variants",
        hint="",
        badges=["3d", "[family: TRELLIS] (3 variants)"],
        sizes=(
            "microsoft--TRELLIS-image-large",
            "microsoft--TRELLIS.2-4B",
            "gqk--TRELLIS-image-large-fork",
        ),
        leaf_details={
            "microsoft--TRELLIS-image-large":
                ("microsoft--TRELLIS-image-large",
                 ("3d", "mesh_model", "5.20GB")),
            "microsoft--TRELLIS.2-4B":
                ("microsoft--TRELLIS.2-4B",
                 ("3d", "mesh_model", "3.10GB")),
            "gqk--TRELLIS-image-large-fork":
                ("gqk--TRELLIS-image-large-fork",
                 ("3d", "mesh_model", "5.20GB")),
        },
    )


def _ollama_parent():
    """A 2-size Ollama-style parent (no leaf_details) for control."""
    return PromptOption(
        value="qwen3",
        label="qwen3",
        hint="",
        badges=["embedding"],
        sizes=("8b", "14b"),
    )


def test_comfyui_parent_expansion_skips_synthetic_latest_leaf():
    """The Ollama tree code prepends a synthetic ``latest`` leaf at
    the top of every expansion. ComfyUI parents must SKIP that — the
    variants in opt.sizes are already full catalog names, and no
    "model-maker default" concept exists for ComfyUI."""
    parent = _comfyui_parent()
    stub = _PanelStub(options=[parent], expanded={"family:TRELLIS"})
    rows = stub._rebuild_visible()
    leaf_rows = [r for r in rows if r.kind == "leaf"]
    leaf_tags = [r.variant for r in leaf_rows]
    assert "latest" not in leaf_tags, (
        "ComfyUI parent must not emit a synthetic 'latest' leaf — "
        "every leaf is a full catalog name from opt.sizes"
    )
    assert set(leaf_tags) == set(parent.sizes)


def test_ollama_parent_still_emits_latest_leaf_at_head():
    """Defense: my ComfyUI branch must not regress the Ollama path."""
    parent = _ollama_parent()
    stub = _PanelStub(options=[parent], expanded={"qwen3"})
    rows = stub._rebuild_visible()
    leaf_rows = [r for r in rows if r.kind == "leaf"]
    leaf_tags = [r.variant for r in leaf_rows]
    assert "latest" in leaf_tags, (
        "Ollama path must still synthesize the 'latest' leaf at the "
        "head of every expansion (this is the model-maker-default tag)"
    )


def test_leaf_render_data_uses_leaf_details_for_comfyui():
    """For a ComfyUI parent, _leaf_render_data returns the
    pre-computed (label, badges) from opt.leaf_details instead of
    formatting parent:variant + Ollama-style size_label."""
    parent = _comfyui_parent()
    # _leaf_render_data is a bound method; call it with a minimal panel
    class _Mini:
        _leaf_render_data = PromptPanel._leaf_render_data
        _variant_cache: dict = {}
    vrow = _VisibleRow(
        kind="leaf", abs_idx=0,
        parent_value="family:TRELLIS",
        variant="microsoft--TRELLIS-image-large",
    )
    full_name, size_label, leaf_badges = _Mini()._leaf_render_data(vrow, parent)
    assert full_name == "microsoft--TRELLIS-image-large"
    assert size_label == ""
    assert "3d" in leaf_badges
    assert "mesh_model" in leaf_badges
    assert "5.20GB" in leaf_badges


def test_row_is_checked_comfyui_aggregates_over_sizes():
    """The Ollama prefix-match wouldn't match a ComfyUI parent
    because its synthetic value ('family:TRELLIS') never appears in
    _checked_values. _row_is_checked_comfyui checks if ANY variant
    in opt.sizes is in the selection set."""
    sizes = ("microsoft--TRELLIS-image-large", "microsoft--TRELLIS.2-4B")
    assert _row_is_checked_comfyui(sizes, set())                              is False
    assert _row_is_checked_comfyui(sizes, {"microsoft--TRELLIS-image-large"}) is True
    assert _row_is_checked_comfyui(sizes, {"microsoft--TRELLIS.2-4B"})        is True
    # Unrelated entry doesn't false-positive
    assert _row_is_checked_comfyui(sizes, {"facebook--VGGT-1B"})              is False
