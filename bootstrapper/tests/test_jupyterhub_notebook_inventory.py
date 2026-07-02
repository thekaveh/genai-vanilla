from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_DIR = ROOT / "services" / "jupyterhub" / "build" / "notebooks"


def _markdown_mentions(path: Path) -> set[str]:
    return set(re.findall(r"`([0-9][0-9]_[^`]+\.ipynb)`", path.read_text(encoding="utf-8")))


def test_jupyterhub_notebook_inventory_matches_docs_and_starter_notebook():
    notebooks = {p.name for p in NOTEBOOK_DIR.glob("*.ipynb")}
    readme_mentions = _markdown_mentions(ROOT / "services" / "jupyterhub" / "README.md")
    build_readme_mentions = _markdown_mentions(
        ROOT / "services" / "jupyterhub" / "build" / "README.md"
    )

    starter = json.loads((NOTEBOOK_DIR / "00_environment_check.ipynb").read_text())
    starter_text = "\n".join(
        "".join(cell.get("source", []))
        for cell in starter.get("cells", [])
        if cell.get("cell_type") == "markdown"
    )
    starter_mentions = set(re.findall(r"`([0-9][0-9]_[^`]+\.ipynb)`", starter_text))
    starter_mentions.add("00_environment_check.ipynb")

    assert readme_mentions == notebooks
    assert build_readme_mentions == notebooks
    assert starter_mentions == notebooks
