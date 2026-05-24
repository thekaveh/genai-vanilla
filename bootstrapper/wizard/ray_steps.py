"""Ray wizard cascade — follow-up prompts after RAY_SOURCE is selected.

When the user picks ``ray-container-cpu`` or ``ray-container-gpu``, prompt for
RAY_WORKER_COUNT (number, default 2, min 0, max 64). When the user picks
``ray-external``, prompt for RAY_EXTERNAL_ADDRESS (free-form text). ``disabled``
triggers no follow-up.

This module is parallel to ``wizard.llm_steps`` — same pattern, simpler
scope (no library scrape, no multiselect).

Step titles are exported as module-level constants so ``integration.py``
can key into the wizard's ``selections`` dict without duplicating the
string literals.
"""

from __future__ import annotations

from typing import List

from ui.textual.widgets.prompt_panel import PromptStep  # type: ignore

# Exported so integration.py can extract the selected values by title.
RAY_WORKER_COUNT_TITLE = "Ray  ·  worker count"
RAY_EXTERNAL_ADDRESS_TITLE = "Ray  ·  external address"

# Container sources that trigger the worker-count follow-up.
_CONTAINER_SOURCES = {"ray-container-cpu", "ray-container-gpu"}


def build_ray_followup_steps(env_vars: dict, selections: dict) -> List[PromptStep]:
    """Return the follow-up steps appropriate for the active Ray source.

    Args:
        env_vars: Parsed .env or .env.example (used for default fallbacks).
        selections: User selections accumulated so far; expects ``RAY_SOURCE``.

    Returns:
        List of ``PromptStep`` instances. Empty when source is ``disabled``.
    """
    source = selections.get("RAY_SOURCE", env_vars.get("RAY_SOURCE", "disabled"))

    if source in _CONTAINER_SOURCES:
        raw_default = (env_vars.get("RAY_WORKER_COUNT") or "2").strip()
        try:
            default_int = max(0, int(raw_default))
        except (ValueError, TypeError):
            default_int = 2
        return [
            PromptStep(
                title=RAY_WORKER_COUNT_TITLE,
                step_index=0,
                step_total=0,
                heading="How many Ray worker containers?",
                subtitle=(
                    "Number of ray-worker replicas launched alongside the head node. "
                    "0 = head-only single-node cluster (Ray still works; useful for small "
                    "dev boxes). Upper bound is your host's CPU/memory budget."
                ),
                default_value=str(default_int),
                kind="number",
                number_min=0,
                number_max=64,
                service_name="Ray",
                service_key="ray",
                skip_if_prev=lambda sel: sel.get("RAY_SOURCE", "disabled")
                not in _CONTAINER_SOURCES,
            )
        ]

    if source == "ray-external":
        default_val = (env_vars.get("RAY_EXTERNAL_ADDRESS") or "").strip()
        return [
            PromptStep(
                title=RAY_EXTERNAL_ADDRESS_TITLE,
                step_index=0,
                step_total=0,
                heading="Ray external cluster URL",
                subtitle=(
                    "The ray:// address of your external Ray cluster. "
                    "Format: ray://hostname:10001 (Anyscale or self-hosted). "
                    "Press Enter to keep the current value, or type a new address."
                ),
                default_value=default_val,
                kind="text",
                service_name="Ray",
                service_key="ray",
                skip_if_prev=lambda sel: sel.get("RAY_SOURCE", "disabled")
                != "ray-external",
            )
        ]

    return []
