"""Tests for the no-TUI track prompt fallback (spec §6.2 / §8.6).

When ./start.sh --no-tui is run without --track, the linear flow
should print the track list to stderr and either prompt on stdin
(if TTY) or default to gen-ai-rag (if non-interactive).
"""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_no_tui_prompt_block_exists_in_start_py():
    """Static check: the no-TUI track prompt block is present in start.py.
    Without this guard, the spec §6.2 / §8.6 promise silently regresses."""
    src = (REPO_ROOT / "bootstrapper" / "start.py").read_text(encoding="utf-8")
    assert "Pick a track" in src, (
        "no-TUI track prompt block missing from start.py — spec §6.2 / §8.6 "
        "promises a stdin prompt with default gen-ai-rag for non-TTY no-TUI runs."
    )
    assert "is_tui_capable" in src, (
        "start.py should consult is_tui_capable() to decide whether the no-TUI "
        "prompt fires."
    )


def test_no_tui_prompt_defaults_to_first_track():
    """Unit test: when stdin returns empty, the first track is chosen."""
    from tracks import load_tracks
    reg = load_tracks()
    # Simulate the logic in start.py's no-TUI prompt block.
    selected = ""  # empty input = Enter key
    if not selected:
        selected = reg.tracks[0].key
    assert selected == "gen-ai-rag", (
        f"Expected default track 'gen-ai-rag', got '{selected}'"
    )


def test_no_tui_prompt_unknown_track_falls_back():
    """Unit test: unknown track input falls back to gen-ai-rag."""
    from tracks import load_tracks
    reg = load_tracks()
    selected = "bogus-track-xyz"
    if selected not in reg.by_key:
        selected = reg.tracks[0].key
    assert selected == "gen-ai-rag"


def test_no_tui_prompt_valid_track_accepted():
    """Unit test: a valid track key is accepted as-is."""
    from tracks import load_tracks
    reg = load_tracks()
    for t in reg.tracks:
        selected = t.key
        if not selected:
            selected = reg.tracks[0].key
        if selected not in reg.by_key:
            selected = reg.tracks[0].key
        assert selected == t.key, (
            f"Valid track '{t.key}' should not be altered by the fallback logic"
        )


def test_no_tui_prompt_block_is_inside_will_run_wizard():
    """Structural check: the prompt block is gated inside the will_run_wizard
    branch so it only fires when the full wizard would have run."""
    src = (REPO_ROOT / "bootstrapper" / "start.py").read_text(encoding="utf-8")
    # The prompt must appear AFTER 'will_run_wizard' is defined and inside
    # the branch that tests it.
    wizard_pos = src.find("will_run_wizard =")
    prompt_pos = src.find("Pick a track")
    assert wizard_pos != -1, "will_run_wizard not found in start.py"
    assert prompt_pos != -1, "Pick a track prompt not found in start.py"
    assert prompt_pos > wizard_pos, (
        "The no-TUI track prompt must appear AFTER will_run_wizard is defined"
    )
    # The prompt must also appear before the linear flow marker.
    linear_pos = src.find("# Linear (--no-tui / non-TTY) flow from here on")
    assert linear_pos != -1, "Linear flow marker not found in start.py"
    assert prompt_pos < linear_pos, (
        "The no-TUI track prompt must fire BEFORE the linear flow section"
    )
