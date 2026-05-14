"""
Unit tests for the per-leaf ``[pulled]`` / ``[library]`` status badge
rendered under an expanded Ollama-family parent in the wizard.

Before the fix, ``_leaf_render_data`` ran inherited badges through
``_inherited_leaf_badges`` which strips status tags under the comment
*"every leaf of a [library] parent is library; the user already sees
that on the parent right above"*. That assumption is wrong: a family
like ``qwen3.6`` whose host has ``qwen3.6:35b-a3b-coding-mxfp8``
pulled but not ``qwen3.6:27b``/``35b``/etc. has mixed-status leaves.
The fix added a per-leaf status computation that consults
``opt.pulled_variants`` directly.

These tests exercise ``_leaf_render_data`` on a stub ``PromptPanel``
instance — the method only reads ``self._variant_cache`` and the
inputs we pass, so we don't need a full Textual app context. The same
behaviour is verified end-to-end against a live host Ollama in
``test_live_catalog_sync.py``.
"""

from __future__ import annotations

import pytest

from ui.textual.widgets.prompt_panel import (
    PromptOption,
    PromptPanel,
    _VisibleRow,
)


# ────────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────────


class _PanelStub:
    """Minimal stand-in for PromptPanel that satisfies ``_leaf_render_data``'s
    self-attribute reads. The real class wires Textual reactive
    plumbing in ``__init__`` that we don't need (and can't easily
    bring up in a headless unit test)."""
    _variant_cache: dict = {}

    # Bind the method so we can call it on our stub.
    _leaf_render_data = PromptPanel._leaf_render_data


@pytest.fixture
def panel():
    return _PanelStub()


def _qwen_parent_option(*, pulled_variants=frozenset()):
    """Build the qwen3.6 family parent PromptOption as the wizard's
    options_provider would produce it for an ollama-localhost run.
    ``pulled_variants`` carries the per-tag host state."""
    badges = ["thinking", "tools"]
    badges.insert(
        0, "pulled" if pulled_variants else "library",
    )
    return PromptOption(
        value="qwen3.6",
        label="qwen3.6",
        hint="frontier dense + MoE model — strong reasoning / coding",
        badges=badges,
        pulls=1_300_000,
        sizes=("27b", "35b"),
        pulled_variants=pulled_variants,
    )


def _leaf_row(tag):
    return _VisibleRow(
        kind="leaf", abs_idx=0,
        parent_value="qwen3.6", variant=tag,
    )


# ────────────────────────────────────────────────────────────────────────────
# Per-leaf status badge — the screenshot fix
# ────────────────────────────────────────────────────────────────────────────


def test_leaf_carrying_a_pulled_tag_renders_pulled_status(panel):
    """A variant whose tag is in ``opt.pulled_variants`` renders
    ``[pulled]`` even when the parent family is in the library."""
    opt = _qwen_parent_option(
        pulled_variants=frozenset({"35b-a3b-coding-mxfp8"}),
    )
    _, _, leaf_badges = panel._leaf_render_data(
        _leaf_row("35b-a3b-coding-mxfp8"), opt,
    )
    assert "pulled" in leaf_badges, (
        f"Leaf 35b-a3b-coding-mxfp8 is on the host (in pulled_variants) — "
        f"must render [pulled]. Got: {leaf_badges}"
    )
    assert "library" not in leaf_badges, (
        f"A leaf rendered as [pulled] must NOT also carry [library]. "
        f"Got: {leaf_badges}"
    )


def test_sibling_leaf_not_on_host_renders_library_status(panel):
    """A sibling variant of the same family whose tag is NOT in
    ``opt.pulled_variants`` must render ``[library]``, NOT the
    pulled status the family carries. This is the inverse of the
    above and the crux of the per-leaf bug: previously every leaf
    of a pulled family inherited ``[pulled]`` (after the family
    badge fix) which was equally wrong."""
    opt = _qwen_parent_option(
        pulled_variants=frozenset({"35b-a3b-coding-mxfp8"}),
    )
    _, _, leaf_badges = panel._leaf_render_data(_leaf_row("27b"), opt)
    assert "library" in leaf_badges, (
        f"Leaf 27b is NOT on the host — must render [library]. "
        f"Got: {leaf_badges}"
    )
    assert "pulled" not in leaf_badges


def test_mixed_status_within_one_family_is_independently_rendered(panel):
    """End-to-end: render every leaf under a family that has SOME
    pulled, SOME not. The pulled set ``{latest, 35b-a3b-coding-mxfp8}``
    must light up exactly those two leaves; every other variant must
    stay ``[library]``."""
    opt = _qwen_parent_option(
        pulled_variants=frozenset({"latest", "35b-a3b-coding-mxfp8"}),
    )
    leaves_to_check = (
        ("latest", "pulled"),
        ("27b", "library"),
        ("35b", "library"),
        ("27b-coding-mxfp8", "library"),
        ("35b-a3b-coding-mxfp8", "pulled"),
        ("35b-a3b-coding-nvfp4", "library"),
    )
    for tag, expected in leaves_to_check:
        _, _, badges = panel._leaf_render_data(_leaf_row(tag), opt)
        assert expected in badges, (
            f"Leaf {tag!r} expected to render [{expected}]; got {badges}"
        )
        other = "library" if expected == "pulled" else "pulled"
        assert other not in badges, (
            f"Leaf {tag!r} should NOT carry [{other}] (mixed status "
            f"would confuse the picker). Got: {badges}"
        )


def test_leaf_carries_no_status_when_pulled_variants_is_empty(panel):
    """When the upstream Ollama isn't reachable (or this is a
    container-mode wizard run), the options_provider leaves
    ``pulled_variants`` empty. In that state ``_leaf_render_data``
    must NOT emit ``[pulled]`` or ``[library]`` on the leaf — the
    parent's aggregate status is the only signal and per-leaf
    status would be a wild guess."""
    opt = _qwen_parent_option(pulled_variants=frozenset())
    _, _, badges = panel._leaf_render_data(_leaf_row("27b"), opt)
    assert "pulled" not in badges
    assert "library" not in badges
