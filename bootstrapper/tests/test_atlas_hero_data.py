import json
import re
from pathlib import Path

import pytest

ASSETS = Path(__file__).resolve().parent.parent / "ui" / "textual" / "assets"
BREAKPOINTS = (80, 100, 120, 160)
PROFILE_BREAKPOINTS = (60, 80, 100, 120)
_HEX = re.compile(r"^#[0-9a-f]{6}$")


def _assert_wellformed(data, cols):
    assert data["cols"] == cols
    assert data["rows"] == len(data["cells"]) > 0
    for row in data["cells"]:
        assert len(row) == cols
        for glyph, fg, bg in row:
            assert isinstance(glyph, str) and len(glyph) == 1
            assert _HEX.match(fg) and _HEX.match(bg)


@pytest.mark.parametrize("cols", BREAKPOINTS)
def test_hero_grid_is_wellformed(cols):
    _assert_wellformed(
        json.loads((ASSETS / f"atlas_hero_{cols}.json").read_text(encoding="utf-8")), cols
    )


@pytest.mark.parametrize("cols", PROFILE_BREAKPOINTS)
def test_profile_grid_is_wellformed(cols):
    _assert_wellformed(
        json.loads((ASSETS / f"atlas_profile_{cols}.json").read_text(encoding="utf-8")), cols
    )
