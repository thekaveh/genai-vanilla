"""
Number widget — keyboard-driven number input rendered inside the Live region.

Used by the wizard's base-port prompt.

Keys:
  ↑ / ↓        ±1
  PgUp / PgDn  ±100  (avoids shift+arrow combos which readchar reports
                     inconsistently across terminals)
  digits 0-9   append to a typed value (typing mode)
  backspace    delete last typed digit
  Enter        confirm
  Esc          cancel (returns None)
  Ctrl+C       quit (raises KeyboardInterrupt)

The current value is clamped to [min_allowed, max_allowed] on every update.
"""

from __future__ import annotations

from typing import Optional

import readchar

from rich.align import Align
from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from ui import palette


def number(
    app,
    prompt: str,
    *,
    default: int,
    min_allowed: int,
    max_allowed: int,
) -> Optional[int]:
    """
    Show a number-entry prompt. Returns the chosen int, or None on Esc.
    Raises KeyboardInterrupt on Ctrl+C.
    """
    value = _clamp(default, min_allowed, max_allowed)
    typing_buffer = ""  # accumulates digit keys; commits on next non-digit

    def renderable():
        # Title comes from app.status_ribbon — the wizard sets the step
        # counter ("Step 12 of 15") right before showing each widget.
        title = app.status_ribbon.title_text()
        return _build_panel(prompt, value, min_allowed, max_allowed, typing_buffer, title=title)

    with app._show_widget(renderable()):
        while True:
            key = readchar.readkey()
            if key == readchar.key.CTRL_C:
                raise KeyboardInterrupt
            if key == readchar.key.ESC:
                return None
            if key in (readchar.key.ENTER, "\r", "\n"):
                # Commit any pending typed digits before returning.
                if typing_buffer:
                    try:
                        value = _clamp(int(typing_buffer), min_allowed, max_allowed)
                    except ValueError:
                        pass
                return value
            if key == readchar.key.UP:
                value = _clamp(value + 1, min_allowed, max_allowed)
                typing_buffer = ""
            elif key == readchar.key.DOWN:
                value = _clamp(value - 1, min_allowed, max_allowed)
                typing_buffer = ""
            elif key == readchar.key.PAGE_UP:
                value = _clamp(value + 100, min_allowed, max_allowed)
                typing_buffer = ""
            elif key == readchar.key.PAGE_DOWN:
                value = _clamp(value - 100, min_allowed, max_allowed)
                typing_buffer = ""
            elif isinstance(key, str) and key.isdigit():
                # Typing mode — accumulate digits, preview as the displayed
                # value. Commit happens on Enter or any non-digit non-arrow key.
                if len(typing_buffer) < 6:  # cap at 6 digits (max port = 65535)
                    typing_buffer += key
                    try:
                        candidate = int(typing_buffer)
                        # Show the typed value live, even if temporarily out
                        # of range — clamp only on commit so the user can
                        # backspace and continue typing.
                        value = candidate
                    except ValueError:
                        pass
            elif key == readchar.key.BACKSPACE:
                typing_buffer = typing_buffer[:-1]
                if typing_buffer:
                    try:
                        value = int(typing_buffer)
                    except ValueError:
                        pass
                else:
                    value = default
            else:
                # Any other key: refresh widget so the typed buffer is reset
                # if the user starts navigating again.
                pass
            app.update_widget(renderable())


def _clamp(value: int, min_allowed: int, max_allowed: int) -> int:
    return max(min_allowed, min(value, max_allowed))


def _build_panel(prompt: str, value: int, lo: int, hi: int, typing: str, title=None):
    rows = [Text(prompt, style=palette.COLOR_TITLE)]

    # Current value, prominent.
    val_line = Text()
    val_line.append("  ▸ ", style=palette.COLOR_ACCENT)
    val_line.append(str(value), style=palette.COLOR_ACCENT)

    # Show range + clamp warning if the typed value is out of range.
    range_text = f"  (range: {lo}–{hi})"
    if value < lo or value > hi:
        val_line.append(range_text, style=palette.COLOR_WARN)
    else:
        val_line.append(range_text, style=palette.COLOR_DIM)

    rows.append(val_line)

    # Hints
    hint = Text()
    hint.append("\n  ", style=palette.COLOR_DIM)
    hint.append("↑↓", style=palette.COLOR_ACCENT)
    hint.append(" ±1  ·  ", style=palette.COLOR_DIM)
    hint.append("PgUp/PgDn", style=palette.COLOR_ACCENT)
    hint.append(" ±100  ·  ", style=palette.COLOR_DIM)
    hint.append("digits", style=palette.COLOR_ACCENT)
    hint.append(" type  ·  ", style=palette.COLOR_DIM)
    hint.append("enter", style=palette.COLOR_ACCENT)
    hint.append(" confirm  ·  ", style=palette.COLOR_DIM)
    hint.append("esc", style=palette.COLOR_ACCENT)
    hint.append(" restart", style=palette.COLOR_DIM)
    rows.append(hint)

    panel = Panel(
        Align.left(Group(*rows)),
        title=title,
        title_align="left",
        border_style=palette.COLOR_BORDER,
        padding=(1, 2),
        expand=False,
    )
    return Align.left(panel)
