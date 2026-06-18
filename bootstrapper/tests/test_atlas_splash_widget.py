from ui.textual.widgets.atlas_splash import AtlasSplash


def test_full_progress_blanks_every_cell():
    s = AtlasSplash(100, on_done=lambda: None)
    s._progress = 1.0
    assert s._blank_cell_count() == s._n_cells


def test_zero_progress_blanks_nothing():
    s = AtlasSplash(100, on_done=lambda: None)
    s._progress = 0.0
    assert s._blank_cell_count() == 0


def test_skip_is_idempotent():
    calls = []
    s = AtlasSplash(100, on_done=lambda: calls.append(1))
    s.skip()
    s.skip()
    assert calls == [1]
