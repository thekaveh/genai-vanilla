"""Hover-tooltip logic for the wizard ServiceTable.

Covers the two pieces that don't need a live Textual app:
  - ``_build_tooltip`` — the access-summary string for a row.
  - ``_row_at`` — mapping a widget-relative (x, y) back to a rendered row,
    using the grid layout that render() stashes.

The visual hover behavior itself (Textual showing the tooltip after a hover
delay) is validated live in the TUI, not here.
"""

from __future__ import annotations

from ui.textual.widgets.service_table import ServiceRow, ServiceTable


def _row(name, **kw):
    return ServiceRow(name=name, **kw)


def test_build_tooltip_basic():
    row = _row("n8n", source="container", alias="n8n.localhost",
               alias_port="63000", port="63064")
    tip = ServiceTable._build_tooltip(row)
    assert tip.splitlines() == [
        "n8n  ·  container",
        "http://n8n.localhost:63000",
        "localhost:63064",
    ]


def test_build_tooltip_omits_empty_url_and_dash_port():
    row = _row("Supabase DB", source="container", alias="", alias_port="",
               port="—")
    assert ServiceTable._build_tooltip(row) == "Supabase DB  ·  container"


def test_build_tooltip_appends_extra_lines():
    row = _row("MinIO Console", source="container", alias="minio.localhost",
               alias_port="63000", port="63019",
               tooltip_lines=["S3 API: http://localhost:63018",
                              "S3 API (Kong): http://s3.minio.localhost:63000"])
    tip = ServiceTable._build_tooltip(row)
    assert "S3 API: http://localhost:63018" in tip
    assert "S3 API (Kong): http://s3.minio.localhost:63000" in tip
    # extra lines come after the row's own console URL
    assert tip.index("63019") < tip.index("63018")


def test_row_at_single_column():
    t = ServiceTable(rows=[])
    rows = [_row("a"), _row("b"), _row("c")]
    # Simulate a single-column render layout.
    t._hit_flat = rows
    t._hit_offsets = [0]
    t._hit_lens = [3]
    t._hit_block_w = 40
    assert t._row_at(5, 0) is rows[0]
    assert t._row_at(5, 2) is rows[2]
    assert t._row_at(5, 3) is None        # past the last row
    assert t._row_at(5, -1) is None


def test_row_at_two_columns():
    t = ServiceTable(rows=[])
    rows = [_row("a"), _row("b"), _row("c"), _row("d")]
    # Two columns: group0=[a,b] (offset 0), group1=[c,d] (offset 2).
    t._hit_flat = rows
    t._hit_offsets = [0, 2]
    t._hit_lens = [2, 2]
    t._hit_block_w = 40
    assert t._row_at(5, 0) is rows[0]     # col 0, row 0
    assert t._row_at(5, 1) is rows[1]     # col 0, row 1
    assert t._row_at(45, 0) is rows[2]    # col 1, row 0
    assert t._row_at(45, 1) is rows[3]    # col 1, row 1
    assert t._row_at(85, 0) is None       # past last column


def test_row_at_no_layout_returns_none():
    t = ServiceTable(rows=[])
    # No render() yet → no hit layout.
    assert t._row_at(0, 0) is None
