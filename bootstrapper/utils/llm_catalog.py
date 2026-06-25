"""
Curated LLM catalog — single source of truth for what models the stack
knows about.

Three consumers import this module:

  • The wizard step builder (cloud + Ollama multi-select option lists).
  • ``llm-catalog-init`` (UPSERTs DB rows from this catalog into
    ``public.llms``).
  • ``litellm-init`` (renders ``volumes/litellm/config.yaml`` from
    rows that are ``active = true`` in ``public.llms`` — query is
    ``SELECT provider, name FROM public.llms WHERE active = true``
    followed by per-provider routing rules baked into the init
    script. Catalog capability metadata (content / structured_content
    / vision / embeddings) is consumed by the wizard and backend,
    NOT by litellm-init at config-render time).

To add a model: append a ``CatalogEntry`` below. To remove one: delete
the entry (it stays in the DB row history but won't be re-UPSERTed).
The ``llm-catalog-init`` UPSERT is idempotent — capability flags
(content / structured_content / vision / embeddings) and immutable
model facts (context_window, size_gb) refresh from the catalog on
every run; ``active`` and ``description`` are preserved on conflict
so wizard choices and hand-edited notes survive re-runs.

The default-active Ollama trio is seeded by ``llm-catalog-init`` at every
``docker compose up`` — the rest of the catalog (cloud + non-default Ollama)
is also populated by ``llm-catalog-init``.

Maintenance cadence
-------------------
Cloud-provider catalogs drift faster than the rest of the codebase.
Suggested cadence:

  • **Quarterly** (or whenever a major release lands): refresh the
    ``CLOUD_CATALOG`` to add new flagship models (e.g. gpt-6, claude-5,
    gemini-3) and update ``default_active`` so first-run wizard users
    get the current sensible defaults.
  • **Every 6 months**: prune deprecated entries (after their replacement
    has been ``default_active`` for at least one cycle). Removed entries
    stop being UPSERTed but stay in DBs that already have them — no DB
    migration needed.
  • **Ollama**: only the ``OLLAMA_DEFAULT_CATALOG`` trio needs upkeep
    (the wizard's catalog multiselect goes via the live
    ``ollama.com/library`` scrape). Update when one of the three is
    superseded by a clearly better default.

When live-fetched names overlap catalog names, the catalog metadata
wins (capability flags + descriptions); when live-only names appear,
``llm-catalog-init`` UPSERTs them with generic capability defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class CatalogEntry:
    """One catalog row.

    Capability fields are integer priority (0..10). Higher is "more
    preferred" for that capability. Zero means "not capable."

    Convention:
      • content              — chat / instruction-following
      • structured_content   — reliable JSON / function-calling
      • vision               — image input
      • embeddings           — text → vector
    """
    provider: str           # 'ollama' | 'openai' | 'anthropic' | 'openrouter'
    name: str               # exact model_name as LiteLLM should see it
    content: int = 0
    structured_content: int = 0
    vision: int = 0
    embeddings: int = 0
    context_window: int = 0
    size_gb: float | None = None
    description: str = ""
    # True for entries that should be active=true on first run; cloud
    # entries are always opt-in (default_active=False) — the user picks
    # them via wizard multi-select.
    default_active: bool = False
    # Optional badges shown in the wizard's multi-select option rows.
    badges: List[str] = field(default_factory=list)


# ─── Cloud catalog ────────────────────────────────────────────────────
# Two roles:
#   1. **Pre-check intersection** for the wizard's live multi-select.
#      When the user pastes a key, we query ``/v1/models`` (OpenAI /
#      Anthropic) or the public ``/api/v1/models`` (OpenRouter) and
#      pre-check ``(live_ids ∩ catalog.default_active)``. Each
#      provider's curated default-active set is what shows up checked
#      out of the box. Listing additional non-default entries here
#      makes them available to pre-check for users whose accounts
#      don't have access to the newer flagships (e.g. an OpenAI
#      account without gpt-5 access still gets gpt-4o pre-checked
#      because we list it here).
#   2. **Capability metadata** for ``public.llms`` rows — when the
#      live API returns a name that matches a catalog entry, the
#      ``content`` / ``structured_content`` / ``vision`` / ``embeddings``
#      flags get carried over to the DB row. Live-only names get
#      generic defaults from ``llm-catalog-init``.
#
# Bump on releases. The DB UPSERT in ``llm-catalog-init`` will pick
# it up on the next ``./start.sh``.

CLOUD_CATALOG: List[CatalogEntry] = [
    # ─── OpenAI ──────────────────────────────────────────────────────
    CatalogEntry(
        provider="openai", name="gpt-5",
        content=10, structured_content=10, vision=10,
        context_window=400000,
        description="OpenAI flagship multimodal — strongest content + vision + structured output",
        default_active=True,
        badges=["flagship"],
    ),
    CatalogEntry(
        provider="openai", name="gpt-5-mini",
        content=8, structured_content=8, vision=8,
        context_window=400000,
        description="OpenAI mid-tier multimodal — fast, cheaper than gpt-5",
        default_active=True,
    ),
    CatalogEntry(
        provider="openai", name="gpt-5-nano",
        content=6, structured_content=6, vision=6,
        context_window=128000,
        description="OpenAI ultra-cheap multimodal — for high-volume tasks",
    ),
    CatalogEntry(
        provider="openai", name="gpt-4o",
        content=8, structured_content=8, vision=8,
        context_window=128000,
        description="Previous-gen multimodal — kept for compatibility",
    ),
    CatalogEntry(
        provider="openai", name="gpt-4o-mini",
        content=6, structured_content=6, vision=6,
        context_window=128000,
        description="Previous-gen cheap multimodal",
    ),
    CatalogEntry(
        provider="openai", name="o3",
        content=10, structured_content=10,
        context_window=200000,
        description="OpenAI reasoning model — strong on math, code, logic; no vision",
        badges=["reasoning"],
    ),
    CatalogEntry(
        provider="openai", name="o3-mini",
        content=8, structured_content=8,
        context_window=200000,
        description="OpenAI smaller reasoning model — faster, cheaper",
        badges=["reasoning"],
    ),
    CatalogEntry(
        provider="openai", name="o1",
        content=10, structured_content=9,
        context_window=200000,
        description="OpenAI o1 reasoning model",
        badges=["reasoning"],
    ),
    CatalogEntry(
        provider="openai", name="text-embedding-3-large",
        embeddings=10,
        context_window=8191,
        description="OpenAI flagship embedding model — 3072 dims",
        default_active=True,
        badges=["embeddings"],
    ),
    CatalogEntry(
        provider="openai", name="text-embedding-3-small",
        embeddings=8,
        context_window=8191,
        description="OpenAI cheaper embedding model — 1536 dims",
        badges=["embeddings"],
    ),

    # ─── Anthropic ───────────────────────────────────────────────────
    CatalogEntry(
        provider="anthropic", name="claude-opus-4-7",
        content=10, structured_content=10, vision=10,
        context_window=200000,
        description="Anthropic flagship — strongest reasoning + writing",
        default_active=True,
        badges=["flagship"],
    ),
    CatalogEntry(
        provider="anthropic", name="claude-sonnet-4-6",
        content=9, structured_content=9, vision=9,
        context_window=1000000,
        description="Anthropic mid-tier — 1M context, balanced cost/quality",
        default_active=True,
    ),
    CatalogEntry(
        provider="anthropic", name="claude-haiku-4-5",
        content=7, structured_content=7, vision=7,
        context_window=200000,
        description="Anthropic small/fast — cheapest in the family",
    ),

    # ─── OpenRouter ──────────────────────────────────────────────────
    # OpenRouter is a routing aggregator. Names are prefixed with
    # ``openrouter/`` so LiteLLM routes them via the OpenRouter API.
    CatalogEntry(
        provider="openrouter", name="openrouter/auto",
        content=8, structured_content=8, vision=5,
        context_window=200000,
        description="OpenRouter auto-router — picks a backend per request",
        default_active=True,
        badges=["router"],
    ),
    CatalogEntry(
        provider="openrouter", name="openrouter/anthropic/claude-sonnet-4.6",
        content=9, structured_content=9, vision=9,
        context_window=1000000,
        description="Claude Sonnet 4.6 via OpenRouter (alternative billing)",
    ),
    CatalogEntry(
        provider="openrouter", name="openrouter/openai/gpt-5",
        content=10, structured_content=10, vision=10,
        context_window=400000,
        description="GPT-5 via OpenRouter (alternative billing)",
    ),
    CatalogEntry(
        provider="openrouter", name="openrouter/google/gemini-2.5-pro",
        content=9, structured_content=9, vision=9,
        context_window=2000000,
        description="Gemini 2.5 Pro via OpenRouter — 2M context window",
    ),
    CatalogEntry(
        provider="openrouter", name="openrouter/meta-llama/llama-3.3-70b-instruct",
        content=8, structured_content=7,
        context_window=128000,
        description="Llama 3.3 70B via OpenRouter — open-weight content model",
    ),
]


# ─── Ollama catalog ──────────────────────────────────────────────────
# Default-active baseline only. The user-facing catalog comes from the
# live ollama.com/library scrape (~230 entries) via
# ``utils/ollama_library.py``. This list is the fallback shown when
# the scrape fails AND the default-active set seeded by ``llm-catalog-init``.
# Keep this trim — every entry here needs maintenance; the live library
# is the source of truth for what's available.

OLLAMA_DEFAULT_CATALOG: List[CatalogEntry] = [
    CatalogEntry(
        provider="ollama", name="qwen3.6:latest",
        content=10, structured_content=10, vision=10,
        context_window=256000, size_gb=24.0,
        description="Qwen3.6 multimodal — strong content + vision, default content model",
        default_active=True,
        badges=["default"],
    ),
    CatalogEntry(
        provider="ollama", name="qwen3-embedding:0.6b",
        embeddings=10,
        context_window=32000, size_gb=0.6,
        description="Qwen3 embeddings, 0.6B — top of MTEB multilingual leaderboard",
        default_active=True,
        badges=["default", "embeddings"],
    ),
    CatalogEntry(
        provider="ollama", name="nomic-embed-text",
        embeddings=8,
        context_window=8192, size_gb=0.27,
        description="Nomic text embeddings — small, fast",
        default_active=True,
        badges=["default", "embeddings"],
    ),
]


# Removed entries (llama3.3, llama3.2, mistral-small, phi4, qwen3.6:7b,
# deepseek-r1, mxbai-embed-large) — superseded by the live
# ``ollama.com/library`` scrape used by the wizard's catalog
# multiselect. They never sat in ``default_active``, so removing them
# only affects the (rare) scrape-failure fallback path.


# ─── Convenience accessors ───────────────────────────────────────────

def cloud_entries(provider: str) -> List[CatalogEntry]:
    """All cloud catalog rows for the given provider."""
    p = provider.lower()
    return [e for e in CLOUD_CATALOG if e.provider == p]


def ollama_entries() -> List[CatalogEntry]:
    """All Ollama catalog rows (default + opt-in)."""
    return list(OLLAMA_DEFAULT_CATALOG)


def default_active_names(provider: str) -> List[str]:
    """Names whose ``default_active=True`` for the given provider —
    used as the pre-checked set on first wizard visit.
    """
    p = provider.lower()
    pool: List[CatalogEntry] = (
        OLLAMA_DEFAULT_CATALOG if p == "ollama" else CLOUD_CATALOG
    )
    return [e.name for e in pool if e.provider == p and e.default_active]


def all_catalog_entries() -> List[CatalogEntry]:
    """Every entry — cloud + Ollama. Used by ``llm-catalog-init``'s
    UPSERT loop.
    """
    return list(CLOUD_CATALOG) + list(OLLAMA_DEFAULT_CATALOG)
