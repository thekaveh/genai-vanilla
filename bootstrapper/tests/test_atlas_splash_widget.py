from ui.textual.widgets.atlas_splash import AtlasSplash


def test_skip_is_idempotent():
    calls = []
    s = AtlasSplash(on_done=lambda: calls.append(1))
    s.skip()
    s.skip()
    assert calls == [1]


def test_skip_marks_done_and_fires_callback():
    calls = []
    s = AtlasSplash(on_done=lambda: calls.append(1))
    assert s._done is False
    s.skip()
    assert s._done is True
    assert calls == [1]


def test_on_done_optional():
    # on_done defaults to a no-op; skip must not raise without a callback.
    AtlasSplash().skip()
