"""
Log pane renderable — windowed tail of recent log lines.

Holds a deque of pre-formatted `rich.text.Text` lines. Each `append()`
formats once (timestamp + source-color + separator + message-style); the
Live shell's `render(available_rows)` is then a deque tail-slice +
`Group(*tail)` — no per-frame Text construction. With docker streaming
hundreds of lines per second this drops the render cost from ~75k Text
objects/sec to ~50 (one per appended line, plus one slice per render).

Auto-detects level from message content (errors/warnings) when callers
don't specify one. Source-prefixed docker compose log lines (the typical
shape `service-name  | rest of line`) are parsed so the source column can
be styled separately.
"""

from collections import deque
from datetime import datetime
import re
from typing import Deque, Optional

from rich.console import Group
from rich.text import Text

from ui import palette


# Buffer caps — generous enough to absorb log bursts without being a
# memory hog. Render only ever shows the tail that fits in the terminal.
DEFAULT_BUFFER = 2000

# Width reserved for the source-name column in the rendered output.
# Wider than today's docker-default so service names don't get truncated.
SOURCE_COL_WIDTH = 16

# Patterns used to auto-detect log level from message content. Kept simple
# on purpose — false positives are mostly harmless (a yellow tinge on a
# benign line) and we want to avoid expensive regex per line.
_RE_ERROR = re.compile(r"\b(?:error|fatal|exception|traceback)\b", re.IGNORECASE)
_RE_WARN = re.compile(r"\b(?:warn|warning)\b", re.IGNORECASE)

# Pattern that splits a docker compose log line into (source, message).
# Matches the typical shape: "service-name  | rest of line".
_RE_DOCKER_LINE = re.compile(r"^([\w\-.]+)\s+\|\s?(.*)$")


class LogPane:
    """Owns the log buffer and renders the windowed tail."""

    def __init__(self, max_buffer: int = DEFAULT_BUFFER):
        # Each entry is a pre-built Rich Text — render() just slices and
        # wraps in a Group. Formatting happens once at append() time, not
        # per render tick.
        self._buffer: Deque[Text] = deque(maxlen=max_buffer)

    def append(self, message: str, *, source: Optional[str] = None, level: Optional[str] = None) -> None:
        """
        Append a log line. Auto-detects source (from `service | message` shape)
        and level (from message content) when not provided explicitly.
        """
        # Auto-parse source from docker-style "service-name | message" lines.
        if source is None:
            match = _RE_DOCKER_LINE.match(message)
            if match:
                source = match.group(1)
                message = match.group(2)

        # Auto-detect level when caller didn't override.
        if level is None:
            if _RE_ERROR.search(message):
                level = "error"
            elif _RE_WARN.search(message):
                level = "warn"
            else:
                level = "info"

        self._buffer.append(self._build_line(datetime.now(), source, message, level))

    def append_section_header(self, message: str) -> None:
        """
        Append a "section header" line — bold, in COLOR_TITLE, no source.
        Used for things like '🚀 Starting Services' that today's flow shows
        as visually distinct headers.
        """
        self._buffer.append(self._build_line(datetime.now(), None, message, "title"))

    def clear(self) -> None:
        """Drop all buffered entries (used when restarting the wizard)."""
        self._buffer.clear()

    def render(self, available_rows: int) -> Group:
        """
        Render the most recent `available_rows` lines as a Rich Group.

        Returns an empty Group when no lines fit. Callers should pass the
        terminal height minus the box height minus the status ribbon.
        """
        if available_rows <= 0:
            return Group()

        # The deque already holds pre-formatted Text — slicing is O(N) for
        # the tail, but at REFRESH_HZ × ~50 visible rows that's negligible.
        tail = list(self._buffer)[-available_rows:]
        return Group(*tail)

    @staticmethod
    def _build_line(
        ts: datetime, source: Optional[str], message: str, level: str
    ) -> Text:
        """Build the pre-styled Text once per append (not per render)."""
        line = Text()

        # Section headers: no timestamp, no source — pure title styling.
        if level == "title":
            line.append(message, style=palette.COLOR_TITLE)
            return line

        # Timestamp: HH:MM:SS in dim. Compact enough not to dominate.
        line.append(ts.strftime("%H:%M:%S "), style=palette.COLOR_DIM)

        # Source column (padded to a fixed width for alignment).
        # Each service hashes to a stable hue so the eye can pick out
        # a single source in a wall of concurrent compose logs.
        if source:
            src_text = source[:SOURCE_COL_WIDTH].ljust(SOURCE_COL_WIDTH)
            line.append(src_text, style=palette.color_for_source(source))
            line.append(" │ ", style=palette.COLOR_SEPARATOR)
        else:
            # Synthetic line (status message, no docker source) — pad with
            # spaces so the message column lines up with sourced lines.
            line.append(" " * (SOURCE_COL_WIDTH + 3), style=palette.COLOR_DIM)

        # Message body.
        line.append(message, style=palette.style_for_level(level))
        return line
