"""
BrandHeader — single-row brand strip rendered below the block logo.

Layout:  ◆  GENAI VANILLA   AI Development Suite

The diamond glyph is colored from the first stop of the logo gradient.
Used as a subordinate brand line under the BlockLogo on every screen.
"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget

from .. import palette as P


class BrandHeader(Widget):
    """1-row brand line: diamond + brand name + tagline."""

    DEFAULT_CSS = """
    BrandHeader { height: 1; padding: 0 2; }
    """

    def __init__(
        self,
        *,
        brand_name: str = "GENAI VANILLA",
        tagline: str = "AI Development Suite",
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.brand_name = brand_name
        self.tagline = tagline

    def update_brand(
        self,
        *,
        brand_name: str | None = None,
        tagline: str | None = None,
    ) -> None:
        if brand_name is not None:
            self.brand_name = brand_name
        if tagline is not None:
            self.tagline = tagline
        self.refresh()

    def render(self) -> Text:
        line = Text()
        line.append(P.DOT_DIAMOND, style=P.LOGO_GRADIENT[1])
        line.append("  ")
        line.append(self.brand_name.upper(), style=P.TEXT_BRIGHT)
        line.append("   ")
        line.append(self.tagline, style=P.TEXT_MUTED)
        return line
