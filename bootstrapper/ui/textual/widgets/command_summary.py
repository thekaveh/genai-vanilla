"""
CommandSummary — bordered, multi-line live command preview.

Layout:

    ╭─ Command summary ──────────────────────────────────────────────╮
    │  ./start.sh \\                                                  │
    │      --llm-provider-source ollama-localhost \\                  │
    │      --base-port 63000                                          │
    ╰────────────────────────────────────────────────────────────────╯

Updates as the user picks options. Uses ``Static.update()`` (not
``refresh()``) so the new content actually replaces the old.
"""

from __future__ import annotations

from typing import Iterable

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from .. import palette as P


def _build_text(program: str, flags: list[tuple[str, str]]) -> Text:
    out = Text()
    out.append(program, style=P.TEXT_BRIGHT)
    if not flags:
        out.append("    (using .env defaults)", style=P.TEXT_FAINT)
        return out
    for flag, value in flags:
        out.append(" \\", style=P.TEXT_FAINT)
        out.append("\n    ")
        out.append(flag, style=P.ACCENT)
        if value:
            out.append(" ")
            out.append(value, style=P.TEXT)
    return out


class CommandSummary(Container):
    """Bordered + titled live command summary."""

    DEFAULT_CSS = """
    CommandSummary {
        height: auto;
        border: round #2b2f4a;
        background: #0e0f18;
        padding: 0 1;
        margin-top: 1;
    }
    CommandSummary > Static {
        height: auto;
        background: transparent;
    }
    """

    can_focus = False

    def __init__(
        self,
        *,
        program: str = "./start.sh",
        flags: Iterable[tuple[str, str]] | None = None,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.program = program
        self.flags: list[tuple[str, str]] = list(flags or [])
        self._body = Static(_build_text(self.program, self.flags))

    def on_mount(self) -> None:
        self.border_title = " Command summary "

    def compose(self) -> ComposeResult:
        yield self._body

    def set_flags(self, flags: Iterable[tuple[str, str]]) -> None:
        self.flags = list(flags)
        self._body.update(_build_text(self.program, self.flags))
