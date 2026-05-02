"""
Status ribbon renderable — single-line "Step N/Total · message" between
the box and the log pane.

Always renders one line (occupies a constant 1 row), so the log pane's
height calculation can rely on it. When idle (no message set), renders a
thin dim separator instead so the visual structure is preserved.
"""

from typing import Optional

from rich.spinner import Spinner
from rich.text import Text
from rich.console import Group, RenderableType
from rich.columns import Columns

from ui import palette


class StatusRibbon:
    """
    Owns the current ribbon state and renders it on demand.

    Mutated via `set()`; rendered via `render()`. The Live shell calls
    `render()` each refresh tick.
    """

    def __init__(self):
        self._step: int = 0
        self._total: int = 0
        self._message: str = ""
        self._level: str = "info"
        self._spinner_active: bool = False
        # The Spinner object is reused across renders so its animation
        # advances naturally between Live refreshes.
        self._spinner: Optional[Spinner] = None

    def set(
        self,
        step: int = 0,
        total: int = 0,
        message: str = "",
        level: str = "info",
        spinner: bool = False,
    ) -> None:
        """
        Update the ribbon. Pass spinner=True to show an animated dots glyph
        next to the message — used during long-running operations
        (cold cleanup, image build, etc.) so the UI doesn't look frozen.
        """
        self._step = step
        self._total = total
        self._message = message
        self._level = level
        self._spinner_active = spinner
        if spinner and self._spinner is None:
            self._spinner = Spinner("dots", style=palette.COLOR_ACCENT)
        if not spinner:
            self._spinner = None

    def clear(self) -> None:
        """Reset to idle (renders as a thin separator only)."""
        self.set(step=0, total=0, message="", level="info", spinner=False)

    def title_text(self) -> Optional[Text]:
        """
        Return the current status formatted as a Rich Text suitable for use
        as a Panel border title (e.g. on the wizard's widget panel). Returns
        None when no message is set — caller can omit the title.

        The returned text is wrapped in single spaces so it sits cleanly
        inside the panel's border characters when rendered as a title.
        """
        if not self._message:
            return None
        text = Text(f" {self._message} ", style=palette.style_for_level(self._level))
        return text

    def render(self, width: int) -> RenderableType:
        """Render the ribbon as a one-line renderable."""
        if not self._message and self._step == 0:
            # Idle — return a thin separator line so the visual structure
            # between box and log pane is preserved.
            sep = Text("─" * max(width, 1), style=palette.COLOR_SEPARATOR)
            return sep

        line = Text()

        # Step counter (when set): "8/9 · "
        if self._total > 0:
            line.append(f"{self._step}/{self._total}", style=palette.COLOR_DIM)
            line.append("  ·  ", style=palette.COLOR_SEPARATOR)

        # Message in the level color.
        line.append(self._message, style=palette.style_for_level(self._level))

        # Spinner — composed alongside the text using Columns so the
        # animation cell stays distinct from the message text.
        if self._spinner_active and self._spinner is not None:
            return Columns([self._spinner, line], padding=(0, 1), expand=False)

        return line
