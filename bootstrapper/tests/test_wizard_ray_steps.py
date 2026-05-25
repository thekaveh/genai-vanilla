"""Wizard cascade for Ray: external address is the only follow-up step.

Worker count for container variants is collected inline on the Ray source
prompt via ``SecondaryNumberInput`` (no separate cascade step). See
``tests/test_prompt_panel_secondary_input.py`` for the widget contract.
"""

from __future__ import annotations

from wizard.ray_steps import (  # type: ignore
    RAY_EXTERNAL_ADDRESS_TITLE,
    build_ray_followup_steps,
)


def _build(source: str, env_overrides: dict | None = None):
    """Call build_ray_followup_steps with a minimal env + selections shape."""
    env = {"RAY_SOURCE": "disabled", "RAY_WORKER_COUNT": "2", "RAY_EXTERNAL_ADDRESS": ""}
    env.update(env_overrides or {})
    return build_ray_followup_steps(env_vars=env, selections={"RAY_SOURCE": source})


def test_container_cpu_emits_no_cascade():
    # Worker count is collected via the inline secondary widget on the
    # source prompt — no follow-up step.
    assert _build("ray-container-cpu") == []


def test_container_gpu_emits_no_cascade():
    assert _build("ray-container-gpu") == []


def test_external_emits_address_step():
    steps = _build("ray-external")
    assert len(steps) == 1
    assert steps[0].title == RAY_EXTERNAL_ADDRESS_TITLE


def test_disabled_emits_no_followup():
    assert _build("disabled") == []
