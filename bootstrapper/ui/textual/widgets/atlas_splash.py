"""Atlas opening splash.

A full-screen overlay tinted to the poster's own dark navy (the wizard shows
through dimmed) with the landscape poster artwork centered on top; holds
briefly, then removes itself to reveal the wizard. Any key or mouse press skips.

The artwork (``assets/atlas-poster.png`` — landscape, with the ATLAS-PLATFORM
wordmark) renders SMOOTHLY via the terminal's inline-image protocol on
image-capable terminals (iTerm2, Kitty, WezTerm, Ghostty). On terminals that
garble that protocol inside a TUI (Warp, Apple Terminal, VS Code) it renders
the SAME artwork as a committed colored block-art cell-grid (``AtlasHero``) —
pure Rich text, so it always shows, never blank, garbled, or crashing.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from textual import events
from textual.app import ComposeResult
from textual.containers import Container

# Repo-root assets/atlas-poster.png (landscape artwork + ATLAS-PLATFORM wordmark).
POSTER = Path(__file__).resolve().parents[4] / "assets" / "atlas-poster.png"


def should_show_splash(no_splash: bool) -> bool:
    """False when the master switch is off (``feature_flags.splash_enabled``),
    when suppressed by ``--no-splash`` / ``ATLAS_NO_SPLASH``, or when the
    artwork is missing. (Non-TTY / CI is excluded upstream.)"""
    from feature_flags import splash_enabled
    if not splash_enabled():
        return False
    if no_splash:
        return False
    if (os.environ.get("ATLAS_NO_SPLASH", "") or "").strip():
        return False
    return POSTER.is_file()


def image_capable() -> bool:
    """Whether this terminal reliably paints inline images inside a TUI.

    Allowlist of known-good terminals; everything else (notably Warp, which
    garbles the protocol inside the alternate screen) uses the half-cell text
    renderer instead. Conservative: unknown terminals use half-cell.
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
    """Navy overlay + centered poster artwork; holds, then removes itself
    (revealing the wizard). Timer-guaranteed removal so it can never stick."""

    DEFAULT_CSS = """
    AtlasSplash {
        width: 100%;
        height: 100%;
        background: #000412 88%;
        align: center middle;
    }
    AtlasSplash AtlasHero { width: auto; height: auto; }
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
        yield self._make_artwork()

    def _make_artwork(self):
        """Smooth inline image on capable terminals; otherwise the committed
        block-art cell-grid (pure Rich text — never queries the terminal, so it
        can't crash, unlike a half-cell/protocol image widget in Warp)."""
        if image_capable():
            try:
                from textual_image.widget import Image
                img = Image(str(POSTER))
                self._fit(img)
                return img
            except Exception:  # noqa: BLE001 — degrade to block-art, never crash
                pass
        from ui.textual.widgets.atlas_hero import AtlasHero
        avail_w = max(60, int((self.app.size.width or 100) * 0.85))
        avail_h = max(10, int((self.app.size.height or 30) * 0.82))
        return AtlasHero(avail_w, height=avail_h, prefix="atlas_poster")

    def _fit(self, img) -> None:
        """Explicit, aspect-correct, contained size so the artwork paints
        immediately and is never stretched."""
        try:
            from PIL import Image as _PIL
            from textual_image.widget import get_cell_size
            pw, ph = _PIL.open(POSTER).size
            cw, ch = get_cell_size()
            ratio = (pw / ph) * (ch / cw)  # cols:rows for true aspect
            max_cols = max(1, int(self.app.size.width * 0.8))
            max_rows = max(1, int(self.app.size.height * 0.82))
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
