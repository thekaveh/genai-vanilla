from __future__ import annotations

import json
import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_DIR = ROOT / "services" / "jupyterhub" / "build" / "notebooks"
COMPOSE_FILE = ROOT / "services" / "jupyterhub" / "compose.yml"


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


def test_jupyterhub_notebook_cell_ids_are_nbformat_45_complete_and_unique():
    for path in sorted(NOTEBOOK_DIR.glob("*.ipynb")):
        notebook = json.loads(path.read_text(encoding="utf-8"))
        cells = notebook.get("cells", [])
        ids = [cell.get("id") for cell in cells]
        has_cell_ids = any(cell_id is not None for cell_id in ids)
        if has_cell_ids:
            assert notebook.get("nbformat") == 4
            assert notebook.get("nbformat_minor", 0) >= 5, (
                f"{path} has cell IDs but declares nbformat_minor "
                f"{notebook.get('nbformat_minor')}; cell IDs require 4.5+"
            )
        if notebook.get("nbformat") == 4 and notebook.get("nbformat_minor", 0) >= 5:
            assert all(isinstance(cell_id, str) and cell_id for cell_id in ids), (
                f"{path} declares nbformat 4.5+ but has cells without IDs"
            )
            assert len(ids) == len(set(ids)), f"{path} has duplicate cell IDs"


def test_jupyterhub_allow_origin_flag_uses_env_knob():
    compose = yaml.safe_load(COMPOSE_FILE.read_text(encoding="utf-8"))
    command = compose["services"]["jupyterhub"]["command"]

    assert "--ServerApp.allow_origin=${JUPYTER_ALLOW_ORIGIN:-*}" in command
