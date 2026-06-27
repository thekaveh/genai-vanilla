"""
Curated LLM catalog — single source of truth for what models the stack
knows about.

Three consumers import this module:

  • The wizard step builder (cloud + Ollama multi-select option lists).
  • ``model_resolver`` (computes the active model set from YAML catalogs
    + env; consumed by ``litellm-init`` and ``ollama-pull``).
  • ``litellm-init`` (renders ``volumes/litellm/config.yaml`` via
    ``model_resolver.active_models()`` — no DB query involved. Catalog
    capability metadata (content / structured_content / vision /
    embeddings) is consumed by the wizard and backend,
    NOT by litellm-init at config-render time).

Catalog data lives in YAML files rather than in this module:

  • ``services/ollama/models.yaml``  — flat-sections format
    (sections: content | embeddings | vision)
  • ``services/litellm/models.yaml`` — provider-keyed format
    (top-level keys: openai | anthropic | openrouter; each value is
    a section map)

Path resolution (host vs container):
  1. ``ATLAS_MODELS_DIR`` env var, if set.
  2. ``<repo_root>/services`` (detected as three parents above this file:
     bootstrapper/utils/llm_catalog.py → bootstrapper/utils → bootstrapper
     → repo_root; then repo_root/services).
  3. ``/catalog`` (container bind-mount target).

After loading, the module exposes the same public API as the former
hardcoded version:

  • ``CLOUD_CATALOG``          — list of CatalogEntry for cloud providers
  • ``OLLAMA_DEFAULT_CATALOG`` — list of CatalogEntry for ollama
  • ``cloud_entries(provider)``
  • ``ollama_entries()``
  • ``default_active_names(provider)``
  • ``all_catalog_entries()``

To add a model: add an entry to the relevant YAML file.
To remove one: delete the entry (it stays in DB row history but won't
be re-UPSERTed).

Maintenance cadence
-------------------
Cloud-provider catalogs drift faster than the rest of the codebase.
Suggested cadence:

  • **Quarterly** (or whenever a major release lands): refresh the
    YAML files to add new flagship models and update ``default: true``
    so first-run wizard users get the current sensible defaults.
  • **Every 6 months**: prune deprecated entries.
  • **Ollama**: only the ``OLLAMA_DEFAULT_CATALOG`` trio needs upkeep
    (the wizard's catalog multiselect goes via the live
    ``ollama.com/library`` scrape). Update when one of the three is
    superseded by a clearly better default.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


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
    # Output vector dimension for embedding models (None = unknown / N/A,
    # e.g. content/vision models or live-scraped models with no declared dim).
    # Sourced from the YAML ``dim:`` field; consumed by
    # ``model_resolver.dim_for_model_id`` to match the consumer's required
    # dimension (see ``model_resolver.MEMORY_FACTS_EMBEDDING_DIM``).
    dim: int | None = None


# ─── YAML loader ─────────────────────────────────────────────────────


def _find_models_dir() -> Path:
    """Resolve the directory that contains ollama/models.yaml (or
    ollama-models.yaml) and litellm/models.yaml (or litellm-models.yaml).

    Search order:
      1. ATLAS_MODELS_DIR env var
      2. <repo_root>/services  (repo_root = 3 parents above this file)
      3. /catalog              (container bind-mount target)
    """
    env_dir = os.environ.get("ATLAS_MODELS_DIR")
    if env_dir:
        return Path(env_dir)

    # bootstrapper/utils/llm_catalog.py  → parent = utils/ → parent = bootstrapper/
    # → parent = repo_root
    repo_root = Path(__file__).resolve().parent.parent.parent
    candidates = [repo_root / "services", Path("/catalog")]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate

    raise FileNotFoundError(
        "Cannot locate models directory. Tried: "
        + str([str(c) for c in candidates])
        + ". Set ATLAS_MODELS_DIR to override."
    )


def _find_yaml(base_dir: Path, service: str) -> Path:
    """Try <base_dir>/<service>/models.yaml then <base_dir>/<service>-models.yaml."""
    primary = base_dir / service / "models.yaml"
    if primary.exists():
        return primary
    fallback = base_dir / f"{service}-models.yaml"
    if fallback.exists():
        return fallback
    raise FileNotFoundError(
        f"Cannot find models YAML for '{service}'. "
        f"Tried: {primary}, {fallback}"
    )


def _parse_section(
    entries_raw: list,
    section: str,
    provider: str,
) -> List[Tuple[str, Dict]]:
    """Parse one YAML section list into (key, attrs) tuples where key = (provider, name).

    Priority = len(section) - position_index so the first entry is highest.
    Returns list of (key, attrs_dict) preserving order.
    """
    n = len(entries_raw)
    results = []
    for idx, raw in enumerate(entries_raw):
        name = raw["name"]
        priority = n - idx
        results.append(((provider, name), {
            "section": section,
            "priority": priority,
            "description": raw.get("description", ""),
            "badges": raw.get("badges", []),
            "default_active": raw.get("default", False),
            "dim": raw.get("dim"),
        }))
    return results


def _build_entries(
    section_tuples: List[Tuple[str, Dict]],
) -> List[CatalogEntry]:
    """Merge per-section tuples into CatalogEntry objects (one per (provider, name)).

    When a model appears in multiple sections (e.g. content + vision), the
    fields for each section are SET to the computed priority; description /
    badges / default_active come from the first non-empty occurrence.
    """
    # Ordered dict: (provider, name) → mutable dict of accumulated state
    merged: Dict[Tuple[str, str], dict] = {}

    for (prov, name), attrs in section_tuples:
        key = (prov, name)
        section = attrs["section"]
        priority = attrs["priority"]

        if key not in merged:
            merged[key] = {
                "provider": prov,
                "name": name,
                "content": 0,
                "structured_content": 0,
                "vision": 0,
                "embeddings": 0,
                "description": "",
                "badges": [],
                "default_active": False,
                "dim": None,
            }

        state = merged[key]

        # Set capability for this section
        if section == "content":
            state["content"] = priority
            state["structured_content"] = priority
        elif section == "vision":
            state["vision"] = priority
        elif section == "embeddings":
            state["embeddings"] = priority

        # Take description / badges / default_active / dim from first occurrence
        if not state["description"] and attrs["description"]:
            state["description"] = attrs["description"]
        if not state["badges"] and attrs["badges"]:
            state["badges"] = list(attrs["badges"])
        if not state["default_active"] and attrs["default_active"]:
            state["default_active"] = attrs["default_active"]
        if state["dim"] is None and attrs.get("dim") is not None:
            state["dim"] = attrs["dim"]

    entries = []
    for state in merged.values():
        entries.append(CatalogEntry(
            provider=state["provider"],
            name=state["name"],
            content=state["content"],
            structured_content=state["structured_content"],
            vision=state["vision"],
            embeddings=state["embeddings"],
            context_window=0,
            size_gb=None,
            description=state["description"],
            default_active=state["default_active"],
            badges=list(state["badges"]),
            dim=state["dim"],
        ))
    return entries


def _load_ollama_catalog(models_dir: Path) -> List[CatalogEntry]:
    """Load services/ollama/models.yaml (flat-sections format)."""
    path = _find_yaml(models_dir, "ollama")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    section_tuples: List[Tuple[str, Dict]] = []
    for section in ("content", "embeddings", "vision"):
        raw_entries = data.get(section, [])
        if raw_entries:
            section_tuples.extend(_parse_section(raw_entries, section, "ollama"))

    return _build_entries(section_tuples)


def _load_cloud_catalog(models_dir: Path) -> List[CatalogEntry]:
    """Load services/litellm/models.yaml (provider-keyed format)."""
    path = _find_yaml(models_dir, "litellm")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    all_entries: List[CatalogEntry] = []

    for provider_key, section_map in data.items():
        section_tuples: List[Tuple[str, Dict]] = []
        for section in ("content", "embeddings", "vision"):
            raw_entries = section_map.get(section, [])
            if raw_entries:
                section_tuples.extend(
                    _parse_section(raw_entries, section, provider_key)
                )
        all_entries.extend(_build_entries(section_tuples))

    return all_entries


def _load_catalogs() -> tuple[List[CatalogEntry], List[CatalogEntry]]:
    """Load both YAML files and return (cloud_entries, ollama_entries)."""
    models_dir = _find_models_dir()
    ollama = _load_ollama_catalog(models_dir)
    cloud = _load_cloud_catalog(models_dir)
    return cloud, ollama


# ─── Module-level catalog lists ──────────────────────────────────────
# Loaded once at import time. Both lists are populated from YAML.

CLOUD_CATALOG: List[CatalogEntry]
OLLAMA_DEFAULT_CATALOG: List[CatalogEntry]

CLOUD_CATALOG, OLLAMA_DEFAULT_CATALOG = _load_catalogs()


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
    """Every entry — cloud + Ollama. Used by ``model_resolver`` and
    the wizard step builder.
    """
    return list(CLOUD_CATALOG) + list(OLLAMA_DEFAULT_CATALOG)
