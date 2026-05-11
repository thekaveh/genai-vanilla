"""
OptionRow — single selectable option in the wizard prompt panel.

Mockup 003 layout:

Row 1:  ▸ ◉ ollama-localhost                                  [rec.] [GPU]
Row 2 (only if hint):       Use the Ollama already running on this host

Renders as 1 cell when hint is empty, 2 cells when hint is present.
Cell 1: arrow (1) + gap (1) + bullet (1) + 2-space gap + label + flex
        spacer + right-aligned badges with 2-space gap each.
Cell 2: 5-cell indent + hint in $text-faint.
"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget

from .. import palette as P


_BADGE_STYLES = {
    "rec.": P.OK,
    "rec":  P.OK,
    "default": P.OK,
    "GPU": P.RESOURCE,
    "CPU": P.TEXT_MUTED,
    "cloud": P.INFO,
    "external": P.INFO,
    "disabled": P.TEXT_FAINT,
    "container": P.OK,
}


class OptionRow(Widget):
    """1- or 2-cell option row."""

    DEFAULT_CSS = """
    OptionRow { height: auto; padding: 0 1; }
    OptionRow.option-selected { background: #1c2034; }
    """

    can_focus = False

    def __init__(
        self,
        label: str,
        *,
        hint: str = "",
        badges: list[str] | None = None,
        selected: bool = False,
        # Multi-select extras: when ``multi`` is True, the row shows a
        # ``[✓]`` / ``[ ]`` checkbox prefix and the ``checked`` flag
        # tracks user-toggled state independently of the cursor focus
        # (``selected``).
        multi: bool = False,
        checked: bool = False,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.label = label
        self.hint = hint or ""
        self.badges = badges or []
        self.selected = selected
        self.multi = multi
        self.checked = checked
        if selected:
            self.add_class("option-selected")

    def set_selected(self, value: bool) -> None:
        if value == self.selected:
            return
        self.selected = value
        self.set_class(value, "option-selected")
        self.refresh()

    def set_checked(self, value: bool) -> None:
        if value == self.checked:
            return
        self.checked = value
        self.refresh()

    def render(self) -> Text:
        width = self.size.width or 60
        # ── line 1 ─────────────────────────────────────────────
        line1 = Text()
        if self.selected:
            line1.append(P.ARROW_RIGHT, style=f"bold {P.ACCENT}")
            line1.append(" ")
            line1.append(P.DOT_FILLED, style=P.ACCENT)
        else:
            line1.append(" ")
            line1.append(" ")
            line1.append(P.DOT_HOLLOW, style=P.TEXT_FAINT)
        line1.append("  ")
        if self.multi:
            # Render checkbox prefix in addition to the dot/arrow indicator.
            box = "[✓]" if self.checked else "[ ]"
            box_color = P.OK if self.checked else P.TEXT_FAINT
            line1.append(box, style=box_color)
            line1.append(" ")
        label_color = P.ACCENT if self.selected else P.TEXT
        line1.append(self.label, style=f"bold {label_color}" if self.selected else label_color)
        # right-aligned badges
        badge_block = Text()
        for b in self.badges:
            color = _BADGE_STYLES.get(b, P.TEXT_FAINT)
            badge_block.append("  ")
            badge_block.append(f"[{b}]", style=color)
        gap = max(1, width - line1.cell_len - badge_block.cell_len - 2)
        line1.append(" " * gap)
        line1.append(badge_block)

        if not self.hint:
            return line1

        line2 = Text()
        line2.append(" " * 5)
        line2.append(self.hint, style=P.TEXT_FAINT)

        out = Text()
        out.append(line1)
        out.append("\n")
        out.append(line2)
        return out
