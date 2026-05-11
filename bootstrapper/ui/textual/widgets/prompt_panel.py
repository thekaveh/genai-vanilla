"""
PromptPanel — wizard's main interactive panel (mockup 003).

Layout (fits in 1 cell rows + blank rows + variable-height options):

    ┌─ LLM Provider · Deployment mode               3 / 18 ──┐
    │                                                         │
    │  How should the LLM provider run?                       │
    │  Pick where the model server lives.                     │
    │                                                         │
    │  O P T I O N S                                          │
    │  ▸ ◉ ollama-localhost                       [rec.][GPU] │
    │      Use the Ollama already running on this host        │
    │    ○ ollama-container-gpu                       [GPU]   │
    │      Run in a CUDA container                            │
    │    ○ api                                       [cloud]  │
    │      Use a hosted API endpoint                          │
    │                                                         │
    │  [optional dependency conflict insert here]             │
    └─────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Input, Static

from .. import palette as P
from .dependency_conflict import ConflictAction, DependencyConflict
from .option_row import OptionRow


# Sentinel return values for secret-input steps. Real API keys never
# match these strings, so downstream consumers can branch on intent
# without exposing the actual key.
SECRET_KEEP = "<KEEP>"
SECRET_CLEAR = "<CLEAR>"


def _mask_secret(value: str) -> str:
    """Render a secret as ``••••••…XXXX`` — bullets + last 4 chars."""
    s = (value or "").strip()
    if not s:
        return ""
    if len(s) <= 4:
        return "•" * len(s)
    return "•" * 8 + "…" + s[-4:]


@dataclass
class PromptOption:
    value: str
    label: str
    hint: str = ""
    badges: list[str] = field(default_factory=list)


@dataclass
class PromptStep:
    title: str
    step_index: int
    step_total: int
    heading: str
    subtitle: str = ""
    options: list[PromptOption] = field(default_factory=list)
    default_value: str | None = None
    # Initial checked values for ``kind="multiselect"`` steps. Each
    # entry must match an ``options[i].value``.
    default_values: list[str] = field(default_factory=list)
    # Optional callable that returns ``options`` lazily based on the
    # in-progress wizard selections — used by the Ollama-upstream
    # multiselect, where the option list comes from a live ``/api/tags``
    # query that depends on the user's just-picked LLM source.
    options_provider: "Callable[[dict], list[PromptOption]] | None" = None
    # The exact service-table row name this step controls. Used by the
    # wizard screen to highlight the matching row when this step loads.
    service_name: str = ""
    # Canonical service key from ServiceInfo (e.g. ``llm_provider``,
    # ``doc_processor``). Used by the wizard screen's command preview
    # to emit the correct ``--<key>-source`` flag — deriving the flag
    # from ``service_name`` (display name) silently breaks when display
    # name and key diverge (``LLM Engine`` vs ``llm_provider``).
    service_key: str = ""
    # "options" (default — multiple-choice list), "number" (free
    # integer input, e.g. base port), "secret" (masked free-text
    # input for an API key, with empty/clear/keep semantics),
    # "multiselect" (checkbox list — Space toggles, Enter confirms),
    # or "text" (free-text Input, no masking).
    kind: str = "options"
    number_min: int = 1024
    number_max: int = 65000
    # Optional predicate the wizard screen calls before loading this
    # step. Receives the in-progress ``selections`` dict and returns
    # True if this step should be skipped. Used to skip cloud
    # multi-select steps when the user disabled the provider.
    skip_if_prev: "Callable[[dict], bool] | None" = None
    # Optional override for the hint rendered below a ``kind="secret"``
    # input when an existing key is present. Cloud provider steps use
    # this to distinguish "existing key + provider already enabled"
    # from "existing key + provider currently disabled; Enter enables".
    secret_keep_hint: str | None = None


def _progress_braille(step: int, total: int, width: int = 10) -> str:
    """Tiny inline progress bar for the border subtitle."""
    if total <= 0:
        return P.PROGRESS_EMPTY * width
    ratio = max(0.0, min(1.0, step / total))
    full = int(ratio * width)
    return P.PROGRESS_FILLED * full + P.PROGRESS_EMPTY * (width - full)


class PromptPanel(Container):
    """Wizard prompt body. Title + step counter live on the border."""

    DEFAULT_CSS = """
    PromptPanel {
        border: round #2b2f4a;
        background: #0e0f18;
        padding: 1 2;
        height: auto;
    }
    PromptPanel > .prompt-heading { height: 1; color: #e0e6f2; text-style: bold; }
    PromptPanel > .prompt-subtitle { height: 1; color: #565f89; }
    PromptPanel > .prompt-spacer-2 { height: 1; }
    /* Scrollable option list — capped so a 230-entry library scrape
       doesn't blow past the viewport. The cursor is kept in view by
       PromptPanel.move() calling scroll_visible() on the focused row. */
    PromptPanel > #option-list {
        height: auto;
        max-height: 18;
        scrollbar-size-vertical: 1;
    }
    PromptPanel > #number-slot { height: auto; }
    PromptPanel #number-input {
        height: 1;
        width: 14;
        background: #1c1d30;
        color: #c0caf5;
        border: none;
        padding: 0 1;
    }
    PromptPanel #number-input:focus {
        color: #7dcfff;
        background: #1c2034;
    }
    PromptPanel #secret-input {
        height: 1;
        width: 1fr;
        background: #1c1d30;
        color: #c0caf5;
        border: none;
        padding: 0 1;
    }
    PromptPanel #secret-input:focus {
        color: #7dcfff;
        background: #1c2034;
    }
    PromptPanel #number-hint {
        height: 1;
        color: #3d4261;
        padding-top: 1;
    }
    PromptPanel #secret-hint {
        height: auto;
        color: #3d4261;
        padding-top: 1;
    }
    PromptPanel > #conflict-slot { height: auto; }
    """

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._heading = Static("", classes="prompt-heading")
        self._subtitle = Static("", classes="prompt-subtitle")
        self._spacer2 = Static("", classes="prompt-spacer-2")
        # VerticalScroll (not plain Vertical) so long option lists
        # (Ollama library scrape can be ~230 entries) get a scrollbar
        # and a clipped viewport; otherwise the cursor moves down past
        # the bottom of the screen and the user can't see what they're
        # selecting. PromptPanel.move() calls scroll_visible() on the
        # focused row so the viewport always follows the selection.
        self._option_list = VerticalScroll(id="option-list")
        self._number_slot = Container(id="number-slot")
        # Persistent input/hint widgets — created lazily on first use,
        # reused (display toggled) on every subsequent step. Re-mounting
        # was causing DuplicateIds because Container.remove_children()
        # is asynchronous: the previous step's widget was still in the
        # node list when the next step's mount tried to register an id
        # of the same name.
        self._number_input: Input | None = None
        self._number_hint: Static | None = None
        self._secret_input: Input | None = None
        self._secret_hint: Static | None = None
        self._conflict_slot = Container(id="conflict-slot")
        self._step: PromptStep | None = None
        self._selected_index = 0
        # Set of option.value strings currently checked when the
        # active step is a multi-select.
        self._checked_values: set[str] = set()
        self._on_change: Callable[[int, PromptOption], None] | None = None

    def compose(self) -> ComposeResult:
        yield self._heading
        yield self._subtitle
        yield self._spacer2
        yield self._option_list
        yield self._number_slot
        yield self._conflict_slot

    def set_on_change(self, callback: Callable[[int, PromptOption], None]) -> None:
        self._on_change = callback

    def load_step(self, step: PromptStep) -> None:
        self._step = step
        # All caption info on the top border title — service name +
        # step counter + a small progress bar.
        bar = _progress_braille(step.step_index, step.step_total)
        self.border_title = (
            f" {step.title}  ·  {step.step_index} / {step.step_total}  {bar} "
        )
        self.border_subtitle = ""
        self._heading.update(step.heading)
        self._subtitle.update(step.subtitle)

        if step.kind == "number":
            # Free integer input — reuse the persistent Input/Static
            # pair so we never trigger a DuplicateIds race on re-entry.
            self._option_list.remove_children()
            self._hide_secret_widgets()
            default = step.default_value or ""
            if default:
                hint_text = (
                    f"type a value in {step.number_min}–{step.number_max}, "
                    f"or press Enter to keep {default}"
                )
            else:
                hint_text = (
                    f"type a value in {step.number_min}–{step.number_max}"
                )
            if self._number_input is None:
                self._number_input = Input(
                    value="",
                    placeholder=default,
                    id="number-input",
                )
                self._number_slot.mount(self._number_input)
            else:
                self._number_input.value = ""
                self._number_input.placeholder = default
                self._number_input.display = True
            if self._number_hint is None:
                self._number_hint = Static(hint_text, id="number-hint")
                self._number_slot.mount(self._number_hint)
            else:
                self._number_hint.update(hint_text)
                self._number_hint.display = True
            # Focus the input so the user can type immediately.
            self._number_input.focus()
            return

        if step.kind == "secret":
            # Masked free-text input for an API key. Reuses the
            # persistent Input/Static pair across providers.
            #   empty + no existing key  → leave provider disabled
            #   empty + existing key set → keep current key (no change)
            #   "clear"                  → wipe key, set provider disabled
            #   any other text           → enable provider, store as key
            self._option_list.remove_children()
            self._hide_number_widgets()
            existing = (step.default_value or "").strip()
            placeholder = _mask_secret(existing) if existing else "paste API key here…"
            if existing:
                hint_text = step.secret_keep_hint or (
                    f"key currently set ({placeholder})  ·  Enter to keep  ·  "
                    "type a new key to replace  ·  type \"clear\" + Enter to remove"
                )
            else:
                hint_text = (
                    "paste a key + Enter to enable  ·  Enter (empty) to leave disabled"
                )
            if self._secret_input is None:
                self._secret_input = Input(
                    value="",
                    placeholder=placeholder,
                    password=True,
                    id="secret-input",
                )
                self._number_slot.mount(self._secret_input)
            else:
                self._secret_input.value = ""
                # Reset horizontal scroll — without this, a previously
                # pasted long key leaves the cursor parked at the end
                # and the masked dots scroll out of view.
                try:
                    self._secret_input.cursor_position = 0
                except Exception:  # noqa: BLE001
                    pass
                self._secret_input.placeholder = placeholder
                self._secret_input.display = True
            if self._secret_hint is None:
                self._secret_hint = Static(hint_text, id="secret-hint")
                self._number_slot.mount(self._secret_hint)
            else:
                self._secret_hint.update(hint_text)
                self._secret_hint.display = True
            self._secret_input.focus()
            return

        if step.kind == "text":
            # Free-text input (NOT masked). Reuses the same persistent
            # number-input slot — text is just "number minus the
            # numeric coercion." For Ollama "additional models to pull"
            # and similar comma-separated free-form fields. Honors
            # the same keep-current/clear sentinels as ``kind="secret"``.
            self._option_list.remove_children()
            self._hide_secret_widgets()
            default = (step.default_value or "").strip()
            placeholder = default if default else "type a value"
            if self._number_input is None:
                self._number_input = Input(
                    value="",
                    placeholder=placeholder,
                    id="number-input",
                )
                self._number_slot.mount(self._number_input)
            else:
                self._number_input.value = ""
                self._number_input.placeholder = placeholder
                self._number_input.display = True
            if default:
                hint_text = (
                    f"currently set ({default})  ·  Enter to keep  ·  "
                    "type new text to replace  ·  type \"clear\" + Enter to remove"
                )
            else:
                hint_text = "type a value + Enter, or press Enter (empty) to skip"
            if self._number_hint is None:
                self._number_hint = Static(hint_text, id="number-hint")
                self._number_slot.mount(self._number_hint)
            else:
                self._number_hint.update(hint_text)
                self._number_hint.display = True
            self._number_input.focus()
            return

        if step.kind == "multiselect":
            # Checkbox list — Space toggles the focused row, Enter
            # confirms the entire selection. Uses the existing
            # _option_list container with OptionRow widgets in
            # multi=True mode.
            self._hide_number_widgets()
            self._hide_secret_widgets()
            self._selected_index = 0
            # Intersect default_values with the *visible* option set.
            # Without this, defaults that aren't in step.options (e.g. a
            # cloud account that no longer has access to a previously-
            # active model, or an Ollama upstream that doesn't have a
            # default-active model pulled) stay invisibly checked in
            # _checked_values and leak into the saved CSV at confirm.
            visible_values = {opt.value for opt in step.options}
            self._checked_values = set(step.default_values or []) & visible_values
            # OptionRow has no ``id=`` so the sync remove/mount pair
            # is safe — Textual only raises DuplicateIds when two
            # widgets in the same tree share an explicit id. The
            # persistent Input widgets above (#number-input,
            # #secret-input) carry IDs and therefore went through the
            # await-friendly hide/show path instead.
            self._option_list.remove_children()
            for i, opt in enumerate(step.options):
                self._option_list.mount(OptionRow(
                    opt.label,
                    hint=opt.hint,
                    badges=opt.badges,
                    selected=(i == self._selected_index),
                    multi=True,
                    checked=(opt.value in self._checked_values),
                ))
            return

        # Default options-list step
        self._hide_number_widgets()
        self._hide_secret_widgets()
        self._selected_index = 0
        if step.default_value is not None:
            for i, opt in enumerate(step.options):
                if opt.value == step.default_value:
                    self._selected_index = i
                    break

        self._option_list.remove_children()
        for i, opt in enumerate(step.options):
            self._option_list.mount(OptionRow(
                opt.label,
                hint=opt.hint,
                badges=opt.badges,
                selected=(i == self._selected_index),
            ))

    def _hide_number_widgets(self) -> None:
        """Hide (don't remove) the persistent number-step widgets."""
        if self._number_input is not None:
            self._number_input.display = False
        if self._number_hint is not None:
            self._number_hint.display = False

    def _hide_secret_widgets(self) -> None:
        """Hide (don't remove) the persistent secret-step widgets.
        Also clear any value still in the masked input so the focus
        on the next visit starts from an empty buffer.
        """
        if self._secret_input is not None:
            self._secret_input.value = ""
            self._secret_input.display = False
        if self._secret_hint is not None:
            self._secret_hint.display = False

    def clear_conflict(self) -> None:
        self._conflict_slot.remove_children()

    def show_conflict(
        self,
        *,
        title: str,
        body: str,
        actions: list[ConflictAction],
    ) -> None:
        self._conflict_slot.remove_children()
        self._conflict_slot.mount(DependencyConflict(title=title, body=body, actions=actions))

    @property
    def selected_index(self) -> int:
        return self._selected_index

    @property
    def selected_option(self) -> PromptOption | None:
        if self._step is None:
            return None
        if self._step.kind == "number":
            # Build a synthetic option with the validated number value.
            raw = self._number_input.value if self._number_input else ""
            try:
                v = int(raw) if raw else int(self._step.default_value or 0)
            except ValueError:
                v = int(self._step.default_value or 0)
            v = max(self._step.number_min, min(self._step.number_max, v))
            return PromptOption(value=str(v), label=str(v))
        if self._step.kind == "text":
            # Same keep-current/clear sentinels as ``kind="secret"`` so an
            # empty Enter on a step with an existing default_value doesn't
            # silently wipe the user's previously-saved value (e.g.
            # OLLAMA_CUSTOM_MODELS).
            #   empty + no existing → ""
            #   empty + existing    → SECRET_KEEP (keep current)
            #   "clear"             → SECRET_CLEAR
            #   any other text      → typed value
            raw = (self._number_input.value if self._number_input else "").strip()
            has_existing = bool((self._step.default_value or "").strip())
            if raw == "":
                if has_existing:
                    return PromptOption(value=SECRET_KEEP, label="kept current")
                return PromptOption(value="", label="(empty)")
            if raw.lower() == "clear":
                return PromptOption(value=SECRET_CLEAR, label="cleared")
            return PromptOption(value=raw, label=raw)
        if self._step.kind == "multiselect":
            checked = sorted(self._checked_values)
            return PromptOption(
                value=",".join(checked),
                label=f"{len(checked)} selected" if checked else "(none)",
            )
        if self._step.kind == "secret":
            # Encode the secret-step result with sentinel values so
            # downstream code can distinguish keep-current vs. clear vs.
            # type-a-new-one without leaking the actual key into option
            # state any longer than necessary.
            raw = (self._secret_input.value if self._secret_input else "").strip()
            has_existing = bool((self._step.default_value or "").strip())
            if raw == "":
                if has_existing:
                    return PromptOption(value=SECRET_KEEP, label="kept current")
                return PromptOption(value="", label="(disabled)")
            if raw.lower() == "clear":
                return PromptOption(value=SECRET_CLEAR, label="cleared")
            return PromptOption(value=raw, label="enabled")
        if not self._step.options:
            return None
        idx = max(0, min(self._selected_index, len(self._step.options) - 1))
        return self._step.options[idx]

    def move(self, delta: int) -> None:
        if not self._step or not self._step.options:
            return
        n = len(self._step.options)
        new = (self._selected_index + delta) % n
        if new == self._selected_index:
            return
        self._selected_index = new
        rows = list(self._option_list.query(OptionRow))
        for i, row in enumerate(rows):
            row.set_selected(i == new)
        # Keep the focused row in the scrollable viewport. Without this,
        # moving past the bottom of the visible area scrolls the index
        # but not the viewport — the row is selected but invisible.
        if 0 <= new < len(rows):
            try:
                rows[new].scroll_visible(animate=False)
            except Exception:  # noqa: BLE001
                # Best-effort: pre-mount or test contexts may not have a
                # parent scroller; selection still updates correctly.
                pass
        if self._on_change and self.selected_option is not None:
            self._on_change(new, self.selected_option)

    def on_input_changed(self, event: "Input.Changed") -> None:
        """Live char-count hint for the secret step.

        When the user pastes/types into the masked Input, the visible
        ``••••`` dots can scroll out of view on long keys (OpenAI keys
        are 150+ chars). We update the hint Static below the input to
        ``✓ N chars entered`` so the user has unambiguous confirmation
        the paste landed.
        """
        if (
            self._step is None
            or self._step.kind != "secret"
            or self._secret_input is None
            or self._secret_hint is None
            or event.input is not self._secret_input
        ):
            return
        n = len(event.value or "")
        if n == 0:
            # Restore the static hint when the field is cleared.
            existing = (self._step.default_value or "").strip()
            placeholder = _mask_secret(existing) if existing else "paste API key here…"
            if existing:
                self._secret_hint.update(
                    self._step.secret_keep_hint or (
                        f"key currently set ({placeholder})  ·  Enter to keep  ·  "
                        "type a new key to replace  ·  type \"clear\" + Enter to remove"
                    )
                )
            else:
                self._secret_hint.update(
                    "paste a key + Enter to enable  ·  Enter (empty) to leave disabled"
                )
        else:
            self._secret_hint.update(f"✓ {n} char{'s' if n != 1 else ''} entered  ·  Enter to confirm")

    def toggle_focused(self) -> None:
        """Multi-select: flip the focused row's checkbox state."""
        if not self._step or self._step.kind != "multiselect":
            return
        if not self._step.options:
            return
        idx = max(0, min(self._selected_index, len(self._step.options) - 1))
        opt = self._step.options[idx]
        # Don't toggle the temporary "⏳ Fetching…" splash row that
        # appears while a provider-driven options list is loading.
        # The sentinel value is set by WizardScreen._load_current_step.
        if opt.value == "__loading__":
            return
        if opt.value in self._checked_values:
            self._checked_values.discard(opt.value)
            new_state = False
        else:
            self._checked_values.add(opt.value)
            new_state = True
        rows = list(self._option_list.query(OptionRow))
        if 0 <= idx < len(rows):
            rows[idx].set_checked(new_state)
