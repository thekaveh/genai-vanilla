from ui.textual.widgets.atlas_splash import (
    should_show_splash, dissolve_order, dissolved_count,
)


def test_show_decision(monkeypatch):
    monkeypatch.delenv("ATLAS_NO_SPLASH", raising=False)
    assert should_show_splash(no_splash=False) is True
    assert should_show_splash(no_splash=True) is False
    monkeypatch.setenv("ATLAS_NO_SPLASH", "1")
    assert should_show_splash(no_splash=False) is False


def test_dissolve_order_is_deterministic_permutation():
    a = dissolve_order(500)
    b = dissolve_order(500)
    assert a == b
    assert sorted(a) == list(range(500))


def test_dissolved_count_bounds():
    assert dissolved_count(100, 0.0) == 0
    assert dissolved_count(100, 1.0) == 100
    assert dissolved_count(100, 0.5) == 50
    assert dissolved_count(100, 2.0) == 100
    assert dissolved_count(100, -1.0) == 0
