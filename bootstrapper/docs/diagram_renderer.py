"""DepGraph → HTML+SVG renderer.

Applies the architecture-diagram skill's design system programmatically.
Output is byte-deterministic for the same DepGraph (no timestamps in SVG
body; timestamps live in the HTML footer only).
"""

from __future__ import annotations

import html
import sys
from pathlib import Path
from string import Template

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "bootstrapper"))

from services.topology import CATEGORY_COLORS  # noqa: E402

from .deps_resolver import DepEdge, DepGraph

TEMPLATE_DIR = Path(__file__).parent / "templates"

# ───── Geometry constants ────────────────────────────────────────────────
LANE_W = 240
BOX_W = 200
BOX_H = 60
BOX_GAP = 40
LANE_X = {
    "upstream":   60,
    "focus":      60 + LANE_W + 60,
    "downstream": 60 + LANE_W + 60 + 200 + 60,  # focus is 200 wide
}
FOCUS_W = 200
FOCUS_H = 120
LANE_HEADER_Y = 36
ROWS_TOP_Y = 80


def render_svg(graph: DepGraph) -> str:
    """Render the architecture SVG. Pure function of graph state."""

    defs = (TEMPLATE_DIR / "svg_defs.tmpl").read_text()
    rows = max(len(graph.upstream), len(graph.downstream), 1)
    height = ROWS_TOP_Y + rows * (BOX_H + BOX_GAP) + 40
    width = LANE_X["downstream"] + BOX_W + 60

    parts: list[str] = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">')
    parts.append(defs)
    parts.append(f'<rect width="{width}" height="{height}" fill="url(#grid)"/>')

    # Lane headers
    parts.append(_text(LANE_X["upstream"] + LANE_W // 2 - 80, LANE_HEADER_Y, "UPSTREAM (deps)", size=11, weight=600, color="#94a3b8", anchor="middle"))
    parts.append(_text(LANE_X["focus"] + FOCUS_W // 2, LANE_HEADER_Y, "FOCUS", size=11, weight=600, color="#94a3b8", anchor="middle"))
    parts.append(_text(LANE_X["downstream"] + BOX_W // 2, LANE_HEADER_Y, "DOWNSTREAM (consumers)", size=11, weight=600, color="#94a3b8", anchor="middle"))

    # Edges first (drawn before boxes so they render behind)
    parts.extend(_edges(graph))

    # Upstream boxes
    if graph.upstream:
        for i, e in enumerate(graph.upstream):
            y = ROWS_TOP_Y + i * (BOX_H + BOX_GAP)
            parts.append(_box(LANE_X["upstream"], y, BOX_W, BOX_H, e.other, _sublabel(e), e.kind, _color_for(e)))
    else:
        parts.append(_placeholder(LANE_X["upstream"], ROWS_TOP_Y, "no upstream deps"))

    # Focus
    focus_y = ROWS_TOP_Y + (max(rows, 1) * (BOX_H + BOX_GAP) - FOCUS_H) // 2
    focus_color = CATEGORY_COLORS.get(graph.category, "#94a3b8")
    parts.append(_box(
        LANE_X["focus"], focus_y, FOCUS_W, FOCUS_H,
        graph.focus.upper(),
        f"{graph.category} · {graph.source}",
        "focus",
        focus_color,
        big=True,
    ))

    # Downstream boxes
    if graph.downstream:
        for i, e in enumerate(graph.downstream):
            y = ROWS_TOP_Y + i * (BOX_H + BOX_GAP)
            parts.append(_box(LANE_X["downstream"], y, BOX_W, BOX_H, e.other, _sublabel(e), e.kind, _color_for(e)))
    else:
        parts.append(_placeholder(LANE_X["downstream"], ROWS_TOP_Y, "no downstream consumers"))

    # Aggregate boundary box (for composite focus per spec A.7)
    if graph.source == "(aggregate)":
        parts.append(_aggregate_boundary(LANE_X["focus"], focus_y, FOCUS_W, FOCUS_H))

    parts.append("</svg>")
    return "\n".join(parts)


def render_html(graph: DepGraph) -> str:
    tmpl = Template((TEMPLATE_DIR / "architecture.html.tmpl").read_text())
    svg = render_svg(graph)
    cat_color = CATEGORY_COLORS.get(graph.category, "#94a3b8")
    n_required = sum(1 for e in graph.upstream if e.kind == "required")
    n_optional = sum(1 for e in graph.upstream if e.kind in ("optional", "adaptive"))
    n_consumers = len(graph.downstream)
    return tmpl.substitute(
        focus=graph.focus,
        subtitle=f"category: {graph.category} · source: {graph.source}",
        cat_color=cat_color,
        svg=svg,
        n_required=n_required,
        n_optional=n_optional,
        n_consumers=n_consumers,
        footer=f"Regenerate: python -m bootstrapper.docs.regen {graph.focus}",
    )


# ───── Internal helpers ──────────────────────────────────────────────────


def _color_for(e: DepEdge) -> str:
    """Spec A.3 rule #3: each box uses its category's palette token."""
    return CATEGORY_COLORS.get(e.other_category, "#94a3b8")


def _box(x: int, y: int, w: int, h: int, label: str, sublabel: str, kind: str, stroke: str, *, big: bool = False) -> str:
    fill = "rgba(15, 23, 42, 0.7)"
    cx = x + w // 2
    ty = y + 24 if big else y + 22
    sy = y + 44 if big else y + 38
    ts = 14 if big else 11
    return Template((TEMPLATE_DIR / "svg_box.tmpl").read_text()).substitute(
        x=x, y=y, w=w, h=h, kind=kind, fill=fill, stroke=stroke,
        cx=cx, ty=ty, sy=sy, ts=ts, label=label, sublabel=sublabel or "",
    )


def _placeholder(x: int, y: int, text: str) -> str:
    return f'<text x="{x + BOX_W // 2}" y="{y + BOX_H // 2}" fill="#475569" font-size="10" text-anchor="middle" font-style="italic">— {text} —</text>'


def _aggregate_boundary(x: int, y: int, w: int, h: int) -> str:
    pad = 14
    return (
        f'<rect x="{x - pad}" y="{y - pad}" width="{w + 2 * pad}" height="{h + 2 * pad}" '
        f'rx="12" fill="none" stroke="#fb7185" stroke-width="1.5" stroke-dasharray="4,4"/>'
    )


def _edges(graph: DepGraph) -> list[str]:
    out: list[str] = []
    fy_focus = ROWS_TOP_Y + (max(len(graph.upstream), len(graph.downstream), 1) * (BOX_H + BOX_GAP)) // 2
    for i, e in enumerate(graph.upstream):
        y = ROWS_TOP_Y + i * (BOX_H + BOX_GAP) + BOX_H // 2
        out.append(_edge(LANE_X["upstream"] + BOX_W, y, LANE_X["focus"], fy_focus, e))
        if e.bidirectional:
            out.append(_edge(LANE_X["focus"], fy_focus + 6, LANE_X["upstream"] + BOX_W, y + 6, e))
    for i, e in enumerate(graph.downstream):
        y = ROWS_TOP_Y + i * (BOX_H + BOX_GAP) + BOX_H // 2
        out.append(_edge(LANE_X["focus"] + FOCUS_W, fy_focus, LANE_X["downstream"], y, e))
    return out


def _edge(x1: int, y1: int, x2: int, y2: int, e: DepEdge) -> str:
    if e.kind == "required":
        stroke, marker, dash = "#64748b", "arrowhead-solid", ""
    elif e.kind == "adaptive":
        stroke, marker, dash = "#fbbf24", "arrowhead-dashed", 'stroke-dasharray="4,4"'
    else:
        stroke, marker, dash = "#94a3b8", "arrowhead-solid", 'stroke-dasharray="2,3"'
    title_text = f"{e.kind} · {e.failure_mode or e.mechanism}" if e.failure_mode or e.mechanism else ""
    title = f"<title>{html.escape(title_text)}</title>" if title_text else ""
    return (
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{stroke}" stroke-width="1.5" {dash} marker-end="url(#{marker})">'
        f'{title}</line>'
    )


def _text(x: int, y: int, text: str, *, size: int = 11, weight: int = 400, color: str = "#fff", anchor: str = "start") -> str:
    return f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}">{text}</text>'


def _sublabel(e: DepEdge) -> str:
    suffix = " · ↔" if e.bidirectional else ""
    return f"{e.kind}{suffix}"
