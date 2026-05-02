"""
Select widget — arrow-key driven choice picker rendered inside the Live
region's bottom area.

Each choice is a (value, label) pair. The widget highlights one choice at
a time; ↑/↓ navigates, Enter confirms, Esc cancels (returns None — the
wizard treats this as restart), Ctrl+C raises KeyboardInterrupt.

Choices may include an optional hint annotation (e.g. "GPU", "CPU only",
"localhost", "cloud API" — produced by `get_option_hint()` in
`wizard/service_discovery.py`) and an `is_current` marker so the user
can see which option matches the existing .env value.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import readchar

from rich.align import Align
from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from ui import palette


@dataclass
class Choice:
    """One option in a select prompt."""
    value: str               # the value returned to the caller
    label: str               # display label (the SOURCE value, usually)
    hint: str = ""           # optional context: "GPU", "CPU only", "localhost", "cloud API"
    is_current: bool = False # True if this choice matches the current .env value


def select(
    app,
    prompt: str,
    choices: List[Choice],
    default_value: Optional[str] = None,
) -> Optional[str]:
    """
    Show a select prompt in the Live region's bottom area. Returns the
    selected `value`, or None if the user pressed Esc.

    `default_value` selects which choice starts highlighted. If None or
    not present in choices, the first choice is highlighted.
    """
    if not choices:
        return None

    # Find initial highlight index.
    idx = 0
    if default_value is not None:
        for i, c in enumerate(choices):
            if c.value == default_value:
                idx = i
                break

    def renderable(highlighted_idx: int):
        # Title comes from app.status_ribbon — the wizard sets it (e.g.
        # "Step 12 of 15") right before showing each widget, so the panel
        # border carries the step counter the same way the upper info box
        # carries "Setup Wizard / by Kaveh Razavi".
        title = app.status_ribbon.title_text()
        return _build_panel(prompt, choices, highlighted_idx, title=title)

    with app._show_widget(renderable(idx)):
        while True:
            key = readchar.readkey()
            if key == readchar.key.CTRL_C:
                raise KeyboardInterrupt
            if key == readchar.key.ESC:
                return None
            if key in (readchar.key.ENTER, "\r", "\n"):
                return choices[idx].value
            if key == readchar.key.UP:
                idx = (idx - 1) % len(choices)
                app.update_widget(renderable(idx))
            elif key == readchar.key.DOWN:
                idx = (idx + 1) % len(choices)
                app.update_widget(renderable(idx))
            elif key == readchar.key.HOME:
                idx = 0
                app.update_widget(renderable(idx))
            elif key == readchar.key.END:
                idx = len(choices) - 1
                app.update_widget(renderable(idx))
            # All other keys: ignore (don't redraw — minor optimization).


def _build_panel(prompt: str, choices: List[Choice], highlighted_idx: int, title=None):
    """Render the prompt + choice list + nav hint as a Rich Panel."""
    rows = [Text(prompt, style=palette.COLOR_TITLE)]

    for i, choice in enumerate(choices):
        rows.append(_render_choice_row(choice, highlighted=(i == highlighted_idx)))

    # Nav hints — always shown at the bottom so the user knows the keys.
    hint = Text()
    hint.append("\n  ", style=palette.COLOR_DIM)
    hint.append("↑↓", style=palette.COLOR_ACCENT)
    hint.append(" navigate  ·  ", style=palette.COLOR_DIM)
    hint.append("enter", style=palette.COLOR_ACCENT)
    hint.append(" select  ·  ", style=palette.COLOR_DIM)
    hint.append("esc", style=palette.COLOR_ACCENT)
    hint.append(" restart  ·  ", style=palette.COLOR_DIM)
    hint.append("ctrl+c", style=palette.COLOR_ACCENT)
    hint.append(" quit", style=palette.COLOR_DIM)
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


def _render_choice_row(choice: Choice, *, highlighted: bool) -> Text:
    """One choice row: pointer + label + optional hint + (current) marker."""
    line = Text()
    if highlighted:
        line.append("  ▸ ", style=palette.COLOR_ACCENT)
    else:
        line.append("    ", style=palette.COLOR_DIM)

    label_style = palette.COLOR_ACCENT if highlighted else palette.COLOR_TEXT
    line.append(choice.label, style=label_style)

    annotations = []
    if choice.hint:
        annotations.append(choice.hint)
    if choice.is_current:
        annotations.append("current")
    if annotations:
        line.append(f"  ({', '.join(annotations)})", style=palette.COLOR_DIM)

    return line
