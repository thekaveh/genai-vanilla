"""Resolve COMFYUI_USER_MODELS CSV + sidecar entries into a denormalized
JSON snapshot for the comfyui-init container.

Called from start.py right after apply_user_model_selections(); the
container picks up the file via bind-mount at /catalog-snapshot.json.

Schema (denormalized — init reader doesn't need wizard-side metadata):
    {
      "schema_version": 1,
      "generated_at": "ISO-Z timestamp",
      "entries": [
        {
          "name": "...",
          "url": "...",
          "target_dir": "...",
          "filename": "...",
          "size_gb": float,
          "sha256": str | null
        },
        ...
      ]
    }
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

from utils.comfyui_library import ComfyUILibraryEntry


_SCHEMA_VERSION = 1


def _filename_from_url(url: str) -> str:
    """Extract a filename from a URL. Handles query strings (civitai's
    `?token=...`) by stripping at `?`. Falls back to `model.bin` if the
    URL has no path component."""
    path = urlparse(url).path
    bare = path.rsplit("/", 1)[-1]
    return bare or "model.bin"


def _entry_to_snapshot_dict(e: ComfyUILibraryEntry) -> dict:
    """Translate to the init-script's minimal contract. NOT a general-purpose
    dataclass-to-dict — intentionally omits popularity, min_vram_gb, etc."""
    return {
        "name": e.name,
        "url": e.url,
        "target_dir": e.target_dir,
        "filename": _filename_from_url(e.url),
        "size_gb": e.size_gb,
        "sha256": e.sha256,
    }


def write_snapshot(
    selection_csv: str,
    catalog: Iterable[ComfyUILibraryEntry],
    sidecar_entries: Iterable[ComfyUILibraryEntry],
    out_path: Path,
) -> None:
    """Write the snapshot JSON.

    Args:
        selection_csv: comma-separated catalog names from COMFYUI_USER_MODELS.
            Empty string → no catalog entries included.
        catalog: full catalog from list_catalog(). Names from selection_csv
            that don't resolve here are skipped with stderr warning.
        sidecar_entries: from load_custom_models(). ALWAYS included
            (independent of selection_csv — the sidecar IS the user's
            explicit picks for custom models).
        out_path: target file. Parent directories created as needed.
    """
    catalog_by_name = {e.name: e for e in catalog}
    selected: list[ComfyUILibraryEntry] = []

    csv = selection_csv.strip()
    for raw_name in (n.strip() for n in csv.split(",") if n.strip()):
        if raw_name in catalog_by_name:
            selected.append(catalog_by_name[raw_name])
        else:
            print(
                f"⚠️  COMFYUI_USER_MODELS entry '{raw_name}' not in catalog; "
                f"skipping (run wizard to browse available names).",
                file=sys.stderr,
            )

    selected.extend(sidecar_entries)

    payload = {
        "schema_version": _SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "entries": [_entry_to_snapshot_dict(e) for e in selected],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2))
