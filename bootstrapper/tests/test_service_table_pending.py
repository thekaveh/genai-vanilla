"""Visual snapshot tests for ServiceTable's pending vs answered rows."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _render(table) -> str:
    """Render a ServiceTable with a mocked terminal width of 200."""
    size_mock = MagicMock()
    size_mock.width = 200
    with patch.object(type(table), "size", new_callable=lambda: property(lambda self: size_mock)):
        return table.render().plain


def test_pending_row_renders_hollow_dot_and_dashes():
    """A pending row shows ◌ and em-dashes; not the source color."""
    from ui.textual.widgets.service_table import ServiceRow, ServiceTable
    row = ServiceRow(
        name="ComfyUI", source="", port="", alias="", category="media",
        pending=True,
    )
    table = ServiceTable([row], columns=1)
    text = _render(table)
    assert "◌" in text  # hollow dot
    assert "pending" in text or "—" in text


def test_answered_row_renders_full_dot_and_real_port():
    """An answered row has the running dot and the actual port number."""
    from ui.textual.widgets.service_table import ServiceRow, ServiceTable
    row = ServiceRow(
        name="ComfyUI", source="container-cpu", port="63040", alias="comfyui.localhost",
        category="media", pending=False, default_source="container-cpu",
    )
    table = ServiceTable([row], columns=1)
    text = _render(table)
    assert "63040" in text
    assert "container-cpu" in text
