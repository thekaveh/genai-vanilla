#!/usr/bin/env python3
"""
sync-catalog.py — UPSERT the ComfyUI model catalog into
``public.comfyui_models`` and apply the user's wizard / .env-driven
model selections + sidecar YAML.

Runs once per ``docker compose up`` between ``supabase-db-init`` and
``comfyui-init`` (which queries the table for the active download set).
Mirrors ``services/litellm/catalog-init/scripts/sync-catalog.py``.

Behavior:
  1. Connect to Postgres (retry until supabase-db-init is done).
  2. Import the catalog module (bind-mounted at
     /catalog/comfyui_library.py; sibling of /scripts to avoid
     file-on-dir overlay edge cases — same convention as
     llm-catalog-init).
  3. Assemble the live catalog: HF + civitai scrape, partial-failure
     tolerant, with bundled fallback if both APIs are down + the
     curated allowlist always merged in last.
  4. UPSERT every assembled entry into public.comfyui_models. Conflict
     on (name, type) refreshes immutable model facts (url, filename,
     size, sha256, target_dir, capability flags) but preserves the
     existing ``active`` flag (so wizard / psql edits survive a re-run)
     and the existing ``description`` (so hand-edited notes aren't
     clobbered).
  5. UPSERT every entry from the sidecar YAML
     (COMFYUI_CUSTOM_MODELS_FILE, default /custom-models.yaml) with
     source='custom' and active=true.
  6. Apply COMFYUI_USER_MODELS activation: parse the CSV; UPDATE
     active=true for those names; UPDATE active=false for everything
     else EXCEPT custom rows (which the sidecar keeps active by
     definition). An empty CSV leaves existing actives alone — same
     "no override → keep state" semantics as llm-catalog-init's
     cloud-selection path. Custom rows always stay active.
  7. Commit transaction.

Catalog rows that get removed from comfyui_library.py flow through
on re-runs: they simply stop being UPSERTed. Operators can ``DELETE``
manually for a clean table.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import time
import traceback
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_batch, Json


# ─── env / config ─────────────────────────────────────────────────────

PG_HOST = os.environ.get("PGHOST", "supabase-db")
PG_PORT = int(os.environ.get("PGPORT", "5432"))
PG_DB = os.environ.get("PGDATABASE", "postgres")
PG_USER = os.environ.get("PGUSER", "postgres")
PG_PASSWORD = os.environ.get("PGPASSWORD", "")

COMFYUI_USER_MODELS = os.environ.get("COMFYUI_USER_MODELS", "")
COMFYUI_CUSTOM_MODELS_FILE = os.environ.get(
    "COMFYUI_CUSTOM_MODELS_FILE", "/custom-models.yaml"
)


def _csv(v: str | None) -> list[str]:
    if not v:
        return []
    return [s.strip() for s in v.split(",") if s.strip()]


# ─── catalog import ───────────────────────────────────────────────────

def _import_from(path: Path, mod_name: str):
    """Import a single file as a module. Used for the bind-mounted
    bootstrapper/utils/*.py files at /catalog/. Registers in sys.modules
    BEFORE exec_module so ``@dataclass(frozen=True)`` works on Python
    3.12 (mirrors the workaround in llm-catalog-init's load_catalog).
    """
    if not path.exists():
        sys.exit(
            f"❌ {path} not found — is the bootstrapper/utils bind mount "
            f"configured? Check services/comfyui/compose.yml's "
            f"comfyui-catalog-init service."
        )
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def load_catalog():
    """Import bootstrapper/utils/comfyui_library.py from /catalog/."""
    return _import_from(Path("/catalog/comfyui_library.py"), "comfyui_library")


# ─── DB connection ────────────────────────────────────────────────────

def connect_with_retry(retries: int = 30, delay: float = 2.0):
    """Wait for supabase-db-init to finish before trying to UPSERT.

    Same retry envelope as llm-catalog-init (30 × 2 s = 60 s max).
    """
    last: Exception | None = None
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(
                host=PG_HOST, port=PG_PORT, dbname=PG_DB,
                user=PG_USER, password=PG_PASSWORD, connect_timeout=5,
            )
            conn.autocommit = False
            return conn
        except psycopg2.Error as e:
            last = e
            print(f"  ↳ DB not ready (attempt {attempt + 1}/{retries}): {e}", flush=True)
            time.sleep(delay)
    sys.exit(f"❌ Could not connect to Postgres after {retries} attempts: {last}")


# ─── schema / constraint guard ────────────────────────────────────────

def verify_constraint(conn) -> None:
    """Pre-flight check — abort early if the (name, type) unique
    constraint is missing. Without it the ON CONFLICT clause in
    upsert_catalog() would fail with a cryptic error instead of
    pointing at the migration that should have run.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM pg_constraint
            WHERE conname = 'unique_comfyui_model_name'
              AND conrelid = 'public.comfyui_models'::regclass
            """
        )
        if cur.fetchone() is None:
            sys.exit(
                "❌ unique_comfyui_model_name constraint missing on "
                "public.comfyui_models — did "
                "supabase/db/scripts/05-public-tables.sql fail to run? "
                "Check supabase-db-init logs."
            )
    print(
        "  ↳ verified unique_comfyui_model_name constraint on public.comfyui_models",
        flush=True,
    )


# ─── filename derivation ──────────────────────────────────────────────

def _filename_from_url(url: str) -> str:
    """Extract a filename from a URL. Strips query strings (civitai uses
    ``?token=...``). Falls back to ``model.bin`` if the URL has no path
    component."""
    from urllib.parse import urlparse
    path = urlparse(url).path
    bare = path.rsplit("/", 1)[-1].split("?", 1)[0]
    return bare or "model.bin"


# ─── core sync logic ──────────────────────────────────────────────────

_UPSERT_SQL = """
INSERT INTO public.comfyui_models
  (name, type, filename, download_url, file_size_gb, description, active, essential,
   family, sha256, target_dir, min_vram_gb, cpu_supported,
   requires_custom_node, popularity, source)
VALUES
  (%s, %s, %s, %s, %s, %s, %s, %s,
   %s, %s, %s, %s, %s,
   %s, %s, %s)
ON CONFLICT ON CONSTRAINT unique_comfyui_model_name DO UPDATE SET
  filename             = EXCLUDED.filename,
  download_url         = EXCLUDED.download_url,
  file_size_gb         = EXCLUDED.file_size_gb,
  family               = EXCLUDED.family,
  sha256               = EXCLUDED.sha256,
  target_dir           = EXCLUDED.target_dir,
  min_vram_gb          = EXCLUDED.min_vram_gb,
  cpu_supported        = EXCLUDED.cpu_supported,
  requires_custom_node = EXCLUDED.requires_custom_node,
  popularity           = EXCLUDED.popularity,
  source               = EXCLUDED.source,
  updated_at           = now();
"""


def _entry_row(entry, default_active: bool):
    """Translate a ComfyUILibraryEntry to the UPSERT parameter tuple.
    ``default_active`` controls only the value used on first INSERT;
    on conflict the existing active flag is preserved (the ON CONFLICT
    clause above intentionally omits ``active``).
    """
    return (
        entry.name,
        entry.category,
        # Prefer the catalog-declared filename (civitai URLs carry no
        # usable path component — see ComfyUILibraryEntry.filename).
        getattr(entry, "filename", None) or _filename_from_url(entry.url),
        entry.url,
        float(entry.size_gb) if entry.size_gb is not None else None,
        entry.notes or "",
        default_active,
        False,  # essential — legacy column; default false for live catalog rows
        entry.family,
        entry.sha256,
        entry.target_dir,
        float(entry.min_vram_gb) if entry.min_vram_gb is not None else None,
        bool(entry.cpu_supported),
        Json(list(entry.requires_custom_node)),
        int(entry.popularity or 0),
        entry.source,
    )


def upsert_catalog(conn, catalog_module) -> list:
    """UPSERT every assembled catalog entry into public.comfyui_models.

    Returns the list of assembled entries so the caller can compute
    the activation set without re-scraping.
    """
    entries = catalog_module.assemble_wizard_catalog()
    rows = [_entry_row(e, default_active=False) for e in entries]
    with conn.cursor() as cur:
        execute_batch(cur, _UPSERT_SQL, rows)
    print(f"  ↳ UPSERTed {len(rows)} catalog rows", flush=True)
    return entries


def upsert_custom_sidecar(conn, catalog_module) -> list[str]:
    """Parse the sidecar YAML (COMFYUI_CUSTOM_MODELS_FILE) and UPSERT
    each entry with source='custom' + active=true. Returns the list of
    custom entry names so the activation step can keep them active.

    Missing file → empty list (silently). Sidecar errors are logged
    to stderr by load_custom_models itself.
    """
    sidecar_path = Path(COMFYUI_CUSTOM_MODELS_FILE)
    if not sidecar_path.is_file():
        print(
            f"  ↳ custom sidecar {sidecar_path} not present — skipping custom UPSERT",
            flush=True,
        )
        return []
    customs = catalog_module.load_custom_models(str(sidecar_path))
    if not customs:
        return []
    rows = [_entry_row(c, default_active=True) for c in customs]
    with conn.cursor() as cur:
        execute_batch(cur, _UPSERT_SQL, rows)
        # The UPSERT preserves existing active state on conflict, so
        # force active=true for the custom set explicitly.
        cur.execute(
            "UPDATE public.comfyui_models SET active = true, updated_at = now() "
            "WHERE name = ANY(%s) AND source = 'custom';",
            ([c.name for c in customs],),
        )
    print(f"  ↳ UPSERTed {len(customs)} custom (sidecar) row(s)", flush=True)
    return [c.name for c in customs]


def apply_user_models_selection(
    conn, user_models: list[str], custom_names: list[str]
) -> None:
    """Apply COMFYUI_USER_MODELS activation rules.

    Empty CSV:
      - Leave existing actives alone (mirrors apply_cloud_selection's
        "no override → keep state" path in llm-catalog-init).
      - Custom rows are already active=true from upsert_custom_sidecar.
    Non-empty CSV:
      - UPDATE active=true for names in the CSV.
      - UPDATE active=false for every other row EXCEPT custom rows.
    """
    with conn.cursor() as cur:
        if not user_models:
            cur.execute(
                "SELECT count(*) FROM public.comfyui_models WHERE active = true;"
            )
            (n_active,) = cur.fetchone()
            print(
                f"  ↳ COMFYUI_USER_MODELS empty — keeping {n_active} existing "
                f"active row(s) (+ {len(custom_names)} custom always-active)",
                flush=True,
            )
            return

        # Discover which user-requested names actually exist in the
        # catalog. ComfyUI can't auto-insert a row from just a name
        # (the catalog needs URL + target_dir + filename — none derivable
        # from a name alone), so unknown names are skipped with a loud
        # stderr warning so users notice typos.
        cur.execute(
            "SELECT name FROM public.comfyui_models WHERE name = ANY(%s);",
            (user_models,),
        )
        present = {r[0] for r in cur.fetchall()}
        # Include any sidecar customs as 'present' (they were just
        # upserted in upsert_custom_sidecar; the SELECT above sees them).
        # Any user-requested name not present is a typo / no-longer-in-catalog
        # name — warn but don't fail.
        missing = sorted(set(user_models) - present)
        if missing:
            print(
                "⚠️  COMFYUI_USER_MODELS entries not in catalog or sidecar; "
                f"skipping: {', '.join(missing)}",
                file=sys.stderr,
                flush=True,
            )

        # Activation below is NAME-keyed while uniqueness is (name, type):
        # a name that exists under two types would toggle both rows.
        # No catalog/sidecar name collides across types today — warn
        # loudly if that ever changes so the selection format can grow
        # a type qualifier before this becomes a real bug.
        cur.execute(
            "SELECT name FROM public.comfyui_models "
            "GROUP BY name HAVING count(DISTINCT type) > 1;"
        )
        collisions = [r[0] for r in cur.fetchall()]
        if collisions:
            print(
                "⚠️  comfyui-catalog: name(s) present under multiple types "
                f"(activation toggles all of them): {', '.join(collisions)}",
                file=sys.stderr, flush=True,
            )

        # Activate the matched-known subset.
        matched = sorted(set(user_models) & present)
        if matched:
            cur.execute(
                "UPDATE public.comfyui_models SET active = true, updated_at = now() "
                "WHERE name = ANY(%s);",
                (matched,),
            )
        # Deactivate everything else — but never deactivate the sidecar
        # customs (the sidecar IS the user's explicit pick for custom
        # models; falling out of the CSV is not the same as being
        # un-picked).
        keep_active = list(set(user_models) | set(custom_names))
        cur.execute(
            "UPDATE public.comfyui_models SET active = false, updated_at = now() "
            "WHERE name <> ALL(%s);",
            (keep_active,),
        )
        cur.execute(
            "SELECT count(*) FROM public.comfyui_models WHERE active = true;"
        )
        (n_active,) = cur.fetchone()
        print(
            f"  ↳ COMFYUI_USER_MODELS={len(user_models)} requested, "
            f"{len(custom_names)} custom kept-active, "
            f"{n_active} now active in DB",
            flush=True,
        )


# ─── main ─────────────────────────────────────────────────────────────

def _print_env_summary() -> None:
    user_models = _csv(COMFYUI_USER_MODELS)
    print("  ↳ env inputs:", flush=True)
    print(
        f"      COMFYUI_USER_MODELS        ({len(user_models)}) = {user_models!r}",
        flush=True,
    )
    print(
        f"      COMFYUI_CUSTOM_MODELS_FILE = {COMFYUI_CUSTOM_MODELS_FILE!r}",
        flush=True,
    )


def main() -> int:
    print("comfyui-catalog-init: starting", flush=True)
    _print_env_summary()
    catalog_module = load_catalog()
    conn = connect_with_retry()
    try:
        verify_constraint(conn)
        upsert_catalog(conn, catalog_module)
        custom_names = upsert_custom_sidecar(conn, catalog_module)
        apply_user_models_selection(
            conn, _csv(COMFYUI_USER_MODELS), custom_names
        )
        conn.commit()
        print("comfyui-catalog-init: done", flush=True)
    except Exception as exc:
        conn.rollback()
        print(f"❌ comfyui-catalog-init failed: {exc}", flush=True)
        traceback.print_exc()
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
