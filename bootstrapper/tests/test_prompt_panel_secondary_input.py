"""Unit tests for the per-option ``SecondaryNumberInput`` widget contract.

Eligibility is now per-option: a ``PromptOption`` either carries a
``SecondaryNumberInput`` config (eligible — renders an inline textbox)
or doesn't (no textbox slot rendered on that row). Different options
on the same step can carry configs writing to DIFFERENT env vars; the
widget mirrors keystrokes only between siblings sharing an env_var.
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


@dataclass
class _InputStub:
    """Stand-in for textual.widgets.Input — exposes value + env_var."""
    value: str = ""
    associated_env_var: str = ""


class _PanelStub:
    """Stand-in for PromptPanel exposing only what secondary_values and
    _sync_secondary_inputs need."""

    secondary_values = PromptPanel.secondary_values
    _sync_secondary_inputs = PromptPanel._sync_secondary_inputs
    selected_option = PromptPanel.selected_option

    def __init__(self, step: PromptStep, *, selected_index: int = 0):
        self._step = step
        self._selected_index = selected_index
        self._secondary_inputs: list[_InputStub] = []


def _opt(value: str, *, secondary: SecondaryNumberInput | None = None) -> PromptOption:
    return PromptOption(value=value, label=value, secondary_number=secondary)


def _step(options: list[PromptOption]) -> PromptStep:
    return PromptStep(
        title="test step",
        step_index=1,
        step_total=1,
        heading="",
        options=options,
        kind="options",
    )


# ─── secondary_values: returns ALL eligible rows' values ──────────────

def test_secondary_values_empty_when_no_options_have_config():
    panel = _PanelStub(_step([_opt("a"), _opt("b")]))
    assert panel.secondary_values() == []


def test_secondary_values_returns_one_tuple_per_eligible_option():
    cfg = SecondaryNumberInput(env_var="X", default_value=5, number_min=0, number_max=100)
    panel = _PanelStub(_step([_opt("a", secondary=cfg), _opt("b", secondary=cfg), _opt("c")]))
    panel._secondary_inputs = [
        _InputStub(value="5", associated_env_var="X"),
        _InputStub(value="5", associated_env_var="X"),
    ]
    tuples = panel.secondary_values()
    assert tuples == [("X", "5"), ("X", "5")]


def test_secondary_values_distinct_env_vars_yield_distinct_tuples():
    cfg_a = SecondaryNumberInput(env_var="PARAKEET", default_value=63022,
                                 number_min=1024, number_max=65535)
    cfg_b = SecondaryNumberInput(env_var="WHISPER", default_value=63025,
                                 number_min=1024, number_max=65535)
    panel = _PanelStub(_step([_opt("p", secondary=cfg_a), _opt("w", secondary=cfg_b)]))
    panel._secondary_inputs = [
        _InputStub(value="63022", associated_env_var="PARAKEET"),
        _InputStub(value="63025", associated_env_var="WHISPER"),
    ]
    assert panel.secondary_values() == [("PARAKEET", "63022"), ("WHISPER", "63025")]


def test_secondary_values_clamps_each_independently():
    cfg_a = SecondaryNumberInput(env_var="A", default_value=8000, number_min=1024, number_max=65535)
    cfg_b = SecondaryNumberInput(env_var="B", default_value=11434, number_min=1024, number_max=65535)
    panel = _PanelStub(_step([_opt("a", secondary=cfg_a), _opt("b", secondary=cfg_b)]))
    panel._secondary_inputs = [
        _InputStub(value="99999", associated_env_var="A"),
        _InputStub(value="50",    associated_env_var="B"),
    ]
    assert panel.secondary_values() == [("A", "65535"), ("B", "1024")]


def test_secondary_values_falls_back_to_default_on_garbage_input():
    cfg = SecondaryNumberInput(env_var="X", default_value=8000, number_min=1024, number_max=65535)
    panel = _PanelStub(_step([_opt("a", secondary=cfg)]))
    panel._secondary_inputs = [_InputStub(value="not-a-number", associated_env_var="X")]
    assert panel.secondary_values() == [("X", "8000")]


def test_secondary_values_empty_input_uses_default():
    cfg = SecondaryNumberInput(env_var="X", default_value=8000, number_min=1024, number_max=65535)
    panel = _PanelStub(_step([_opt("a", secondary=cfg)]))
    panel._secondary_inputs = [_InputStub(value="", associated_env_var="X")]
    assert panel.secondary_values() == [("X", "8000")]


# ─── _sync_secondary_inputs: keyed by env_var ─────────────────────────

def test_sync_mirrors_value_across_siblings_sharing_env_var():
    panel = _PanelStub(_step([]))
    a = _InputStub(value="2", associated_env_var="X")
    b = _InputStub(value="2", associated_env_var="X")
    c = _InputStub(value="9000", associated_env_var="Y")
    panel._secondary_inputs = [a, b, c]
    a.value = "7"
    panel._sync_secondary_inputs(a)
    assert b.value == "7", "Same-env_var sibling not synced"
    assert c.value == "9000", "Different-env_var sibling should be independent"


def test_sync_is_idempotent_when_values_already_match():
    panel = _PanelStub(_step([]))
    a = _InputStub(value="5", associated_env_var="X")
    b = _InputStub(value="5", associated_env_var="X")
    panel._secondary_inputs = [a, b]
    panel._sync_secondary_inputs(a)
    assert a.value == "5" and b.value == "5"


# ─── dataclass shape ──────────────────────────────────────────────────

def test_secondary_number_input_dropped_show_when_field():
    fields = {f for f in SecondaryNumberInput.__dataclass_fields__}
    assert "show_when" not in fields, (
        f"SecondaryNumberInput should no longer have show_when. Fields: {fields}"
    )


def test_prompt_option_has_secondary_number_field():
    fields = PromptOption.__dataclass_fields__
    assert "secondary_number" in fields, (
        f"PromptOption should carry secondary_number. Fields: {set(fields)}"
    )
    assert fields["secondary_number"].default is None


def test_prompt_step_no_longer_has_secondary_number_field():
    fields = {f for f in PromptStep.__dataclass_fields__}
    assert "secondary_number" not in fields, (
        f"PromptStep should no longer carry secondary_number. Fields: {fields}"
    )
