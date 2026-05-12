"""
OptionRow — single selectable option in the wizard prompt panel.

Mockup 003 layout:

Row 1:  ▸ ◉ ollama-localhost                                  [rec.] [GPU]
Row 2 (only if hint):       Use the Ollama already running on this host

Renders as 1 cell when hint is empty, 2 cells when hint is present.
Cell 1: arrow (1) + gap (1) + bullet (1) + 2-space gap + label + flex
        spacer + right-aligned badges with 2-space gap each.
Cell 2: 5-cell indent + hint in $text-faint.

The Ollama multiselect step enriches its rows with two extra optional
columns rendered between the label and the badges:

    ▸ [✓] qwen3   [thinking][tools]   0.6b·1.7b·4b·8b·14b·32b   28.6M
          Multi-modal LLM with vision, 100+ language support…

* ``sizes``  → ``tuple[str, ...]`` variant list ("0.6b", "8b", …).
* ``pulls``  → ``int``; formatted "114.2M" / "85K" / "1.2B".

Both columns are dropped when the row is too narrow (priority below).
Default empty values render the row identical to its pre-feature shape,
so non-Ollama steps see zero change.
"""

from __future__ import annotations

from rich.text import Text
from textual.widget import Widget

from .. import palette as P


_BADGE_STYLES = {
    "rec.": P.OK,
    "rec":  P.OK,
    "default": P.OK,
    "GPU": P.RESOURCE,
    "CPU": P.TEXT_MUTED,
    "cloud": P.INFO,
    "external": P.INFO,
    "disabled": P.TEXT_FAINT,
    "container": P.OK,
    # Ollama library capability tags — colours pulled from existing
    # palette accents so the row stays harmonious with the rest of the
    # TUI (no new hex values introduced).
    "embedding": P.ACCENT,        # cyan-ish, sub-family of supabase blue
    "thinking":  P.TAG_INFRA,     # warm purple, sub-family of kong
    "vision":    P.OK,            # green, sub-family of comfyui
    "tools":     P.RESOURCE,      # amber
    "audio":     P.ERR_SOFT,      # soft pink
    # Status badges already in use by the merge helper:
    "pulled":    P.OK,
    "library":   P.INFO,
    # Recency bucket marker — applied to models updated > 365 days ago
    # so they're visually distinct from the recent-popular surface.
    # Muted (TEXT_FAINT) so it reads as "deprioritised" not "warning".
    "legacy":    P.TEXT_FAINT,
}


# Quantization rule of thumb for converting Ollama parameter counts to
# approximate on-disk size. ``0.6`` matches Ollama's default Q4_K_M
# quantization (~4.7 bits/param → 0.59 bytes/param). Real downloads
# can be 10-20% off either direction depending on model architecture
# and chosen tag, but it's a useful order-of-magnitude indicator.
_QUANT_BYTES_PER_PARAM = 0.6


def _approx_size(param_str: str) -> str:
    """Convert an Ollama parameter notation to an approximate disk size.

    The listing page only publishes parameter counts ("8b", "270m"),
    not byte sizes — those live on per-variant detail pages. We
    convert in place so the user sees a familiar GB/MB number instead
    of having to translate ``b`` (billions of parameters) into disk
    footprint mentally.

    "8b"   → "4.8GB"    (8e9 × 0.6 ≈ 4.8e9 bytes)
    "70b"  → "42GB"
    "405b" → "243GB"
    "1.5b" → "900MB"    (sub-GB values render in MB for legibility)
    "1b"   → "600MB"
    "0.6b" → "360MB"
    "270m" → "162MB"

    Unparseable input is returned verbatim (defence against unexpected
    upstream notation; the caller falls through unchanged).
    """
    s = param_str.strip().lower()
    if not s:
        return ""
    suffix = s[-1]
    multipliers = {"b": 1_000_000_000, "m": 1_000_000}
    if suffix not in multipliers:
        return param_str
    try:
        params = float(s[:-1]) * multipliers[suffix]
    except ValueError:
        return param_str
    bytes_ = params * _QUANT_BYTES_PER_PARAM
    gb = bytes_ / 1_000_000_000
    if gb < 1:
        mb = bytes_ / 1_000_000
        return f"{mb:.0f}MB"
    # Drop trailing ".0" for whole-number multiples; keep one decimal
    # otherwise. Mirrors _format_pulls.
    return f"{gb:.1f}".rstrip("0").rstrip(".") + "GB"


def _format_pulls(n: int) -> str:
    """Reverse of :func:`utils.ollama_library._parse_pull_count`.

    ``114_200_000`` → ``"114.2M"`` (one decimal, dropped when .0).
    ``< 1000`` returns the bare integer. Negative or zero → empty
    string (caller suppresses the column).
    """
    if n <= 0:
        return ""
    if n < 1_000:
        return str(n)
    for suffix, scale in (("B", 1_000_000_000), ("M", 1_000_000), ("K", 1_000)):
        if n >= scale:
            v = n / scale
            # Drop trailing ".0" for whole-number multiples; keep one
            # decimal otherwise. Mirrors ollama.com's own formatting.
            return f"{v:.1f}".rstrip("0").rstrip(".") + suffix
    return str(n)


# Joins variant sizes for display. Same separator as the size_compress
# fallback below so the user sees consistent punctuation.
_SIZE_SEP = "·"


class OptionRow(Widget):
    """1- or 2-cell option row."""

    DEFAULT_CSS = """
    OptionRow { height: auto; padding: 0 1; }
    OptionRow.option-selected { background: #1c2034; }
    """

    can_focus = False

    def __init__(
        self,
        label: str,
        *,
        hint: str = "",
        badges: list[str] | None = None,
        selected: bool = False,
        # Multi-select extras: when ``multi`` is True, the row shows a
        # ``[✓]`` / ``[ ]`` checkbox prefix and the ``checked`` flag
        # tracks user-toggled state independently of the cursor focus
        # (``selected``).
        multi: bool = False,
        checked: bool = False,
        # Optional Ollama enrichments. Empty defaults preserve the
        # pre-feature layout for every non-Ollama caller.
        sizes: tuple[str, ...] | None = None,
        pulls: int = 0,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.label = label
        self.hint = hint or ""
        self.badges = badges or []
        self.selected = selected
        self.multi = multi
        self.checked = checked
        self.sizes = tuple(sizes or ())
        self.pulls = pulls
        if selected:
            self.add_class("option-selected")

    def set_selected(self, value: bool) -> None:
        if value == self.selected:
            return
        self.selected = value
        self.set_class(value, "option-selected")
        self.refresh()

    def set_checked(self, value: bool) -> None:
        if value == self.checked:
            return
        self.checked = value
        self.refresh()

    # ─── render ─────────────────────────────────────────────────────────

    def _render_sizes(self, sizes: tuple[str, ...], *, compact: bool) -> str:
        if not sizes:
            return ""
        # Convert each ``8b``/``270m`` parameter notation to an
        # approximate disk size (``4.8GB``, ``162MB``) so the user
        # sees the actual download footprint, not just a parameter
        # count they have to translate mentally. See _approx_size.
        readable = [_approx_size(s) for s in sizes]
        if compact and len(readable) > 3:
            return _SIZE_SEP.join(readable[:3]) + _SIZE_SEP + "…"
        return _SIZE_SEP.join(readable)

    def render(self) -> Text:
        width = self.size.width or 60
        # ── line 1 ─────────────────────────────────────────────
        line1 = Text()
        if self.selected:
            line1.append(P.ARROW_RIGHT, style=f"bold {P.ACCENT}")
            line1.append(" ")
            line1.append(P.DOT_FILLED, style=P.ACCENT)
        else:
            line1.append(" ")
            line1.append(" ")
            line1.append(P.DOT_HOLLOW, style=P.TEXT_FAINT)
        line1.append("  ")
        if self.multi:
            # Render checkbox prefix in addition to the dot/arrow indicator.
            box = "[✓]" if self.checked else "[ ]"
            box_color = P.OK if self.checked else P.TEXT_FAINT
            line1.append(box, style=box_color)
            line1.append(" ")
        label_color = P.ACCENT if self.selected else P.TEXT
        line1.append(self.label, style=f"bold {label_color}" if self.selected else label_color)

        # Right-aligned block: capability badges + (optional) sizes
        # column + (optional) pull count. Build with width-budgeting so
        # narrow terminals drop the size column before the pull count.
        right = Text()
        # Badges first (innermost, closest to label).
        for b in self.badges:
            color = _BADGE_STYLES.get(b, P.TEXT_FAINT)
            right.append("  ")
            right.append(f"[{b}]", style=color)
        # Sizes column.
        pull_text = _format_pulls(self.pulls)
        # Budget: how many cells are left after label + badges + a min
        # 1-cell gap + pulls column? If wide enough, append full sizes;
        # if still cramped, try compact; else drop sizes entirely.
        if self.sizes:
            pull_reserve = (2 + len(pull_text)) if pull_text else 0
            min_gap = 2
            avail = width - line1.cell_len - right.cell_len - pull_reserve - min_gap
            full = self._render_sizes(self.sizes, compact=False)
            compact = self._render_sizes(self.sizes, compact=True)
            chosen = ""
            if len(full) + 2 <= avail:
                chosen = full
            elif len(compact) + 2 <= avail:
                chosen = compact
            # else: drop sizes entirely — pulls column survives.
            if chosen:
                right.append("  ")
                right.append(chosen, style=P.TEXT_FAINT)
        # Pull count — far right, muted.
        if pull_text:
            right.append("  ")
            right.append(pull_text, style=P.TEXT_MUTED)

        gap = max(1, width - line1.cell_len - right.cell_len - 2)
        line1.append(" " * gap)
        line1.append(right)

        if not self.hint:
            return line1

        line2 = Text()
        line2.append(" " * 5)
        line2.append(self.hint, style=P.TEXT_FAINT)

        out = Text()
        out.append(line1)
        out.append("\n")
        out.append(line2)
        return out
