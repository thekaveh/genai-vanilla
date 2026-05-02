"""
Data model for the anchored-box presentation.

Pure data — no Rich, no rendering, no I/O. The renderables in info_box.py
read from these dataclasses; PresentationApp / state_builder mutate them.
Keeping render and state apart makes a future Textual/MVVM port
straightforward — same data, different rendering engine.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ServiceEntry:
    """One service displayed in the box."""
    name: str                   # display name, e.g. "Supabase DB"
    port: Optional[str]         # e.g. ":63001", or None when no port
    source: str                 # raw SOURCE value, e.g. "container", "ollama-localhost", "disabled"
    alias: Optional[str] = None # hostname alias (e.g. "chat.localhost") — shown in alias column


@dataclass
class AppState:
    """
    Top-level state read by the renderables. Mutated by PresentationApp
    (and through it, by the wizard / starter). Renderables only read.
    """
    # Brand metadata — overridable via .env (BRAND_NAME, BRAND_TAGLINE, …)
    # in `state_builder.build_app_state`. Defaults below are the canonical
    # GenAI Vanilla values.
    brand_name: str = "GenAI Vanilla"
    tagline: str = "AI Development Suite"
    version: str = ""
    creator: str = "Kaveh Razavi"
    license: str = "Apache License 2.0"
    repo_url: str = "github.com/thekaveh/genai-vanilla"

    # Optional: shown in the box footer when the user is using a custom env file.
    env_file_path: Optional[str] = None

    # Services grid — ordered as the user should see them.
    services: List[ServiceEntry] = field(default_factory=list)

    hosts_configured: bool = False
    kong_port: str = "63002"

    # Mode controls which decorations the box shows.
    # "normal"  → just the services grid + footer.
    # "wizard"  → adds a progress bar row above the services grid and a
    #             command-preview row below it.
    box_mode: str = "normal"

    # Wizard-only fields (ignored when box_mode == "normal").
    # `wizard_step` is the count of COMPLETED answers, in [0..wizard_total].
    # The progress bar fills to wizard_step / wizard_total — 0% before the
    # first answer, 100% only after the last. The user-facing "Step X of N"
    # label is 1-indexed and derived in info_box._render_wizard_progress.
    wizard_step: int = 0
    wizard_total: int = 0
    wizard_command_preview: str = ""  # e.g. "./start.sh --llm-provider-source ollama-localhost"
