"""
BlockLogo — 6-row block-art "ATLAS" lockup with vertical gradient.

Each of the 6 art rows is painted in one solid color from the
``_GRADIENT`` (deep navy at the bottom, bright blue at the top).
Width is fixed to the natural glyph width of the lockup; Textual centers
the widget horizontally via ``content-align`` in the screen-level CSS so
we don't need to read ``self.size`` (which would cause a re-render on
first layout pass and produce visible flicker).

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


# 6 rows × 5 letter zones (A-T-L-A-S), each (color_idx, glyph). Color
# indices are vestigial; the renderer paints each row in a single solid
# color from ``_GRADIENT``. Outer padding centers the lockup inside the
# 100-cell canvas the surrounding BrandPanel reserves.
_LOGO_ROWS: list[list[tuple[int, str]]] = [
    [
        (0, "                      "),
        (0, " █████╗ "), (0, " "),
        (0, "████████╗"), (0, " "),
        (0, "██╗      "), (0, " "),
        (0, " █████╗ "), (0, " "),
        (0, "███████╗"),
        (0, "                      "),
    ],
    [
        (1, "                      "),
        (1, "██╔══██╗"), (1, " "),
        (1, "╚══██╔══╝"), (1, " "),
        (1, "██║      "), (1, " "),
        (1, "██╔══██╗"), (1, " "),
        (1, "██╔════╝"),
        (1, "                      "),
    ],
    [
        (2, "                      "),
        (2, "███████║"), (2, " "),
        (2, "   ██║   "), (2, " "),
        (2, "██║      "), (2, " "),
        (2, "███████║"), (2, " "),
        (2, "███████╗"),
        (2, "                      "),
    ],
    [
        (3, "                      "),
        (3, "██╔══██║"), (3, " "),
        (3, "   ██║   "), (3, " "),
        (3, "██║      "), (3, " "),
        (3, "██╔══██║"), (3, " "),
        (3, "╚════██║"),
        (3, "                      "),
    ],
    [
        (4, "                      "),
        (4, "██║  ██║"), (4, " "),
        (4, "   ██║   "), (4, " "),
        (4, "███████╗ "), (4, " "),
        (4, "██║  ██║"), (4, " "),
        (4, "███████║"),
        (4, "                      "),
    ],
    [
        (5, "                      "),
        (5, "╚═╝  ╚═╝"), (5, " "),
        (5, "   ╚═╝   "), (5, " "),
        (5, "╚══════╝ "), (5, " "),
        (5, "╚═╝  ╚═╝"), (5, " "),
        (5, "╚══════╝"),
        (5, "                      "),
    ],
]


# Width of one fully-rendered row.
_ROW_WIDTH = sum(len(glyph) for _, glyph in _LOGO_ROWS[0])


# Vertical-gradient color stops (top → bottom). Top is the brightest.
_GRADIENT = [
    "#74A6F4",
    "#4F8AED",
    "#316DDF",
    "#1F4FBE",
    "#14338B",
    "#0A1A55",
]


class BlockLogo(Widget):
    """Block-art lockup, vertical gradient, horizontally centered."""

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
        for i, row in enumerate(_LOGO_ROWS):
            color = _GRADIENT[i] if i < len(_GRADIENT) else _GRADIENT[-1]
            line = Text()
            for _idx, glyph in row:
                line.append(glyph, style=color)
            renderables.append(Align.center(line))
        return Group(*renderables)


class BrandPanel(Container):
    """Bordered, titled box wrapping the BlockLogo with brand metadata
    on the top + bottom borders.

    Top-left title: tagline (e.g. "AI Dev Suite"). Bottom subtitle
    (right-aligned): "by <author> · <license> · v<version> · <repo>".
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
        tagline: str = "Gen-AI Development Suite",
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
