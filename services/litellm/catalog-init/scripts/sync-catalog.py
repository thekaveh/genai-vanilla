#!/usr/bin/env python3
"""
sync-catalog.py — UPSERT the LLM catalog into ``public.llms`` and apply
the user's wizard / .env-driven model selections.

Runs once per ``docker compose up`` between ``supabase-db-init`` and
the downstream services that consume ``public.llms`` (``ollama-pull``,
``litellm-init``).

Behavior:
  1. Read .env-passed env vars for provider toggles, API keys, and
     comma-separated user-model selections.
  2. Import the catalog module (bind-mounted at /catalog/llm_catalog.py;
     sibling of /scripts to avoid file-on-dir overlay edge cases).
  3. UPSERT every catalog row into public.llms. Conflict on
     (provider, name) preserves the existing ``active`` flag (so user
     choices survive re-runs) and the existing ``description``
     (so hand-edited notes aren't clobbered). Capability flags and
     immutable model facts (context_window, size_gb) are refreshed
     from the catalog so updates flow through.
  4. Apply user selections per provider:
       • Cloud provider X with enabled=true AND key set:
           - If X_USER_MODELS set → activate exactly those rows.
           - If X_USER_MODELS empty → leave existing actives alone
             (default-active rows from the catalog stay active).
       • Cloud provider X with enabled=false OR no key:
           - Deactivate all rows for that provider.
       • Ollama:
           - If LLM_PROVIDER_SOURCE in {none, disabled} → deactivate all.
           - If OLLAMA_USER_MODELS set → activate exactly those rows.
           - OLLAMA_CUSTOM_MODELS rows (not in catalog) → INSERT new
             rows with sensible defaults and active=true, for ALL
             ollama sources. Non-container sources get a loud warning:
             ollama-pull doesn't run host-side, so the operator must
             `ollama pull` the model themselves or requests to the row
             404 at LiteLLM.
  5. Exit 0.

Catalog rows that get added/removed in ``llm_catalog.py`` flow through
on every run. Removed rows aren't deleted from the DB — they stay as
historical records, just no longer UPSERTed. Operators can ``DELETE``
manually if they want a clean table.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import time
import traceback
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_batch


# ─── env / config ─────────────────────────────────────────────────────

PG_HOST = os.environ.get("PGHOST", "supabase-db")
PG_PORT = int(os.environ.get("PGPORT", "5432"))
PG_DB = os.environ.get("PGDATABASE", "postgres")
PG_USER = os.environ.get("PGUSER", "postgres")
PG_PASSWORD = os.environ.get("PGPASSWORD", "")

# Cloud-provider toggles + keys. Derived at runtime from
# ``/catalog/cloud_providers.py`` (sibling bind mount of /catalog,
# same path as llm_catalog.py — see docker-compose.yml's
# llm-catalog-init service) so adding a fourth provider only requires
# editing ``bootstrapper/utils/cloud_providers.py``; this script picks
# up the new row automatically. See ``build_providers_cloud()`` below.

LLM_PROVIDER_SOURCE = os.environ.get("LLM_PROVIDER_SOURCE", "ollama-container-cpu").strip().lower()
OLLAMA_USER_MODELS = os.environ.get("OLLAMA_USER_MODELS", "")
OLLAMA_CUSTOM_MODELS = os.environ.get("OLLAMA_CUSTOM_MODELS", "")
OLLAMA_AUTO_IMPORT_LOCAL_MODELS = os.environ.get(
    "OLLAMA_AUTO_IMPORT_LOCAL_MODELS", "true"
)
LITELLM_OLLAMA_UPSTREAM = os.environ.get(
    "LITELLM_OLLAMA_UPSTREAM", "http://ollama:11434"
).strip()


def _truthy(v: str | None) -> bool:
    return (v or "").strip().lower() in ("true", "1", "yes", "enabled")


def _csv(v: str | None) -> list[str]:
    if not v:
        return []
    return [s.strip() for s in v.split(",") if s.strip()]


def _fetch_ollama_tags(upstream_url: str, timeout: float = 3.0) -> list[str]:
    """Query ``{upstream_url}/api/tags`` and return the model tag list.

    Returns an empty list on any failure (unreachable upstream, bad
    JSON, etc.). Callers treat this as "auto-import disabled for this
    boot" and proceed with whatever's in OLLAMA_USER_MODELS only.

    Mirrors ``bootstrapper/utils/ollama_discovery.py::list_pulled_models``
    in shape and failure-mode (empty list on any error) so the two
    sites — the wizard's option list and the catalog's auto-import —
    behave consistently against the same /api/tags endpoint.
    """
    import json
    import socket
    import urllib.error
    import urllib.request

    if not upstream_url:
        return []
    base = upstream_url.rstrip("/")
    url = f"{base}/api/tags"
    try:
        req = urllib.request.Request(
            url, headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError) as exc:
        print(
            f"  ⚠ ollama: /api/tags fetch from {url!r} failed ({exc}); "
            f"auto-import disabled for this boot",
            flush=True,
        )
        return []
    try:
        data = json.loads(body)
    except (ValueError, TypeError):
        print(
            f"  ⚠ ollama: /api/tags response from {url!r} not valid JSON; "
            f"auto-import disabled for this boot",
            flush=True,
        )
        return []
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        return []
    out: list[str] = []
    for entry in models:
        if isinstance(entry, dict):
            name = entry.get("name") or entry.get("model")
            if isinstance(name, str) and name.strip():
                out.append(name.strip())
    return out


# ─── live-only model defaults ─────────────────────────────────────────
# When the wizard's live picker (cloud /v1/models, ollama.com/library)
# returns a model name not present in the curated catalog, we INSERT it
# with these generic capability defaults so LiteLLM can still route to
# it via services/litellm/init/scripts/init.py:render_model_list (which dispatches purely
# on the ``provider`` column). Co-located with sync-catalog.py rather
# than cloud_providers.py because cloud_providers.py is intentionally
# zero-knowledge about catalog/DB capability shape.
#
# content=8/structured_content=5 marks unknown models as "general chat;
# probably JSON-capable" — enough for routing. vision/embeddings default
# to 0 because we can't infer from a model ID alone. context_window=0
# mirrors the OLLAMA_CUSTOM path (see the custom-path INSERT below) — we don't fabricate
# context limits; LiteLLM uses upstream-provided values at request time.
LIVE_DEFAULTS: dict[str, dict] = {
    "openai": dict(
        content=8, structured_content=5, vision=0, embeddings=0,
        context_window=0, size_gb=None,
        description="Live-discovered OpenAI model (not in curated catalog)",
    ),
    "anthropic": dict(
        content=8, structured_content=5, vision=0, embeddings=0,
        context_window=0, size_gb=None,
        description="Live-discovered Anthropic model (not in curated catalog)",
    ),
    "openrouter": dict(
        content=8, structured_content=5, vision=0, embeddings=0,
        context_window=0, size_gb=None,
        description="Live-discovered OpenRouter model (not in curated catalog)",
    ),
    "ollama": dict(
        content=8, structured_content=5, vision=0, embeddings=0,
        context_window=0, size_gb=None,
        description="Live-discovered Ollama model (not in curated catalog)",
    ),
}


# ─── catalog import ───────────────────────────────────────────────────

def load_catalog():
    """Import bootstrapper/utils/llm_catalog.py from the /catalog/ bind
    mount (sibling of /scripts/, see docker-compose.yml).
    """
    catalog_path = Path("/catalog/llm_catalog.py")
    if not catalog_path.exists():
        sys.exit(
            f"❌ {catalog_path} not found — is the bootstrapper/utils "
            f"bind mount configured? Check docker-compose.yml's "
            f"llm-catalog-init service."
        )
    spec = importlib.util.spec_from_file_location("llm_catalog", catalog_path)
    module = importlib.util.module_from_spec(spec)
    # CRITICAL: register the module in sys.modules BEFORE exec_module().
    # Python 3.12's @dataclass decorator (with `from __future__ import
    # annotations`) calls dataclasses._is_type → sys.modules.get(cls.__module__)
    # → expects to find the not-yet-fully-loaded module. Without this
    # line we get:
    #   AttributeError: 'NoneType' object has no attribute '__dict__'
    # at the @dataclass on the very first class defined in llm_catalog.py.
    sys.modules["llm_catalog"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def load_cloud_providers():
    """Import bootstrapper/utils/cloud_providers.py from /catalog/.

    Same import pattern as ``load_catalog()`` — single source of
    truth for the cloud-provider list, mounted into the container at
    /catalog/cloud_providers.py via the same bind mount.
    """
    path = Path("/catalog/cloud_providers.py")
    if not path.exists():
        sys.exit(
            f"❌ {path} not found — is the bootstrapper/utils bind mount "
            f"configured? Check docker-compose.yml's llm-catalog-init service."
        )
    spec = importlib.util.spec_from_file_location("cloud_providers", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["cloud_providers"] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def build_providers_cloud(cloud_providers_module) -> list[tuple[str, str, str, str]]:
    """Derive the (provider_key, enable_var, key_var, models_var) tuples
    consumed by ``main()`` and ``_print_env_summary()`` from the canonical
    ``CLOUD_PROVIDERS`` list. Adding a new provider in ``cloud_providers.py``
    is sufficient — this script will pick it up automatically.
    """
    return [
        (
            p.key,
            p.enabled_flag_var,
            p.api_key_var,
            p.user_models_var,
        )
        for p in cloud_providers_module.CLOUD_PROVIDERS
    ]


# ─── DB connection ────────────────────────────────────────────────────

def connect_with_retry(retries: int = 30, delay: float = 2.0):
    """Wait for supabase-db-init to finish before trying to UPSERT."""
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


# ─── core sync logic ──────────────────────────────────────────────────

def verify_constraint(conn) -> None:
    """Pre-flight check — abort early if the (provider, name) unique
    constraint is missing. Without it, the ON CONFLICT clause in
    upsert_catalog() fails with a cryptic error instead of pointing at
    the migration that should have run.
    """
    # Scope by table — a constraint with the same name on a different
    # table would falsely satisfy this guard otherwise.
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM pg_constraint
            WHERE conname = 'llms_provider_name_key'
              AND conrelid = 'public.llms'::regclass
            """
        )
        if cur.fetchone() is None:
            sys.exit(
                "❌ llms_provider_name_key constraint missing on public.llms — "
                "did supabase/db/scripts/11-litellm.sql fail "
                "to run? Check supabase-db-init logs."
            )
    print("  ↳ verified llms_provider_name_key constraint on public.llms", flush=True)


def upsert_catalog(conn, catalog) -> None:
    """UPSERT every catalog row into public.llms.

    On conflict (provider, name): refresh the capability flags + the
    immutable model facts (context_window, size_gb) from the catalog,
    but preserve user state — both ``active`` (so wizard / psql edits
    survive a re-run) and ``description`` (so a hand-edited note isn't
    silently overwritten on every ``docker compose up``). Newly
    inserted rows start with their catalog ``default_active`` and
    catalog ``description``.
    """
    rows = [
        (
            e.provider, e.name, e.default_active,
            e.content, e.structured_content, e.vision, e.embeddings,
            e.context_window, e.size_gb, e.description,
        )
        for e in catalog.all_catalog_entries()
    ]
    sql = """
    INSERT INTO public.llms
      (provider, name, active,
       content, structured_content, vision, embeddings,
       context_window, size_gb, description)
    VALUES
      (%s, %s, %s,
       %s, %s, %s, %s,
       %s, %s, %s)
    ON CONFLICT (provider, name) DO UPDATE SET
      content            = EXCLUDED.content,
      structured_content = EXCLUDED.structured_content,
      vision             = EXCLUDED.vision,
      embeddings         = EXCLUDED.embeddings,
      context_window     = EXCLUDED.context_window,
      size_gb            = EXCLUDED.size_gb,
      updated_at         = now();
    """
    with conn.cursor() as cur:
        execute_batch(cur, sql, rows)
    print(f"  ↳ UPSERTed {len(rows)} catalog rows", flush=True)


def insert_live_only(conn, provider: str, requested: list[str]) -> tuple[list[str], list[str]]:
    """Ensure every requested model name has a row in public.llms.

    The wizard's live model pickers (cloud /v1/models, ollama.com/library)
    can return names that aren't in the curated catalog. Without this
    step, the subsequent ``UPDATE … SET active = true … WHERE name =
    ANY(%s)`` would match zero rows for those names — silent data loss.

    For each name in ``requested`` not already in public.llms for this
    provider, INSERT a row with generic capability defaults from
    LIVE_DEFAULTS so services/litellm/init/scripts/init.py can render a routable entry.

    Returns ``(matched_in_catalog, inserted_live)`` so callers can log
    the actual outcome instead of overstating with len(user_models).

    Idempotent: ``ON CONFLICT (provider, name) DO NOTHING`` keeps
    re-runs safe; existing rows (including those with edited capability
    flags) are not disturbed.
    """
    if not requested:
        return [], []
    defaults = LIVE_DEFAULTS.get(provider)
    if defaults is None:
        # Unknown provider; nothing to do — caller's UPDATE will simply
        # match zero rows and log accordingly.
        return [], []
    with conn.cursor() as cur:
        cur.execute(
            "SELECT name FROM public.llms WHERE provider = %s AND name = ANY(%s);",
            (provider, requested),
        )
        existing = {r[0] for r in cur.fetchall()}
        matched = [n for n in requested if n in existing]
        to_insert = [n for n in requested if n not in existing]
        if to_insert:
            rows = [
                (
                    provider, n, True,
                    defaults["content"], defaults["structured_content"],
                    defaults["vision"], defaults["embeddings"],
                    defaults["context_window"], defaults["size_gb"],
                    defaults["description"],
                )
                for n in to_insert
            ]
            execute_batch(
                cur,
                """
                INSERT INTO public.llms
                  (provider, name, active,
                   content, structured_content, vision, embeddings,
                   context_window, size_gb, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (provider, name) DO NOTHING;
                """,
                rows,
            )
    return matched, to_insert


def apply_cloud_selection(
    conn,
    provider: str,
    enabled: bool,
    has_key: bool,
    user_models: list[str],
    catalog,
) -> None:
    """Apply cloud-provider activation rules.

    enabled=True AND has_key=True:
      - user_models non-empty → activate exactly those, deactivate the rest.
      - user_models empty AND there are existing actives → leave them alone.
      - user_models empty AND zero existing actives → activate the catalog's
        ``default_active=True`` set so the provider is usable. This handles
        the CLI-flag path ``--openai-api-key sk-... --cloud-openai-source enabled``
        without ``--openai-models`` — otherwise the gateway would have an
        enabled provider with no models in ``model_list``.
    enabled=False OR has_key=False:
      - deactivate all rows for that provider.
    """
    with conn.cursor() as cur:
        if not (enabled and has_key):
            cur.execute(
                "UPDATE public.llms SET active = false WHERE provider = %s;",
                (provider,),
            )
            print(f"  ↳ {provider}: deactivated all (enabled={enabled}, has_key={has_key})", flush=True)
            return
        if not user_models:
            cur.execute(
                "SELECT count(*) FROM public.llms WHERE provider = %s AND active = true;",
                (provider,),
            )
            (n_active,) = cur.fetchone()
            if n_active > 0:
                print(f"  ↳ {provider}: enabled, no user-models override → keep {n_active} existing active(s)", flush=True)
                return
            # Zero actives + no override → activate the catalog defaults.
            curated = [e.name for e in catalog.cloud_entries(provider) if e.default_active]
            if not curated:
                curated = [e.name for e in catalog.cloud_entries(provider)]
            if curated:
                cur.execute(
                    "UPDATE public.llms SET active = true "
                    "WHERE provider = %s AND name = ANY(%s);",
                    (provider, curated),
                )
                print(
                    f"  ↳ {provider}: enabled but zero actives — activated curated defaults "
                    f"({len(curated)}): {', '.join(curated)}",
                    flush=True,
                )
            else:
                print(f"  ↳ {provider}: enabled but no catalog rows to activate", flush=True)
            return
        # Live-only fixup: insert any selected names not in public.llms
        # before activating, so the wizard's live picks land in the
        # model_list. Returns (matched_in_catalog, inserted_live).
        matched, inserted = insert_live_only(cur.connection, provider, user_models)
        cur.execute(
            "UPDATE public.llms SET active = true WHERE provider = %s AND name = ANY(%s);",
            (provider, user_models),
        )
        cur.execute(
            "UPDATE public.llms SET active = false WHERE provider = %s AND name <> ALL(%s);",
            (provider, user_models),
        )
        live_suffix = f" [live-only: {', '.join(inserted)}]" if inserted else ""
        print(
            f"  ↳ {provider}: {len(user_models)} requested, "
            f"{len(matched)} matched in catalog, "
            f"{len(inserted)} inserted as live-only{live_suffix}",
            flush=True,
        )


def apply_ollama_selection(conn, llm_source: str, user_models: list[str], custom_models: list[str]) -> None:
    """Apply Ollama activation rules.

    Source none/disabled → deactivate everything Ollama.
    Otherwise:
      - Auto-import (``OLLAMA_AUTO_IMPORT_LOCAL_MODELS=true``, the
        default for ``ollama-localhost``): query the upstream's
        ``/api/tags``, union the result with ``user_models``, and treat
        the union as the activation set. This makes ``ollama pull <name>``
        on the host propagate to LiteLLM on the next ``./start.sh`` with
        no wizard re-run needed. Set ``OLLAMA_AUTO_IMPORT_LOCAL_MODELS=false``
        to keep strict wizard-only control (useful when private
        fine-tunes on the host should NOT be exposed across the stack).
      - user_models non-empty → activate exactly those rows.
      - custom_models → INSERT (or UPSERT-active) any names not in
        the catalog with sensible default capability flags.

    Custom-model handling per source:
      * ``ollama-container-*``: registered + active. ollama-pull will
        fetch them on the next docker compose up. Auto-import is a
        no-op here (no host-side upstream to query — the container
        Ollama is populated by ollama-pull, not /api/tags).
      * ``ollama-localhost``: registered + active with a loud warning.
        ollama-pull does NOT run for this source (per
        service_config.OLLAMA_PULL_SCALE rules), so the operator is
        responsible for ``ollama pull <name>`` on the host. The row
        exists so LiteLLM can route to it once pulled.

    Stale-actives warning: when the user switches LLM_PROVIDER_SOURCE
    (e.g. container → localhost) without supplying OLLAMA_USER_MODELS,
    we keep existing active rows but warn loudly — they may reference
    models that aren't pulled on the new upstream and will return 404
    at request time.
    """
    is_container = llm_source.startswith("ollama-container-")
    is_host_side = llm_source.startswith("ollama-localhost")

    # Auto-import: union host /api/tags into user_models for host-side
    # sources, gated by OLLAMA_AUTO_IMPORT_LOCAL_MODELS. Container
    # sources skip this (their upstream is the in-stack ollama
    # container, which is populated FROM user_models via ollama-pull —
    # querying its /api/tags at catalog-init time is circular).
    if is_host_side and _truthy(OLLAMA_AUTO_IMPORT_LOCAL_MODELS):
        host_tags = _fetch_ollama_tags(LITELLM_OLLAMA_UPSTREAM)
        if host_tags:
            before = set(user_models)
            unioned = sorted(before | set(host_tags))
            added = sorted(set(host_tags) - before)
            if added:
                print(
                    f"  ↳ ollama: auto-import found {len(host_tags)} model(s) "
                    f"on {LITELLM_OLLAMA_UPSTREAM!r}, "
                    f"adding {len(added)} not in OLLAMA_USER_MODELS: "
                    f"{', '.join(added)}",
                    flush=True,
                )
            else:
                print(
                    f"  ↳ ollama: auto-import found {len(host_tags)} model(s) "
                    f"on {LITELLM_OLLAMA_UPSTREAM!r}, all already in "
                    f"OLLAMA_USER_MODELS",
                    flush=True,
                )
            user_models = unioned

    with conn.cursor() as cur:
        if llm_source in ("none", "disabled"):
            cur.execute("UPDATE public.llms SET active = false WHERE provider = 'ollama';")
            print("  ↳ ollama: source=none/disabled → deactivated all", flush=True)
            return

        # Custom models — INSERT new rows or UPSERT to active=true.
        # Default capability flags chosen as a generic content model.
        # For host-side Ollama (localhost/external), warn that the
        # operator must pull the model themselves; the row registers
        # the routable name in LiteLLM's model_list so requests can
        # land once the model is on disk.
        if custom_models and not is_container:
            print(
                f"  ⚠ ollama: registering {len(custom_models)} custom model(s) "
                f"({', '.join(custom_models)}) for source {llm_source!r}. "
                f"ollama-pull doesn't run for host-side Ollama — you must "
                f"`ollama pull <name>` each one yourself before requests "
                f"will succeed (otherwise LiteLLM gets 404 from the upstream).",
                flush=True,
            )
        if custom_models:
            cur.executemany(
                """
                INSERT INTO public.llms
                  (provider, name, active, content, structured_content, vision, embeddings,
                   context_window, size_gb, description)
                VALUES ('ollama', %s, true, 8, 5, 0, 0, 0, NULL, 'User-added Ollama model')
                ON CONFLICT (provider, name) DO UPDATE SET active = true, updated_at = now();
                """,
                [(name,) for name in custom_models],
            )
            print(f"  ↳ ollama: registered {len(custom_models)} custom model(s)", flush=True)

        if user_models:
            # Live-only fixup: insert any selected names not already in
            # public.llms before activation, so live picks from the
            # ollama.com/library scrape land in the model_list. Custom
            # models are already inserted above; live-only handles the
            # ``ollama-container-*`` library multiselect path.
            matched, inserted = insert_live_only(cur.connection, "ollama", user_models)
            cur.execute(
                "UPDATE public.llms SET active = true WHERE provider = 'ollama' AND name = ANY(%s);",
                (user_models,),
            )
            # Combine user-selected + custom into the activation set,
            # then deactivate everything else for ollama.
            keep_active = list(set(user_models) | set(custom_models))
            cur.execute(
                "UPDATE public.llms SET active = false WHERE provider = 'ollama' AND name <> ALL(%s);",
                (keep_active,),
            )
            live_suffix = f" [live-only: {', '.join(inserted)}]" if inserted else ""
            print(
                f"  ↳ ollama: {len(user_models)} requested, "
                f"{len(matched)} matched in catalog, "
                f"{len(inserted)} inserted as live-only{live_suffix}",
                flush=True,
            )
        else:
            # No explicit override. Existing actives stay, but warn for
            # host-side sources where the existing actives may have been
            # picked for a previous container Ollama and now reference
            # models that don't exist on the user's host.
            cur.execute(
                "SELECT name FROM public.llms WHERE provider = 'ollama' AND active = true ORDER BY name;",
            )
            actives = [r[0] for r in cur.fetchall()]
            if actives and not is_container:
                print(
                    f"  ⚠ ollama: keeping {len(actives)} existing active row(s) "
                    f"({', '.join(actives)}) for host-side source {llm_source!r}. "
                    f"If these models aren't pulled on your host upstream, "
                    f"LiteLLM will return 404 for them. Set OLLAMA_USER_MODELS "
                    f"explicitly (or re-run the wizard) to refresh the active set.",
                    flush=True,
                )
            else:
                print("  ↳ ollama: no user-models override → keep existing actives", flush=True)


# ─── main ─────────────────────────────────────────────────────────────

def _print_env_summary(providers_cloud: list[tuple[str, str, str, str]]) -> None:
    """Log the .env-driven inputs we're about to act on. NEVER prints
    raw API keys — only their truthy presence and CSV model selections.
    """
    print("  ↳ env inputs:", flush=True)
    print(f"      LLM_PROVIDER_SOURCE  = {LLM_PROVIDER_SOURCE!r}", flush=True)
    for provider, enable_var, key_var, models_var in providers_cloud:
        enabled = _truthy(os.environ.get(enable_var))
        has_key = bool((os.environ.get(key_var) or "").strip())
        user_models = _csv(os.environ.get(models_var))
        print(
            f"      {provider:11s} enabled={enabled} has_key={has_key} "
            f"user_models={user_models!r}",
            flush=True,
        )
    print(
        f"      ollama       user_models={_csv(OLLAMA_USER_MODELS)!r} "
        f"custom={_csv(OLLAMA_CUSTOM_MODELS)!r}",
        flush=True,
    )


def main() -> int:
    print("llm-catalog-init: starting", flush=True)
    cloud_providers_module = load_cloud_providers()
    providers_cloud = build_providers_cloud(cloud_providers_module)
    _print_env_summary(providers_cloud)
    catalog = load_catalog()
    print(f"  ↳ catalog loaded: {len(catalog.all_catalog_entries())} entries", flush=True)
    conn = connect_with_retry()
    try:
        verify_constraint(conn)
        upsert_catalog(conn, catalog)

        for provider, enable_var, key_var, models_var in providers_cloud:
            enabled = _truthy(os.environ.get(enable_var))
            key_val = (os.environ.get(key_var) or "").strip()
            user_models = _csv(os.environ.get(models_var))
            apply_cloud_selection(
                conn, provider, enabled, bool(key_val), user_models, catalog,
            )

        apply_ollama_selection(
            conn, LLM_PROVIDER_SOURCE,
            _csv(OLLAMA_USER_MODELS), _csv(OLLAMA_CUSTOM_MODELS),
        )

        conn.commit()
        print("llm-catalog-init: done", flush=True)
    except Exception as exc:
        conn.rollback()
        print(f"❌ llm-catalog-init failed: {exc}", flush=True)
        traceback.print_exc()
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
