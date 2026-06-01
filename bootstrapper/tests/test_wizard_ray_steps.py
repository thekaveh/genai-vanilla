"""Wizard cascade for Ray: no follow-up steps for any source.

After the stack-wide `external` source strip, Ray only ships
container-cpu / container-gpu / disabled. Worker count for container
variants is collected inline on the source prompt via
``SecondaryNumberInput``. There are no follow-up cascade steps for any
source value today; the function is kept as a no-op so callers don't
need conditional imports.
"""

from __future__ import annotations

from wizard.ray_steps import build_ray_followup_steps  # type: ignore


def _build(source: str, env_overrides: dict | None = None):
    """Call build_ray_followup_steps with a minimal env + selections shape."""
    env = {"RAY_SOURCE": "disabled", "RAY_WORKER_COUNT": "2"}
    env.update(env_overrides or {})
    return build_ray_followup_steps(env_vars=env, selections={"RAY_SOURCE": source})


def test_container_cpu_emits_no_cascade():
    assert _build("ray-container-cpu") == []


def test_container_gpu_emits_no_cascade():
    assert _build("ray-container-gpu") == []


def test_disabled_emits_no_followup():
    assert _build("disabled") == []
