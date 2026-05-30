"""Color-coding for ComfyUI badges in OptionRow.

The post-PR-#21 wizard screenshot exposed that only [audio] and
[embedding] tags were color-coded — those happened to overlap with
Ollama's capability palette and got hues by accident. Every other
ComfyUI badge (`[3d]`, `[mesh_model]`, `[checkpoint]`, `[lora]`,
warnings like `[⚠ requires GPU]`, …) fell through to P.TEXT_FAINT
and rendered as faint grey, making rows hard to scan.

This test pins:
  1. Every ComfyUI display-group badge (image / image-edit / video /
     audio / 3d / custom) is colored.
  2. Every ComfyUI category badge (checkpoint / lora / vae /
     controlnet / ipadapter / instantid / upscaler / clip /
     animatediff / motion_lora / video_model / voice_model /
     audio_model / mesh_model) is colored.
  3. Warning badges (any text starting with ⚠) get P.WARN.
"""
from __future__ import annotations

from ui.textual import palette as P
from ui.textual.widgets.option_row import _BADGE_STYLES, _render_status_badges


def test_every_comfyui_group_badge_has_a_color():
    groups = ("image", "image-edit", "video", "audio", "3d", "custom")
    for g in groups:
        assert g in _BADGE_STYLES, f"display-group badge {g!r} missing from _BADGE_STYLES"
        assert _BADGE_STYLES[g] != P.TEXT_FAINT, (
            f"display-group badge {g!r} maps to TEXT_FAINT — "
            f"that's the unrecognized-tag fallback, not a real color"
        )


def test_every_comfyui_category_badge_has_a_color():
    categories = (
        "checkpoint", "lora", "vae", "controlnet", "ipadapter",
        "instantid", "upscaler", "embedding", "clip", "animatediff",
        "motion_lora", "video_model", "voice_model", "audio_model",
        "mesh_model",
    )
    for cat in categories:
        assert cat in _BADGE_STYLES, f"category badge {cat!r} missing"
        assert _BADGE_STYLES[cat] != P.TEXT_FAINT, (
            f"category badge {cat!r} maps to TEXT_FAINT — that's the "
            f"unrecognized-tag fallback, not a real color"
        )


def test_warning_badge_gets_warn_color():
    """`⚠ requires GPU`, `⚠ node: <name>`, etc. — all variable-text
    warnings get P.WARN by prefix-match without each variant needing
    a full entry in _BADGE_STYLES."""
    rendered = _render_status_badges([
        "⚠ requires GPU",
        "⚠ node: ComfyUI-3D-Pack",
    ])
    plain = rendered.plain
    assert "⚠ requires GPU" in plain
    assert "⚠ node: ComfyUI-3D-Pack" in plain
    # Verify the WARN style was applied to the warning spans.
    # rendered.spans carries (start, end, style) tuples; collect any
    # span whose style references the P.WARN hex string.
    styled = [s for s in rendered.spans if P.WARN in str(s.style)]
    assert len(styled) >= 2, (
        f"expected 2 warning spans to carry P.WARN ({P.WARN!r}); "
        f"got spans={rendered.spans!r}"
    )


def test_unrecognized_badge_still_falls_through_to_faint():
    """Defense: a badge with no entry and no ⚠ prefix should still
    render with P.TEXT_FAINT so the row never crashes on an
    unforeseen tag."""
    rendered = _render_status_badges(["totally-made-up-tag"])
    assert "totally-made-up-tag" in rendered.plain
    faint = [s for s in rendered.spans if P.TEXT_FAINT in str(s.style)]
    assert faint, "fallback to TEXT_FAINT broke for unknown tag"
