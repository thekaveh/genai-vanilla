"""Ray wizard cascade — follow-up prompts after RAY_SOURCE is selected.

For container sources (``ray-container-cpu`` / ``ray-container-gpu``), the
worker count is collected INLINE on the Ray source prompt via the generic
``SecondaryNumberInput`` widget (see ``ui.textual.widgets.prompt_panel`` and
the Ray-specific wiring in ``ui.textual.integration``) — no follow-up step.

For ``ray-external``, prompt for ``RAY_EXTERNAL_ADDRESS`` (free-form text).
``disabled`` triggers no follow-up.

This module is parallel to ``wizard.llm_steps`` — same pattern, simpler
scope (no library scrape, no multiselect).

Step titles are exported as module-level constants so ``integration.py``
can key into the wizard's ``selections`` dict without duplicating the
string literals.
"""

from __future__ import annotations

from typing import List

from ui.textual.widgets.prompt_panel import PromptStep  # type: ignore

# Exported so integration.py can extract the selected value by title.
RAY_EXTERNAL_ADDRESS_TITLE = "Ray  ·  external address"


def build_ray_followup_steps(env_vars: dict, selections: dict) -> List[PromptStep]:
    """Return the follow-up steps appropriate for the active Ray source.

    Args:
        env_vars: Parsed .env or .env.example (used for default fallbacks).
        selections: User selections accumulated so far; expects ``RAY_SOURCE``.

    Returns:
        List of ``PromptStep`` instances. Empty for container/disabled sources
        — container worker count is collected via the inline secondary input
        on the Ray source prompt itself, not a separate step.
    """
    source = selections.get("RAY_SOURCE", env_vars.get("RAY_SOURCE", "disabled"))

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
