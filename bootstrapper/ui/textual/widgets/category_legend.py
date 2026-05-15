"""
CategoryLegend — single-line strip below ServiceTable explaining the category
color bars. Six chips: ▰▰ in category color + label.
"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget

from .. import palette as P


# Display order matches services/topology.py::CATEGORY_ORDER.
_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("infra",  "Infrastructure"),
    ("data",   "Data"),
    ("llm",    "LLM Core"),
    ("media",  "Media"),
    ("agents", "Agents & Workflows"),
    ("apps",   "Apps & UIs"),
)


class CategoryLegend(Widget):
    """One-line legend mapping bar colors to category labels."""

    DEFAULT_CSS = """
    CategoryLegend { height: auto; padding: 1 0 0 0; }
    """

    can_focus = False

    def render(self) -> Text:
        out = Text()
        first = True
        for slug, label in _CATEGORIES:
            if not first:
                out.append("   ", style=P.TEXT_FAINT)
            first = False
            out.append("▰▰", style=P.style_for_category(slug))
            out.append(" ")
            out.append(label, style=P.TEXT)
        return out
