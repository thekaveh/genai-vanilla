"""
PresentationApp — owns the rich.live.Live region for the wizard phase.

The Live shell holds two regions in a vertical Layout:
  ┌─ TOP    — info_box (variable height, fixed at top)
  └─ BOTTOM — log_pane OR active wizard widget (fills remainder)
                                  ↑ widgets are select / number; their panel
                                  border carries the wizard step counter

Live runs in `screen=True` mode (alternate screen buffer, like vim/less) so
the box stays ANCHORED at the top of the visible terminal area regardless
of how much output the log pane emits. Auto-refresh is throttled at
REFRESH_HZ; the bottom slot's `_BottomRenderable` re-queries the LogPane
each tick so streamed appends show up without manual `Live.update()` calls.

After the wizard finishes (launch confirmed), Live tears down. The
post-wizard log streaming is owned by `ui.log_stream_app.LogStreamApp`
(Textual), not this class.

Public API:
  with PresentationApp(state) as app:
      app.log("…")                                # append a log line
      app.section("🚀 Starting Services")         # append a section header
      app.status(step, total, "…", spinner=True)  # status shown on widget
                                                  # panel title border
      app.set_box_mode("wizard")                  # toggle wizard chrome
      app.set_wizard(step, total, command)        # wizard progress + preview
      app.apply_wizard_selection(key, source, …)  # live-update one service
      app.prompt_select(...) / app.prompt_number(...)
"""

from __future__ import annotations

import shutil
import sys
import threading
from contextlib import contextmanager
from typing import Optional

try:
    import termios
    import tty
    _HAS_TERMIOS = True
except ImportError:  # Windows — terminal-mode handling is not available.
    _HAS_TERMIOS = False

from rich.console import Console, RenderableType, Group
from rich.layout import Layout
from rich.live import Live
from rich.text import Text

from ui import palette
from ui import logo as _logo
from ui.info_box import (
    WIDTH_COMPACT,
    render_compact_summary,
    render_info_box,
)
from ui.log_pane import LogPane
from ui.status_ribbon import StatusRibbon
from ui.state import AppState


# Refresh rate. 8 Hz is a sweet spot for streaming docker logs: smooth
# enough that lines feel live, low enough that the alternate-screen
# repaint isn't visibly flickering on wide terminals.
REFRESH_HZ = 8

# Below this row count, fall back to legacy banner — the box can't fit
# meaningfully in such a short terminal.
MIN_TERMINAL_ROWS = 20


class _BottomRenderable:
    """
    Renderable that lives in the Layout's bottom slot. Each render tick,
    Rich invokes `__rich_console__` and we re-query `log_pane.render()`
    for the current tail. This is the ONLY part of the frame that's
    rebuilt per refresh — top regions (logo, info-box, status ribbon,
    spacer) are static renderables held by the Layout, so their bytes
    are byte-identical across frames. That stability is what kills the
    "wiggle" the user reported during log streaming.
    """

    def __init__(self, app: "PresentationApp") -> None:
        self._app = app

    def __rich_console__(self, console, options):
        # options.max_height = the row count Rich allotted to this slot.
        rows = max(1, options.max_height or options.height or 1)
        yield self._app.log_pane.render(available_rows=rows)


class PresentationApp:
    """
    Owns the Live region, the AppState, and the three child renderables
    (info_box, status_ribbon, log_pane).
    """

    def __init__(self, state: AppState, console: Optional[Console] = None):
        self.state = state
        self.console = console or Console()
        self.log_pane = LogPane()
        self.status_ribbon = StatusRibbon()

        # Lock around state mutations so the wizard / pipeline writers
        # don't race with Rich Live's auto-refresh thread reading the
        # AppState during a paint.
        self._lock = threading.Lock()

        # The active widget, if a prompt is currently displayed. When set,
        # the bottom region renders the widget instead of the log pane.
        self._active_widget: Optional[RenderableType] = None

        # Live instance — created on __enter__, torn down on __exit__.
        self._live: Optional[Live] = None

        # The Layout handed to Live. Built once in __enter__; the top-region
        # renderables are static so their bytes don't shift across refreshes
        # (no "wiggle"). State mutators that affect the top region call
        # _rebuild_layout() to swap in fresh renderables; log()/section()
        # just append to log_pane and the bottom slot's _BottomRenderable
        # picks up the change on the next auto-refresh tick.
        self._layout: Optional[Layout] = None

        # Reusable bottom renderable — shared across rebuilds so its
        # identity is stable; only swapped out when a widget prompt takes
        # over the bottom slot.
        self._bottom_renderable: _BottomRenderable = _BottomRenderable(self)

        # Saved terminal attributes captured on __enter__, restored on
        # __exit__. While Live is active we put the tty in cbreak mode with
        # echo disabled so mouse-wheel and arrow-key bytes during log
        # streaming don't get echoed onto the alternate screen (and don't
        # leak as ASCII into the log tail).
        self._saved_term_attrs = None

    # --- Context manager -------------------------------------------------

    def __enter__(self) -> "PresentationApp":
        # Quiet the terminal first — without this, scroll-wheel events and
        # any keystroke during log streaming get echoed by the terminal
        # into the alternate screen / scroll region, looking like garbage
        # at the log tail. We do NOT restore in __exit__: the post-Live
        # log-streaming phase still benefits from no-echo. An atexit hook
        # restores at program teardown.
        self._disable_terminal_echo()

        # Build the Layout once with stable top-region renderables and a
        # _BottomRenderable in the bottom slot. Auto-refresh re-invokes
        # _BottomRenderable.__rich_console__ at REFRESH_HZ to refresh the
        # log pane; the rest of the layout is byte-stable across frames.
        self._build_layout()
        self._live = Live(
            self._layout,
            console=self.console,
            screen=True,
            refresh_per_second=REFRESH_HZ,
            redirect_stdout=False,  # we route stdout through self.log instead
            redirect_stderr=False,
            transient=False,
        )
        self._live.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._live is not None:
            self._live.__exit__(exc_type, exc, tb)
            self._live = None
        # Terminal echo stays disabled — see __enter__ comment. The atexit
        # hook registered in _disable_terminal_echo() restores at program
        # teardown so the user's shell isn't left in cbreak/no-echo mode.
        return False  # never swallow exceptions

    def _disable_terminal_echo(self) -> None:
        """
        Put stdin in cbreak + no-echo mode for the rest of the program's
        lifetime. The original attributes are captured on first call and
        restored via an atexit hook at program teardown — so the user's
        shell isn't left in cbreak mode if we crash. No-ops on non-POSIX
        or when stdin isn't a tty.
        """
        if not _HAS_TERMIOS:
            return
        try:
            fd = sys.stdin.fileno()
            if not sys.stdin.isatty():
                return
            # Capture the original state only once — multiple __enter__
            # invocations reuse the same captured baseline so atexit
            # restores correctly.
            if self._saved_term_attrs is None:
                self._saved_term_attrs = termios.tcgetattr(fd)
                import atexit
                atexit.register(self._atexit_restore)
            new_attrs = termios.tcgetattr(fd)
            # Drop ECHO + ICANON in lflag so keystrokes aren't echoed and
            # input is delivered without line buffering. readchar still
            # reads from stdin happily.
            new_attrs[3] = new_attrs[3] & ~(termios.ECHO | termios.ICANON)
            termios.tcsetattr(fd, termios.TCSANOW, new_attrs)
        except (termios.error, ValueError, OSError):
            self._saved_term_attrs = None

    def _atexit_restore(self) -> None:
        """Restore the terminal attributes captured at first __enter__."""
        if not _HAS_TERMIOS or self._saved_term_attrs is None:
            return
        try:
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSANOW, self._saved_term_attrs)
        except (termios.error, ValueError, OSError):
            pass
        finally:
            self._saved_term_attrs = None

    # --- Public API: logging ---------------------------------------------

    def log(self, message: str, *, source: Optional[str] = None, level: Optional[str] = None) -> None:
        """
        Append a line to the log pane. NO Layout rebuild — the bottom slot's
        `_BottomRenderable` re-queries the log pane on the next auto-refresh
        tick (~125 ms at REFRESH_HZ=8).
        """
        with self._lock:
            self.log_pane.append(message, source=source, level=level)

    def section(self, title: str) -> None:
        """
        Append a bold section header (e.g. '🚀 Starting Services'). Same
        as log() — bottom-only update, no Layout rebuild.
        """
        with self._lock:
            self.log_pane.append_section_header(title)

    def status(
        self,
        step: int = 0,
        total: int = 0,
        message: str = "",
        level: str = "info",
        spinner: bool = False,
    ) -> None:
        """Update the status ribbon (top region — triggers a rebuild)."""
        with self._lock:
            self.status_ribbon.set(step=step, total=total, message=message, level=level, spinner=spinner)
        self._rebuild_layout()

    # --- Public API: state mutations -------------------------------------

    def set_box_mode(self, mode: str) -> None:
        """Switch between 'normal' and 'wizard' box decorations."""
        with self._lock:
            self.state.box_mode = mode
        self._rebuild_layout()

    def set_wizard(self, step: int, total: int, command_preview: str = "") -> None:
        """Update wizard-mode-only chrome (progress bar + command preview)."""
        with self._lock:
            self.state.wizard_step = step
            self.state.wizard_total = total
            self.state.wizard_command_preview = command_preview
        self._rebuild_layout()

    def apply_wizard_selection(self, service_key: str, new_source: str,
                               config_parser=None) -> None:
        """
        Mutate the AppState.services entry matching `service_key` to reflect
        a new SOURCE chosen in the wizard, then rebuild the layout so the
        box updates immediately.

        `service_key` uses the wizard's keying (e.g. 'llm_provider',
        'neo4j-graph-db'); we map it through DISPLAY_NAME_OVERRIDES (and a
        Title-Case fallback for keys without an override) to the matching
        ServiceEntry display name.

        `config_parser` is used to re-read the .env when computing
        localhost-source ports. Optional — falls back to a fresh
        ConfigParser pointed at the bootstrapper's parent directory.
        """
        from ui.state_builder import lookup_service_meta, resolve_port
        from wizard.service_discovery import DISPLAY_NAME_OVERRIDES

        # service_key → display name
        display_name = DISPLAY_NAME_OVERRIDES.get(service_key)
        if display_name is None:
            display_name = service_key.replace('_', ' ').replace('-', ' ').title()

        meta = lookup_service_meta(display_name)
        if meta is None:
            return  # Service isn't in the box's canonical list — nothing to update.

        if config_parser is None:
            from core.config_parser import ConfigParser
            from pathlib import Path
            config_parser = ConfigParser(str(Path(__file__).resolve().parent.parent.parent))

        env = config_parser.parse_env_file()

        with self._lock:
            for entry in self.state.services:
                if entry.name == display_name:
                    entry.source = new_source
                    entry.port = resolve_port(display_name, new_source, meta["port_var"], env)
                    break
        self._rebuild_layout()

    # --- Internal: rendering ---------------------------------------------

    def _refresh_now(self) -> None:
        """
        Force an immediate paint. Used only by interactive paths (widget
        keystrokes, prompt show/hide) where the user pressed a key and
        expects the frame to update without waiting for the auto-refresh
        tick.
        """
        if self._live is not None:
            try:
                self._live.refresh()
            except Exception:
                # Live may have torn down concurrently; suppress and let
                # the next auto-refresh handle it.
                pass

    def _build_layout(self) -> None:
        """
        Construct the Layout for the current state. Top regions hold STATIC
        renderables (Panel, Text, etc.) — Rich renders them identically
        across refreshes, so no per-frame "wiggle." The bottom slot uses a
        _BottomRenderable wrapper whose __rich_console__ re-queries
        log_pane each refresh tick — so streamed log lines flow without
        any manual Live.update() calls.

        Stored on `self._layout`. Callers handle the Live wiring.
        """
        width, height = self._terminal_size()

        # Squeezed terminal — render a one-line fallback. Caller should
        # have routed to legacy mode before reaching here.
        if height < MIN_TERMINAL_ROWS or width < WIDTH_COMPACT:
            self._layout = Layout(
                Text(
                    "Terminal too small for the anchored box — see logs above.",
                    style=palette.COLOR_WARN,
                )
            )
            return

        # Logo — adaptive height by terminal size; may be skipped entirely
        # on short terminals.
        logo_height = _logo.estimated_height(width, height)
        logo_renderable = _logo.render_logo(width, height) if logo_height else None

        # Info box — full or compact depending on available height.
        if height < 30:
            box = render_compact_summary(self.state, available_width=width)
            box_size = 4
        else:
            box = render_info_box(self.state, available_width=width, available_rows=height)
            box_size = self._estimate_box_height(available_rows=height)

        # Bottom slot: a _BottomRenderable that re-queries the log pane on
        # each refresh, OR the active widget if a prompt is showing.
        bottom: RenderableType = (
            self._active_widget if self._active_widget is not None
            else self._bottom_renderable
        )

        layout = Layout()
        children = []
        if logo_renderable is not None:
            children.append(Layout(logo_renderable, name="logo", size=logo_height))
        children.extend([
            Layout(box, name="box", size=box_size),
            # 1-row spacer between info-box and bottom region.
            # Status text (e.g. "Step 12 of 15") used to live in a
            # separate ribbon row here, but it now appears on the widget
            # panel's title border (mirroring how "Setup Wizard" / "by
            # Kaveh Razavi" sit on the upper info-box border). The
            # StatusRibbon state object is still around — widgets read
            # its `title_text()` for their panel title.
            Layout(Text(" "), name="spacer", size=1),
            Layout(bottom, name="bottom", ratio=1),
        ])
        layout.split_column(*children)
        self._layout = layout

    def _rebuild_layout(self) -> None:
        """
        Rebuild the Layout from current state and hand it to Live. Called
        only by mutators that change top-region content (status, box mode,
        wizard chrome, service source/port, env file). NOT called during
        log streaming — the log pane updates via the bottom slot's
        _BottomRenderable on auto-refresh.
        """
        self._build_layout()
        if self._live is not None and self._layout is not None:
            self._live.update(self._layout, refresh=False)

    def _estimate_box_height(self, available_rows: int = 0) -> int:
        """
        Compute the box's row count without measuring. The current layout:
        a 2-column flat services list (no separate Endpoints row — aliases
        are inlined in each service's row). Plus border, optional footer,
        and wizard chrome when applicable.
        """
        from ui.info_box import WIDTH_TWO_COL

        n = len(self.state.services)
        width, _ = self._terminal_size()
        if width >= WIDTH_TWO_COL:
            services_rows = (n + 1) // 2  # ceil(n / 2)
        else:
            services_rows = n

        # Layout: 2 border + services + optional footer.
        height = 2 + services_rows
        if self.state.env_file_path:
            height += 1
        if self.state.box_mode == "wizard":
            height += 2  # progress row + spacer
            if self.state.wizard_command_preview:
                height += 2  # spacer + command-preview row
        return height

    def _terminal_size(self):
        return shutil.get_terminal_size()

    # --- Public API: prompts (delegate to widget modules) ----------------
    # These are wired by the widget modules (select_widget, number_widget)
    # which import PresentationApp via a small accessor. They share a
    # common helper to swap the bottom region during the prompt's key loop.

    @contextmanager
    def _show_widget(self, renderable: RenderableType):
        """
        Internal: temporarily swap the bottom Layout slot from the log pane
        to a widget renderable. Used by prompt_select/prompt_number/
        prompt_confirm. Forces an immediate paint so the user sees the
        prompt without waiting for the next auto-refresh tick.
        """
        self._active_widget = renderable
        if self._layout is not None:
            self._layout["bottom"].update(renderable)
        self._refresh_now()
        try:
            yield
        finally:
            self._active_widget = None
            # Restore the dynamic bottom — log pane resumes streaming.
            if self._layout is not None:
                self._layout["bottom"].update(self._bottom_renderable)
            self._refresh_now()

    def update_widget(self, renderable: RenderableType) -> None:
        """
        Refresh the active widget renderable (called by widgets each
        keystroke). Forces an immediate paint so arrow-key / Enter feedback
        feels instant — auto-refresh would otherwise add up to ~125 ms lag.
        """
        self._active_widget = renderable
        if self._layout is not None:
            self._layout["bottom"].update(renderable)
        self._refresh_now()

    # --- Public API: prompts ---------------------------------------------

    def prompt_select(self, prompt: str, choices, default_value=None):
        """
        Show an arrow-key select prompt. Returns the chosen value, or None
        on Esc. Raises KeyboardInterrupt on Ctrl+C.

        `choices` is a list of ui.select_widget.Choice instances.
        """
        from ui.select_widget import select
        return select(self, prompt, choices, default_value=default_value)

    def prompt_number(self, prompt: str, *, default: int, min_allowed: int, max_allowed: int):
        """
        Show a number-entry prompt. Returns int or None on Esc.
        """
        from ui.number_widget import number
        return number(self, prompt, default=default, min_allowed=min_allowed, max_allowed=max_allowed)

    # --- BannerDisplay-shaped adapter methods ----------------------------
    # These mirror the methods on utils.banner.BannerDisplay so callers that
    # currently do `self.banner.show_status_message(...)` continue to work
    # when `self.banner` is swapped for a PresentationApp instance during
    # TUI-capable runs. Adds zero call-site churn.

    def show_status_message(self, message: str, status: str = "info") -> None:
        """BannerDisplay shim — route status messages through the log pane."""
        # Map BannerDisplay's status keywords to our log levels.
        level_map = {"info": "info", "success": "ok", "warning": "warn", "error": "error"}
        self.log(message, level=level_map.get(status, "info"))

    def show_section_header(self, title: str, icon: str = "🔧") -> None:
        """BannerDisplay shim — route section headers through the log pane."""
        self.section(f"{icon} {title}")

    def show_banner(self, force_compact: bool = False) -> None:
        """
        BannerDisplay shim — no-op when the Live region is active.

        The anchored top box already shows the brand; legacy code that
        calls `self.banner.show_banner()` early in the flow shouldn't
        produce a second banner outside the Live region.
        """
        return None


# --- Legacy fallback --------------------------------------------------------

def is_tui_capable(no_tui_flag: bool = False) -> bool:
    """
    Decide whether the Live shell can be used.

    Returns False for: --no-tui, non-TTY stdin, or terminals smaller than
    the minimum supported size. Caller should fall back to the legacy
    linear flow in that case.
    """
    import sys
    if no_tui_flag:
        return False
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False
    try:
        size = shutil.get_terminal_size()
        if size.columns < WIDTH_COMPACT or size.lines < MIN_TERMINAL_ROWS:
            return False
    except OSError:
        return False
    return True
