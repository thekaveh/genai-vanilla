"""
model_resolver.py — DB-free active-model set computation and convention winner picker.

OVERVIEW
--------
This module is the host-side replacement for the activation+ranking logic that
the former ``sync-catalog.py`` + the former ``public.llms`` DB ``ORDER BY`` performed at
container-init time. Instead of querying Postgres, it drives model selection
purely from:
  • the curated YAML catalogs (loaded by ``utils.llm_catalog``)
  • env vars (selection knobs the user sets via the wizard or ``.env``)
  • an optional ``ollama_tags`` argument for host-side auto-discovered models

This makes the three "which model should I use for role X?" decisions available
to the bootstrapper, wizard, and env_assembler without requiring a running DB or
Docker stack — enabling compile-time defaults (e.g. ``.env.example`` values)
and single-source-of-truth answers before any container is up.

IMPORTANT DIVERGENCE FROM THE FORMER sync-catalog.py
------------------------------------------------------
When a provider's ``*_USER_MODELS`` is empty, this module ALWAYS falls back to
the catalog's ``default_active=True`` names. The former ``sync-catalog.py`` instead preserved
whatever rows were already active in the database on a re-run. That distinction
is moot here (there is no DB to preserve state) and is correct for bootstrap,
wizard, and ``.env.example`` generation, but callers must NOT treat
``active_models()`` as a mirror of a running stack's persisted DB state.

ACTIVATION RULES
----------------
These replicate the former ``sync-catalog.py``'s DB-write logic without touching the DB:

Ollama (provider ``'ollama'``):
  1. ``LLM_PROVIDER_SOURCE`` must start with ``'ollama-'`` (i.e. not ``'none'``
     or ``'disabled'``) — otherwise no ollama models are active.
  2. Base name set = ``OLLAMA_USER_MODELS`` (CSV) if non-empty, else the
     catalog's ``default_active=True`` ollama names.
  3. If ``ollama_tags`` is provided (host-side auto-import), union them in.
  4. Union ``OLLAMA_CUSTOM_MODELS`` (CSV).
  5. Catalog entries whose name is in the set are included (in catalog order).
     Any active name NOT in the catalog gets a synthesized ``CatalogEntry``
     with generic ``content=8`` defaults (appended after catalog entries).

Cloud (each provider in ``CLOUD_PROVIDERS``, in canonical order):
  1. Must be both enabled (``LITELLM_<PROV>_ENABLED=true``) and keyed
     (``<PROV>_API_KEY`` non-empty) — otherwise provider produces no actives.
  2. Name set = ``<PROV>_USER_MODELS`` (CSV) if non-empty, else the
     catalog's ``default_active=True`` names for that provider.
  3. Catalog entries whose name is in the set are included (in catalog order).
     Any selected name NOT in the catalog gets a synthesized entry (content=8).

ORDERING = PRIORITY
-------------------
``active_models()`` returns entries in a STABLE priority order:
  ollama catalog entries (catalog order) → ollama synthesized
  → openai catalog → openai synthesized
  → anthropic catalog → anthropic synthesized
  → openrouter catalog → openrouter synthesized

This order is used directly by ``best()``: the FIRST entry with the requested
capability > 0 wins. With the default config (ollama-container-cpu, no cloud
keys), this yields ``ollama/qwen3.6:latest`` for both content and vision.

EMBEDDING CARVE-OUT
-------------------
``best('embeddings', ...)`` EXISTS in this module (it's needed for the B3
wizard step and B4's model picker). However, ``resolved_defaults()`` deliberately
EXCLUDES ``LITELLM_EMBEDDING_MODEL`` from its return value.

Rationale: ``LITELLM_EMBEDDING_MODEL`` defaults to ``ollama/nomic-embed-text``
(768-dim), which matches the ``public.memory_facts.embedding vector(768)``
pgvector column used by the backend's memory fallback. Switching to a
different-dimension embedding model (e.g. qwen3-embedding:0.6b at 1536 dims)
would silently break all existing embedding storage. Therefore that var stays
an explicit static default in ``services/litellm/service.yml``; the resolver
never overrides it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Optional

# Container-safe dual-mode import.
#
# This module is consumed in two contexts:
#   1. Bootstrapper venv (host): `bootstrapper/utils/` is a proper Python
#      package, so `from utils import llm_catalog` resolves against the
#      package's __init__ and works fine.
#   2. litellm-init container: `bootstrapper/utils/` is bind-mounted as
#      `/catalog` and the scripts import modules LOOSE (no `utils` package).
#      In that context `from utils import llm_catalog` raises ImportError
#      because there is no `utils` package on sys.path — only the bare
#      `/catalog` directory. The fallback branch handles this case.
try:                                   # bootstrapper venv (package context)
    from utils import llm_catalog
    from utils.llm_catalog import CatalogEntry
    from utils.cloud_providers import CLOUD_PROVIDERS
except ImportError:                    # container /catalog (loose modules)
    import llm_catalog  # type: ignore[no-redef]
    from llm_catalog import CatalogEntry  # type: ignore[no-redef]
    from cloud_providers import CLOUD_PROVIDERS  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Local helpers — mirror the former sync-catalog.py with safe extensions
# ---------------------------------------------------------------------------

def _truthy(val: str | None) -> bool:
    """Accepts a conservative superset of the former sync-catalog.py's truthy set (adds 'on');
    harmless since no env var uses other spellings."""
    return (val or "").strip().lower() in ("true", "1", "yes", "on", "enabled")


def _csv(val: str | None) -> list[str]:
    """Split a comma-separated string into a list of non-empty stripped tokens."""
    if not val:
        return []
    return [s.strip() for s in val.split(",") if s.strip()]


# ---------------------------------------------------------------------------
# Synthesized-entry factory
# ---------------------------------------------------------------------------

def _synthesize(provider: str, name: str) -> CatalogEntry:
    """Create a minimal CatalogEntry for a model not in the curated catalog.

    Mirrors ``LIVE_DEFAULTS`` in the former sync-catalog.py: content=8, structured_content=5,
    vision/embeddings=0.  vision=0 is deliberately conservative — we cannot
    infer vision capability from a model name alone.
    """
    return CatalogEntry(
        provider=provider,
        name=name,
        content=8,
        structured_content=5,
        vision=0,
        embeddings=0,
        context_window=0,
        size_gb=None,
        description=f"Live-discovered/custom {provider} model (not in curated catalog)",
        default_active=False,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def active_models(
    env: Mapping[str, str],
    *,
    ollama_tags: Iterable[str] | None = None,
) -> list[CatalogEntry]:
    """Return the active catalog entries for the given env selection.

    Replicates the former sync-catalog.py's activation rules WITHOUT a DB (env is the
    persistent selection store). See module docstring for the full rule set.

    Args:
        env: A mapping of env var names to string values (e.g. os.environ or
            a dict from ``.env`` parsing). Missing keys are treated as empty
            strings (= "not set").
        ollama_tags: Optional list of model-tag strings returned by the
            Ollama ``/api/tags`` endpoint (host-side auto-import).  When
            provided, they are unioned into the Ollama active set.  Pass
            ``None`` (the default) to skip auto-import (e.g. container
            sources, tests without a live Ollama).

            Container vs. host source distinction: For container Ollama
            sources (``ollama-container-*``), pass ``ollama_tags=None``.
            Host ``/api/tags`` auto-import only applies to host-side sources
            (``ollama-localhost``) with ``OLLAMA_AUTO_IMPORT_LOCAL_MODELS=true``.
            The resolver does NOT gate on source type — it unions any tags
            it is given, so the caller is responsible for only passing tags
            for host-side sources.

    Returns:
        Ordered list of active CatalogEntry objects.  Order IS priority
        (see module docstring).  Empty list when nothing is enabled.
    """
    result: list[CatalogEntry] = []
    result.extend(_active_ollama(env, ollama_tags))
    for provider in CLOUD_PROVIDERS:
        result.extend(_active_cloud(env, provider))
    return result


def best(
    category: str,
    env: Mapping[str, str],
    *,
    ollama_tags: Iterable[str] | None = None,
) -> Optional[str]:
    """Return the litellm model-id of the highest-priority active model for
    the given capability category.

    Args:
        category: One of ``'content'``, ``'embeddings'``, ``'vision'``.
        env: Env var mapping (same as ``active_models``).
        ollama_tags: Optional Ollama auto-import tag list.

    Returns:
        The litellm model id string if a capable active model exists, else
        ``None``.

        Format:
          • Ollama models → ``'ollama/<name>'``
          • Cloud models  → bare ``name`` (matches litellm-init per-provider routing)
    """
    for entry in active_models(env, ollama_tags=ollama_tags):
        cap_value = getattr(entry, category, 0)
        if cap_value and cap_value > 0:
            if entry.provider == "ollama":
                return f"ollama/{entry.name}"
            return entry.name
    return None


def resolved_defaults(
    env: Mapping[str, str],
    *,
    ollama_tags: Iterable[str] | None = None,
) -> dict[str, str]:
    """Return the env-var overrides this resolver owns.

    Exactly two keys are returned:
      • ``LITELLM_DEFAULT_MODEL``  — best content-capable active model
      • ``LITELLM_VISION_MODEL``   — best vision-capable active model

    NOTE: ``LITELLM_EMBEDDING_MODEL`` is deliberately EXCLUDED.  Changing
    the embedding model changes the vector dimension, which would silently
    break the ``public.memory_facts.embedding vector(768)`` pgvector column
    in supabase-db.  That var stays a static explicit default in
    ``services/litellm/service.yml``.

    Args:
        env: Env var mapping.  Pass ``{}`` (empty dict) to get the
            template/default-config result — what ``.env.example`` should
            contain when no cloud keys are set.
        ollama_tags: Optional Ollama auto-import tag list.

    Returns:
        Dict with exactly the two keys above.  Values are empty strings when
        no capable active model exists (e.g. all providers disabled).
    """
    return {
        "LITELLM_DEFAULT_MODEL": best("content", env, ollama_tags=ollama_tags) or "",
        "LITELLM_VISION_MODEL": best("vision", env, ollama_tags=ollama_tags) or "",
    }


# ---------------------------------------------------------------------------
# Private activation helpers
# ---------------------------------------------------------------------------

def _active_ollama(
    env: Mapping[str, str],
    ollama_tags: Iterable[str] | None,
) -> list[CatalogEntry]:
    """Compute the active Ollama entries per the activation rules."""
    source = env.get("LLM_PROVIDER_SOURCE", "ollama-container-cpu").strip().lower()

    # Disabled / none → no ollama actives
    if not source.startswith("ollama-"):
        return []

    # Base name set: explicit user selection or catalog defaults
    user_models = _csv(env.get("OLLAMA_USER_MODELS", ""))
    if user_models:
        active_names: set[str] = set(user_models)
    else:
        active_names = set(llm_catalog.default_active_names("ollama"))

    # Union host-side auto-import tags (only meaningful for ollama-localhost)
    if ollama_tags is not None:
        active_names.update(str(t).strip() for t in ollama_tags if str(t).strip())

    # Union custom models
    custom = _csv(env.get("OLLAMA_CUSTOM_MODELS", ""))
    active_names.update(custom)

    # Build result: catalog-ordered entries first, then synthesized
    catalog_entries = llm_catalog.ollama_entries()
    result: list[CatalogEntry] = []
    seen: set[str] = set()

    for entry in catalog_entries:
        if entry.name in active_names:
            result.append(entry)
            seen.add(entry.name)

    # Synthesize entries for active names not in the catalog
    for name in sorted(active_names - seen):  # sorted for stable ordering
        result.append(_synthesize("ollama", name))

    return result


def _active_cloud(
    env: Mapping[str, str],
    provider,  # CloudProvider dataclass
) -> list[CatalogEntry]:
    """Compute the active entries for one cloud provider."""
    enabled = _truthy(env.get(provider.enabled_flag_var, ""))
    has_key = bool((env.get(provider.api_key_var, "") or "").strip())

    if not (enabled and has_key):
        return []

    user_models = _csv(env.get(provider.user_models_var, ""))
    if user_models:
        active_names: set[str] = set(user_models)
    else:
        active_names = set(llm_catalog.default_active_names(provider.key))

    catalog_entries = llm_catalog.cloud_entries(provider.key)
    result: list[CatalogEntry] = []
    seen: set[str] = set()

    for entry in catalog_entries:
        if entry.name in active_names:
            result.append(entry)
            seen.add(entry.name)

    # Synthesize entries for selected names not in the catalog
    for name in sorted(active_names - seen):
        result.append(_synthesize(provider.key, name))

    return result
