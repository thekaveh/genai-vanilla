from pathlib import Path

from ui.textual.widgets.atlas_splash import image_capable, should_show_splash


def test_show_decision(monkeypatch):
    # The committed poster exists, so with no suppression the splash shows.
    monkeypatch.delenv("ATLAS_NO_SPLASH", raising=False)
    assert should_show_splash(no_splash=False) is True
    assert should_show_splash(no_splash=True) is False
    monkeypatch.setenv("ATLAS_NO_SPLASH", "1")
    assert should_show_splash(no_splash=False) is False


def test_show_decision_requires_poster(monkeypatch):
    import ui.textual.widgets.atlas_splash as m
    monkeypatch.delenv("ATLAS_NO_SPLASH", raising=False)
    monkeypatch.setattr(m, "POSTER", Path("/nonexistent/atlas-poster.png"))
    assert should_show_splash(no_splash=False) is False


def test_image_capability_allowlist(monkeypatch):
    def caps(term_program="", term="", kitty=False):
        monkeypatch.setenv("TERM_PROGRAM", term_program)
        monkeypatch.setenv("TERM", term)
        if kitty:
            monkeypatch.setenv("KITTY_WINDOW_ID", "1")
        else:
            monkeypatch.delenv("KITTY_WINDOW_ID", raising=False)
        return image_capable()

    # Capable terminals
    assert caps(term_program="iTerm.app") is True
    assert caps(term_program="WezTerm") is True
    assert caps(term_program="ghostty") is True
    assert caps(term="xterm-kitty") is True
    assert caps(kitty=True) is True
    # Not capable (Warp garbles inline images in the TUI) + unknown -> fallback
    assert caps(term_program="WarpTerminal") is False
    assert caps(term_program="Apple_Terminal") is False
    assert caps(term_program="vscode") is False
    assert caps(term_program="", term="xterm-256color") is False
