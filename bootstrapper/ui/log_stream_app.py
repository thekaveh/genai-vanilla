"""
LogStreamApp — Textual app that owns the post-wizard "running stack" phase.

Layout (vertical):
  ┌─────────────────────────────────────────────────────┐
  │  Static: the rendered info-box (pinned at top)      │
  ├─────────────────────────────────────────────────────┤
  │  RichLog (bordered): docker compose build / up /    │
  │  logs streaming inside, mouse-wheel scrollable,     │
  │  auto-scroll on new lines                           │
  └─────────────────────────────────────────────────────┘

Why Textual instead of Rich Live + ANSI hacks:
  - Compositing — the Static and the log border are written once and
    kept by Textual's diff renderer; nothing repaints on log writes.
  - Native bordered region — `border: round $primary;` *is* the box.
    No DECSTBM, no DECSLRM, no ANSI sanitizer.
  - Mouse-wheel scroll inside the log widget; the info-box stays put.
  - Resize handled — Textual reflows on SIGWINCH automatically.
  - ANSI from docker compose is parsed by `Text.from_ansi()` straight
    into a styled Rich Text — original colors preserved.

The wizard's PresentationApp (Rich Live + readchar) still runs first
and exits cleanly before this app launches; they don't overlap.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
from typing import TYPE_CHECKING, List, Optional

from rich.console import RenderableType
from rich.text import Text

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import RichLog, Static


if TYPE_CHECKING:
    # Avoid circular import — start.py imports this module, and the type
    # is only used for annotation.
    from start import GenAIStackStarter


class LogStreamApp(App):
    """Textual app: pinned info-box on top, bordered streaming logs below."""

    # Border + title styling matches the upper info-box (rich.box.ROUNDED,
    # palette.COLOR_BORDER = color(60) ≈ #5F5F87 — slate-blue, restrained).
    # Title bar uses bold pale-blue color(189) ≈ #D7D7FF; subtitle uses
    # the same slate as the border. Thin 1-cell scrollbars and slate
    # accent match the sleek look of the wizard's box. wrap=True on the
    # RichLog removes the unusable horizontal scrollbar — long lines
    # wrap to the next visual row.
    CSS = """
    /* Apply 1-cell scrollbars to ALL widgets, including the implicit
       Screen scrollbar that appears when the user resizes the terminal
       narrower than the rendered info-box width. Without this, the
       horizontal scrollbar that pops up on resize uses Textual's
       default 2-row thickness — visually clumsy. */
    * {
        scrollbar-size-horizontal: 1;
        scrollbar-size-vertical: 1;
    }

    Screen {
        layout: vertical;
        background: $background;
        scrollbar-color: #5F5F87;
        scrollbar-color-hover: #D7D7FF;
        scrollbar-color-active: #D7D7FF;
        scrollbar-background: $background;
    }

    #info-box {
        height: auto;
        padding: 0;
        margin: 0;
    }

    #log-pane {
        border: round #5F5F87;
        border-title-color: #D7D7FF;
        border-title-style: bold;
        border-subtitle-color: #5F5F87;
        padding: 0 1;
        margin: 0;
        height: 1fr;
        scrollbar-color: #5F5F87;
        scrollbar-color-hover: #D7D7FF;
        scrollbar-color-active: #D7D7FF;
        scrollbar-background: $background;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Detach"),
        Binding("q", "quit", "Detach"),
    ]

    def __init__(
        self,
        info_box: RenderableType,
        starter: "GenAIStackStarter",
        cold: bool,
    ) -> None:
        super().__init__()
        self._info_box = info_box
        self._starter = starter
        self._cold = cold

    # --- Composition ------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Static(self._info_box, id="info-box")
        log = RichLog(
            id="log-pane",
            highlight=False,
            markup=False,
            # wrap=True wraps long log lines to the next visual row. This
            # removes the horizontal scrollbar entirely (it was rendered
            # but not interactable in the previous build), and keeps the
            # vertical-only scrolling that the user actually wants.
            wrap=True,
            auto_scroll=True,
            max_lines=10_000,
        )
        log.border_title = "Streaming Logs"
        log.border_subtitle = "Ctrl+C / q to detach (stack keeps running)"
        yield log

    def on_mount(self) -> None:
        # Kick off the streaming pipeline in an async worker. exclusive=True
        # ensures only one stream runs at a time; exit_on_error=False so we
        # surface failures inside the log instead of crashing the app.
        self.run_worker(self._stream_pipeline(), exclusive=True, exit_on_error=False)

    # --- Worker: docker compose build / up / verify / logs ----------------

    async def _stream_pipeline(self) -> None:
        """End-to-end docker pipeline. Each phase writes into the log."""
        log = self.query_one(RichLog)

        # --- Cold-start cleanup ---------------------------------------------
        # Done HERE inside the box (rather than in start.py's pipeline)
        # because the "Container … Removed" output is voluminous and the
        # user wants it encapsulated under the same border.
        if self._cold:
            self._write_status(log, "🧹 Cold-start cleanup", style="bold cyan")
            await self._cold_cleanup(log)

        # --- Cold-start build ------------------------------------------------
        if self._cold:
            self._write_status(log, "📦 Building images (cold start)…", style="bold cyan")
            rc = await self._run_compose(['build', '--no-cache'], log)
            if rc != 0:
                self._write_status(log, "❌ Build failed", style="bold red")
                return

        # --- Up --------------------------------------------------------------
        self._write_status(log, "🚀 Starting containers…", style="bold cyan")
        rc = await self._run_compose(['up', '-d', '--force-recreate'], log)
        if rc != 0:
            self._write_status(log, "❌ Start failed", style="bold red")
            return
        self._write_status(log, "✅ All services started", style="bold green")

        # --- Port verification + ComfyUI models check ------------------------
        # show_container_status_and_verify_ports already accepts an on_line
        # callback — feed it a writer that funnels into the RichLog. The
        # function is sync so we run it via to_thread to keep the event
        # loop responsive.
        def _on_verify_line(msg: str, level: str) -> None:
            tag = {"ok": "green", "warn": "yellow", "error": "red"}.get(level, "")
            text = Text(msg)
            if tag:
                text.stylize(tag)
            log.write(text)

        await asyncio.to_thread(
            self._starter.show_container_status_and_verify_ports,
            on_line=_on_verify_line,
        )

        # check_comfyui_models prints to plain stdout — those one or two
        # lines won't appear inside the RichLog. Acceptable cosmetic gap;
        # see plan note (a). Run in a thread so we don't block the loop.
        await asyncio.to_thread(self._starter.check_comfyui_models)

        # --- Stream logs (blocks until Ctrl+C / q) ---------------------------
        self._write_status(log, "📋 Streaming logs · Ctrl+C / q to detach", style="bold cyan")
        await self._run_compose(['logs', '-f'], log)

    async def _cold_cleanup(self, log_widget: RichLog) -> None:
        """
        Cold-start cleanup, ported from
        `core.docker_manager.DockerManager.perform_cold_start_cleanup` so
        the noisy "Container … Removed" output streams into the RichLog
        widget instead of the main screen above the box.
        """
        project_name = self._starter.config_parser.get_project_name()

        self._write_status(log_widget, "  • Stopping and removing containers…", style="dim")
        await self._run_compose(['down', '--remove-orphans'], log_widget)

        self._write_status(log_widget, "  • Removing volumes…", style="dim")
        await self._run_compose(['down', '-v'], log_widget)

        self._write_status(log_widget, "  • Removing project network…", style="dim")
        await self._run_command(
            ['docker', 'network', 'rm', f'{project_name}-network'],
            log_widget,
            ignore_errors=True,
        )

        self._write_status(log_widget, "  • Aggressive Docker system prune…", style="dim")
        await self._run_command(
            ['docker', 'system', 'prune', '-f', '--volumes'],
            log_widget,
        )

        self._write_status(log_widget, "  • General Docker system prune…", style="dim")
        await self._run_command(
            ['docker', 'system', 'prune', '-f'],
            log_widget,
        )

    async def _run_command(
        self,
        cmd: List[str],
        log_widget: RichLog,
        ignore_errors: bool = False,
    ) -> int:
        """
        Run an arbitrary command (not necessarily `docker compose`) with
        stdout piped, line-buffered, forwarded into the RichLog. Used for
        cold-cleanup steps (`docker network rm`, `docker system prune`).
        """
        cmd_text = Text("$ " + " ".join(cmd), style="dim")
        log_widget.write(cmd_text)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except FileNotFoundError as exc:
            self._write_status(log_widget, f"❌ {exc}", style="bold red")
            return 1

        try:
            assert proc.stdout is not None
            async for raw in proc.stdout:
                line = raw.decode(errors='replace').rstrip("\r\n")
                log_widget.write(Text.from_ansi(line))
            rc = await proc.wait()
            if rc != 0 and not ignore_errors:
                self._write_status(log_widget, f"  ↳ exit {rc}", style="dim red")
            return rc
        except asyncio.CancelledError:
            with contextlib.suppress(ProcessLookupError):
                proc.send_signal(signal.SIGINT)
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(proc.wait(), timeout=3)
            if proc.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    proc.kill()
                with contextlib.suppress(Exception):
                    await proc.wait()
            raise

    async def _run_compose(self, args: List[str], log_widget: RichLog) -> int:
        """
        Run `docker compose <args>` with stdout piped + line-buffered;
        each line is converted from raw ANSI to a styled Rich Text and
        written into the RichLog widget.

        Returns the subprocess exit code.
        """
        full_cmd = self._starter.docker_manager._build_compose_command(
            args, top_level_flags=['--ansi=always'],
        )
        # BUILDKIT_PROGRESS=plain keeps `docker compose build` line-based
        # so buildkit's fancy renderer doesn't dump cursor codes into our
        # widget (RichLog would render them as styled text and waste rows).
        env = {**os.environ, 'BUILDKIT_PROGRESS': 'plain'}

        # Optional command echo — dim grey, distinguishes our log entries
        # from docker's. Reuses the docker_manager's _on_command callback
        # contract conceptually.
        cmd_text = Text("$ " + " ".join(full_cmd), style="dim")
        log_widget.write(cmd_text)

        try:
            proc = await asyncio.create_subprocess_exec(
                *full_cmd,
                cwd=str(self._starter.docker_manager.root_dir),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env,
            )
        except FileNotFoundError as exc:
            self._write_status(log_widget, f"❌ {exc}", style="bold red")
            return 1

        try:
            assert proc.stdout is not None
            async for raw in proc.stdout:
                line = raw.decode(errors='replace').rstrip("\r\n")
                # Text.from_ansi converts SGR codes from docker compose
                # (and from the services themselves) into a Rich Text
                # with the original styling; everything that isn't SGR
                # — cursor moves, screen clears, scroll-region resets —
                # is silently ignored by the parser. No manual sanitizer.
                log_widget.write(Text.from_ansi(line))
            return await proc.wait()
        except asyncio.CancelledError:
            # User pressed Ctrl+C / q. Send SIGINT, give docker 3 s to
            # exit cleanly (it'll detach from logs without stopping
            # containers), then SIGKILL as a last resort.
            with contextlib.suppress(ProcessLookupError):
                proc.send_signal(signal.SIGINT)
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(proc.wait(), timeout=3)
            if proc.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    proc.kill()
                with contextlib.suppress(Exception):
                    await proc.wait()
            raise

    # --- Helpers ----------------------------------------------------------

    @staticmethod
    def _write_status(log_widget: RichLog, message: str, *, style: str = "") -> None:
        """Write a styled status line to the RichLog."""
        text = Text(message)
        if style:
            text.stylize(style)
        log_widget.write(text)

    # --- Actions ----------------------------------------------------------

    def action_quit(self) -> None:
        self.exit()
