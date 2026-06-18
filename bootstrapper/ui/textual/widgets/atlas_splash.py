"""Atlas opening-splash: pure logic (Task 3) + Textual widget (Task 4)."""
from __future__ import annotations

import os
import random
from typing import Callable

from rich.align import Align
from rich.console import Group, RenderableType
from rich.style import Style
from rich.text import Text
from textual import events
from textual.widget import Widget

from ui.textual.widgets.atlas_hero import load_hero


def should_show_splash(no_splash: bool) -> bool:
    if no_splash:
        return False
    if (os.environ.get("ATLAS_NO_SPLASH", "") or "").strip():
        return False
    return True


def dissolve_order(n_cells: int, seed: int = 1337) -> list[int]:
    idx = list(range(n_cells))
    random.Random(seed).shuffle(idx)
    return idx


def dissolved_count(n_cells: int, progress: float) -> int:
    p = max(0.0, min(1.0, progress))
    return round(p * n_cells)


class AtlasSplash(Widget):
    """Overlay that holds the hero, then pixel-dissolves to reveal the
    wizard beneath, removing itself when done. Any key/mouse skips."""

    DEFAULT_CSS = """
    AtlasSplash { width: 100%; height: 100%; background: transparent; }
    """

    can_focus = True

    def __init__(self, width: int, *, hold: float = 3.0, frames: int = 14,
                 on_done: Callable[[], None]) -> None:
        super().__init__()
        self._data = load_hero(width)
        self._hold = hold
        self._frames = max(1, frames)
        self._on_done = on_done
        self._done = False
        self._progress = 0.0
        self._step = 0
        self._hold_timer = None
        self._interval = None
        cols = self._data["cols"] if self._data else 0
        rows = self._data["rows"] if self._data else 0
        self._n_cells = cols * rows
        self._order = dissolve_order(self._n_cells)

    # --- rendering -----------------------------------------------------
    def _blank_indices(self) -> set[int]:
        return set(self._order[: dissolved_count(self._n_cells, self._progress)])

    def _blank_cell_count(self) -> int:
        return len(self._blank_indices())

    def render(self) -> RenderableType:
        if not self._data:
            return Text("")
        blanks = self._blank_indices()
        cols = self._data["cols"]
        out: list[RenderableType] = []
        for y, row in enumerate(self._data["cells"]):
            t = Text()
            for x, (glyph, fg, bg) in enumerate(row):
                if (y * cols + x) in blanks:
                    t.append(" ")  # transparent -> wizard shows through
                else:
                    t.append(glyph, Style(color=fg, bgcolor=bg))
            out.append(Align.center(t))
        return Group(*out)

    # --- lifecycle -----------------------------------------------------
    def on_mount(self) -> None:
        self.focus()
        self._hold_timer = self.set_timer(self._hold, self._start_dissolve)

    def _start_dissolve(self) -> None:
        if self._done:
            return
        self._step = 0
        self._interval = self.set_interval(0.05, self._tick)

    def _tick(self) -> None:
        self._step += 1
        self._progress = self._step / self._frames
        self.refresh()
        if self._step >= self._frames:
            self._finish()

    def _finish(self) -> None:
        if self._done:
            return
        self._done = True
        if self._hold_timer is not None:
            self._hold_timer.stop()
        if self._interval is not None:
            self._interval.stop()
        try:
            self.remove()
        except Exception:
            pass
        self._on_done()

    def skip(self) -> None:
        if self._done:
            return
        self._progress = 1.0
        self._finish()

    def on_key(self, event: events.Key) -> None:
        event.stop()
        self.skip()

    def on_mouse_down(self, event: events.MouseDown) -> None:
        event.stop()
        self.skip()
