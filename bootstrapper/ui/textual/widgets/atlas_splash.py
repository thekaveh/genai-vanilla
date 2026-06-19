"""Atlas opening splash.

A full-screen, semi-transparent dim overlay (the wizard shows through dimmed)
with the poster centered on top; holds briefly, then fades out to reveal the
wizard. Any key or mouse press skips.

The poster renders SMOOTHLY via the terminal's inline-image protocol on
image-capable terminals (iTerm2, Kitty, WezTerm, Ghostty). On terminals that
cannot paint inline images inside a full-screen TUI (Warp, Apple Terminal, VS
Code) it falls back to the committed block-art rendering — so the splash is
never blank or garbled.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from textual import events
from textual.app import ComposeResult
from textual.containers import Container

from ui.textual.widgets.atlas_hero import AtlasHero  # block-art fallback

# Repo-root assets/atlas-poster.png (artwork + ATLAS-PLATFORM wordmark).
POSTER = Path(__file__).resolve().parents[4] / "assets" / "atlas-poster.png"


def should_show_splash(no_splash: bool) -> bool:
    """False when suppressed by ``--no-splash`` / ``ATLAS_NO_SPLASH``, or when
    the poster is missing. (Non-TTY / CI is excluded upstream.)"""
    if no_splash:
        return False
    if (os.environ.get("ATLAS_NO_SPLASH", "") or "").strip():
        return False
    return POSTER.is_file()


def image_capable() -> bool:
    """Whether this terminal reliably paints inline images inside a TUI.

    Allowlist of known-good terminals; everything else (notably Warp, which
    garbles the protocol inside the alternate screen) gets the block-art
    fallback. Conservative by design: unknown terminals fall back.
    """
    tp = os.environ.get("TERM_PROGRAM", "")
    term = os.environ.get("TERM", "")
    if tp in ("WarpTerminal", "Apple_Terminal", "vscode"):
        return False
    if tp in ("iTerm.app", "WezTerm", "ghostty"):
        return True
    if term in ("xterm-kitty", "xterm-ghostty") or os.environ.get("KITTY_WINDOW_ID"):
        return True
    return False


class AtlasSplash(Container):
    """Dim overlay + centered poster; holds, then removes itself (revealing the
    wizard). Timer-guaranteed removal so it can never stick on a blank screen."""

    DEFAULT_CSS = """
    AtlasSplash {
        width: 100%;
        height: 100%;
        background: #0a0b12 80%;
        align: center middle;
    }
    """

    can_focus = True

    def __init__(self, *, hold: float = 4.0,
                 on_done: Callable[[], None] | None = None) -> None:
        super().__init__()
        self._hold = hold
        self._on_done = on_done or (lambda: None)
        self._done = False
        self._timer = None

    def compose(self) -> ComposeResult:
        if image_capable():
            from textual_image.widget import Image
            img = Image(str(POSTER))
            self._fit(img)
            yield img
        else:
            # Block-art fallback (no inline-image support): the committed
            # cell-grid artwork, sized to fit the screen width.
            width = max(80, int((self.app.size.width or 100) * 0.8))
            yield AtlasHero(width)

    def _fit(self, img) -> None:
        """Explicit, aspect-correct, contained size so the image paints
        immediately (not lazily) and is never stretched."""
        try:
            from PIL import Image as _PIL
            from textual_image.widget import get_cell_size
            pw, ph = _PIL.open(POSTER).size
            cw, ch = get_cell_size()
            ratio = (pw / ph) * (ch / cw)
            max_cols = max(1, int(self.app.size.width * 0.8))
            max_rows = max(1, int(self.app.size.height * 0.8))
            rows = max_rows
            cols = int(rows * ratio)
            if cols > max_cols:
                cols = max_cols
                rows = int(cols / ratio)
            img.styles.width = cols
            img.styles.height = rows
        except Exception:  # noqa: BLE001 — never let sizing crash the splash
            pass

    def on_mount(self) -> None:
        self.focus()
        self._timer = self.set_timer(self._hold, self._finish)
        # Nudge a repaint after the first render settles (some terminals need
        # it to actually emit the inline image).
        self.call_after_refresh(self._nudge)

    def _nudge(self) -> None:
        try:
            self.refresh(layout=True)
            for child in self.children:
                child.refresh()
        except Exception:  # noqa: BLE001
            pass

    def _finish(self) -> None:
        if self._done:
            return
        self._done = True
        if self._timer is not None:
            self._timer.stop()
        try:
            self.remove()
        except Exception:  # noqa: BLE001 — removal outside a running app is a no-op
            pass
        self._on_done()

    def skip(self) -> None:
        """Skip the hold and reveal the wizard immediately."""
        self._finish()

    def on_key(self, event: events.Key) -> None:
        event.stop()
        self.skip()

    def on_mouse_down(self, event: events.MouseDown) -> None:
        event.stop()
        self.skip()
