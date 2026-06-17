"""Branch coverage for ``term_caps.is_tui_capable`` — the production gate
that chooses between the Textual TUI and the linear --no-tui flow.

The only prior reference in the suite string-grepped ``start.py`` source
for the call; none of the five decision branches (opt-out flag, non-TTY
stdin/stdout, limited TERM, get_terminal_size OSError, size threshold)
were actually exercised.
"""

from __future__ import annotations

import os
import shutil

import pytest

from ui.term_caps import is_tui_capable, MIN_TERMINAL_COLS, MIN_TERMINAL_ROWS


@pytest.fixture
def capable_tty(monkeypatch):
    """Baseline where every signal reports 'TUI-capable'."""
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setattr(
        shutil, "get_terminal_size", lambda *a, **k: os.terminal_size((120, 40))
    )
    return monkeypatch


def test_capable_terminal_returns_true(capable_tty):
    assert is_tui_capable() is True


def test_no_tui_flag_forces_false(capable_tty):
    assert is_tui_capable(no_tui_flag=True) is False


def test_non_tty_stdin_returns_false(capable_tty):
    capable_tty.setattr("sys.stdin.isatty", lambda: False)
    assert is_tui_capable() is False


def test_non_tty_stdout_returns_false(capable_tty):
    capable_tty.setattr("sys.stdout.isatty", lambda: False)
    assert is_tui_capable() is False


@pytest.mark.parametrize("term", ["dumb", "linux", "DUMB", "Linux"])
def test_limited_term_returns_false(capable_tty, term):
    capable_tty.setenv("TERM", term)  # case-insensitive match
    assert is_tui_capable() is False


def test_get_terminal_size_oserror_returns_false(capable_tty):
    def boom(*a, **k):
        raise OSError("no controlling terminal")

    capable_tty.setattr(shutil, "get_terminal_size", boom)
    assert is_tui_capable() is False


@pytest.mark.parametrize(
    "cols,rows,expected",
    [
        (MIN_TERMINAL_COLS, MIN_TERMINAL_ROWS, True),        # exactly at threshold
        (MIN_TERMINAL_COLS - 1, MIN_TERMINAL_ROWS, False),   # one column too narrow
        (MIN_TERMINAL_COLS, MIN_TERMINAL_ROWS - 1, False),   # one row too short
    ],
)
def test_size_threshold_boundary(capable_tty, cols, rows, expected):
    capable_tty.setattr(
        shutil, "get_terminal_size", lambda *a, **k: os.terminal_size((cols, rows))
    )
    assert is_tui_capable() is expected
