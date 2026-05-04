"""
LogPane — bordered, filterable log surface that subclasses RichLog
directly so its native bounded-scroll behavior handles containment.

Wrapping RichLog in a Container with overflow:hidden was unreliable in
production (long compose lines pushed past the parent bounds). RichLog
itself manages an internal viewport — when it owns the border, lines
cannot escape it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from rich.text import Text
from textual.widgets import RichLog


@dataclass
class _LogRecord:
    level: str         # "info" | "warn" | "error" | "ok" | "dim" | …
    source: str        # docker service name or pipeline phase
    raw: str           # ANSI line as received


class LogPane(RichLog):
    """Bordered, filterable log surface."""

    DEFAULT_CSS = """
    LogPane {
        height: 1fr;
        min-height: 5;
        border: round #2b2f4a;
        background: #0e0f18;
        padding: 0 1;
        margin: 1 0 0 0;
        scrollbar-size-vertical: 1;
    }
    LogPane:focus { border: round #7dcfff; }
    """

    DEFAULT_BUFFER = 10_000

    def __init__(
        self,
        *,
        title: str = " Logs ",
        subtitle: str = "",
        buffer: int = DEFAULT_BUFFER,
        id: str | None = None,
    ) -> None:
        super().__init__(
            id=id,
            highlight=False, markup=False, wrap=True,
            auto_scroll=True, max_lines=buffer,
        )
        self._title = title
        self._subtitle = subtitle
        self._buffer_cap = buffer
        self._records: list[_LogRecord] = []
        self._level_filter: str = "all"
        self._disabled_sources: set[str] = set()
        self._on_new_source = None

    def on_mount(self) -> None:
        if self._title:
            self.border_title = self._title
        if self._subtitle:
            self.border_subtitle = self._subtitle

    def set_title(self, title: str, *, subtitle: str | None = None) -> None:
        self._title = title
        self.border_title = title
        if subtitle is not None:
            self._subtitle = subtitle
            self.border_subtitle = subtitle

    def set_on_new_source(self, callback) -> None:
        """Notified when a previously-unseen source appears (so the chip
        bar can add a chip for it)."""
        self._on_new_source = callback

    def write_log(
        self, line: str, *, level: str = "info", source: str = "",
    ) -> None:
        rec = _LogRecord(level=(level or "info").lower(), source=source, raw=line)
        # Notify on new source
        if (
            source
            and source not in self._disabled_sources
            and self._on_new_source is not None
            and not any(r.source == source for r in self._records)
        ):
            self._on_new_source(source)
        self._records.append(rec)
        if len(self._records) > self._buffer_cap:
            del self._records[: len(self._records) - self._buffer_cap]
        if self._passes_filter(rec):
            self._write_record(rec)

    def write_styled(
        self, text: Text, *, level: str = "info", source: str = "",
    ) -> None:
        rec = _LogRecord(level=(level or "info").lower(), source=source, raw=text.plain)
        if (
            source
            and source not in self._disabled_sources
            and self._on_new_source is not None
            and not any(r.source == source for r in self._records)
        ):
            self._on_new_source(source)
        self._records.append(rec)
        if len(self._records) > self._buffer_cap:
            del self._records[: len(self._records) - self._buffer_cap]
        if self._passes_filter(rec):
            self.write(text)

    def _passes_filter(self, rec: _LogRecord) -> bool:
        if self._level_filter != "all" and rec.level != self._level_filter:
            return False
        if rec.source and rec.source in self._disabled_sources:
            return False
        return True

    def _write_record(self, rec: _LogRecord) -> None:
        self.write(Text.from_ansi(rec.raw))

    def set_filter(self, level: str, disabled_sources: Iterable[str]) -> None:
        self._level_filter = (level or "all").lower()
        self._disabled_sources = set(disabled_sources)
        self._rerender()

    def _rerender(self) -> None:
        self.clear()
        for rec in self._records:
            if self._passes_filter(rec):
                self._write_record(rec)

    def known_sources(self) -> list[str]:
        seen: list[str] = []
        for rec in self._records:
            if rec.source and rec.source not in seen:
                seen.append(rec.source)
        return seen
