from utils.banner import BannerDisplay


def test_hero_suppressed_when_splash_disabled(monkeypatch):
    # Master switch OFF by default -> hero never prints, even on a wide terminal.
    monkeypatch.delenv("ATLAS_SPLASH", raising=False)
    monkeypatch.setattr(BannerDisplay, "get_terminal_width", lambda self: 120)
    assert BannerDisplay().show_hero(no_splash=False) is False


def test_hero_suppressed_when_no_splash(monkeypatch):
    monkeypatch.setenv("ATLAS_SPLASH", "1")
    monkeypatch.setattr(BannerDisplay, "get_terminal_width", lambda self: 120)
    assert BannerDisplay().show_hero(no_splash=True) is False


def test_hero_suppressed_when_too_narrow(monkeypatch):
    monkeypatch.setenv("ATLAS_SPLASH", "1")
    monkeypatch.setattr(BannerDisplay, "get_terminal_width", lambda self: 70)
    assert BannerDisplay().show_hero(no_splash=False) is False


def test_hero_prints_when_wide(monkeypatch):
    monkeypatch.setenv("ATLAS_SPLASH", "1")
    monkeypatch.setattr(BannerDisplay, "get_terminal_width", lambda self: 120)
    assert BannerDisplay().show_hero(no_splash=False) is True
