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
from textual.containers import Container, Vertical
from textual.widgets import Input, Static

from .. import palette as P
from .dependency_conflict import ConflictAction, DependencyConflict
from .option_row import OptionRow


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
    # The exact service-table row name this step controls. Used by the
    # wizard screen to highlight the matching row when this step loads.
    service_name: str = ""
    # "options" (default — multiple-choice list) or "number" (free
    # integer input, e.g. base port).
    kind: str = "options"
    number_min: int = 1024
    number_max: int = 65000


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
    PromptPanel > #option-list { height: auto; }
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
    PromptPanel #number-hint {
        height: 1;
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
        self._option_list = Vertical(id="option-list")
        self._number_slot = Container(id="number-slot")
        self._number_input: Input | None = None
        self._conflict_slot = Container(id="conflict-slot")
        self._step: PromptStep | None = None
        self._selected_index = 0
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
            # Free integer input — clear option list, mount Input.
            # Empty value + default in placeholder so the user can just
            # type a new port without first deleting the prefilled one
            # (which led to digits getting appended → wrong value).
            self._option_list.remove_children()
            self._number_slot.remove_children()
            default = step.default_value or ""
            self._number_input = Input(
                value="",
                placeholder=default,
                id="number-input",
            )
            self._number_slot.mount(self._number_input)
            hint = Static(
                f"type a value in {step.number_min}–{step.number_max}, "
                f"or press Enter to keep {default}",
                id="number-hint",
            )
            self._number_slot.mount(hint)
            # Focus the input so the user can type immediately.
            self._number_input.focus()
            return

        # Default options-list step
        self._number_slot.remove_children()
        self._number_input = None
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
        for i, row in enumerate(self._option_list.query(OptionRow)):
            row.set_selected(i == new)
        if self._on_change and self.selected_option is not None:
            self._on_change(new, self.selected_option)
