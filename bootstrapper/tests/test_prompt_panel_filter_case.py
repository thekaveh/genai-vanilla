"""Filter-chip visibility filter must match badges case-insensitively.

multiselect_filter_chips.py:132 lowercases every input tag, so the
ACTIVE chip key reaches ``_rebuild_visible`` already lowercased
(prompt_panel.py:972 → ``tag = (...).strip().lower()``). Badges on
options come from arbitrary upstream code paths that may emit Title-
Case strings — e.g. ComfyUI's group names "Image" / "Image-edit" /
"Video" / "Audio" / "3D" / "Custom". The line-975 ``if tag not in
opt.badges`` comparison was case-sensitive, so the lowercased active
tag never matched a Title-Case badge and the chip filtered every row
out. This test pins case-insensitive comparison as a
defense-in-depth guard regardless of what badges any future picker
emits.
"""
from __future__ import annotations

import pytest

from ui.textual.widgets.prompt_panel import PromptOption, PromptPanel


class _FilterStub:
    """Stand-in for PromptPanel that exposes only the state
    ``_rebuild_visible`` reads. Mirrors _RebuildStub in
    test_prompt_panel_leaf_badges.py — _rebuild_visible is a pure
    list-builder over these attributes, so the stub keeps the test
    hermetic (no Textual event loop)."""

    _rebuild_visible = PromptPanel._rebuild_visible

    def __init__(self, options, *, active_tag: str):
        class _Step:
            pass
        self._step = _Step()
        self._step.options = options
        self._filter_tag = active_tag
        self._search_query = ""
        self._expanded = set()
        self._variant_cache = {}
        self._variant_loading = set()


@pytest.mark.parametrize("active_tag,badge_form,should_match", [
    # The widget emits an already-lowercased active tag. Badges may be
    # any case — the filter must normalize both sides before comparison.
    ("image",      "Image",      True),
    ("image-edit", "Image-edit", True),
    ("video",      "Video",      True),
    ("audio",      "Audio",      True),
    ("3d",         "3D",         True),
    # Sanity: a non-matching badge still doesn't match (no false positives).
    ("image",      "Video",      False),
])
def test_filter_chip_match_is_case_insensitive(active_tag, badge_form, should_match):
    """Repro for the post-PR-#20 wizard screenshot: every ComfyUI filter
    chip showed `0 / N` rows because the chip-active tag was lowercase
    while the group badge was Title-Case. After the defense-in-depth
    fix in prompt_panel.py the comparison normalizes case on both sides."""
    options = [
        PromptOption(value="m1", label="m1", hint="",
                     badges=[badge_form, "lora", "0.05GB"]),
    ]
    stub = _FilterStub(options, active_tag=active_tag)
    rows = stub._rebuild_visible()
    if should_match:
        assert len(rows) == 1, (
            f"active_tag={active_tag!r} badge={badge_form!r} → "
            f"expected 1 visible row, got {len(rows)}. "
            f"Filter comparison must be case-insensitive."
        )
    else:
        assert len(rows) == 0, (
            f"active_tag={active_tag!r} badge={badge_form!r} → "
            f"expected 0 visible rows (no false positives), got {len(rows)}."
        )
