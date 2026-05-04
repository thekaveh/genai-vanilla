"""
WizardScreen — single screen for the entire setup → launch → logs flow.

Layout (top to bottom):
    BlockLogo                           7 cells
    Vertical#wizard-body                1fr
        Vertical#info-section: InfoPanel        (always visible, auto)
        Vertical#lower-pane:
            during setup:  PromptPanel + CommandSummary
            during launch: LogFilterChips + LogPane
    FooterBar                           3 cells (docked bottom)

No tab bar, no status ribbon — the prompt panel's border carries its
own title and step counter, so the chrome stays minimal. The service
status box stays pinned at top, and the lower pane swaps from
prompt+command-summary to filter-chips+log-pane when the user
confirms launch.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
import sys
from typing import Callable

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen

from ..widgets import (
    BrandInfo,
    BrandPanel,
    CommandSummary,
    FooterBar,
    InfoBoxState,
    InfoPanel,
    LogFilterChips,
    LogPane,
    PromptPanel,
    PromptStep,
    ServiceRow,
    ServiceSummary,
    ServiceTable,
)


_SETUP_HINTS = [
    (("↑", "↓"), "navigate"),
    (("↵",), "confirm"),
    (("esc",), "back"),
    (("ctrl+q",), "quit & save"),
]

_LAUNCH_HINTS = [
    (("a",), "all"),
    (("e",), "errors"),
    (("w",), "warns"),
    (("i",), "info"),
    (("ctrl+q",), "detach"),
]


class WizardScreen(Screen):
    """Setup wizard + in-place log streaming."""

    AUTO_FOCUS = None

    BINDINGS = [
        Binding("up", "move(-1)", "Up", priority=True),
        Binding("down", "move(1)", "Down", priority=True),
        Binding("k", "move(-1)", "Up", priority=True),
        Binding("j", "move(1)", "Down", priority=True),
        Binding("enter", "confirm", "Confirm", priority=True),
        Binding("escape", "back", "Back", priority=True),
        Binding("ctrl+q", "quit_wizard", "Quit", priority=True),
        Binding("a", "filter_all", "All logs", show=False, priority=True),
        Binding("e", "filter_errors", "Errors only", show=False, priority=True),
        Binding("w", "filter_warns", "Warns only", show=False, priority=True),
        Binding("i", "filter_info", "Info only", show=False, priority=True),
    ]

    DEFAULT_CSS = """
    WizardScreen {
        background: #12131e;
        layers: base popup;
    }
    WizardScreen > #wizard-body {
        height: 1fr;
        padding: 0 2;
    }
    WizardScreen #info-section { width: 100%; height: auto; }
    WizardScreen #lower-pane {
        width: 100%;
        height: 1fr;
    }
    """

    def __init__(
        self,
        *,
        steps: list[PromptStep],
        services: list[ServiceRow],
        brand: BrandInfo | None = None,
        starter=None,
        stack_options_resolver: Callable[[dict[str, str]], tuple[dict, dict]] | None = None,
        on_complete: Callable[[dict[str, str]], None] | None = None,
        on_base_port_change: Callable[[int, list[ServiceRow]], list[ServiceRow]] | None = None,
        resolve_port_for_service: Callable[[str, str], str] | None = None,
        auto_launch: bool = False,
        prefilled_source_args: dict | None = None,
        prefilled_stack_options: dict | None = None,
    ) -> None:
        super().__init__()
        self._steps = steps
        self._services = services
        self._brand = brand or BrandInfo()
        self._starter = starter
        self._stack_options_resolver = stack_options_resolver
        self._on_complete = on_complete
        # Called when the user confirms a new base port; should return
        # an updated list of ServiceRows with recomputed ports.
        self._on_base_port_change = on_base_port_change
        # Called when the user picks a new SOURCE for a service. Given
        # (service_name, new_source) returns the port string to display
        # — typically the localhost port for "localhost" sources and
        # the container port otherwise. Returns "" when no port should
        # be shown (e.g., disabled).
        self._resolve_port_for_service = resolve_port_for_service
        # Auto-launch mode: skip the wizard prompts entirely and jump
        # straight to the launch phase. Used when start.py is invoked
        # with explicit CLI flags so the user doesn't have to walk
        # through the wizard for choices they've already made.
        self._auto_launch = auto_launch
        if prefilled_source_args is not None:
            self._source_args = dict(prefilled_source_args)
        else:
            self._source_args = None
        if prefilled_stack_options is not None:
            self._stack_options = dict(prefilled_stack_options)
        else:
            self._stack_options = None

        self._step_index = 0
        self._selections: dict[str, str] = {}
        # Frozen defaults snapshot — used to compute "N changed from
        # defaults" correctly (only count selections that DIFFER from
        # their step's default_value).
        self._defaults: dict[str, str] = {
            s.title: (s.default_value or "") for s in steps
        }

        self._phase: str = "setup"   # "setup" | "launch"

        self._command_summary = CommandSummary()
        self._service_table = ServiceTable(services)
        summaries = [
            ServiceSummary(name=r.name, source=r.source, port=r.port, alias=r.alias)
            for r in services
        ]
        self._info_panel = InfoPanel(
            InfoBoxState(brand=self._brand, services=summaries),
            body_widgets=[self._service_table],
            title=f" Stack overview · {len(services)} services ",
        )
        self._prompt = PromptPanel()
        self._footer = FooterBar(hints=_SETUP_HINTS)

        # Launch-phase widgets created lazily on transition.
        # NOTE: ``_source_args`` and ``_stack_options`` may have been
        # seeded above from prefilled_* arguments — DON'T overwrite
        # them here.
        self._log_chips: LogFilterChips | None = None
        self._log_pane: LogPane | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="wizard-body"):
            yield BrandPanel(
                tagline=self._brand.tagline or "Gen-AI Development Suite",
                author=self._brand.creator,
                author_email=self._brand.creator_email,
                license=self._brand.license,
                version=self._brand.version,
                repo=self._brand.repo,
            )
            with Vertical(id="info-section"):
                yield self._info_panel
            with Vertical(id="lower-pane"):
                yield self._prompt
                yield self._command_summary
            yield self._footer

    def on_mount(self) -> None:
        # Set the compose-line project prefix as EARLY as possible so
        # any source name that flows into the filter dropdown gets
        # stripped to its bare form (``supabase-db`` instead of
        # ``<project>-supabase-db``). Doing it here, before any worker
        # runs, eliminates the timing window in which the default
        # ``"genai-"`` prefix could leak through and produce both
        # stripped + unstripped chips.
        if self._starter is not None:
            try:
                set_project_prefix(self._starter.config_parser.get_project_name())
            except Exception:  # noqa: BLE001
                pass
        if self._auto_launch:
            # CLI-flag mode: skip the wizard and jump straight to the
            # launch phase. The prompt panel and command summary are
            # composed in the tree but get removed by the transition's
            # ``await lower.remove_children()`` step.
            self.run_worker(
                self._transition_to_launch(),
                exclusive=True, exit_on_error=False,
            )
            return
        self._load_current_step()
        # Pin --base-port into the command summary from the start so it's
        # ALWAYS visible regardless of whether the user has reached the
        # base-port step yet.
        self._refresh_command_summary()

    # ─── setup phase ─────────────────────────────────────────────────

    def _changed_count(self) -> int:
        n = 0
        for title, value in self._selections.items():
            default = self._defaults.get(title, "")
            if default and value != default:
                n += 1
        return n

    def _load_current_step(self) -> None:
        original = self._steps[self._step_index]
        step = PromptStep(
            title=original.title,
            step_index=self._step_index + 1,
            step_total=len(self._steps),
            heading=original.heading,
            subtitle=original.subtitle,
            options=original.options,
            default_value=original.default_value,
            service_name=original.service_name,
            kind=original.kind,
            number_min=original.number_min,
            number_max=original.number_max,
        )
        self._prompt.load_step(step)
        if step.service_name:
            target = step.service_name.lower()
            for i, row in enumerate(self._services):
                if row.name.lower() == target:
                    self._service_table.set_cursor(i)
                    break
        else:
            self._service_table.set_cursor(None)
        self._prompt.clear_conflict()

    def action_move(self, delta: int) -> None:
        if self._phase != "setup":
            return
        self._prompt.move(delta)

    def action_confirm(self) -> None:
        if self._phase != "setup":
            return
        opt = self._prompt.selected_option
        if opt is None:
            return
        step = self._steps[self._step_index]
        self._selections[step.title] = opt.value
        # Service-source step: update that row's source and refresh.
        for row in self._services:
            if step.service_name and row.name == step.service_name:
                row.source = opt.value
                # Re-derive the port for the new source — localhost
                # sources should show the host machine's port, container
                # sources the assigned container port, disabled none.
                if self._resolve_port_for_service is not None:
                    try:
                        new_port = self._resolve_port_for_service(row.name, row.source)
                        row.port = new_port or ""
                    except Exception:  # noqa: BLE001
                        pass
                # Re-sort the overview by displayed port — a localhost
                # source can radically change the port (e.g. ComfyUI
                # :63018 → :8000), so this row's position in the list
                # may need to move.
                def _port_key(r):
                    raw = (r.port or "").lstrip(":").strip()
                    try:
                        return (0, int(raw)) if raw else (1, 0)
                    except ValueError:
                        return (1, 0)
                self._services.sort(key=_port_key)
                self._service_table.set_rows(self._services)
                summaries = [
                    ServiceSummary(name=r.name, source=r.source, port=r.port, alias=r.alias)
                    for r in self._services
                ]
                self._info_panel.update_state(
                    InfoBoxState(brand=self._brand, services=summaries)
                )
                break
        # Base-port step: recompute every row's port from the new base.
        if "base port" in step.title.lower() and self._on_base_port_change is not None:
            try:
                new_base = int(opt.value)
            except ValueError:
                new_base = None
            if new_base is not None:
                self._services = self._on_base_port_change(new_base, self._services)
                self._service_table.set_rows(self._services)
                summaries = [
                    ServiceSummary(name=r.name, source=r.source, port=r.port, alias=r.alias)
                    for r in self._services
                ]
                self._info_panel.update_state(
                    InfoBoxState(brand=self._brand, services=summaries)
                )
        self._refresh_command_summary()
        if self._step_index + 1 < len(self._steps):
            self._step_index += 1
            self._load_current_step()
        else:
            # Last step is the launch confirm. opt.value is "yes" / "no".
            if self._on_complete is not None:
                self._on_complete(dict(self._selections))
            if opt.value == "yes":
                self.run_worker(self._transition_to_launch(), exclusive=True)

    def _refresh_command_summary(self) -> None:
        flags: list[tuple[str, str]] = []
        # Base-port flag is ALWAYS shown — pinned at the top so the user
        # can see the chosen base port at a glance regardless of whether
        # it differs from the default. Falls back to the step's default
        # value when the user hasn't reached the base-port step yet.
        for step in self._steps:
            if "base port" in step.title.lower() and not step.service_name:
                value = self._selections.get(
                    step.title, self._defaults.get(step.title, ""),
                )
                if value:
                    flags.append(("--base-port", value))
                break
        # All other steps follow.
        for step in self._steps:
            value = self._selections.get(step.title)
            if value is None:
                continue
            default = self._defaults.get(step.title, "")

            if step.service_name:
                # Service source flag — always show once picked.
                flag = "--" + step.service_name.lower().replace(" ", "-") + "-source"
                flags.append((flag, value))
                continue

            # Skip base-port here (already pinned above) and meta steps
            # whose value matches the default.
            title_low = step.title.lower()
            if "base port" in title_low:
                continue
            if value == default:
                continue
            if "cold" in title_low and value == "yes":
                flags.append(("--cold", ""))
            elif "hosts" in title_low and value == "setup":
                flags.append(("--setup-hosts", ""))
            elif "hosts" in title_low and value == "skip":
                flags.append(("--skip-hosts", ""))
            # launch confirm itself never appears as a flag

        self._command_summary.set_flags(flags)

    def action_back(self) -> None:
        # If a chip popup is open, escape closes it first instead of
        # rewinding the wizard step.
        if (
            self._log_chips is not None
            and getattr(self._log_chips, "_open_popup", None) is not None
        ):
            self._log_chips._open_popup.action_dismiss()
            return
        if self._phase != "setup":
            return
        if self._step_index > 0:
            self._step_index -= 1
            self._load_current_step()
        else:
            self.app.exit()

    def action_quit_wizard(self) -> None:
        self.app.exit()

    # ─── transition ──────────────────────────────────────────────────

    async def _transition_to_launch(self) -> None:
        # If args were prefilled at construction time (auto-launch mode),
        # honor them. Otherwise resolve from the wizard's selections.
        if self._source_args is None or self._stack_options is None:
            if self._stack_options_resolver is not None:
                self._source_args, self._stack_options = self._stack_options_resolver(
                    dict(self._selections)
                )
            else:
                self._source_args, self._stack_options = {}, {}

        self._phase = "launch"
        self.set_focus(None)

        lower = self.query_one("#lower-pane", Vertical)
        await lower.remove_children()

        self._log_chips = LogFilterChips(on_change=self._on_log_filter_change)
        self._log_pane = LogPane(
            title=" Stack startup · pipeline ",
            subtitle=" ctrl+q to detach ",
        )
        self._log_pane.set_on_new_source(self._log_chips.add_source)
        await lower.mount(self._log_chips)
        await lower.mount(self._log_pane)

        self._footer.update_hints(_LAUNCH_HINTS)

        if self._starter is None:
            return  # wizard-only mode (tests)

        self.run_worker(
            self._run_pipeline_and_stream(),
            exclusive=False, exit_on_error=False,
        )

    def _on_log_filter_change(self, level: str, disabled: set[str]) -> None:
        if self._log_pane is not None:
            self._log_pane.set_filter(level, disabled)

    def action_filter_all(self) -> None:
        if self._phase == "launch" and self._log_chips is not None:
            self._log_chips.clear_filters()

    def action_filter_errors(self) -> None:
        if self._phase == "launch" and self._log_chips is not None:
            self._log_chips.set_level("error")

    def action_filter_warns(self) -> None:
        if self._phase == "launch" and self._log_chips is not None:
            self._log_chips.set_level("warn")

    def action_filter_info(self) -> None:
        if self._phase == "launch" and self._log_chips is not None:
            self._log_chips.set_level("info")

    # ─── pipeline + docker compose runner ────────────────────────────

    def _write_status(self, msg: str, *, style: str = "", source: str = "pipeline") -> None:
        if self._log_pane is None:
            return
        text = Text(msg)
        if style:
            text.stylize(style)
        level = "info"
        if "red" in style: level = "error"
        elif "yellow" in style: level = "warn"
        elif "green" in style: level = "ok"
        elif "cyan" in style: level = "info"
        elif "dim" in style: level = "dim"
        self._log_pane.write_styled(text, level=level, source=source)

    def _safe_log(self, msg: str, *, source: str = "pipeline", level: str = "info") -> None:
        """Thread-safe write into the LogPane — used by callbacks coming
        from the pipeline's worker thread."""
        if self._log_pane is None:
            return
        try:
            self.app.call_from_thread(
                self._log_pane.write_log, msg, level=level, source=source,
            )
        except Exception:  # noqa: BLE001
            pass

    async def _run_pipeline_and_stream(self) -> None:
        starter = self._starter
        cold = bool((self._stack_options or {}).get("cold", False))
        base_port = int((self._stack_options or {}).get("base_port", 63000))
        setup_hosts = bool((self._stack_options or {}).get("setup_hosts", False))
        skip_hosts = bool((self._stack_options or {}).get("skip_hosts", False))

        original_banner = getattr(starter, "banner", None)
        starter.banner = _NullBanner()

        # Tell the compose-line classifier the actual project name so
        # container names like ``<project>-supabase-db-1`` collapse to
        # ``supabase-db`` and don't appear as duplicate sources in the
        # filter dropdown next to the bare names.
        try:
            set_project_prefix(starter.config_parser.get_project_name())
        except Exception:  # noqa: BLE001
            pass

        # Route any subprocess output the docker_manager / hosts_manager
        # would otherwise print to the terminal directly into the LogPane,
        # so the Textual chrome doesn't get corrupted by stray writes.
        try:
            starter.docker_manager.set_command_echo_callback(
                lambda msg: self._safe_log(msg, source="docker", level="info")
            )
        except Exception:  # noqa: BLE001
            pass
        try:
            starter.hosts_manager.set_logger(
                lambda msg, level="info": self._safe_log(
                    msg, source="hosts",
                    level={"warning": "warn", "success": "ok"}.get(level, level),
                )
            )
        except Exception:  # noqa: BLE001
            pass

        # Capture any stray ``print()`` calls from starter helpers
        # (port_manager, key_generator, etc.) and route them to the LogPane.
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = _LogPaneWriter(self, source="pipeline", level="info")
        sys.stderr = _LogPaneWriter(self, source="pipeline", level="warn")

        # CRITICAL: ``docker_manager.execute_compose_command`` runs
        # ``subprocess.run`` WITHOUT redirecting stdout — its docker compose
        # output goes straight to the terminal fd and overwrites the
        # Textual screen. Wrap it for the duration of the pipeline so its
        # output gets piped into the LogPane like every other compose call.
        original_execute = starter.docker_manager.execute_compose_command

        def _patched_execute(args, use_env_file=True):
            full_cmd = starter.docker_manager._build_compose_command(
                args, top_level_flags=["--ansi=always"],
            )
            self._safe_log("$ " + " ".join(full_cmd), source="docker", level="dim")
            try:
                import subprocess as _sp
                proc = _sp.Popen(
                    full_cmd,
                    cwd=str(starter.docker_manager.root_dir),
                    stdin=_sp.DEVNULL, stdout=_sp.PIPE, stderr=_sp.STDOUT,
                    text=True, bufsize=1,
                )
                assert proc.stdout is not None
                for line in proc.stdout:
                    line = line.rstrip("\r\n")
                    if line:
                        src, lvl = _classify_compose_line(line)
                        self._safe_log(line, source=(src or "docker"), level=lvl)
                return proc.wait()
            except Exception as exc:  # noqa: BLE001
                self._safe_log(f"❌ {exc}", source="docker", level="error")
                return 1

        starter.docker_manager.execute_compose_command = _patched_execute

        steps = [
            ("Apply source overrides",
             lambda: starter.apply_source_overrides(**(self._source_args or {}))),
            ("Validate source configurations",
             starter.validate_source_configurations),
            # Always clear any port env vars left over from a previous
            # session BEFORE port configuration runs, so the new
            # base-port assignments aren't shadowed by stale exports.
            ("Clear stale port environment",
             lambda: (starter.unset_port_environment_variables() or True)),
            ("Configure ports",
             lambda: starter.handle_port_configuration(base_port)),
            ("Generate service configuration",
             starter.generate_service_configuration),
            ("Check service dependencies",
             starter.check_service_dependencies),
            ("Generate Kong configuration",
             starter.generate_kong_configuration),
            ("Validate Supabase keys",
             lambda: starter.validate_supabase_keys(cold_start=cold)),
            ("Configure hosts",
             lambda: starter.handle_hosts_configuration(setup_hosts, skip_hosts)),
            ("Generate encryption keys",
             lambda: starter.generate_encryption_keys(cold_start=cold)),
            ("Validate localhost services",
             starter.validate_localhost_services),
        ]

        self._write_status("⚙ Running setup pipeline", style="bold cyan",
                           source="pipeline")
        try:
            for i, (label, fn) in enumerate(steps, start=1):
                self._write_status(f"  · {label}…", style="dim",
                                   source="pipeline")
                try:
                    ok = await asyncio.to_thread(fn)
                except Exception as exc:  # noqa: BLE001
                    self._write_status(f"  ✗ {label} crashed: {exc}",
                                       style="bold red", source="pipeline")
                    return
                if not ok:
                    self._write_status(f"  ✗ {label} failed",
                                       style="bold red", source="pipeline")
                    return
                self._write_status(f"  ✓ {label}", style="bold green",
                                   source="pipeline")

            self._write_status("", style="", source="pipeline")

            if cold:
                self._write_status("🧹 Cold-start cleanup",
                                   style="bold cyan", source="pipeline")
                await self._cold_cleanup()
                self._write_status("📦 Building images (cold start)…",
                                   style="bold cyan", source="pipeline")
                rc = await self._run_compose(["build", "--no-cache"])
                if rc != 0:
                    self._write_status("❌ Build failed", style="bold red",
                                       source="pipeline")
                    return

            self._write_status("🚀 Starting containers…",
                               style="bold cyan", source="pipeline")
            rc = await self._run_compose(["up", "-d", "--force-recreate"])
            if rc != 0:
                self._write_status("❌ Start failed", style="bold red",
                                   source="pipeline")
                return
            self._write_status("✅ All services started",
                               style="bold green", source="pipeline")

            if self._log_pane is not None:
                self._log_pane.set_title(
                    " Live docker logs ",
                    subtitle=" ctrl+q to detach ",
                )

            # Kick off port verification + ComfyUI model check in the
            # background so the live log stream starts IMMEDIATELY rather
            # than waiting for ~18 sequential subprocess calls.
            def _on_verify_line(msg: str, level: str) -> None:
                self._safe_log(msg, source="verify", level=level)

            async def _post_up_checks() -> None:
                with contextlib.suppress(Exception):
                    await asyncio.to_thread(
                        starter.show_container_status_and_verify_ports,
                        on_line=_on_verify_line,
                    )
                with contextlib.suppress(Exception):
                    await asyncio.to_thread(starter.check_comfyui_models)

            self.run_worker(_post_up_checks(), exclusive=False, exit_on_error=False)

            self._write_status(
                "📋 Streaming docker logs · ctrl+q to detach",
                style="bold cyan", source="pipeline",
            )
            await self._run_compose(["logs", "-f"])
        finally:
            starter.banner = original_banner
            try:
                starter.docker_manager.set_command_echo_callback(print)
            except Exception:  # noqa: BLE001
                pass
            try:
                starter.hosts_manager.set_logger(None)
            except Exception:  # noqa: BLE001
                pass
            try:
                starter.docker_manager.execute_compose_command = original_execute
            except Exception:  # noqa: BLE001
                pass
            sys.stdout, sys.stderr = old_stdout, old_stderr

    async def _cold_cleanup(self) -> None:
        project_name = self._starter.config_parser.get_project_name()
        self._write_status("  • Stopping and removing containers…",
                           style="dim", source="pipeline")
        await self._run_compose(["down", "--remove-orphans"])
        self._write_status("  • Removing volumes…", style="dim", source="pipeline")
        await self._run_compose(["down", "-v"])
        self._write_status("  • Removing project network…",
                           style="dim", source="pipeline")
        await self._run_command(
            ["docker", "network", "rm", f"{project_name}-network"],
            ignore_errors=True,
        )
        self._write_status("  • Aggressive Docker system prune…",
                           style="dim", source="pipeline")
        await self._run_command(["docker", "system", "prune", "-f", "--volumes"])
        self._write_status("  • General Docker system prune…",
                           style="dim", source="pipeline")
        await self._run_command(["docker", "system", "prune", "-f"])

    async def _run_command(
        self, cmd: list[str], *, ignore_errors: bool = False,
    ) -> int:
        cmd_text = Text("$ " + " ".join(cmd), style="dim")
        if self._log_pane is not None:
            self._log_pane.write_styled(cmd_text, level="dim", source="docker")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except FileNotFoundError as exc:
            self._write_status(f"❌ {exc}", style="bold red", source="docker")
            return 1
        try:
            assert proc.stdout is not None
            async for raw in proc.stdout:
                line = raw.decode(errors="replace").rstrip("\r\n")
                if self._log_pane is not None:
                    self._log_pane.write_log(line, level="info", source="docker")
            rc = await proc.wait()
            if rc != 0 and not ignore_errors:
                self._write_status(f"  ↳ exit {rc}", style="dim red",
                                   source="docker")
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

    async def _run_compose(self, args: list[str]) -> int:
        full_cmd = self._starter.docker_manager._build_compose_command(
            args, top_level_flags=["--ansi=always"],
        )
        env = {**os.environ, "BUILDKIT_PROGRESS": "plain"}
        cmd_text = Text("$ " + " ".join(full_cmd), style="dim")
        if self._log_pane is not None:
            self._log_pane.write_styled(cmd_text, level="dim", source="docker")
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
            self._write_status(f"❌ {exc}", style="bold red", source="docker")
            return 1
        try:
            assert proc.stdout is not None
            async for raw in proc.stdout:
                line = raw.decode(errors="replace").rstrip("\r\n")
                source, level = _classify_compose_line(line)
                if self._log_pane is not None:
                    self._log_pane.write_log(line, level=level, source=source)
            return await proc.wait()
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


# Module-level project prefix — set at launch transition via
# ``set_project_prefix()`` from the actual ConfigParser.get_project_name()
# value, so containers like ``<project_name>-supabase-db-1`` are stripped
# down to ``supabase-db`` regardless of how the user named their stack.
_PROJECT_PREFIX = "genai-"


def set_project_prefix(project_name: str) -> None:
    """Update the project-name prefix used by ``_strip_project``."""
    global _PROJECT_PREFIX
    if project_name:
        _PROJECT_PREFIX = f"{project_name.strip().rstrip('-')}-"


_ANSI_RE = __import__("re").compile(r"\x1b\[[0-9;]*[A-Za-z]")


def _strip_ansi(s: str) -> str:
    """Drop ANSI color/style escape sequences. ``compose --ansi=always``
    wraps service names in color codes that would otherwise defeat the
    project-prefix string match below."""
    return _ANSI_RE.sub("", s)


def _strip_project(name: str) -> str:
    """Strip project prefix + trailing replica suffix from a compose container name.

    Handles both Compose v2 (``<project>-<service>-1``, hyphen-joined)
    and v1 (``<project>_<service>_1``, underscore-joined). Also strips
    any embedded ANSI color escape sequences before matching.

    ``<project>-supabase-db-1`` → ``supabase-db``
    ``<project>_supabase-db_1`` → ``supabase-db``
    ``<project>-ollama-pull``   → ``ollama-pull``
    """
    n = _strip_ansi(name).strip()
    # Try the active project prefix in both -/_ separators.
    base = _PROJECT_PREFIX.rstrip("-_")
    for prefix in (f"{base}-", f"{base}_"):
        if n.startswith(prefix):
            n = n[len(prefix):]
            break
    # Drop trailing -<digit>+ or _<digit>+ replica suffix.
    for sep in ("-", "_"):
        if sep in n:
            head, _, tail = n.rpartition(sep)
            if tail.isdigit() and head:
                n = head
                break
    return n


def _classify_compose_line(line: str) -> tuple[str, str]:
    """Best-effort (source, level) classification for a docker compose line.

    Three common shapes:
      * ``service-1  | message`` — from ``compose logs -f``
      * ``Container genai-svc-1  Created`` — from ``compose up/down``
      * ``Network genai-network  Created`` — from ``compose up/down``

    Level is sniffed from common keywords (ERROR/WARN/etc).
    """
    src = ""
    rest = line
    if "|" in line:
        head, _, rest = line.partition("|")
        head_word = head.strip().split()[0] if head.strip() else ""
        src = _strip_project(head_word)
        rest = rest.strip()
    else:
        words = line.strip().split()
        if len(words) >= 2 and words[0] in ("Container", "Network", "Volume"):
            src = _strip_project(words[1])
    upper = rest.upper()
    if "ERROR" in upper or " ERR " in upper or upper.startswith("ERR"):
        level = "error"
    elif "WARN" in upper or "WARNING" in upper:
        level = "warn"
    else:
        level = "info"
    return src, level


class _LogPaneWriter:
    """File-like sink that flushes whole lines into a WizardScreen's LogPane.

    Captures stray ``print()`` calls from pipeline helpers so they don't
    corrupt Textual's screen buffer.
    """

    def __init__(self, screen, *, source: str = "stdout", level: str = "info") -> None:
        self._screen = screen
        self._source = source
        self._level = level
        self._buf = ""

    def write(self, s: str) -> int:
        if not s:
            return 0
        self._buf += s
        while "\n" in self._buf:
            line, _, self._buf = self._buf.partition("\n")
            line = line.rstrip("\r")
            if line.strip():
                self._screen._safe_log(line, source=self._source, level=self._level)
        return len(s)

    def flush(self) -> None:
        if self._buf.strip():
            self._screen._safe_log(self._buf, source=self._source, level=self._level)
            self._buf = ""

    def isatty(self) -> bool:
        return False

    def fileno(self) -> int:  # pragma: no cover — required for some libs
        raise OSError("LogPaneWriter has no fileno")


class _NullBanner:
    """Drop-in for ``starter.banner`` that swallows pipeline status messages
    so they don't print to stdout while we're inside the Textual app."""

    def show_status_message(self, *args, **kwargs) -> None: ...
    def show_section_header(self, *args, **kwargs) -> None: ...
    def show_subsection_header(self, *args, **kwargs) -> None: ...
    def log(self, *args, **kwargs) -> None: ...
    def status(self, *args, **kwargs) -> None: ...
    def section(self, *args, **kwargs) -> None: ...
    def __getattr__(self, name): return lambda *a, **k: None
