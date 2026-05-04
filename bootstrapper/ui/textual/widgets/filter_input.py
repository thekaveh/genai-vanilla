"""
FilterInput — leading ⌕ icon + Input.

Mockup 003 layout:
    ⌕  Filter services...

Caret cyan, placeholder very faint, no border. Posts the typed value via
``set_on_change`` to the parent container.
"""

from __future__ import annotations

from typing import Callable

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Input, Static

from .. import palette as P


class FilterInput(Horizontal):
    DEFAULT_CSS = """
    FilterInput { height: 1; }
    FilterInput > .filter-icon {
        width: 2;
        color: #565f89;
    }
    FilterInput > Input {
        height: 1;
        background: #161728;
        border: none;
        color: #c0caf5;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        *,
        placeholder: str = "Filter services...",
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._on_change: Callable[[str], None] | None = None
        self._input = Input(placeholder=placeholder, id="filter-input")

    def compose(self) -> ComposeResult:
        yield Static(P.GLYPH_SEARCH, classes="filter-icon")
        yield self._input

    def on_input_changed(self, event: Input.Changed) -> None:  # noqa: N802
        if self._on_change is not None:
            self._on_change(event.value)

    def set_on_change(self, callback: Callable[[str], None]) -> None:
        self._on_change = callback
