"""
FooterBar — bordered, titled, center-aligned shortcut strip.

Layout (anchored to the bottom):

    ╭─ shortcuts ──────────────────────────────────────────────────────╮
    │      [↑] [↓] navigate   [↵] confirm   [esc] back   [ctrl+q] quit │
    ╰──────────────────────────────────────────────────────────────────╯

Each key is rendered as a small bracketed keycap; labels follow in
muted text. All hints (including ctrl+q) sit inline so there's no
awkward right-side gap.
"""

from __future__ import annotations

from rich.align import Align
from rich.console import RenderableType
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from .. import palette as P


# A hint is (keys, label) — keys is a tuple of one or more keycap labels
# rendered side-by-side (e.g. ("↑", "↓") for the arrow pair).
Hint = tuple[tuple[str, ...], str]


DEFAULT_HINTS: list[Hint] = [
    (("↑", "↓"), "navigate"),
    (("↵",), "confirm"),
    (("esc",), "back"),
    (("ctrl+q",), "quit"),
]


def _append_keycap(text: Text, label: str) -> None:
    text.append("[", style=P.TEXT_FAINT)
    text.append(label, style=f"bold {P.ACCENT}")
    text.append("]", style=P.TEXT_FAINT)


def _append_hint(text: Text, hint: Hint) -> None:
    keys, label = hint
    for i, k in enumerate(keys):
        if i > 0:
            text.append(" ")
        _append_keycap(text, k)
    text.append(" ")
    text.append(label, style=P.TEXT_MUTED)


class _Body(Static):
    def __init__(self, hints: list[Hint]) -> None:
        super().__init__()
        self.hints: list[Hint] = list(hints)

    def update_hints(self, hints: list[Hint]) -> None:
        self.hints = list(hints)
        self.update(self._build())

    def on_mount(self) -> None:
        self.update(self._build())

    def _build(self) -> RenderableType:
        line = Text()
        for i, hint in enumerate(self.hints):
            if i > 0:
                line.append("   ")
            _append_hint(line, hint)
        return Align.center(line)


class FooterBar(Container):
    """Bordered + titled shortcuts strip, center-aligned content."""

    DEFAULT_CSS = """
    FooterBar {
        height: 3;
        border: round #2b2f4a;
        background: #0e0f18;
        padding: 0 1;
    }
    FooterBar > _Body {
        height: 1;
        background: transparent;
    }
    """

    can_focus = False

    def __init__(
        self,
        *,
        hints: list[Hint] | None = None,
        right: Hint | None = None,  # kept for back-compat; merged inline
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        merged = list(hints) if hints else list(DEFAULT_HINTS)
        if right is not None:
            merged.append(right)
        self._body = _Body(merged)

    def on_mount(self) -> None:
        self.border_title = " Shortcuts "

    def compose(self) -> ComposeResult:
        yield self._body

    def update_hints(
        self,
        hints: list[Hint],
        *,
        right: Hint | None = None,
    ) -> None:
        merged = list(hints)
        if right is not None:
            merged.append(right)
        self._body.update_hints(merged)
