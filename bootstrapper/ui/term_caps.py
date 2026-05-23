"""Terminal-capability gate for the Textual TUI.

Returns False when the user opted out (--no-tui), stdin/stdout aren't TTYs
(CI, piped runs), the terminal is too small to host the wizard, or the
TERM environment variable indicates a known-limited terminal (e.g.
TERM=dumb in some CI shells, TERM=linux on bare-metal Linux consoles).
start.py falls back to the linear stdout flow in those cases.
"""

import os
import shutil
import sys

MIN_TERMINAL_ROWS = 20
MIN_TERMINAL_COLS = 60

# Terminals that don't support the cursor-addressable / 256-color
# behavior Textual requires. ``dumb`` is what Emacs M-x shell, some CI
# runners, and unconfigured TERM environments report. ``linux`` is the
# bare-metal console kernel driver — usable for basic curses but no
# truecolor / unicode-art.
_LIMITED_TERMS = {"dumb", "linux"}


def is_tui_capable(no_tui_flag: bool = False) -> bool:
    if no_tui_flag:
        return False
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False
    if os.environ.get("TERM", "").strip().lower() in _LIMITED_TERMS:
        return False
    try:
        size = shutil.get_terminal_size()
    except OSError:
        return False
    return size.columns >= MIN_TERMINAL_COLS and size.lines >= MIN_TERMINAL_ROWS
