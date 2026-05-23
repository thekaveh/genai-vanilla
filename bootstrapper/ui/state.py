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
    category: str = ""          # drives bar color in the box
    pending: bool = False       # drives pending rendering


@dataclass
class CloudApiEntry:
    """One cloud LLM provider — API toggle, NOT a service.

    Cloud providers (OpenAI, Anthropic, OpenRouter) contribute env flags +
    an API key to the LiteLLM gateway. They never run as compose services
    (scale: 0 in their manifest runtime_sc:), so they render in their own block
    in the stack overview rather than alongside real services.
    """
    name: str           # display label, e.g. "OpenAI"
    source_var: str     # e.g. "CLOUD_OPENAI_SOURCE"
    api_key_var: str    # e.g. "OPENAI_API_KEY"
    enabled: bool       # source == "enabled"
    key_set: bool       # api_key value is non-empty


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
    tagline: str = "Gen-AI Development Suite"
    version: str = ""
    creator: str = "Kaveh Razavi"
    creator_email: str = "kaveh.razavi@gmail.com"
    license: str = "Apache License 2.0"
    repo_url: str = "github.com/thekaveh/genai-vanilla"

    # Services grid — ordered as the user should see them.
    services: List[ServiceEntry] = field(default_factory=list)

    # Cloud LLM provider toggles — rendered separately from `services`,
    # since they're API credentials routed through LiteLLM, not containers.
    cloud_apis: List[CloudApiEntry] = field(default_factory=list)

    kong_port: str = "63002"
