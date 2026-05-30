"""_family_root extracts the leading-letters family from HF names.

The post-PR-#21 wizard screenshot showed multiple TRELLIS variants
rendered as separate flat rows (user: "two MS Trellis models
displayed sequentially"). _family_root produces the grouping key
used by _merged_comfyui_options to collapse those variants into one
expandable parent row.

Rule:
  • huggingface entries (name shape `owner--repo`) → leading
    [A-Za-z] run of the repo portion is the root
  • civitai-NNN entries → "" (no family, stay flat)
  • curated / sidecar / fallback / custom → "" (stay flat — these are
    hand-picked, grouping them would be confusing)
"""
from __future__ import annotations

import pytest

from utils.comfyui_library import _family_root


@pytest.mark.parametrize("name,expected", [
    # HF variants of the same model family
    ("microsoft--TRELLIS-image-large",   "TRELLIS"),
    ("microsoft--TRELLIS.2-4B",          "TRELLIS"),
    ("gqk--TRELLIS-image-large-fork",    "TRELLIS"),
    ("yyfz233--Pi3",                     "Pi"),
    ("yyfz233--Pi3X",                    "Pi"),
    ("tencent--Hunyuan3D-2",             "Hunyuan"),
    ("tencent--HunyuanImage-3.0",        "Hunyuan"),
    ("facebook--VGGT-1B",                "VGGT"),
    # Camel-case stops at the next capital — keeps the prefix as the
    # root so future "TripoSR-v2" / "TripoSR-mini" would group with
    # TripoSR. Singletons stay flat anyway (see _merged_comfyui_options).
    ("stabilityai--TripoSR",             "Tripo"),
    ("depth-anything--DA3-BASE",         "DA"),
    # Documented over-grouping risk (user accepted it)
    ("stabilityai--stable-diffusion-xl-base-1.0", "stable"),
    ("stabilityai--stable-cascade",      "stable"),
])
def test_family_root_for_huggingface_entries(name, expected):
    assert _family_root(name, source="huggingface") == expected


@pytest.mark.parametrize("source", ["civitai", "curated", "fallback", "custom"])
def test_non_huggingface_sources_never_group(source):
    """Only HF participates in family grouping. civitai numeric IDs +
    hand-picked curated/sidecar entries always stay flat."""
    assert _family_root("microsoft--TRELLIS-image-large", source=source) == ""


def test_huggingface_entry_without_separator_returns_empty():
    """A malformed HF name without the `owner--repo` shape should
    return empty (no family) rather than crash."""
    assert _family_root("noseparator", source="huggingface") == ""
