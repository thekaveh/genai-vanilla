"""
Logo renderable — the GenAI Vanilla block ASCII art that anchors the top
of the presentation, both in the wizard's anchored info-box view and in
the post-launch Textual log streaming app.

Single horizontal lockup: "GEN-AI ─ VANILLA" laid out side-by-side as
one 6-row line of `█ ╗ ╔ ═ ║ ╝ ╚` block-drawing glyphs (plus a 1-row
trailing spacer for breathing room before the info-box border) — 7 rows
total. Half the vertical footprint of a stacked GEN-AI / VANILLA layout.

Coloring is **row-wise vertical**: each of the 6 art rows is painted in
a single solid color from `palette.LOGO_GRADIENT[0..5]` — top row in
the light-blue `[5]` end of the ramp, bottom row in the deep-navy `[0]`
end. The whole lockup gradates top-to-bottom **light → dark**,
regardless of which letter you're looking at. (The per-zone color
indices stored in `_LOGO_ROWS` are vestigial documentation of the prior
horizontal-zone scheme — they're ignored by the renderer below.)
"""

from __future__ import annotations

from typing import List, Tuple

from rich.align import Align
from rich.console import Group, RenderableType
from rich.text import Text

from ui import palette


# --- Color-zoned ASCII art -------------------------------------------------
#
# Each row is a list of (LOGO_GRADIENT index, glyph string) tuples. 13
# zones per row matching the user's `[N]` markup:
#   G[0] E[0] N[1] A[1] I[2] dash[2] V[3] A[3] N[4] I[4] L[5] L[5] A[5]

_LOGO_ROWS: List[List[Tuple[int, str]]] = [
    [
        (0, " ██████╗ "), (0, "███████╗"), (1, "███╗   ██╗"), (1, " █████╗ "),
        (2, "██╗  "),     (2, "      "),
        (3, "██╗   ██╗"), (3, " █████╗ "), (4, "███╗   ██╗"), (4, "██╗"),
        (5, "██╗     "), (5, "██╗      "), (5, " █████╗"),
    ],
    [
        (0, "██╔════╝ "), (0, "██╔════╝"), (1, "████╗  ██║"), (1, "██╔══██╗"),
        (2, "██║  "),     (2, "      "),
        (3, "██║   ██║"), (3, "██╔══██╗"), (4, "████╗  ██║"), (4, "██║"),
        (5, "██║     "), (5, "██║     "), (5, "██╔══██╗"),
    ],
    [
        (0, "██║  ███╗"), (0, "█████╗  "), (1, "██╔██╗ ██║"), (1, "███████║"),
        (2, "██║  "),     (2, "█████╗"),
        (3, "██║   ██║"), (3, "███████║"), (4, "██╔██╗ ██║"), (4, "██║"),
        (5, "██║     "), (5, "██║     "), (5, "███████║"),
    ],
    [
        (0, "██║   ██║"), (0, "██╔══╝  "), (1, "██║╚██╗██║"), (1, "██╔══██║"),
        (2, "██║  "),     (2, "╚════╝"),
        (3, "╚██╗ ██╔╝"), (3, "██╔══██║"), (4, "██║╚██╗██║"), (4, "██║"),
        (5, "██║     "), (5, "██║     "), (5, "██╔══██║"),
    ],
    [
        (0, "╚██████╔╝"), (0, "███████╗"), (1, "██║ ╚████║"), (1, "██║  ██║"),
        (2, "██║  "),     (2, "      "),
        (3, " ╚████╔╝ "), (3, "██║  ██║"), (4, "██║ ╚████║"), (4, "██║"),
        (5, "███████╗"), (5, "███████╗"), (5, "██║  ██║"),
    ],
    [
        (0, " ╚═════╝ "), (0, "╚══════╝"), (1, "╚═╝  ╚═══╝"), (1, "╚═╝  ╚═╝"),
        (2, "╚═╝  "),     (2, "      "),
        (3, "  ╚═══╝  "), (3, "╚═╝  ╚═╝"), (4, "╚═╝  ╚═══╝"), (4, "╚═╝"),
        (5, "╚══════╝"), (5, "╚══════╝"), (5, "╚═╝  ╚═╝"),
    ],
]


# --- Threshold rules (match presentation_app.MIN_TERMINAL_ROWS as floor) ---

ROWS_FOR_FULL_LOGO = 28   # >= this many rows: render the full 6-row block art
ROWS_FOR_TAGLINE = 22     # below ROWS_FOR_FULL_LOGO but >= this: 1-line fallback
                          # below ROWS_FOR_TAGLINE: render nothing


def render_logo(
    available_width: int,
    available_rows: int,
    *,
    brand_name: str = "GenAI Vanilla",
) -> RenderableType:
    """
    Render the GenAI Vanilla logo for the available terminal size.

    The 1-row spacer is **above** the art — gives the logo a small top
    margin away from the screen edge and lets the bottom of the art sit
    flush against the info-box's top border for a tighter visual link
    between logo and stack-overview.

    - Tall (≥28 rows): full 7-row horizontal block art (1 top spacer + 6 art rows).
    - Medium (22..27 rows): single-line block-styled tagline fallback (2 rows).
    - Short (<22 rows): empty group (caller skips the logo region).

    `brand_name` is used by the tagline fallback only — the multi-row
    art is the project's fixed nameplate; a fork that wants its own
    multi-row art would replace this module.
    """
    if available_rows < ROWS_FOR_TAGLINE:
        return Group()
    if available_rows < ROWS_FOR_FULL_LOGO:
        return Group(Text(" "), _render_tagline(brand_name))
    return Group(Text(" "), *_render_full_block_art())


def estimated_height(available_width: int, available_rows: int) -> int:
    """How many rows the logo region occupies. Matches `render_logo` output."""
    if available_rows < ROWS_FOR_TAGLINE:
        return 0
    if available_rows < ROWS_FOR_FULL_LOGO:
        return 2  # top spacer (1) + tagline (1)
    return 1 + 6  # top spacer (1) + 6 art rows


# --- Multi-row block art ---------------------------------------------------

def _render_full_block_art() -> List[RenderableType]:
    """
    Render the 6-row "GEN-AI ─ VANILLA" horizontal lockup with a
    **vertical** gradient — each row painted in one solid color from
    `LOGO_GRADIENT`, top row in the light end (`[5]`), bottom row in
    the dark end (`[0]`). Each row is `Align.center`-wrapped so the
    lockup self-centers in the available width.
    """
    n_rows = len(_LOGO_ROWS)
    return [
        Align.center(_color_row(row, (n_rows - 1) - row_idx))
        for row_idx, row in enumerate(_LOGO_ROWS)
    ]


def _color_row(segments: List[Tuple[int, str]], color_idx: int) -> Text:
    """
    Build one Rich Text line from the row's glyph segments, all painted
    in the single solid color at `LOGO_GRADIENT[color_idx]`. The
    per-segment color indices stored in `_LOGO_ROWS` tuples are
    intentionally ignored — they were used by the previous horizontal-
    gradient scheme.
    """
    line = Text()
    color = palette.LOGO_GRADIENT[color_idx]
    for _idx, glyph in segments:
        line.append(glyph, style=color)
    return line


# --- Tagline fallback ------------------------------------------------------

def _render_tagline(brand_name: str) -> RenderableType:
    """
    Single-line fallback for terminals too short to fit the multi-row
    art. Echoes the block aesthetic via `█▓▒░` shading bookends; the
    brand text in the middle is colored across the `LOGO_GRADIENT` ramp.
    """
    line = Text()
    line.append("█▓▒░", style=palette.LOGO_GRADIENT[2])
    line.append("  ", style=palette.COLOR_DIM)
    n = max(1, len(brand_name))
    palette_size = len(palette.LOGO_GRADIENT)
    for i, ch in enumerate(brand_name):
        idx = min(int(i * palette_size / n), palette_size - 1)
        line.append(ch, style=f"bold {palette.LOGO_GRADIENT[idx]}")
    line.append("  ", style=palette.COLOR_DIM)
    line.append("░▒▓█", style=palette.LOGO_GRADIENT[-2])
    return Align.center(line)
