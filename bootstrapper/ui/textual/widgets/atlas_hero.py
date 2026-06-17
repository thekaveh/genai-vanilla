"""Load and render the pre-generated Atlas hero cell-grid.

The grids are produced by bootstrapper/scripts/generate_logo.py and
committed under ../assets/. This module has no chafa/Pillow dependency.
"""
from __future__ import annotations

import json
from pathlib import Path

from rich.align import Align
from rich.console import Group, RenderableType
from rich.style import Style
from rich.text import Text
from textual.widget import Widget

_ASSETS = Path(__file__).resolve().parent.parent / "assets"
_BREAKPOINTS = (160, 120, 100, 80)  # descending


def load_hero(width: int) -> dict | None:
    """Largest breakpoint <= width, or None when width < smallest (80)."""
    for cols in _BREAKPOINTS:
        if width >= cols:
            path = _ASSETS / f"atlas_hero_{cols}.json"
            return json.loads(path.read_text(encoding="utf-8"))
    return None


def hero_rows(data: dict) -> list[Text]:
    rows: list[Text] = []
    for row in data["cells"]:
        t = Text()
        for glyph, fg, bg in row:
            t.append(glyph, Style(color=fg, bgcolor=bg))
        rows.append(t)
    return rows


class AtlasHero(Widget):
    """Static block-art hero, horizontally centered, sized to the grid."""

    can_focus = False

    def __init__(self, width: int, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._data = load_hero(width)

    @property
    def grid_rows(self) -> int:
        return self._data["rows"] if self._data else 0

    def render(self) -> RenderableType:
        if not self._data:
            return Text("")
        return Group(*[Align.center(t) for t in hero_rows(self._data)])
