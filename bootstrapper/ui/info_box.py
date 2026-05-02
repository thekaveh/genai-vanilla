"""
Info box renderable — the anchored top region of the presentation.

Iteration-5 layout: a single 2-column flat list of services. No category
headers, no per-character gradient inside the box (that's reserved for the
logo above). Sort order is (source bucket, port asc), so containers come
first (green dots), then localhost/external/cloud (cyan dots), then off
(slate dots) — natural visual grouping without category labels.

Each service row uses an identical compact format:
    ●  Service Name        :63015   container

Color of the dot AND the choice label come from `palette.style_for_source`
(green / cyan / slate). The user's choice is always visible at a glance.

Pure function: `render_info_box(state, available_width, available_rows=0)
-> Panel`. No I/O, no side effects. Caller falls back to compact-summary
or legacy presentations when the terminal is too small.
"""

from math import ceil
from typing import List

from rich.box import ROUNDED
from rich.columns import Columns
from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.progress_bar import ProgressBar
from rich.table import Table
from rich.text import Text

from ui import palette
from ui.state import AppState, ServiceEntry


# Width thresholds for layout selection.
#  >= WIDTH_TWO_COL : services rendered as two side-by-side columns
#  >= WIDTH_COMPACT : single column of services
#  <  WIDTH_COMPACT : caller should fall back to the legacy banner
WIDTH_TWO_COL = 160
WIDTH_COMPACT = 60

# Per-service row column widths (used by the Table that renders services).
# Alias and port live in separate columns so both stay visible when a service
# has a hosts alias — alias shows the friendly URL with Kong port (e.g.
# "chat.localhost:55668" — what the user pastes in a browser), port shows
# the bare ":63015" service-direct port. Disabled services collapse the
# port to "—". ALIAS_COL_WIDTH = 24 fits the longest expected alias form
# ("openclaw.localhost:NNNNN").
NAME_COL_WIDTH = 20
ALIAS_COL_WIDTH = 24
PORT_COL_WIDTH = 8
CHOICE_COL_WIDTH = 10


# --- Public API -------------------------------------------------------------

def render_info_box(
    state: AppState,
    available_width: int,
    available_rows: int = 0,
) -> Panel:
    """
    Render the anchored top box. Returns a Rich Panel ready for the Live
    Layout. `available_rows` is accepted for API compatibility with prior
    iterations but is not consulted (the box uses one layout — 2-column
    when wide enough, 1-column otherwise).
    """
    body_parts: List[RenderableType] = []

    # Wizard-mode header rows (above services list)
    if state.box_mode == "wizard":
        body_parts.append(_render_wizard_progress(state, available_width))
        body_parts.append(Text(""))  # spacer

    # Services list — 2 columns when wide enough, 1 column otherwise.
    # Each row inlines the service's hosts alias (chat.localhost:KONG_PORT)
    # for services that have one and where /etc/hosts is configured;
    # services without an alias show their port; disabled show "—".
    body_parts.append(_render_services(state, available_width))

    # Wizard mode: command preview just below the services list
    if state.box_mode == "wizard" and state.wizard_command_preview:
        body_parts.append(Text(""))
        body_parts.append(_render_command_preview(state))

    # Optional footer (GENAI_ENV_FILE indicator only — license/repo/creator
    # live above the box in the logo region).
    footer = _render_footer(state)
    if footer.plain:
        body_parts.append(footer)

    return Panel(
        Group(*body_parts),
        title=_render_title(state),
        title_align="left",
        subtitle=_render_subtitle(state),
        subtitle_align="right",
        border_style=palette.COLOR_BORDER,
        box=ROUNDED,
        padding=(1, 2),
        expand=True,
    )


def render_compact_summary(state: AppState, available_width: int) -> Panel:
    """
    A 4-row compact summary used when the terminal is too short to fit the
    full box. Shows the title row + a one-line "X running · Y off" rollup
    + the footer. Caller is responsible for choosing this over render_info_box.
    """
    counts = _summarize_choices(state.services)
    rollup = Text()
    rollup.append(f"  {counts['container']} container", style=palette.COLOR_CONTAINER)
    rollup.append("  ·  ", style=palette.COLOR_SEPARATOR)
    rollup.append(f"{counts['accent']} local/cloud", style=palette.COLOR_ACCENT)
    rollup.append("  ·  ", style=palette.COLOR_SEPARATOR)
    rollup.append(f"{counts['off']} off", style=palette.COLOR_OFF)

    body = Group(rollup, _render_footer(state))

    # Compact summary keeps padding=(0, 2) — it's the short-terminal
    # fallback, vertical breathing room would push it past the height
    # threshold that triggered this branch in the first place.
    return Panel(
        body,
        title=_render_title(state),
        title_align="left",
        border_style=palette.COLOR_BORDER,
        box=ROUNDED,
        padding=(0, 2),
        expand=True,
    )


# --- Title / footer --------------------------------------------------------

def _render_title(state: AppState) -> Text:
    """
    Title-in-border (top). Hermes-style integrated header showing the
    brand label, version, and tagline. The big ASCII logo sits above
    this title bar — the title bar carries the smaller-typeface info
    that used to be captions below the logo.
    """
    title = Text()
    title.append(" ", style=palette.COLOR_TEXT)
    label = "Setup Wizard" if state.box_mode == "wizard" else state.brand_name
    title.append(label, style=palette.COLOR_TITLE)
    if state.version:
        title.append("  ·  ", style=palette.COLOR_BORDER)
        title.append(f"v{state.version}", style=palette.COLOR_DIM)
    if state.tagline:
        title.append("  ·  ", style=palette.COLOR_BORDER)
        title.append(f"{state.tagline} ", style=palette.COLOR_DIM)
    return title


def _render_subtitle(state: AppState) -> Text:
    """
    Subtitle-in-border (bottom). Carries the creator + license + repo URL
    — the second half of the Hermes-style integrated header. Right-aligned
    so the title (left) and subtitle (right) frame the box symmetrically.
    """
    sub = Text()
    sub.append(f" by {state.creator}", style=palette.COLOR_DIM)
    sub.append("  ·  ", style=palette.COLOR_BORDER)
    sub.append(state.license, style=palette.COLOR_DIM)
    sub.append("  ·  ", style=palette.COLOR_BORDER)
    sub.append(state.repo_url, style=palette.COLOR_DIM)
    sub.append(" ", style=palette.COLOR_DIM)
    return sub


def _render_footer(state: AppState) -> Text:
    """
    Footer is rendered ONLY when there's something situational to show
    (currently: the GENAI_ENV_FILE indicator). Brand/license/repo info
    lives above the box in the logo region.
    """
    if not state.env_file_path:
        return Text("", style=palette.COLOR_DIM)
    line = Text()
    line.append(f"env: {state.env_file_path}", style=palette.COLOR_DIM)
    return line


# --- Wizard chrome ---------------------------------------------------------

def _render_wizard_progress(state: AppState, available_width: int) -> RenderableType:
    """
    Wizard-mode progress row: 'Step N/Total  ████████░░░░  XX%'.

    `wizard_step` is the count of *completed* answers (0..wizard_total).
    The label shows the user-facing "currently on" step (completed + 1)
    while still in progress, and "total/total" only after the final
    answer. The bar fill follows the completion fraction so 100% appears
    only after the last question is answered.
    """
    if state.wizard_total <= 0:
        return Text("")

    pct = int((state.wizard_step / state.wizard_total) * 100)
    if state.wizard_step >= state.wizard_total:
        display_step = state.wizard_total
    else:
        display_step = state.wizard_step + 1
    label = Text(f"Step {display_step}/{state.wizard_total}  ", style=palette.COLOR_DIM)

    bar_width = max(20, min(available_width - 30, 50))
    bar = ProgressBar(
        total=state.wizard_total,
        completed=state.wizard_step,
        width=bar_width,
        complete_style=palette.COLOR_ACCENT,
        finished_style=palette.COLOR_CONTAINER,
    )

    pct_text = Text(f"  {pct}%", style=palette.COLOR_DIM)

    return Columns([label, bar, pct_text], padding=0, expand=False)


def _render_command_preview(state: AppState) -> Text:
    """Wizard-mode command preview, shown below the services list."""
    cmd = Text()
    cmd.append("Command: ", style=palette.COLOR_DIM)
    cmd.append(state.wizard_command_preview, style=palette.COLOR_ACCENT)
    return cmd


# --- Services list (the heart of the box) ----------------------------------

def _render_services(state: AppState, available_width: int) -> RenderableType:
    """
    Render the flat services list — 2 columns when wide enough, 1 column
    otherwise. Sort order is the same in both layouts. Alias and port get
    their own columns so both stay visible for services that have a hosts
    alias.
    """
    sorted_svcs = _sort_services(state.services)

    if available_width >= WIDTH_TWO_COL:
        return _render_two_columns(sorted_svcs, state)
    return _render_one_column(sorted_svcs, state)


def _render_two_columns(services: List[ServiceEntry], state: AppState) -> RenderableType:
    """
    Split the sorted service list across two roughly-equal columns. The
    first half goes in a left Table, the second half in a right Table.
    Tables enforce per-column widths so rows align identically across both
    halves. The cluster is left-aligned (no Align.center wrapper) — wide
    terminals leave room on the right for future service additions and
    visual breathing room.
    """
    n = len(services)
    half = ceil(n / 2)
    left_table = _build_services_table(services[:half], state)
    right_table = _build_services_table(services[half:], state)
    # padding=(0, 6) puts 12 cells of horizontal gap between the two
    # halves — clearly demarcating left and right service groups while
    # leaving the tables' fixed column widths intact.
    return Columns([left_table, right_table], padding=(0, 6), expand=False)


def _render_one_column(services: List[ServiceEntry], state: AppState) -> RenderableType:
    """One-column fallback for narrow terminals (60 ≤ width < WIDTH_TWO_COL)."""
    return _build_services_table(services, state)


def _build_services_table(services: List[ServiceEntry], state: AppState) -> Table:
    """
    Build a Table with five fixed-width columns: dot, name, alias, port,
    choice. Tables natively align rows within a column — using one Table
    per half (instead of variable-width Text rows) eliminates the drift
    between left and right columns in the 2-column layout.
    """
    table = Table(
        box=None,
        padding=(0, 1),
        show_header=False,
        show_edge=False,
        expand=False,
        pad_edge=False,
    )
    table.add_column("dot", width=2, no_wrap=True)
    table.add_column("name", width=NAME_COL_WIDTH, no_wrap=True)
    table.add_column("alias", width=ALIAS_COL_WIDTH, no_wrap=True)
    table.add_column("port", width=PORT_COL_WIDTH, justify="right", no_wrap=True)
    table.add_column("choice", width=CHOICE_COL_WIDTH, no_wrap=True)

    for svc in services:
        table.add_row(*_service_row_cells(svc, state))
    return table


def _service_row_cells(svc: ServiceEntry, state: AppState) -> tuple:
    """
    Build the five Text cells for one service row:
        ●   Open WebUI          chat.localhost      :63015   container
        ●   Supabase DB                             :63001   container
        ●   Document Pr.                                 —   off

    - Dot color comes from `palette.style_for_source(svc.source)`.
    - Name is rendered in COLOR_TEXT (active) or COLOR_OFF (disabled).
    - Alias column carries the hostname only (no `:port` suffix) — the
      port lives in its own column. Empty when no alias or hosts not
      configured. Cyan when shown.
    - Port column is right-justified, dim style. "—" when disabled.
    - Choice label colored to match the dot.
    """
    is_off = svc.source == "disabled"
    color = palette.style_for_source(svc.source)

    # Dot
    dot_cell = Text(palette.DOT_RUNNING, style=color)

    # Name — truncate with ellipsis if too long
    name = svc.name
    if len(name) > NAME_COL_WIDTH:
        name = name[: NAME_COL_WIDTH - 1] + "…"
    name_style = palette.COLOR_OFF if is_off else palette.COLOR_TEXT
    name_cell = Text(name, style=name_style)

    # Alias (hostname only — no port)
    alias_text, alias_style = _alias_for(svc, state)
    alias_cell = Text(alias_text, style=alias_style)

    # Port (bare, e.g. ":63015")
    port_text, port_style = _port_for(svc)
    port_cell = Text(port_text, style=port_style)

    # Choice label
    choice_cell = Text(_choice_label(svc), style=color)

    return (dot_cell, name_cell, alias_cell, port_cell, choice_cell)


def _alias_for(svc: ServiceEntry, state: AppState) -> tuple:
    """
    Return (text, style) for the alias column.

    Returns the friendly URL with Kong port ("chat.localhost:55668" — the
    URL the user actually pastes into a browser) in COLOR_ACCENT when the
    service has an alias AND hosts are configured AND a kong port is set.
    Otherwise an empty string in COLOR_DIM (preserves alignment).
    """
    if svc.source == "disabled":
        return ("", palette.COLOR_DIM)
    if svc.alias and state.hosts_configured and state.kong_port:
        return (f"{svc.alias}:{state.kong_port}", palette.COLOR_ACCENT)
    return ("", palette.COLOR_DIM)


def _port_for(svc: ServiceEntry) -> tuple:
    """
    Return (text, style) for the port column.

    Disabled services show "—". Active services with a port show the bare
    ":NNNN" form. Active services without a port (rare — Multi2Vec CLIP)
    show empty.
    """
    if svc.source == "disabled":
        return ("—", palette.COLOR_DIM)
    if svc.port:
        return (svc.port, palette.COLOR_DIM)
    return ("", palette.COLOR_DIM)


def _choice_label(svc: ServiceEntry) -> str:
    """
    Always-rendered choice label reflecting the user's CHOICE (the SOURCE
    value), independent of runtime state. Possible labels:
        container / CPU / GPU / local / ext / cloud / off
    """
    src = svc.source or ""
    if src == "disabled":
        return "off"
    if "container-gpu" in src or src.endswith("-gpu"):
        return "GPU"
    if "container-cpu" in src or src.endswith("-cpu"):
        return "CPU"
    if "localhost" in src:
        return "local"
    if "external" in src:
        return "ext"
    if src == "api":
        return "cloud"
    return "container"


# --- Sorting ---------------------------------------------------------------

# Sort priority for the source buckets in the box: containers first
# (green), then localhost/external/cloud (cyan), then disabled (slate).
def _source_bucket(source: str) -> int:
    if not source or source == "disabled":
        return 2
    if "localhost" in source or "external" in source or source == "api":
        return 1
    return 0  # container*


def _sort_services(services: List[ServiceEntry]) -> List[ServiceEntry]:
    """
    Sort key: (source bucket, port asc, name).
    - Bucket 0 (container) → green dots
    - Bucket 1 (local/ext/cloud) → cyan dots
    - Bucket 2 (disabled) → slate dots
    Within a bucket, services with a port sort by port number; services
    without a port sort to the end of the bucket, alphabetically by name.
    """
    def key(svc: ServiceEntry):
        bucket = _source_bucket(svc.source)
        if svc.port:
            try:
                return (bucket, 0, int(svc.port.lstrip(":")), svc.name)
            except ValueError:
                pass
        return (bucket, 1, 0, svc.name)
    return sorted(services, key=key)


# --- Helpers ---------------------------------------------------------------

def _summarize_choices(services: List[ServiceEntry]) -> dict:
    """Count services by source bucket for the compact summary."""
    counts = {"container": 0, "accent": 0, "off": 0}
    for s in services:
        b = _source_bucket(s.source)
        counts["container" if b == 0 else "accent" if b == 1 else "off"] += 1
    return counts
