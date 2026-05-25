"""Unit tests for the inline ``SecondaryNumberInput`` widget contract.

The widget lets a ``kind="options"`` PromptStep carry an integer textbox
that's rendered BELOW the tile grid in the same prompt. The wizard
captures the value via ``PromptPanel.secondary_value()`` and forwards it
through a ``__secondary__:<ENV_VAR>`` key in the selections dict (see
``ui.textual.integration._selections_to_args``).

These tests exercise ``secondary_value`` on a stub PromptPanel — the
method only reads ``self._step`` / ``self._secondary_input`` /
``self.selected_option`` so we can sidestep Textual's reactive plumbing.

The widget is generic: today Ray uses it for ``RAY_WORKER_COUNT`` on
container sources; tomorrow localhost-mode services will use it to
override default host ports. The Ray-specific wiring lives in
``ui/textual/integration.py``; this file verifies only the contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest

from ui.textual.widgets.prompt_panel import (
    PromptOption,
    PromptPanel,
    PromptStep,
    SecondaryNumberInput,
)


# ────────────────────────────────────────────────────────────────────────────
# Stubs — minimal stand-ins that satisfy what `secondary_value` reads.
# ────────────────────────────────────────────────────────────────────────────


@dataclass
class _InputStub:
    """Stand-in for textual.widgets.Input — only exposes ``value``."""
    value: str = ""


class _PanelStub:
    """Minimal stand-in for PromptPanel. ``secondary_value`` only reads
    ``_step``, ``_secondary_input``, and the ``selected_option`` property,
    so we don't need a live Textual app."""

    secondary_value = PromptPanel.secondary_value
    selected_option = PromptPanel.selected_option

    def __init__(self, step: PromptStep, *, selected_index: int = 0, raw: str = ""):
        self._step = step
        self._selected_index = selected_index
        # Per-row inputs list — populated by load_step() in the real
        # PromptPanel; here we seed it with one stub so secondary_value
        # has something to read. Empty list models the "no eligible rows
        # on this step" case.
        if raw is None:
            self._secondary_inputs: list[_InputStub] = []
        else:
            self._secondary_inputs = [_InputStub(value=raw)]


def _options_step(secondary: SecondaryNumberInput | None,
                  values: tuple[str, ...] = ("a", "b")) -> PromptStep:
    return PromptStep(
        title="test step",
        step_index=1,
        step_total=1,
        heading="",
        options=[PromptOption(value=v, label=v) for v in values],
        kind="options",
        secondary_number=secondary,
    )


def _ray_secondary(default: int = 2) -> SecondaryNumberInput:
    """The Ray wiring's exact shape — covers the documented use case."""
    return SecondaryNumberInput(
        env_var="RAY_WORKER_COUNT",
        default_value=default,
        number_min=0,
        number_max=64,
        show_when=("ray-container-cpu", "ray-container-gpu"),
        unit_suffix="workers",
    )


# ────────────────────────────────────────────────────────────────────────────
# Contract: returns None when not applicable
# ────────────────────────────────────────────────────────────────────────────


def test_returns_none_when_step_has_no_secondary():
    """A vanilla options step (no secondary_number set) reports None."""
    panel = _PanelStub(_options_step(secondary=None))
    assert panel.secondary_value() is None


def test_returns_none_when_step_is_not_options_kind():
    """Number/secret/text kinds never carry a secondary."""
    step = PromptStep(title="x", step_index=1, step_total=1, heading="",
                      kind="number", number_min=0, number_max=10)
    panel = _PanelStub(step, raw=None)  # no eligible rows on a number step
    assert panel.secondary_value() is None


def test_returns_none_when_no_eligible_rows():
    """An options step whose secondary's show_when matches no option
    yields an empty ``_secondary_inputs`` list — secondary_value is None."""
    panel = _PanelStub(_options_step(secondary=_ray_secondary()), raw=None)
    assert panel.secondary_value() is None


def test_returns_none_when_selected_option_not_in_show_when():
    """``show_when`` filters out options that shouldn't trigger persistence.
    Picking ``ray-disabled`` (or ``ray-external``) must skip the worker-count
    write entirely — otherwise we'd corrupt .env for non-container sources."""
    step = _options_step(
        secondary=_ray_secondary(),
        values=("ray-container-cpu", "ray-external", "disabled"),
    )
    # selected_index=1 ⇒ "ray-external" — not in show_when
    panel = _PanelStub(step, selected_index=1, raw="5")
    assert panel.secondary_value() is None


def test_empty_show_when_always_persists():
    """A SecondaryNumberInput with no show_when (empty tuple) is the
    "always write" mode — e.g. for a future localhost host-port override
    where the integer applies regardless of which tile is picked."""
    sec = SecondaryNumberInput(
        env_var="SOME_PORT",
        default_value=8080,
        number_min=1024,
        number_max=65535,
        show_when=(),
        unit_suffix="port",
    )
    step = _options_step(secondary=sec, values=("localhost", "container"))
    panel = _PanelStub(step, selected_index=0, raw="9090")
    assert panel.secondary_value() == ("SOME_PORT", "9090")
    panel2 = _PanelStub(step, selected_index=1, raw="9090")
    assert panel2.secondary_value() == ("SOME_PORT", "9090")


# ────────────────────────────────────────────────────────────────────────────
# Contract: value capture & default-handling
# ────────────────────────────────────────────────────────────────────────────


def test_returns_default_when_input_empty():
    """Empty input ⇒ fall back to ``default_value`` (Enter-to-accept)."""
    step = _options_step(
        secondary=_ray_secondary(default=2),
        values=("ray-container-cpu",),
    )
    panel = _PanelStub(step, selected_index=0, raw="")
    assert panel.secondary_value() == ("RAY_WORKER_COUNT", "2")


def test_returns_typed_integer_value():
    step = _options_step(
        secondary=_ray_secondary(),
        values=("ray-container-cpu",),
    )
    panel = _PanelStub(step, selected_index=0, raw="7")
    assert panel.secondary_value() == ("RAY_WORKER_COUNT", "7")


def test_clamps_value_above_max():
    """A typed value above number_max gets clamped (matches kind='number')."""
    step = _options_step(
        secondary=_ray_secondary(),  # max=64
        values=("ray-container-cpu",),
    )
    panel = _PanelStub(step, selected_index=0, raw="9999")
    assert panel.secondary_value() == ("RAY_WORKER_COUNT", "64")


def test_clamps_value_below_min():
    """Negative values clamp up to number_min (Ray min=0 ⇒ 0)."""
    step = _options_step(
        secondary=_ray_secondary(),
        values=("ray-container-cpu",),
    )
    panel = _PanelStub(step, selected_index=0, raw="-5")
    assert panel.secondary_value() == ("RAY_WORKER_COUNT", "0")


def test_falls_back_to_default_on_garbage_input():
    """Non-numeric input ⇒ swallow the ValueError and use the default
    rather than crashing the wizard mid-launch."""
    step = _options_step(
        secondary=_ray_secondary(default=3),
        values=("ray-container-cpu",),
    )
    panel = _PanelStub(step, selected_index=0, raw="not-a-number")
    assert panel.secondary_value() == ("RAY_WORKER_COUNT", "3")


# ────────────────────────────────────────────────────────────────────────────
# Contract: sibling-sync between per-row inputs
# ────────────────────────────────────────────────────────────────────────────


def test_sync_mirrors_value_across_siblings():
    """Two eligible rows ⇒ two Input widgets. Typing in one must mirror
    to the other (shared logical value). Reading from either matches."""
    step = _options_step(
        secondary=_ray_secondary(default=2),
        values=("ray-container-cpu", "ray-container-gpu", "disabled"),
    )

    class _PanelWithSync:
        _sync_secondary_inputs = PromptPanel._sync_secondary_inputs

    panel = _PanelWithSync()
    a, b = _InputStub(value="2"), _InputStub(value="2")
    panel._secondary_inputs = [a, b]
    # User types "7" into the cpu row's Input
    a.value = "7"
    panel._sync_secondary_inputs(a)
    assert b.value == "7", f"Sibling not synced: a={a.value} b={b.value}"

    # User then edits the gpu row's Input to "12"
    b.value = "12"
    panel._sync_secondary_inputs(b)
    assert a.value == "12"


def test_sync_is_idempotent_when_values_already_match():
    """A no-op sync (siblings already equal) must not loop."""
    class _PanelWithSync:
        _sync_secondary_inputs = PromptPanel._sync_secondary_inputs

    panel = _PanelWithSync()
    a, b = _InputStub(value="5"), _InputStub(value="5")
    panel._secondary_inputs = [a, b]
    panel._sync_secondary_inputs(a)
    assert a.value == "5" and b.value == "5"
