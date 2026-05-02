"""
Logo renderable — the big GenAI Vanilla ASCII art that anchors the top of
the presentation (Hermes-style header). Rendered above the info box when
the terminal is tall enough; collapsed to a one-line tagline below ~35 rows
so the log pane doesn't get squeezed.

The full ASCII art and its compact variant come from utils/banner.py
(unchanged source of truth). This module only adds the gradient styling
and the size-adaptive selection logic.
"""

from __future__ import annotations

from typing import List

from rich.align import Align
from rich.console import Group, RenderableType
from rich.text import Text

from ui import palette
from utils.banner import BannerDisplay


# Threshold rules — match presentation_app.MIN_TERMINAL_ROWS as the floor.
ROWS_FOR_FULL_LOGO = 36   # >= this many rows: render the full 12-line logo
ROWS_FOR_TAGLINE = 22     # below ROWS_FOR_FULL_LOGO but >= this: render a 1-line tagline
                          # below ROWS_FOR_TAGLINE: render nothing (caller skips this region)


def render_logo(available_width: int, available_rows: int) -> RenderableType:
    """
    Pick and render the appropriate logo variant for the terminal size.

    Returns a Rich renderable. Caller should not include this region at all
    when `available_rows < ROWS_FOR_TAGLINE` — the function still returns a
    safe empty Group in that case so it never raises.
    """
    if available_rows < ROWS_FOR_TAGLINE:
        return Group()

    if available_rows < ROWS_FOR_FULL_LOGO:
        return _render_tagline()

    return _render_full_logo(available_width)


def estimated_height(available_width: int, available_rows: int) -> int:
    """How many rows the logo will occupy. Matches what render_logo emits."""
    if available_rows < ROWS_FOR_TAGLINE:
        return 0
    if available_rows < ROWS_FOR_FULL_LOGO:
        return 2  # 1-line tagline + 1 spacer
    return _full_logo_height()


def _render_full_logo(available_width: int) -> RenderableType:
    """
    Full ASCII art with the cyan/blue gradient applied per character.

    The tagline + creator/license/repo info that previously appeared as
    captions below the art now live INSIDE the info box's title bar
    (top) and subtitle bar (bottom). The logo is just the art now.
    """
    art = _get_full_logo_lines()
    rendered_lines: List[Text] = []
    for line in art:
        rendered_lines.append(_apply_gradient(line))
    return Group(*(Align.center(line) for line in rendered_lines))


def _render_tagline() -> RenderableType:
    """One-line tagline for terminals too short for the full art."""
    line = Text()
    line.append("░▒▓ ", style=palette.LOGO_GRADIENT[2])
    # Brand text in gradient — short enough to read on one line.
    brand = "GenAI Vanilla Stack"
    n = len(brand)
    palette_size = len(palette.LOGO_GRADIENT)
    for i, ch in enumerate(brand):
        idx = min(int(i * palette_size / n), palette_size - 1)
        line.append(ch, style=f"bold {palette.LOGO_GRADIENT[idx]}")
    line.append(" ▓▒░", style=palette.LOGO_GRADIENT[-3])
    line.append("   AI Development Suite", style=palette.COLOR_DIM)
    return Align.center(line)


def _full_logo_height() -> int:
    """ASCII art lines only — no captions (those moved into the box title)."""
    return len(_get_full_logo_lines())


def _get_full_logo_lines() -> List[str]:
    """Read the full ASCII art from BannerDisplay (unchanged source of truth)."""
    return BannerDisplay().get_ascii_art_full()


def _apply_gradient(text: str) -> Text:
    """Per-character gradient using LOGO_GRADIENT — same algorithm as banner.py."""
    out = Text()
    n = len(text)
    if n == 0:
        return out
    palette_size = len(palette.LOGO_GRADIENT)
    for i, ch in enumerate(text):
        idx = min(int(i * palette_size / n), palette_size - 1)
        out.append(ch, style=f"bold {palette.LOGO_GRADIENT[idx]}")
    return out
