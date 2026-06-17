"""Atlas opening-splash: pure logic (Task 3) + Textual widget (Task 4)."""
from __future__ import annotations

import os
import random


def should_show_splash(no_splash: bool) -> bool:
    if no_splash:
        return False
    if (os.environ.get("ATLAS_NO_SPLASH", "") or "").strip():
        return False
    return True


def dissolve_order(n_cells: int, seed: int = 1337) -> list[int]:
    idx = list(range(n_cells))
    random.Random(seed).shuffle(idx)
    return idx


def dissolved_count(n_cells: int, progress: float) -> int:
    p = max(0.0, min(1.0, progress))
    return round(p * n_cells)
