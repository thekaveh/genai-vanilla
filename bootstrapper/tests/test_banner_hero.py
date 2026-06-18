from utils.banner import BannerDisplay


def test_hero_suppressed_when_no_splash(monkeypatch):
    monkeypatch.setattr(BannerDisplay, "get_terminal_width", lambda self: 120)
    assert BannerDisplay().show_hero(no_splash=True) is False


def test_hero_suppressed_when_too_narrow(monkeypatch):
    monkeypatch.setattr(BannerDisplay, "get_terminal_width", lambda self: 70)
    assert BannerDisplay().show_hero(no_splash=False) is False


def test_hero_prints_when_wide(monkeypatch):
    monkeypatch.setattr(BannerDisplay, "get_terminal_width", lambda self: 120)
    assert BannerDisplay().show_hero(no_splash=False) is True
