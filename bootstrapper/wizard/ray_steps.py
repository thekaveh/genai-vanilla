"""Ray wizard cascade — currently a no-op.

The Ray source list is `ray-container-cpu`, `ray-container-gpu`, `disabled`.
Worker count for container variants is collected INLINE on the source prompt
via the generic ``SecondaryNumberInput`` widget — see ``ui.textual.widgets.prompt_panel``
and the Ray-specific wiring in ``ui.textual.integration``.

No source value triggers a follow-up cascade today. The function is kept as a
no-op so callers (integration.py) don't need conditional imports — and so a
future spec reintroducing an authenticated remote variant has an obvious
home for the cascade.
"""

from __future__ import annotations

from typing import List

from ui.textual.widgets.prompt_panel import PromptStep  # type: ignore


def build_ray_followup_steps(env_vars: dict, selections: dict) -> List[PromptStep]:
    """Return follow-up steps for the active Ray source. Currently always empty."""
    return []
