"""Terminal-capability gate for the Textual TUI.

Returns False when the user opted out (--no-tui), stdin/stdout aren't TTYs
(CI, piped runs), or the terminal is too small to host the wizard. start.py
falls back to the linear stdout flow in that case.
"""

import shutil
import sys

MIN_TERMINAL_ROWS = 20
MIN_TERMINAL_COLS = 60


def is_tui_capable(no_tui_flag: bool = False) -> bool:
    if no_tui_flag:
        return False
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False
    try:
        size = shutil.get_terminal_size()
    except OSError:
        return False
    return size.columns >= MIN_TERMINAL_COLS and size.lines >= MIN_TERMINAL_ROWS
