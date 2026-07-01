import pytest
from rich.text import Text

from ui.textual.widgets.atlas_hero import load_hero, hero_rows


@pytest.mark.parametrize("width,expected_cols", [
    (200, 160), (160, 160), (159, 120), (120, 120),
    (110, 100), (100, 100), (90, 80), (80, 80),
    (79, 60), (60, 60),
])
def test_load_hero_picks_largest_fitting_breakpoint(width, expected_cols):
    data = load_hero(width)
    assert data is not None and data["cols"] == expected_cols


def test_load_hero_returns_none_below_min():
    assert load_hero(59) is None


def test_hero_rows_render_one_text_per_row_full_width():
    data = load_hero(100)
    rows = hero_rows(data)
    assert len(rows) == data["rows"]
    assert all(isinstance(t, Text) for t in rows)
    assert len(rows[0].plain) == data["cols"]


def test_atlas_hero_grid_rows_matches_data():
    from ui.textual.widgets.atlas_hero import AtlasHero, load_hero
    hero = AtlasHero(100)
    assert hero.grid_rows == load_hero(100)["rows"]


def test_atlas_hero_below_min_is_empty():
    from ui.textual.widgets.atlas_hero import AtlasHero
    hero = AtlasHero(50)
    assert hero.grid_rows == 0


def test_atlas_hero_render_returns_renderable():
    from ui.textual.widgets.atlas_hero import AtlasHero
    hero = AtlasHero(100)
    assert hero.render() is not None


def test_atlas_hero_centering_padding_uses_image_background():
    from rich.align import Align
    from rich.console import Group
    from ui.textual.widgets.atlas_hero import AtlasHero, HERO_BACKGROUND

    renderable = AtlasHero(60).render()

    assert isinstance(renderable, Group)
    rows = list(renderable.renderables)
    assert rows
    assert all(isinstance(row, Align) for row in rows)
    assert all(row.style.bgcolor is not None for row in rows)
    assert {row.style.bgcolor.triplet for row in rows} == {
        HERO_BACKGROUND.bgcolor.triplet,
    }
