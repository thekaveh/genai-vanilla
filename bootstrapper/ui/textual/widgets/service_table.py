"""
ServiceTable — dense, color-coded service grid for InfoPanel.

Two slots (sets of columns) side-by-side, separated by a wide gutter
so the visual break between left and right halves is unambiguous.
Each slot has these sub-columns, in order:

    [lock]  [port]  [name]  [source]  [full alias URL]

Where:
- ``port``: the assigned port (``:63002``) — ``—`` when disabled
- ``lock``: 🔒 for always-on infrastructure whose source the user
  cannot change; blank for services the wizard will ask about
- ``name``: the service display name
- ``source``: the chosen variant (e.g. ``ollama-container-gpu``)
- ``full alias URL``: ``http://host:kong_port`` — clickable; ``—``
  when no alias exists for this service. All Kong-routed aliases
  share the Kong listener port (virtual-host routing).

Each column is sized exactly one cell wider than the longest value
present in the actual data — never inflated past content. If the
data is too wide for two slots side-by-side, the layout falls back
to one column so every value still renders without truncation.

Spacing is governed by ``COL_SEP`` (gap between adjacent sub-columns)
and ``GUTTER`` (gap between the two slot halves). ``GUTTER`` is held
at >= 3 * COL_SEP so the visual break between halves is clearly
larger than the gaps between columns inside a half.
"""

from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text
from textual.widget import Widget

from .. import palette as P


@dataclass
class ServiceRow:
    name: str
    source: str = "container"
    alias: str = ""
    port: str = ""              # the service's own assigned port
    # Port to use when building the clickable alias URL — for Kong
    # virtual-host-routed services this is the Kong listener port
    # (KONG_HTTP_PORT), NOT the service's internal port. Falls back
    # to ``port`` when not explicitly set.
    alias_port: str = ""
    tag: str = ""              # kept for back-compat
    selected: bool = False
    default_source: str = ""
    # True when the user can pick the service's source via the wizard.
    # False marks always-on infrastructure (e.g. Supabase DB) where the
    # source is fixed; rendered with a lock icon in the table.
    configurable: bool = True
    category: str = ""        # drives leading bar color (Task 5.4 uses this)
    pending: bool = False     # drives pending-state rendering

    @property
    def is_changed(self) -> bool:
        return bool(self.default_source) and self.source != self.default_source


def _fit(text: str, width: int) -> str:
    """Pad with spaces, or truncate with an ellipsis when too long."""
    if width <= 0:
        return ""
    if len(text) <= width:
        return text + " " * (width - len(text))
    if width == 1:
        return "…"
    return text[: width - 1] + "…"


def _port_label(r: ServiceRow) -> str:
    p = (r.port or "").strip().lstrip(":")
    return f":{p}" if p else ""


def _alias_url(r: ServiceRow) -> str:
    """Full clickable URL for the alias, when one exists.

    Kong-routed aliases (the only kind we render) all share Kong's
    listener port — that's how virtual-host routing works. We pull
    that from ``r.alias_port`` when set, falling back to ``r.port``
    only if a caller didn't provide a Kong port.
    """
    alias = (r.alias or "").strip()
    if not alias:
        return ""
    p = (r.alias_port or r.port or "").strip().lstrip(":")
    if p:
        return f"http://{alias}:{p}"
    return f"http://{alias}"


class ServiceTable(Widget):
    """Service grid rendered as a single styled Text block."""

    DEFAULT_CSS = """
    ServiceTable { height: auto; min-height: 6; }
    """

    can_focus = False

    # Leading category bar — colored stripe matching each row's category.
    # 2 cells wide; renders ▰▰ to fill the cell width with a solid block-like
    # glyph that survives without TrueColor.
    BAR_W = 2
    BAR_GLYPH = "▰" * BAR_W  # two cells filled

    # Fixed-width portions of each slot.
    ARROW_W = 1
    DOT_W = 1
    # Lock-status column. The 🔒 emoji is double-width on most terminals
    # so the column is allocated 2 cells; configurable rows render blank.
    LOCK_W = 2
    LOCK_ICON = "🔒"
    # Spacing rules:
    #   COL_SEP: gap between adjacent columns within one slot.
    #   GUTTER:  gap between the two slot halves — kept at >= 3 * COL_SEP
    #            so the visual division between halves is clearly larger
    #            than the gaps between sub-columns inside a half.
    COL_SEP = 2
    GUTTER = 6
    # Absolute floors — only apply when the actual data is empty.
    MIN_PORT = 4
    MIN_NAME = 6
    MIN_SOURCE = 6
    MIN_ALIAS_URL = 6

    def __init__(
        self,
        rows: list[ServiceRow] | None = None,
        *,
        max_visible: int | None = None,
        columns: int = 2,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self._rows: list[ServiceRow] = list(rows or [])
        self._filter: str = ""
        self.max_visible = max_visible if max_visible is not None else 999
        # Number of slot columns the user requested. The actual number
        # rendered may drop to 1 when the data is too wide to fit two
        # tight-packed slots side-by-side.
        self.columns = max(1, columns)
        self._cursor: int | None = 0

    def set_cursor(self, index: int | None) -> None:
        self._cursor = index
        self.refresh()

    def set_rows(self, rows: list[ServiceRow]) -> None:
        self._rows = list(rows)
        self._cursor = 0
        self.refresh()

    def set_filter(self, q: str) -> None:
        self._filter = (q or "").strip().lower()
        self._cursor = 0
        self.refresh()

    @property
    def visible_rows(self) -> list[ServiceRow]:
        if not self._filter:
            return self._rows
        q = self._filter
        return [
            r for r in self._rows
            if q in r.name.lower() or q in r.alias.lower()
            or q in r.source.lower() or q in r.tag.lower()
        ]

    def move_cursor(self, delta: int) -> None:
        rows = self.visible_rows
        if not rows:
            return
        self._cursor = (self._cursor + delta) % len(rows)
        self.refresh()

    # ─── width math ─────────────────────────────────────────────────

    @property
    def _slot_fixed(self) -> int:
        # bar(BAR_W) sp(1) arrow(1) sp(1) dot(1) sp(2) + lock(LOCK_W) + 4*COL_SEP
        return (
            self.BAR_W + 1
            + self.ARROW_W + 1 + self.DOT_W + 2
            + self.LOCK_W + 4 * self.COL_SEP
        )

    def _raw_widths(
        self, rows: list[ServiceRow],
    ) -> tuple[int, int, int, int]:
        """Tightest possible widths for the given data — longest content
        in each of the four columns plus exactly one cell of breathing
        room. Returned in render order: (port, name, source, alias_url).
        No scaling, no truncation."""
        def _maxlen(values) -> int:
            return max((len(v) for v in values), default=0)

        port_max = max(self.MIN_PORT, _maxlen((_port_label(r) or "—") for r in rows))
        name_max = max(self.MIN_NAME, _maxlen(r.name for r in rows))
        src_max = max(self.MIN_SOURCE, _maxlen((r.source or "—") for r in rows))
        alias_max = max(
            self.MIN_ALIAS_URL,
            _maxlen((_alias_url(r) or "—") for r in rows),
        )
        return (
            port_max + 1, name_max + 1, src_max + 1, alias_max + 1,
        )

    def _scaled_widths(
        self, raw: tuple[int, int, int, int], slot_width: int,
    ) -> tuple[int, int, int, int]:
        """Fall-back when even the raw widths don't fit a slot — scale
        each down proportionally so we still render something."""
        available = max(10, slot_width - self._slot_fixed)
        total = sum(raw)
        if total <= available:
            return raw
        scale = available / total
        p = max(self.MIN_PORT, int(raw[0] * scale))
        n = max(self.MIN_NAME, int(raw[1] * scale))
        s = max(self.MIN_SOURCE, int(raw[2] * scale))
        a = max(self.MIN_ALIAS_URL, available - p - n - s)
        return p, n, s, a

    def _slot_text(
        self,
        r: ServiceRow | None,
        *,
        is_cursor: bool,
        widths: tuple[int, int, int, int],
    ) -> Text:
        port_w, name_w, source_w, alias_w = widths
        slot = Text()
        sep = " " * self.COL_SEP
        # Leading category bar — 2 cells in the category color.
        bar_color = P.style_for_category(r.category) if r else P.TEXT_FAINT
        slot.append(self.BAR_GLYPH, style=bar_color)
        slot.append(" ")
        if r is None:
            # Bar (BAR_W + 1) already written above; pad the remaining columns.
            total = (
                self.ARROW_W + 1 + self.DOT_W + 2 + port_w + self.COL_SEP
                + self.LOCK_W + self.COL_SEP
                + name_w + self.COL_SEP + source_w + self.COL_SEP + alias_w
            )
            slot.append(" " * total)
            return slot
        slot.append(P.ARROW_RIGHT if is_cursor else " ",
                    style=f"bold {P.ACCENT}" if is_cursor else P.TEXT_FAINT)
        slot.append(" ")
        is_disabled = (r.source or "").lower() == "disabled"
        # Pending-state branch: row decided by the user has not been confirmed yet.
        # All "decided" columns collapse to em-dashes / placeholders; the dot
        # switches to a hollow yellow ◌. Locked rows can never be pending so we
        # don't need to coordinate with the lock branch.
        if r.pending:
            slot.append("◌", style=P.WARN)
            slot.append("  ")
            if r.configurable:
                slot.append(" " * self.LOCK_W)
            else:
                slot.append(self.LOCK_ICON)
            slot.append(sep)
            slot.append(_fit("—", port_w), style=P.TEXT_FAINT)
            slot.append(sep)
            name_color = P.ACCENT if is_cursor else P.TEXT
            slot.append(_fit(r.name, name_w),
                        style=f"bold {name_color}" if is_cursor else name_color)
            slot.append(sep)
            slot.append(_fit("pending…", source_w), style=f"italic {P.WARN}")
            slot.append(sep)
            slot.append(_fit("—", alias_w), style=P.TEXT_FAINT)
            return slot
        slot.append(P.DOT_RUNNING, style=P.style_for_source_choice(r.source))
        slot.append("  ")
        # 1) Lock status — 🔒 for always-on services whose source can't
        # be picked in the wizard; blank for configurable services so
        # the user's eye is drawn to the rows the wizard will ask about.
        if r.configurable:
            slot.append(" " * self.LOCK_W)
        else:
            slot.append(self.LOCK_ICON)
        slot.append(sep)
        # 2) Port — the at-a-glance answer to "what port is this on?"
        port = _port_label(r) if not is_disabled else ""
        port_text = port or "—"
        port_color = P.ACCENT if port else P.TEXT_FAINT
        slot.append(_fit(port_text, port_w), style=port_color)
        slot.append(sep)
        # 3) Name
        name_color = P.TEXT_MUTED if is_disabled else (P.ACCENT if is_cursor else P.TEXT)
        slot.append(_fit(r.name, name_w),
                    style=f"bold {name_color}" if is_cursor else name_color)
        slot.append(sep)
        # 3) Source — full variant name. CHANGED highlights it.
        source_style = (
            P.WARN if r.is_changed else P.style_for_source_choice(r.source)
        )
        source_label = r.source or "—"
        slot.append(_fit(source_label, source_w), style=source_style)
        slot.append(sep)
        # 4) Full clickable alias URL — uses Kong listener port for
        # virtual-host-routed aliases, NOT the service's own port.
        url = _alias_url(r) if not is_disabled else ""
        url_text = url or "—"
        url_color = P.INFO if url else P.TEXT_FAINT
        slot.append(_fit(url_text, alias_w), style=url_color)
        return slot

    def render(self) -> Text:
        rows = self.visible_rows[: self.max_visible]
        out = Text()
        if not rows:
            out.append("  no services match the filter", style=P.TEXT_MUTED)
            return out

        avail = self.size.width or 130

        # Each column gets exactly (longest content + 1) cells. If two
        # tight slots don't fit side-by-side at that width, fall back to
        # one column so every value still renders without truncation.
        raw = self._raw_widths(rows)
        needed = sum(raw) + self._slot_fixed
        cols = self.columns
        while cols > 1:
            slot_width = (avail - self.GUTTER * (cols - 1)) // cols
            if needed <= slot_width:
                break
            cols -= 1
        slot_width = (avail - self.GUTTER * (cols - 1)) // cols
        widths = self._scaled_widths(raw, slot_width)

        half = (len(rows) + cols - 1) // cols
        groups = [rows[i * half:(i + 1) * half] for i in range(cols)]
        for r_idx in range(half):
            for c_idx, group in enumerate(groups):
                if c_idx > 0:
                    out.append(" " * self.GUTTER)
                if r_idx < len(group):
                    abs_idx = c_idx * half + r_idx
                    is_cursor = (self._cursor is not None and abs_idx == self._cursor)
                    out.append(self._slot_text(
                        group[r_idx], is_cursor=is_cursor, widths=widths,
                    ))
                else:
                    out.append(self._slot_text(
                        None, is_cursor=False, widths=widths,
                    ))
            if r_idx + 1 < half:
                out.append("\n")
        return out

    def on_resize(self) -> None:
        self.refresh()
