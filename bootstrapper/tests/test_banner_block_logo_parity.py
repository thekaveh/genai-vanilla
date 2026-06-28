"""Parity + brand-override guard for the block-art lockup.

Both render surfaces now resolve their art through ``utils.brand_logo``:

  * ``ui/textual/widgets/block_logo`` — the Textual TUI brand panel.
  * ``utils/banner.BannerDisplay.get_ascii_art_full`` — the linear
    ``--no-tui`` startup banner.

so the built-in ATLAS default AND a fork's ``BRAND_LOGO_FILE`` override stay in
parity across both. These tests pin that shared contract: the default matches
ATLAS on both surfaces, the wide-vs-narrow width switch behaves identically,
and a CUSTOM lockup flows through both render paths. They monkeypatch the
resolver so they don't depend on the ambient ``.env``.
"""
from __future__ import annotations

import os
import shutil

import pytest

from utils import brand_logo


def _force_width(monkeypatch, cols: int) -> None:
    monkeypatch.setattr(
        shutil, "get_terminal_size", lambda *a, **k: os.terminal_size((cols, 50))
    )


def _patch_art(monkeypatch, full, compact, threshold) -> None:
    monkeypatch.setattr(
        brand_logo, "resolve_from_env", lambda: (full, compact, threshold)
    )


def _rendered_rows(group) -> list[str]:
    """Pull the row strings back out of BlockLogo.render()'s Group.

    render() yields a leading ``Text("")`` spacer then one
    ``Align(Text(row))`` per art row.
    """
    rows: list[str] = []
    for item in group.renderables[1:]:  # skip the leading spacer
        renderable = getattr(item, "renderable", item)
        rows.append(renderable.plain)
    return rows


# ── default ATLAS art is the shared source across both surfaces ──────────────

def test_default_constants_are_the_shared_atlas_source():
    import ui.textual.widgets.block_logo as bl

    assert bl._LOGO_ROWS_FULL == brand_logo.ATLAS_FULL
    assert bl._LOGO_ROWS_COMPACT == brand_logo.ATLAS_COMPACT
    assert bl._WIDTH_THRESHOLD == brand_logo.width_threshold(brand_logo.ATLAS_FULL)
    assert bl._WIDTH_THRESHOLD == 119  # 118-cell ATLAS full + 1 margin


def test_banner_default_matches_atlas_across_widths(monkeypatch):
    from utils.banner import BannerDisplay

    _patch_art(monkeypatch, brand_logo.ATLAS_FULL, brand_logo.ATLAS_COMPACT, 119)
    _force_width(monkeypatch, 200)
    assert BannerDisplay().get_ascii_art_full() == brand_logo.ATLAS_FULL
    _force_width(monkeypatch, 80)
    assert BannerDisplay().get_ascii_art_full() == brand_logo.ATLAS_COMPACT


@pytest.mark.parametrize("cols,variant", [(118, "compact"), (119, "full")])
def test_threshold_boundary_picks_the_right_lockup(monkeypatch, cols, variant):
    from utils.banner import BannerDisplay

    _patch_art(monkeypatch, brand_logo.ATLAS_FULL, brand_logo.ATLAS_COMPACT, 119)
    _force_width(monkeypatch, cols)
    art = BannerDisplay().get_ascii_art_full()
    expected = brand_logo.ATLAS_FULL if variant == "full" else brand_logo.ATLAS_COMPACT
    assert art == expected


def test_default_lockups_are_six_rows_of_uniform_width():
    for art in (brand_logo.ATLAS_FULL, brand_logo.ATLAS_COMPACT):
        assert len(art) == 6
        assert len({len(row) for row in art}) == 1  # no ragged right edge


# ── a custom BRAND_LOGO_FILE override flows through BOTH surfaces ─────────────

_CUSTOM_FULL = ["RAG-FULL-AAAA", "RAG-FULL-BBBB"]
_CUSTOM_COMPACT = ["RAG", "RAG"]
_CUSTOM_THRESHOLD = brand_logo.width_threshold(_CUSTOM_FULL)  # 13 + 1 = 14


def test_custom_lockup_flows_through_banner(monkeypatch):
    from utils.banner import BannerDisplay

    _patch_art(monkeypatch, _CUSTOM_FULL, _CUSTOM_COMPACT, _CUSTOM_THRESHOLD)
    _force_width(monkeypatch, 200)
    assert BannerDisplay().get_ascii_art_full() == _CUSTOM_FULL
    _force_width(monkeypatch, 5)  # below the custom threshold
    assert BannerDisplay().get_ascii_art_full() == _CUSTOM_COMPACT


def test_custom_lockup_flows_through_block_logo(monkeypatch):
    import ui.textual.widgets.block_logo as bl

    _patch_art(monkeypatch, _CUSTOM_FULL, _CUSTOM_COMPACT, _CUSTOM_THRESHOLD)
    _force_width(monkeypatch, 200)
    assert _rendered_rows(bl.BlockLogo().render()) == _CUSTOM_FULL
    _force_width(monkeypatch, 5)
    assert _rendered_rows(bl.BlockLogo().render()) == _CUSTOM_COMPACT
