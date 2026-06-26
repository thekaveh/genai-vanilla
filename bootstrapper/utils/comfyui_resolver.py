"""
comfyui_resolver.py — DB-free active ComfyUI model set computation + manifest writer.

OVERVIEW
--------
This module is the host-side replacement for the activation logic that the
former ``comfyui-catalog-init``'s ``sync-catalog.py`` performed against
``public.comfyui_models``.  Instead of UPSERTing into Postgres and then
running UPDATE queries to toggle ``active`` flags, it computes the active
set purely from:

  • the curated + live catalog (loaded by ``utils.comfyui_library``)
  • the sidecar YAML (``services/comfyui/custom-models.yaml`` or the path
    in ``COMFYUI_CUSTOM_MODELS_FILE``)
  • env vars (``COMFYUI_USER_MODELS``, ``COMFYUI_CUSTOM_MODELS_FILE``)

This makes the "which models are active?" decision available to:
  • **comfyui-init** (C3) — reads the manifest YAML to know what to download
  • **the backend GET /comfyui/db/models** (C4) — reads the manifest to serve
    the active-model list to Open WebUI / n8n / the frontend

No DB, no Docker stack, and no running container is required.

ACTIVATION RULES  (replicate sync-catalog.py DB-write logic, DB-free)
----------------------------------------------------------------------
1.  Sidecar entries (``load_custom_models(sidecar_path)``) are **ALWAYS**
    active, regardless of ``COMFYUI_USER_MODELS``.  They represent the
    operator's explicit custom additions.

2.  **Non-empty ``COMFYUI_USER_MODELS`` (CSV):**
    Activate exactly the catalog entries whose name appears in the CSV,
    PLUS the sidecar.  Names not found in the catalog or sidecar are
    silently dropped with a stderr warning (can't download without metadata
    — no URL, no filename, no target_dir).  All other catalog entries are
    inactive.

3.  **Empty ``COMFYUI_USER_MODELS``:**
    Activate the catalog entries whose ``essential=True`` PLUS the sidecar.
    This is the DB-free equivalent of sync-catalog's "keep existing actives"
    path on a **fresh deployment** — where the DB has no pre-existing state,
    the essential entries are the safe minimal default set that keeps
    seeded workflows and backend defaults functional.

Deduplication: sidecar wins over catalog on name collision (sidecar is
user-authoritative).  Within-catalog and within-sidecar names are assumed
unique (assemble_wizard_catalog guarantees this via _dedupe_by_name).

Ordering: catalog entries in catalog order, sidecar entries appended after.

MANIFEST FORMAT  (what comfyui-init + backend GET read)
-------------------------------------------------------
``manifest_dict()`` returns a dict ``{"models": [ ... ]}`` where each entry
maps ``ComfyUILibraryEntry`` fields to the column names the DB + downloader
expect:

  ComfyUILibraryEntry field   →   manifest key
  ─────────────────────────────────────────────
  .category                   →   type
  .url                        →   download_url
  .size_gb                    →   file_size_gb
  .notes                      →   description
  (all other fields)          →   same name

Additionally ``active=True`` and ``essential=False`` are always written
(every row in the manifest IS active by definition; essential is a catalog
attribute, not a manifest attribute).

``filename`` is derived from ``entry.filename`` if present, else from the
URL path (strips query strings; falls back to ``"model.bin"``).

Schema: ``bootstrapper/schemas/comfyui-manifest.schema.json``.

IMPORTANT DIVERGENCE FROM sync-catalog.py
------------------------------------------
When ``COMFYUI_USER_MODELS`` is empty, sync-catalog.py **preserved** the
DB's existing active flags (no UPDATE was issued).  Here there is no DB to
read, so the fresh-deployment equivalent is to activate the catalog's
``essential=True`` entries.  Callers MUST NOT treat ``active_comfyui_models``
as a mirror of a running stack's persisted DB state.
"""
from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlparse

import yaml

# Container-safe dual-mode import.
#
# This module is consumed in two contexts:
#   1. Bootstrapper venv (host): ``bootstrapper/utils/`` is a proper Python
#      package, so ``from utils import comfyui_library`` works fine.
#   2. comfyui-init container: ``bootstrapper/utils/`` is bind-mounted as
#      ``/catalog`` and scripts import modules LOOSE (no ``utils`` package).
#      In that context ``from utils import comfyui_library`` raises ImportError
#      because there is no ``utils`` package on sys.path.  The fallback handles
#      this case.
try:                                    # bootstrapper venv (package context)
    from utils import comfyui_library
    from utils.comfyui_library import ComfyUILibraryEntry
except ImportError:                     # container /catalog (loose modules)
    import comfyui_library  # type: ignore[no-redef]
    from comfyui_library import ComfyUILibraryEntry  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default sidecar path inside the comfyui-init container
#: (bind-mounted from ``services/comfyui/custom-models.yaml``).
_DEFAULT_SIDECAR_PATH = "/custom-models.yaml"


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _csv(val: str | None) -> list[str]:
    """Split a comma-separated string into a list of non-empty stripped tokens."""
    if not val:
        return []
    return [s.strip() for s in val.split(",") if s.strip()]


def _filename_from_url(url: str) -> str:
    """Extract a filename from a URL.

    Strips query strings (civitai uses ``?token=…``).  Falls back to
    ``"model.bin"`` if the URL has no path component with a filename.
    """
    path = urlparse(url).path
    bare = path.rsplit("/", 1)[-1].split("?", 1)[0]
    return bare or "model.bin"


def _derive_filename(entry: ComfyUILibraryEntry) -> str:
    """Return the on-disk filename for an entry.

    Prefers ``entry.filename`` (explicitly declared in the catalog for civitai
    entries whose URL path has no real filename) over a URL-derived name.
    """
    return entry.filename or _filename_from_url(entry.url)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def active_comfyui_models(
    env: Mapping[str, str],
    *,
    catalog: list[ComfyUILibraryEntry] | None = None,
    sidecar_path: str | None = None,
) -> list[ComfyUILibraryEntry]:
    """Return the active ComfyUI entries (with full metadata) for the given env.

    Replicates ``sync-catalog.py``'s activation logic DB-free:

    * **Sidecar entries** (``load_custom_models(sidecar_path or
      COMFYUI_CUSTOM_MODELS_FILE)``) are **ALWAYS** active.

    * **Non-empty ``COMFYUI_USER_MODELS`` (CSV):** activate exactly those
      named entries from the catalog PLUS the sidecar.  Names not found in
      the catalog or sidecar are dropped with a stderr warning.

    * **Empty ``COMFYUI_USER_MODELS``:** activate the catalog's
      ``essential=True`` entries PLUS the sidecar.  This is the DB-free
      equivalent of sync-catalog's "keep existing/essential" behaviour on a
      fresh deployment (where the DB holds no pre-existing active state).

    Deduplication: sidecar wins over catalog on name collision.
    Ordering: catalog entries in catalog order, sidecar appended after.

    Args:
        env: Mapping of env var names → string values.  Missing keys are
            treated as empty strings ("not set").  Reads:
            ``COMFYUI_USER_MODELS`` (CSV of model names to activate),
            ``COMFYUI_CUSTOM_MODELS_FILE`` (path to the sidecar YAML).
        catalog: Optional pre-assembled catalog list.  When ``None`` the
            live ``comfyui_library.assemble_wizard_catalog()`` is called.
            **Pass a synthetic list in tests to avoid the live scrape.**
        sidecar_path: Path to the sidecar YAML.  When ``None`` falls back to
            ``env.get("COMFYUI_CUSTOM_MODELS_FILE")`` and then to
            ``/custom-models.yaml`` (container default).

    Returns:
        Ordered list of active ``ComfyUILibraryEntry`` objects.  May be
        empty when the catalog is empty and the sidecar is absent/empty.
    """
    # ── 1. Resolve sidecar path ──────────────────────────────────────────
    if sidecar_path is None:
        sidecar_path = env.get(
            "COMFYUI_CUSTOM_MODELS_FILE", _DEFAULT_SIDECAR_PATH
        )

    # ── 2. Load sidecar (always active) ─────────────────────────────────
    sidecar_entries: list[ComfyUILibraryEntry] = comfyui_library.load_custom_models(
        sidecar_path
    )
    sidecar_by_name: dict[str, ComfyUILibraryEntry] = {
        e.name: e for e in sidecar_entries
    }

    # ── 3. Resolve catalog ───────────────────────────────────────────────
    if catalog is None:
        catalog = comfyui_library.assemble_wizard_catalog()

    # ── 4. Parse COMFYUI_USER_MODELS ────────────────────────────────────
    user_models: list[str] = _csv(env.get("COMFYUI_USER_MODELS", ""))

    # ── 5. Determine active catalog entries ─────────────────────────────
    # Build a name→entry index from the catalog (sidecar wins on collision,
    # so we exclude sidecar names here and append sidecar after).
    catalog_by_name: dict[str, ComfyUILibraryEntry] = {
        e.name: e for e in catalog if e.name not in sidecar_by_name
    }

    if user_models:
        # Non-empty CSV: activate exactly the named entries in CATALOG ORDER
        # (stable, regardless of CSV order) — see module docstring.
        # Names not in either catalog or sidecar are dropped with a warning.
        user_model_set = set(user_models)
        # Warn about names absent from both catalog and sidecar.
        for name in user_models:
            if name not in catalog_by_name and name not in sidecar_by_name:
                print(
                    f"⚠️  COMFYUI_USER_MODELS entry '{name}' not found in "
                    "catalog or sidecar — skipping (no download metadata).",
                    file=sys.stderr,
                    flush=True,
                )
        # Preserve catalog order (iterate catalog, keep only those in the set).
        active_catalog: list[ComfyUILibraryEntry] = [
            e for e in catalog
            if e.name in user_model_set and e.name not in sidecar_by_name
        ]
    else:
        # Empty CSV: activate essential entries.
        active_catalog = [
            e for e in catalog
            if e.essential and e.name not in sidecar_by_name
        ]

    # ── 6. Deduplicate + assemble final list (catalog order, sidecar last) ──
    # Preserve the relative order of active_catalog, then append sidecar.
    result: list[ComfyUILibraryEntry] = []
    seen_names: set[str] = set()
    for entry in active_catalog:
        if entry.name not in seen_names:
            result.append(entry)
            seen_names.add(entry.name)
    for entry in sidecar_entries:
        if entry.name not in seen_names:
            result.append(entry)
            seen_names.add(entry.name)

    return result


def manifest_dict(entries: list[ComfyUILibraryEntry]) -> dict:
    """Build the manifest dict from a list of active entries.

    Returns ``{"models": [ ... ]}`` where each entry maps
    ``ComfyUILibraryEntry`` fields to the names that:
      • ``comfyui-init``'s ``download_models.sh`` reads:
        ``name``, ``type``, ``filename``, ``download_url``, ``sha256``
      • the backend's ``GET /comfyui/db/models`` returns as JSON:
        the full set of columns below

    Field mapping (ComfyUILibraryEntry → manifest key):
      .category          → type
      .url               → download_url
      .size_gb           → file_size_gb
      .notes             → description
      (all others)       → same name

    ``active=True`` and ``essential=False`` are always written:
    every row in the manifest IS active by definition; the manifest is
    the active set, not the full catalog.

    ``filename`` is derived from ``entry.filename`` if present, else
    from the URL path (strips query strings; fallback ``"model.bin"``).

    Args:
        entries: Ordered list of active ``ComfyUILibraryEntry`` objects,
            as returned by ``active_comfyui_models()``.

    Returns:
        Dict with a single ``"models"`` key whose value is a list of
        manifest entry dicts.  Validates against
        ``bootstrapper/schemas/comfyui-manifest.schema.json``.
    """
    rows = []
    for e in entries:
        rows.append({
            "name":                 e.name,
            "type":                 e.category,          # category → type
            "filename":             _derive_filename(e),
            "download_url":         e.url,               # url → download_url
            "sha256":               e.sha256,
            "file_size_gb":         float(e.size_gb) if e.size_gb is not None else None,  # size_gb → file_size_gb
            "family":               e.family,
            "target_dir":           e.target_dir,
            "min_vram_gb":          float(e.min_vram_gb) if e.min_vram_gb is not None else None,
            "cpu_supported":        bool(e.cpu_supported),
            "requires_custom_node": list(e.requires_custom_node),
            "popularity":           int(e.popularity or 0),
            "source":               e.source,
            "active":               True,
            "essential":            False,
            "description":          e.notes,             # notes → description
        })
    return {"models": rows}


def write_manifest(entries: list[ComfyUILibraryEntry], path: str) -> None:
    """Write ``manifest_dict(entries)`` as YAML to ``path``.

    Creates parent directories if they do not exist.  The YAML is written
    atomically via a temporary file and os.replace() (no partial writes).

    Args:
        entries: Active model entries, as returned by ``active_comfyui_models()``.
        path: Absolute or relative path for the output YAML file.
    """
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = manifest_dict(entries)
    yaml_content = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)

    fd, tmp = tempfile.mkstemp(dir=str(out_path.parent), prefix=out_path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(yaml_content)
        os.replace(tmp, str(out_path))
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
