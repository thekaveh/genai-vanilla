"""Wizard cascade for Ray: source-variant tile drives a follow-up number
prompt for RAY_WORKER_COUNT (when container-*) or a text prompt for
RAY_EXTERNAL_ADDRESS (when ray-external)."""

from __future__ import annotations

from wizard.ray_steps import (  # type: ignore
    RAY_EXTERNAL_ADDRESS_TITLE,
    RAY_WORKER_COUNT_TITLE,
    build_ray_followup_steps,
)


def _build(source: str, env_overrides: dict | None = None):
    """Call build_ray_followup_steps with a minimal env + selections shape."""
    env = {"RAY_SOURCE": "disabled", "RAY_WORKER_COUNT": "2", "RAY_EXTERNAL_ADDRESS": ""}
    env.update(env_overrides or {})
    return build_ray_followup_steps(env_vars=env, selections={"RAY_SOURCE": source})


def test_container_cpu_emits_worker_count_step():
    steps = _build("ray-container-cpu")
    assert len(steps) == 1
    assert steps[0].title == RAY_WORKER_COUNT_TITLE
    assert steps[0].default_value == "2"


def test_container_gpu_emits_worker_count_step():
    steps = _build("ray-container-gpu")
    assert len(steps) == 1
    assert steps[0].title == RAY_WORKER_COUNT_TITLE


def test_external_emits_address_step():
    steps = _build("ray-external")
    assert len(steps) == 1
    assert steps[0].title == RAY_EXTERNAL_ADDRESS_TITLE


def test_disabled_emits_no_followup():
    steps = _build("disabled")
    assert steps == []


def test_worker_count_default_from_env():
    steps = _build("ray-container-cpu", env_overrides={"RAY_WORKER_COUNT": "5"})
    assert steps[0].default_value == "5"
