"""
BlockLogo — 6-row block-art "ATLAS-PLATFORM" lockup with vertical gradient.

Each of the 6 art rows is painted in one solid color from the
``_GRADIENT`` (bright blue at the top, deep navy at the bottom). Since
every letter spans the same 6 rows, each letter naturally inherits the
same vertical bright→dark fade.

Width is fixed to the natural glyph width of the lockup (129 cells);
Textual centers the widget horizontally via ``content-align`` in the
screen-level CSS so we don't need to read ``self.size`` (which would
cause a re-render on first layout pass and produce visible flicker).

Total height: 7 cells (1 spacer + 6 art). No bottom spacer — the
panel below it (InfoPanel) provides the breathing room.
"""

from __future__ import annotations

from rich.align import Align
from rich.console import Group, RenderableType
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.widget import Widget


# Single-line "ATLAS-PLATFORM" block-art lockup. 6 rows, 129 cells wide.
# Letter widths: A(8) T(9) L(8) A(8) S(8) hyphen(6) P(8) L(8) A(8) T(9)
# F(8) O(9) R(8) M(11); 1-cell gap between every adjacent glyph. The
# hyphen is a 6-cell horizontal block at mid-height (rows 2-3 only).
_LOGO_ROWS: list[str] = [
    " █████╗  ████████╗ ██╗       █████╗  ███████╗        ██████╗  ██╗       █████╗  ████████╗ ███████╗  ██████╗  ██████╗  ███╗   ███╗",
    "██╔══██╗ ╚══██╔══╝ ██║      ██╔══██╗ ██╔════╝        ██╔══██╗ ██║      ██╔══██╗ ╚══██╔══╝ ██╔════╝ ██╔═══██╗ ██╔══██╗ ████╗ ████║",
    "███████║    ██║    ██║      ███████║ ███████╗ ██████ ██████╔╝ ██║      ███████║    ██║    █████╗   ██║   ██║ ██████╔╝ ██╔████╔██║",
    "██╔══██║    ██║    ██║      ██╔══██║ ╚════██║ ██████ ██╔═══╝  ██║      ██╔══██║    ██║    ██╔══╝   ██║   ██║ ██╔══██╗ ██║╚██╔╝██║",
    "██║  ██║    ██║    ███████╗ ██║  ██║ ███████║        ██║      ███████╗ ██║  ██║    ██║    ██║      ╚██████╔╝ ██║  ██║ ██║ ╚═╝ ██║",
    "╚═╝  ╚═╝    ╚═╝    ╚══════╝ ╚═╝  ╚═╝ ╚══════╝        ╚═╝      ╚══════╝ ╚═╝  ╚═╝    ╚═╝    ╚═╝       ╚═════╝  ╚═╝  ╚═╝ ╚═╝     ╚═╝",
]


# Width of one fully-rendered row.
_ROW_WIDTH = len(_LOGO_ROWS[0])


# Vertical-gradient color stops (top → bottom). Top is the brightest.
# Every letter inherits this same fade because each row is painted in
# one solid color and every letter spans the same 6 rows.
_GRADIENT = [
    "#74A6F4",
    "#4F8AED",
    "#316DDF",
    "#1F4FBE",
    "#14338B",
    "#0A1A55",
]


class BlockLogo(Widget):
    """Single-line block-art lockup with vertical gradient, horizontally centered."""

    DEFAULT_CSS = """
    BlockLogo {
        height: 7;
        width: 100%;
        background: #0e0f18;
    }
    """

    can_focus = False

    def render(self) -> RenderableType:
        # 1 row top spacer + 6 art rows = 7 cells. No bottom spacer.
        renderables: list[RenderableType] = [Text("")]
        for i, row_str in enumerate(_LOGO_ROWS):
            color = _GRADIENT[i] if i < len(_GRADIENT) else _GRADIENT[-1]
            renderables.append(Align.center(Text(row_str, style=color)))
        return Group(*renderables)


class BrandPanel(Container):
    """Bordered, titled box wrapping the BlockLogo with brand metadata
    on the top + bottom borders.

    Top-left title: tagline (e.g. "Self-hosted Engineering Platform").
    Bottom subtitle (right-aligned): "by <author> · <license> · v<version> · <repo>".
    """

    DEFAULT_CSS = """
    BrandPanel {
        height: 9;
        width: 100%;
        border: round #2b2f4a;
        background: #0e0f18;
        padding: 0;
        border-title-align: left;
        border-subtitle-align: right;
    }
    BrandPanel > BlockLogo {
        height: 7;
        background: transparent;
    }
    """

    can_focus = False

    def __init__(
        self,
        *,
        tagline: str = "Self-hosted Engineering Platform",
        author: str = "",
        author_email: str = "",
        license: str = "",  # noqa: A002 - matches BrandInfo field name
        version: str = "",
        repo: str = "",
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.tagline = tagline
        self.author = author
        self.author_email = author_email
        self.license = license
        self.version = version
        self.repo = repo

    def compose(self) -> ComposeResult:
        yield BlockLogo()

    def on_mount(self) -> None:
        if self.tagline:
            self.border_title = f" {self.tagline} "
        parts: list[str] = []
        if self.author:
            who = f"by {self.author}"
            if self.author_email:
                who = f"{who} <{self.author_email}>"
            parts.append(who)
        if self.license:
            parts.append(self.license)
        if self.version:
            v = self.version if self.version.startswith("v") else f"v{self.version}"
            parts.append(v)
        if self.repo:
            parts.append(self.repo)
        if parts:
            self.border_subtitle = " " + "  ·  ".join(parts) + " "
