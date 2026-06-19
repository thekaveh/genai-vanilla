"""Parity + boundary guard for the ATLAS-PLATFORM block-art lockup.

The 6-row FULL lockup, the ATLAS COMPACT fallback, and the 119-column
width threshold are duplicated across two render surfaces:

  * ``ui/textual/widgets/block_logo`` — the Textual TUI brand panel.
  * ``utils/banner.BannerDisplay.get_ascii_art_full`` — the linear
    ``--no-tui`` startup banner.

Nothing else pins the two surfaces to each other, so editing one (a glyph
fix, a threshold shift) can silently diverge the wide-vs-narrow switch —
exactly the off-by-one logic that regresses unnoticed. These tests fail
the moment the two surfaces disagree.
"""

from __future__ import annotations

import os
import shutil

import pytest


def _force_width(monkeypatch, cols: int) -> None:
    monkeypatch.setattr(
        shutil, "get_terminal_size", lambda *a, **k: os.terminal_size((cols, 50))
    )


def test_full_lockup_matches_across_surfaces(monkeypatch):
    import ui.textual.widgets.block_logo as bl
    from utils.banner import BannerDisplay

    _force_width(monkeypatch, 200)  # comfortably above threshold
    assert bl._LOGO_ROWS_FULL == BannerDisplay().get_ascii_art_full()


def test_compact_lockup_matches_across_surfaces(monkeypatch):
    import ui.textual.widgets.block_logo as bl
    from utils.banner import BannerDisplay

    _force_width(monkeypatch, 80)  # below threshold
    assert bl._LOGO_ROWS_COMPACT == BannerDisplay().get_ascii_art_full()


def test_width_threshold_matches_across_surfaces():
    import ui.textual.widgets.block_logo as bl
    from utils.banner import BannerDisplay

    assert bl._WIDTH_THRESHOLD == BannerDisplay._FULL_WIDTH_THRESHOLD


@pytest.mark.parametrize("cols,variant", [(118, "compact"), (119, "full")])
def test_threshold_boundary_picks_the_right_lockup(monkeypatch, cols, variant):
    import ui.textual.widgets.block_logo as bl
    from utils.banner import BannerDisplay

    _force_width(monkeypatch, cols)
    art = BannerDisplay().get_ascii_art_full()
    expected = bl._LOGO_ROWS_FULL if variant == "full" else bl._LOGO_ROWS_COMPACT
    assert art == expected


def test_lockups_are_six_rows_of_uniform_width():
    import ui.textual.widgets.block_logo as bl

    for art in (bl._LOGO_ROWS_FULL, bl._LOGO_ROWS_COMPACT):
        assert len(art) == 6
        # No ragged right edge — every row must be the same cell width.
        assert len({len(row) for row in art}) == 1
