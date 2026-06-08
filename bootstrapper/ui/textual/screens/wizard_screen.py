"""
WizardScreen — single screen for the entire setup → launch → logs flow.

Layout (top to bottom):
    BrandPanel (contains BlockLogo)     7 cells
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
    CloudApiSummary,
    CloudApisRow,
    CommandSummary,
    FooterBar,
    InfoBoxState,
    InfoPanel,
    LogFilterChips,
    LogPane,
    PromptOption,
    PromptPanel,
    PromptStep,
    ServiceRow,
    ServiceSummary,
    ServiceTable,
)


_SETUP_HINTS = [
    (("↑", "↓"), "navigate"),
    (("space",), "toggle"),
    (("↵",), "confirm"),
    # `Tab` / `/` both focus the model-name search input on steps that
    # mount one (today: only ``Ollama  ·  models``). No-op on other
    # steps but the hint stays visible so users know the search box is
    # keyboard-reachable. Tab again (or Esc) returns focus to the
    # option list.
    (("tab", "/"), "search"),
    # `f` cycles capability filter chips when the active step exposes
    # them (today: only ``Ollama  ·  models``). No-op on other steps;
    # hint stays visible so users on terminals without mouse passthrough
    # know the chip row is reachable from the keyboard.
    (("f",), "filter"),
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
        # Vim-style ``k``/``j`` are kept as a convenience but split
        # into a separate action so ``check_action`` can disable them
        # while the search input has focus (otherwise typing
        # ``"kimi"`` or ``"jinja"`` would walk the cursor instead of
        # appearing as text in the search box).
        Binding("k", "vim_move(-1)", "Up", priority=True),
        Binding("j", "vim_move(1)", "Down", priority=True),
        Binding("space", "toggle", "Toggle", priority=True),
        Binding("enter", "confirm", "Confirm", priority=True),
        Binding("escape", "back", "Back", priority=True),
        Binding("ctrl+q", "quit_wizard", "Quit", priority=True),
        # Multiselect filter cycle — no-op on steps without filter_tags.
        # show=False because the footer hints are explicitly listed in
        # _SETUP_HINTS rather than auto-derived from the BINDINGS list.
        Binding("f", "cycle_filter", "Filter", show=False, priority=True),
        # `/` focuses the model-name search input on the Ollama
        # multiselect step (only step that mounts one). Priority lets
        # us steal `/` even when the option list has focus.
        Binding("slash", "focus_search", "Search", show=False, priority=True),
        # Tab toggles focus between the search input and the option
        # list. Symmetric: pressing Tab from either side flips. This
        # gives the user a discoverable, keyboard-only affordance —
        # the implicit "first focusable widget" Tab behaviour Textual
        # provides isn't enough because we explicitly park focus on
        # the option list to keep Space from being eaten by an
        # unfocused-looking Input.
        Binding("tab", "toggle_search_focus", "Search", show=False, priority=True),
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
        cloud_apis: list[CloudApiSummary] | None = None,
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
        # Provider-options cache for ``options_provider``-driven steps.
        # Keyed by step_index → list[PromptOption]. ``_provider_done``
        # tracks whether the worker has populated the cache, so the
        # splash branch in ``_load_current_step`` doesn't fire twice.
        # Cleared on action_back so revisits re-fetch with the (possibly
        # changed) upstream key.
        self._provider_cache: dict[int, list] = {}
        self._provider_done: dict[int, bool] = {}
        # Generation token incremented every time we invalidate the
        # cache (action_back, etc.). Each ``_fetch_provider_options``
        # captures the generation at dispatch and refuses to write its
        # result if the token has bumped — protects against a slow
        # fetch (slow API + 5s timeout) writing stale options into a
        # cache the user has already invalidated by going back and
        # changing the upstream key.
        self._fetch_generation: int = 0

        self._phase: str = "setup"   # "setup" | "launch"

        from ..widgets.category_legend import CategoryLegend
        self._command_summary = CommandSummary()
        self._service_table = ServiceTable(services)
        self._cloud_apis: list[CloudApiSummary] = list(cloud_apis or [])
        # Pass the service table so the row can align its category legend
        # to the actual 2nd-slot start (cached by ServiceTable on each render).
        self._cloud_apis_row = CloudApisRow(
            self._cloud_apis, service_table=self._service_table,
        )
        self._category_legend = CategoryLegend()
        summaries = [
            ServiceSummary(name=r.name, source=r.source, port=r.port,
                           alias=r.alias, pending=r.pending)
            for r in services
        ]
        self._info_panel = InfoPanel(
            InfoBoxState(
                brand=self._brand,
                services=summaries,
                cloud_apis=self._cloud_apis,
            ),
            # CloudApisRow now renders the category legend on its right
            # half, so the standalone CategoryLegend widget is no longer
            # part of the body composition.
            body_widgets=[self._service_table, self._cloud_apis_row],
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

        # Register a wizard-time warning sink so cloud /v1/models fetch
        # failures (and similar) land in the launch log + log pane.
        # The sink is module-level state on integration.py so the
        # closures in _build_steps_and_rows (built BEFORE this screen
        # exists) can reach it.
        try:
            from .. import integration as _integration_mod
            _integration_mod._set_wizard_warn_sink(
                lambda msg: self._safe_log(msg, source="wizard", level="warn")
            )
        except Exception:  # noqa: BLE001
            pass

        # Open the session-log tee NOW so wizard-time warnings (cloud
        # /v1/models fetch failures, etc.) get persisted from the
        # moment the screen exists. Previously the tee was opened only
        # in the launch transition, so any setup-phase warning was
        # silently dropped — contradicting docs that promised the file
        # captured ``everything the log pane showed plus a few sources
        # the pane filters out``. The path is announced in the log
        # pane at launch time when _log_pane finally exists.
        self._launch_log_fh = None
        self._launch_log_path = None
        self._open_launch_log_tee(announce_in_pane=False)

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

    def _step_should_skip(self, idx: int) -> bool:
        """Run a step's ``skip_if_prev`` predicate. Exceptions are caught
        and treated as "don't skip" so a buggy predicate can't crash the
        wizard. Used by both the forward (``_load_current_step``) and
        backward (``action_back``) navigation walks.
        """
        if not (0 <= idx < len(self._steps)):
            return False
        skip = getattr(self._steps[idx], "skip_if_prev", None)
        if skip is None:
            return False
        try:
            return bool(skip(self._selections))
        except Exception:  # noqa: BLE001
            return False

    def _advance_past_skipped(self, direction: int) -> None:
        """Walk ``self._step_index`` in ``direction`` (+1 forward, -1 backward)
        past any consecutive skip_if_prev=True steps. Stops at the
        respective boundary (last step on forward, first step on
        backward) even if that step is itself skipped — the boundary
        steps in this wizard never set skip_if_prev, so this is safe.
        ``len(self._steps)`` bounds the loop so a pathological skip
        chain can't loop forever.
        """
        guard = 0
        max_iter = len(self._steps)
        while guard < max_iter and self._step_should_skip(self._step_index):
            next_idx = self._step_index + direction
            if direction > 0 and next_idx >= len(self._steps):
                break
            if direction < 0 and next_idx < 0:
                break
            self._step_index = next_idx
            guard += 1

    def _load_current_step(self) -> None:
        # Honor skip_if_prev — used by cloud multi-select steps to
        # bypass themselves when the previous secret step disabled
        # the provider.
        self._advance_past_skipped(direction=1)

        original = self._steps[self._step_index]
        provider = getattr(original, "options_provider", None)

        # Live options-provider path — render a "⏳ Fetching…" splash
        # first, then dispatch a worker to run the (potentially HTTP)
        # options_provider, then re-render with the real options when
        # it returns. Keeps the UI responsive (Esc still works) instead
        # of freezing the whole wizard for 5s.
        provider_pending = (
            provider is not None
            and original.kind == "multiselect"
            and not self._provider_done.get(self._step_index, False)
        )
        if provider_pending:
            # Strip a redundant " Cloud" suffix so the splash reads
            # "⏳ Fetching OpenAI models…" not "OpenAI Cloud models".
            provider_name = original.title.split('  ·  ')[0]
            if provider_name.endswith(" Cloud"):
                provider_name = provider_name[: -len(" Cloud")]
            splash_options = [PromptOption(
                value="__loading__",
                label=f"⏳ Fetching {provider_name} models…",
                hint="(usually <2s)",
            )]
            self._render_step(original, options=splash_options, is_loading=True)
            self.run_worker(
                self._fetch_provider_options(self._step_index, original, provider),
                exclusive=False, exit_on_error=False,
            )
            return

        # Provider already ran (cache hit) OR this step has no provider —
        # use the cached/static options directly.
        live_options = self._provider_cache.get(self._step_index, original.options)
        self._render_step(original, options=live_options)

    def _render_step(self, original: PromptStep, *, options=None, is_loading: bool = False) -> None:
        """Build a PromptStep instance with display-time-resolved fields
        and load it into the prompt panel.

        ``is_loading`` is set when this is the splash render between
        the user reaching a provider-driven step and the worker's
        options fetch returning. It prefixes the subtitle with an
        hourglass to match the splash option row.
        """
        # Preserve user state across revisits: if this is a multi-select
        # the user has already answered (e.g. they hit back then forward),
        # restore their checkbox state from self._selections rather than
        # reverting to the step's original default_values.
        live_default_values = list(original.default_values)
        if original.kind == "multiselect":
            prior = self._selections.get(original.title)
            if isinstance(prior, str):
                live_default_values = [s for s in prior.split(",") if s]
        live_options = options if options is not None else original.options
        # ``dataclasses.replace`` carries every field on the dataclass
        # forward by default — new fields added to PromptStep show up
        # at display time automatically, no need to update this method
        # in lock-step. Only the fields that change at render time get
        # an explicit override.
        from dataclasses import replace
        step = replace(
            original,
            step_index=self._step_index + 1,
            step_total=len(self._steps),
            subtitle=("⏳  " + original.subtitle.lstrip()) if is_loading else original.subtitle,
            options=live_options,
            default_values=live_default_values,
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

    async def _fetch_provider_options(
        self, step_index: int, original: PromptStep, provider,
    ) -> None:
        """Run the step's options_provider in a worker, then re-render.

        ``step_index`` is captured at dispatch time so we can detect
        the user navigating away mid-fetch and avoid stomping the
        currently-displayed step. ``generation`` is also captured so a
        late-arriving worker whose cache slot has since been
        invalidated (action_back) silently drops its result instead of
        polluting the new cache entry.
        """
        sel_snapshot = dict(self._selections)
        generation = self._fetch_generation
        try:
            options = await asyncio.to_thread(provider, sel_snapshot)
        except Exception:  # noqa: BLE001
            options = []
        # Generation drift means action_back ran while we were waiting
        # — the user may have changed the upstream key, so writing our
        # results would be wrong. Drop silently. The cache is empty so
        # on revisit the splash will dispatch a fresh worker.
        if generation != self._fetch_generation:
            return
        # Cache the result so going back-and-forward doesn't re-fetch
        # within the same wizard run. Cleared on action_back so the
        # user's revisit always sees a fresh fetch when they return.
        self._provider_cache[step_index] = options or []
        self._provider_done[step_index] = True
        # If the user has navigated away mid-fetch, don't disturb their
        # current step — but the cache will be ready on revisit.
        if self._step_index != step_index or self._phase != "setup":
            return
        # Re-render with real options on the main thread.
        self._load_current_step()

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        """Suppress screen-level priority bindings while the search
        input has focus, so typed keys land in the Input as text.

        The wizard's keyboard model binds bare letters (``f``, ``a``,
        ``e``, ``w``, ``i``, ``j``, ``k``) and ``space`` with
        ``priority=True``. That's the right default while focus sits
        on the non-focusable option list, but it makes the search box
        useless: typing ``"qwen"`` would hijack the ``"w"`` to fire
        ``filter_warns``. The whitelist below names the actions that
        STAY enabled while search is focused — every other action
        returns ``False`` so the key flows through to the Input.

        Whitelist:
        * ``back`` — Esc unfocuses the search (see ``action_back``).
        * ``quit_wizard`` — Ctrl+Q stays a universal escape hatch.
        * ``move`` — arrow keys still walk the option list. Textual
          ``Input`` uses left/right for cursor movement, leaving
          up/down free to live-preview the narrowed results while
          typing.
        * ``toggle_search_focus`` — Tab toggles focus back to the
          option list (symmetric with the Tab-to-enter-search path).

        Deliberately NOT in the whitelist:
        * ``confirm`` — Enter inside the focused Input emits Textual's
          ``Input.Submitted`` message, which ``PromptPanel.on_input_
          submitted`` catches and routes to ``unfocus_search()``. The
          step's commit-Enter is reachable as soon as focus is back
          on the option list. The user picks the explicit "I'm done
          searching" moment instead of accidentally committing the
          whole multiselect while mid-keystroke.
        * ``vim_move`` (``j``/``k``), ``cycle_filter`` (``f``),
          ``filter_*`` (``a``/``e``/``w``/``i``), ``toggle`` (Space),
          ``focus_search`` (``/``) — all suppressed so the bound
          letters / Space / slash land in the Input as plain text.
        """
        if (
            self._phase == "setup"
            and self._prompt.has_search_focus()
        ):
            _SEARCH_ALLOWED = {
                "back", "quit_wizard", "move", "toggle_search_focus",
            }
            if action not in _SEARCH_ALLOWED:
                return False
        return True

    def action_vim_move(self, delta: int) -> None:
        """``j``/``k`` movement — delegates to :meth:`action_move` but
        named separately so ``check_action`` can suppress it while
        the search input has focus (without also suppressing the
        arrow-key navigation users expect to keep working there).
        """
        self.action_move(delta)

    def action_move(self, delta: int) -> None:
        if self._phase != "setup":
            return
        self._prompt.move(delta)

    def action_toggle(self) -> None:
        """Space: toggle / expand / collapse the focused multi-select row.

        Delegated to ``PromptPanel.toggle_focused``, which branches on
        the row kind (parent vs leaf) and whether the parent is
        expandable. No popup ⇒ no focus handover ⇒ no priority-binding
        conflict; the cursor and arrows stay in the prompt panel
        throughout.
        """
        if self._phase != "setup":
            return
        self._prompt.toggle_focused()

    def action_cycle_filter(self) -> None:
        """``f``: cycle the multiselect filter chip forward.

        Order is ``[ALL, *step.filter_tags]``; wraps. No-op on steps
        without filter_tags (so `f` is safe to leave bound globally —
        it just does nothing on non-filter steps).
        """
        if self._phase != "setup":
            return
        self._prompt.cycle_filter(direction=+1)

    def action_focus_search(self) -> None:
        """``/``: focus the model-name search input on multiselect
        steps that mount one (today: only ``Ollama  ·  models``).

        No-op on every other step. When focused, typing into the input
        live-narrows the option list; Esc returns focus to the option
        list (handled by ``action_back`` below).
        """
        if self._phase != "setup":
            return
        self._prompt.focus_search()

    def action_toggle_search_focus(self) -> None:
        """``Tab``: flip focus between the search input and the option
        list. No-op on steps without a search input.

        Symmetric on purpose — pressing Tab from either side returns
        to the other. Combined with the explicit focus park on step
        load (see ``PromptPanel._mount_search_input``), this is the
        only way the search box gets focus by accident.
        """
        if self._phase != "setup":
            return
        self._prompt.toggle_search_focus()

    def action_confirm(self) -> None:
        if self._phase != "setup":
            return
        # Suppress confirmation while the splash row is showing for a
        # provider-driven multiselect — committing now would silently
        # commit only the step's static default_values (the live
        # options haven't arrived yet). The splash row's value is the
        # ``__loading__`` sentinel, which is harmless to commit but
        # confusing UX-wise. Wait for the worker to populate the cache.
        step = self._steps[self._step_index]
        if (
            step.kind == "multiselect"
            and getattr(step, "options_provider", None) is not None
            and not self._provider_done.get(self._step_index, False)
        ):
            return
        opt = self._prompt.selected_option
        if opt is None:
            return
        self._selections[step.title] = opt.value
        # Inline secondary integer inputs (kind="options" + per-option
        # secondary_number): capture each visible eligible input's value
        # under a synthetic ``__secondary__:<ENV_VAR>`` key so
        # _selections_to_args can route them to the env-write bag.
        # Empty list when the step has no eligible rows.
        for env_var, value in self._prompt.secondary_values():
            self._selections[f"__secondary__:{env_var}"] = value
        # Cloud secret step: live-update the Cloud APIs row in the
        # overview to reflect the user's choice.
        if step.kind == "secret" and self._cloud_apis:
            self._apply_secret_step_to_cloud_apis(step, opt.value)
        # Cloud multiselect step: an empty CSV ("0 selected") means
        # the user explicitly de-selected every model. Match the
        # _selections_to_args policy ("disable provider + wipe key")
        # by reflecting the disabled state in the overview now,
        # instead of waiting until launch to surprise the user.
        if step.kind == "multiselect" and self._cloud_apis:
            self._apply_models_step_to_cloud_apis(step, opt.value)
        # Service-source step: update that row's source and refresh.
        for row in self._services:
            if step.service_name and row.name == step.service_name:
                row.source = opt.value
                row.pending = False
                # Re-derive the port for the new source — localhost
                # sources should show the host machine's port, container
                # sources the assigned container port, disabled none.
                if self._resolve_port_for_service is not None:
                    try:
                        new_port = self._resolve_port_for_service(row.name, row.source)
                        row.port = new_port or ""
                    except Exception:  # noqa: BLE001
                        pass
                # Row position is fixed by canonical topology order — a
                # source change only updates this row's port/source/alias
                # values, not its place in the list. (Earlier versions
                # re-sorted by ascending port on every confirm, which
                # silently broke same-category adjacency the moment a
                # localhost source surfaced a small port number.)
                self._service_table.set_rows(self._services)
                self._refresh_info_panel()
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
                self._refresh_info_panel()
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

    def _refresh_info_panel(self) -> None:
        """Rebuild the service summaries from self._services and re-emit
        them + the current cloud_apis state through the InfoPanel.

        Extracted from the four sites that previously inlined the same
        4-line "summaries = [...]; self._info_panel.update_state(...)"
        block: action_confirm (service-source branch + base-port branch)
        and the two cloud overview update helpers below.
        """
        summaries = [
            ServiceSummary(name=r.name, source=r.source, port=r.port,
                           alias=r.alias, pending=r.pending)
            for r in self._services
        ]
        self._info_panel.update_state(
            InfoBoxState(
                brand=self._brand,
                services=summaries,
                cloud_apis=self._cloud_apis,
            )
        )

    def _apply_models_step_to_cloud_apis(self, step: PromptStep, value: str) -> None:
        """Live-update the Cloud APIs overview block after a cloud
        multiselect step.

        Two cases mirror ``_selections_to_args``:
          • Empty CSV ("0 selected") → user wants this provider OFF.
          • Non-empty CSV on a previously-disabled provider whose key
            is set → auto-promote (same path as the secret step's
            SECRET_KEEP+disabled+key path; without this, the overview
            would lag the launch state).
        """
        from wizard.llm_steps import cloud_models_title
        title = step.title or ""
        target: CloudApiSummary | None = None
        for entry in self._cloud_apis:
            if title == cloud_models_title(entry.name):
                target = entry
                break
        if target is None:
            return
        csv = (value or "").strip()
        if csv == "":
            # Empty selection ⇒ provider gets disabled at launch.
            target.enabled = False
            target.key_set = False
        elif target.key_set and not target.enabled:
            # Non-empty selection on a previously-disabled provider with
            # a saved key. _selections_to_args auto-promotes the source
            # to ``enabled``; mirror that in the overview now.
            target.enabled = True
        else:
            return  # no overview change required
        self._cloud_apis_row.set_cloud_apis(self._cloud_apis)
        self._refresh_info_panel()

    def _apply_secret_step_to_cloud_apis(self, step: PromptStep, value: str) -> None:
        """Live-update the Cloud APIs overview block after a secret step.

        Maps the step title (e.g. ``OpenAI Cloud  ·  API key``) to the
        matching CloudApiSummary, applies the wizard's sentinel-encoded
        value, and refreshes the row + footer count line.
        """
        # Local imports avoid a hard dependency at module load time.
        from ..widgets.prompt_panel import SECRET_KEEP, SECRET_CLEAR
        from wizard.llm_steps import cloud_secret_title

        # Exact title match via the same helper that built the step
        # title. Keeps the two sides in lockstep — if cloud_secret_title
        # ever changes format, both producer and consumer move together.
        title = step.title or ""
        target: CloudApiSummary | None = None
        for entry in self._cloud_apis:
            if title == cloud_secret_title(entry.name):
                target = entry
                break
        if target is None:
            return
        if value == SECRET_KEEP:
            # Auto-promote case: .env had source=disabled but a key is
            # present. The skip predicate let the multiselect through;
            # _selections_to_args will flip source to enabled. Mirror
            # that in the overview so the user sees the correct state
            # immediately instead of waiting until launch.
            if target.key_set and not target.enabled:
                target.enabled = True
            else:
                return  # truly nothing changed
        elif value == SECRET_CLEAR or value == "":
            target.enabled = False
            target.key_set = False
        else:
            target.enabled = True
            target.key_set = True
        self._cloud_apis_row.set_cloud_apis(self._cloud_apis)
        self._refresh_info_panel()

    def _refresh_command_summary(self) -> None:
        from ..widgets.prompt_panel import SECRET_KEEP, SECRET_CLEAR
        from wizard.llm_steps import (
            OLLAMA_CUSTOM_TITLE,
            OLLAMA_MODELS_TITLE,
            cloud_models_title,
            cloud_secret_title,
        )

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

        # Build per-cloud title indexes once so we can match cloud
        # secret + multiselect steps without scanning the cloud list
        # for every step. Iterate the canonical CLOUD_PROVIDERS list so
        # adding a 4th provider doesn't silently miss this site.
        from utils.cloud_providers import CLOUD_PROVIDERS
        cloud_secret_titles = {
            cloud_secret_title(p.name): p.key for p in CLOUD_PROVIDERS
        }
        cloud_models_titles = {
            cloud_models_title(p.name): p.key for p in CLOUD_PROVIDERS
        }

        # All other steps follow.
        for step in self._steps:
            value = self._selections.get(step.title)
            if value is None:
                continue
            default = self._defaults.get(step.title, "")

            if step.service_name:
                # Service source flag — always show once picked. Derive
                # from the canonical ``ServiceInfo.key`` carried on the
                # PromptStep (e.g. ``llm_provider`` → ``--llm-provider-source``).
                # Falling back to the display-name slug is a bug:
                # ``LLM Engine`` → ``--llm-engine-source`` is not a real
                # Click flag and Click rejects it.
                key = step.service_key or step.service_name.lower().replace(" ", "-")
                flag = "--" + key.replace("_", "-") + "-source"
                flags.append((flag, value))
                continue

            title_low = step.title.lower()
            if "base port" in title_low:
                continue

            # Cloud secret step → equivalent --cloud-X-source +
            # sanitized --X-api-key. Never emit the raw key string.
            if step.title in cloud_secret_titles:
                provider = cloud_secret_titles[step.title]
                if value == SECRET_KEEP:
                    pass  # no flag — keeping current state
                elif value == SECRET_CLEAR or value == "":
                    flags.append((f"--cloud-{provider}-source", "disabled"))
                else:
                    flags.append((f"--cloud-{provider}-source", "enabled"))
                    flags.append((f"--{provider}-api-key", "<set>"))
                continue

            # Cloud multiselect → --X-models with truncated CSV /
            # selection count.
            if step.title in cloud_models_titles:
                provider = cloud_models_titles[step.title]
                csv = (value or "").strip()
                if csv == "":
                    flags.append((f"--{provider}-models", "(none — provider disabled)"))
                else:
                    n = csv.count(",") + 1
                    short = csv if len(csv) <= 60 else csv[:57] + "..."
                    flags.append((f"--{provider}-models", f"{n} selected ({short})"))
                continue

            # Ollama models step (single unified [pulled]/[library] view).
            # The custom free-text step has its own flag below.
            if step.title == OLLAMA_MODELS_TITLE:
                csv = (value or "").strip()
                if csv == "":
                    continue
                n = csv.count(",") + 1
                short = csv if len(csv) <= 60 else csv[:57] + "..."
                flags.append(("--ollama-models", f"{n} selected ({short})"))
                continue
            if step.title == OLLAMA_CUSTOM_TITLE:
                if value in (SECRET_KEEP, "", None):
                    continue
                if value == SECRET_CLEAR:
                    flags.append(("--ollama-custom-models", "(cleared)"))
                else:
                    short = value if len(value) <= 60 else value[:57] + "..."
                    flags.append(("--ollama-custom-models", short))
                continue

            # Meta steps (cold, hosts) — only show when non-default.
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
        # If the search box has focus, Esc returns focus to the option
        # list — same UX pattern as :input in vim. Without this Esc
        # would rewind a wizard step while the user is actively typing
        # a search query.
        if (
            self._phase == "setup"
            and self._prompt.has_search_focus()
        ):
            self._prompt.unfocus_search()
            return
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
            # Walk backwards over any skip_if_prev steps so the user
            # doesn't land on an auto-skipped page when going back.
            self._step_index -= 1
            # Invalidate cached options_provider results from the new
            # step onward — earlier steps' caches still hold (the user's
            # upstream choices for them haven't changed). This means
            # going back from step 12 to step 10 doesn't blow away a
            # cached fetch from step 6.
            for k in list(self._provider_cache):
                if k >= self._step_index:
                    self._provider_cache.pop(k, None)
                    self._provider_done.pop(k, None)
            # Bump the generation so any in-flight fetch worker for the
            # cleared range (or beyond) drops its result instead of
            # writing back into the now-empty cache.
            self._fetch_generation += 1
            self._advance_past_skipped(direction=-1)
            self._load_current_step()
        else:
            self.app.exit()

    def action_quit_wizard(self) -> None:
        # Close the tee on a setup-phase quit so the wizard-time
        # warnings flushed earlier aren't left in a still-open fh
        # past process exit. The launch-phase ``finally`` block
        # already does this; this branch covers the setup-quit path.
        self._close_launch_log_tee()
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

        # The session log was opened in __init__ so it could capture
        # wizard-time warnings. Now that the log pane exists, surface
        # the path as the first user-visible line so the operator can
        # find it on disk.
        if self._launch_log_path is not None and self._log_pane is not None:
            self._log_pane.write_log(
                f"📝 session log: {self._launch_log_path}",
                level="info", source="pipeline",
            )

        if self._starter is None:
            return  # wizard-only mode (tests)

        self.run_worker(
            self._run_pipeline_and_stream(),
            exclusive=False, exit_on_error=False,
        )

    # ─── launch-log tee ──────────────────────────────────────────────

    def _open_launch_log_tee(self, *, announce_in_pane: bool = True) -> None:
        """Open ``/tmp/genai-vanilla-launch-<ts>.log`` for the duration
        of the wizard. _write_status / _safe_log mirror their output
        into this file so a user who quits the wizard still has a
        record of what happened (cloud /v1/models fetch failures during
        setup, plus everything compose printed during launch).

        ``announce_in_pane=False`` is used for the early call from
        ``__init__`` — the log pane doesn't exist yet there. The
        launch transition does the announce later when the pane is up.
        """
        import datetime
        from pathlib import Path
        ts = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        path = Path(f"/tmp/genai-vanilla-launch-{ts}.log")
        try:
            self._launch_log_path = path
            self._launch_log_fh = open(path, "w", buffering=1, encoding="utf-8")  # line-buffered
            self._launch_log_fh.write(f"# genai-vanilla session log — started {ts}\n")
            self._launch_log_fh.flush()
            if announce_in_pane and self._log_pane is not None:
                self._log_pane.write_log(
                    f"📝 session log: {path}",
                    level="info", source="pipeline",
                )
        except OSError as exc:  # noqa: BLE001
            self._launch_log_fh = None
            self._launch_log_path = None
            if self._log_pane is not None:
                self._log_pane.write_log(
                    f"⚠ could not open launch log file: {exc}",
                    level="warn", source="pipeline",
                )

    def _close_launch_log_tee(self) -> None:
        fh = getattr(self, "_launch_log_fh", None)
        if fh is not None:
            try:
                fh.close()
            except Exception:  # noqa: BLE001
                pass
            self._launch_log_fh = None
        # Drop the wizard warn sink so a stale screen reference can't
        # leak into a future invocation.
        try:
            from .. import integration as _integration_mod
            _integration_mod._set_wizard_warn_sink(None)
        except Exception:  # noqa: BLE001
            pass

    def _tee_to_log(self, msg: str, *, source: str = "", level: str = "") -> None:
        """Append a line to the launch-log file. Best-effort, no raise."""
        fh = getattr(self, "_launch_log_fh", None)
        if fh is None:
            return
        try:
            prefix = ""
            if source or level:
                prefix = f"[{level or '·'}/{source or '·'}] "
            fh.write(prefix + (msg or "") + "\n")
        except Exception:  # noqa: BLE001
            pass

    async def _capture_failure_compose_logs(self) -> None:
        """On compose-up failure, dump ``docker compose logs --tail=200``
        for every service into the launch-log file. The output is NOT
        echoed to the live log pane (too noisy); only the tee file gets it.
        """
        fh = getattr(self, "_launch_log_fh", None)
        if fh is None or self._starter is None:
            return
        try:
            cmd = self._starter.docker_manager._build_compose_command(
                ["logs", "--no-color", "--tail=200"],
                top_level_flags=[],
            )
        except Exception:  # noqa: BLE001
            return
        fh.write("\n# ─── docker compose logs --tail=200 (post-failure) ───\n")
        fh.write(f"# {' '.join(cmd)}\n\n")
        fh.flush()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(self._starter.docker_manager.root_dir),
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert proc.stdout is not None
            captured: list[str] = []
            async for raw in proc.stdout:
                line = raw.decode(errors="replace").rstrip("\r\n")
                fh.write(line + "\n")
                captured.append(line)
            await proc.wait()
            fh.flush()
            self._emit_failure_hints(captured)
        except Exception as exc:  # noqa: BLE001
            try:
                fh.write(f"# capture failed: {exc}\n")
                fh.flush()
            except Exception:  # noqa: BLE001
                pass

    def _emit_failure_hints(self, log_lines: list[str]) -> None:
        """Surface a recovery hint in the live log pane when the
        captured docker-compose output reveals a well-known failure
        mode (stale volume, port conflict, etc.).

        Pattern → hint mapping kept intentionally narrow: only mention
        recoveries the user can act on directly. We never silently
        wipe state; we tell them exactly which command to run.
        """
        joined = "\n".join(log_lines).lower()

        # Stale supabase-db volume: pgdata initialized with an old
        # password, current .env now has a different one. Postgres
        # won't re-init existing pgdata, so the stored creds and the
        # .env creds diverge until the volume is wiped.
        if (
            "password authentication failed" in joined
            and "supabase_admin" in joined
        ):
            self._write_status(
                "🔧 Stale supabase-db volume detected.",
                style="bold yellow", source="pipeline",
            )
            self._write_status(
                "   The DB was initialized with a different password "
                "than the current .env (likely from an earlier failed run).",
                style="yellow", source="pipeline",
            )
            self._write_status(
                "   Recovery: ./start.sh --cold "
                "(wipes volumes + re-initializes from scratch).",
                style="bold cyan", source="pipeline",
            )
            return

        # Bind-mount permission denied. Containers (especially init
        # ones running as root) can leave host dirs root-owned, then
        # subsequent runs fail because the new container can't write
        # to its own bind mount. ``_ensure_volume_dir_writable`` covers
        # the litellm/kong cases proactively; this hint catches the
        # generic case where some other volume dir is locked.
        if (
            "permission denied" in joined
            and (
                "config.yaml.tmp" in joined
                or "/litellm-config/" in joined
                or "/kong-config/" in joined
                or "errno 13" in joined
            )
        ):
            self._write_status(
                "🔧 Bind-mount permission denied — a prior container left "
                "a host directory root-owned. Recovery: "
                "`sudo chmod -R 777 volumes/` and re-run ./start.sh, "
                "or `./start.sh --cold` to wipe state entirely.",
                style="bold yellow", source="pipeline",
            )
            return

        # Generic auth failure on a non-supabase service (less common).
        if "authentication failed" in joined or "password authentication" in joined:
            self._write_status(
                "🔧 Authentication failed for one or more services — "
                "likely a stale volume from a prior run. "
                "Try ./start.sh --cold to wipe and re-initialize.",
                style="bold yellow", source="pipeline",
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
        self._tee_to_log(msg, source=source, level=level)

    def _safe_log(self, msg: str, *, source: str = "pipeline", level: str = "info") -> None:
        """Write a log line to the pane + tee file, from any thread.

        Two contexts call this:
          • Pipeline-step callbacks invoked via ``asyncio.to_thread`` —
            they run in a worker thread; UI writes must marshal back
            to the main loop with ``call_from_thread``.
          • ``_run_compose`` / ``_run_command`` — these are coroutines
            on the main event loop; ``call_from_thread`` from the
            same thread silently mis-routes (no UI update). Use a
            direct call instead.

        Always tee to the launch-log file regardless of thread.
        """
        import threading
        self._tee_to_log(msg, source=source, level=level)
        if self._log_pane is None:
            return
        on_main = threading.current_thread() is threading.main_thread()
        try:
            if on_main:
                self._log_pane.write_log(msg, level=level, source=source)
            else:
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
            # ``--ansi=never`` — stdout here is a Popen pipe; with
            # ``--ansi=always`` compose tries to attach a TTY-based
            # progress console and fails with "failed to get console:
            # provided file is not a console". Same fix as _run_compose.
            full_cmd = starter.docker_manager._build_compose_command(
                args, top_level_flags=["--ansi=never"],
            )
            self._safe_log("$ " + " ".join(full_cmd), source="docker", level="dim")
            try:
                import subprocess as _sp
                proc = _sp.Popen(
                    full_cmd,
                    cwd=str(starter.docker_manager.root_dir),
                    stdin=_sp.DEVNULL, stdout=_sp.PIPE, stderr=_sp.STDOUT,
                    text=True, bufsize=1, encoding="utf-8", errors="replace",
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
            ("Apply cloud API keys",
             lambda: starter.apply_cloud_api_keys(
                 (self._stack_options or {}).get("cloud_api_keys", {})
             )),
            ("Apply user model selections",
             lambda: starter.apply_user_model_selections({
                 **((self._stack_options or {}).get("cloud_user_models", {}) or {}),
                 **((self._stack_options or {}).get("ollama_user_models", {}) or {}),
                 **((self._stack_options or {}).get("comfyui_user_models", {}) or {}),
                 # CLI-launch catch-all: COMFYUI_CUSTOM_MODELS_FILE,
                 # RAY_WORKER_COUNT, PROMETHEUS_RETENTION_DAYS,
                 # SPARK_WORKER_COUNT — flags that don't match the wizard's
                 # cosmetic *_USER_MODELS / OLLAMA_* bucket patterns.
                 # Without this bucket they'd be silently dropped on the
                 # ./start.sh --flag <value> path while TUI is active.
                 **((self._stack_options or {}).get("user_env_writes", {}) or {}),
             })),
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
            ("Generate LiteLLM configuration",
             starter.generate_litellm_configuration),
            ("Validate Supabase keys",
             lambda: starter.validate_supabase_keys(cold_start=cold)),
            ("Configure hosts",
             lambda: starter.handle_hosts_configuration(setup_hosts, skip_hosts)),
            ("Generate encryption keys",
             lambda: starter.generate_encryption_keys(cold_start=cold)),
            ("Validate localhost services",
             starter.validate_localhost_services),
            # Defensive final backfill — runs after every other
            # pipeline step has touched .env. Catches the edge case
            # where a user merged new entries into .env.example after
            # their .env was last fully written; if any earlier step
            # somehow regenerated .env from a parsed snapshot rather
            # than regex-replacing, the new vars (MINIO_IMAGE,
            # MINIO_PORT, etc.) would be missing at compose time and
            # ``docker compose up`` would fail with ``variable X not
            # set, defaulting to blank string``. Cheap when there's
            # nothing to add (a no-op tail append).
            ("Backfill .env from .env.example",
             starter.backfill_missing_env_vars),
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
                self._write_status("❌ Start failed — capturing per-service logs to launch log",
                                   style="bold red", source="pipeline")
                await self._capture_failure_compose_logs()
                self._write_status(
                    f"📝 see {self._launch_log_path or '/tmp/genai-vanilla-launch-*.log'} "
                    "for full output",
                    style="bold yellow", source="pipeline",
                )
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
            self._close_launch_log_tee()

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
        # Route through _safe_log so the launch-log tee picks up
        # the command and its output. Direct _log_pane.write_* calls
        # bypass the tee — that's the gap that left the user's first
        # failure with only the bootstrapper pipeline in the file.
        self._safe_log("$ " + " ".join(cmd), source="docker", level="dim")
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
                self._safe_log(line, source="docker", level="info")
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
        # IMPORTANT: stdout is a pipe (no TTY). Don't pass
        # --ansi=always — it tells compose "I have a TTY, use the
        # animated progress display". Buildkit then tries to attach
        # a console to the pipe and fails with
        #   "failed to get console: provided file is not a console"
        # → compose up exits 1 with no containers created.
        # Default ``--ansi=auto`` correctly picks no-ANSI when piped,
        # which also picks plain progress automatically. We lose
        # Docker's own coloring in the log pane, but our level-based
        # coloring still works via _classify_compose_line.
        full_cmd = self._starter.docker_manager._build_compose_command(
            args, top_level_flags=["--ansi=never"],
        )
        env = {**os.environ, "BUILDKIT_PROGRESS": "plain"}
        # Route through _safe_log so every compose line lands in the
        # launch-log tee (/tmp/genai-vanilla-launch-*.log). Direct
        # _log_pane.write_* calls bypassed the tee — image-pull errors
        # from compose up never reached the file.
        self._safe_log("$ " + " ".join(full_cmd), source="docker", level="dim")
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
                self._safe_log(line, source=source, level=level)
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
