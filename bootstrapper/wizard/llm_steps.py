"""
LLM cluster prompt-step builders for the Textual wizard.

Two consumers in ``bootstrapper/ui/textual/integration.py``:
  * ``build_ollama_steps(env_vars)`` — three Ollama variant steps
    (live `/api/tags` multiselect, ``ollama.com/library`` multiselect,
    free-text "additional to pull"). Only one fires per wizard run,
    gated by ``LLM_PROVIDER_SOURCE`` via ``skip_if_prev``.
  * ``build_cloud_steps(env_vars, warn)`` — three (secret + multiselect)
    pairs for OpenAI / Anthropic / OpenRouter. The multiselect step
    is gated by the secret step's result (clear/empty → skip) and
    fetches its option list live via ``cloud_models`` (with curated
    catalog fallback).

Why a separate module: ``_build_steps_and_rows`` in integration.py was
~600 lines because every closure for these step lists lived inline.
Extracting the LLM cluster keeps integration.py focused on the screen
glue (steps + rows + state).
"""

from __future__ import annotations

from typing import Callable, Dict, List

from utils.cloud_models import (
    list_anthropic_models,
    list_openai_models,
    list_openrouter_models,
)
from utils.llm_catalog import (
    cloud_entries,
    default_active_names,
    ollama_entries,
)
from utils.ollama_discovery import list_pulled_models
from utils.ollama_library import list_library_models
from utils.cloud_providers import CLOUD_PROVIDERS

from ui.textual.widgets.prompt_panel import (
    SECRET_CLEAR,
    SECRET_KEEP,
    PromptOption,
    PromptStep,
)


LLM_ENGINE_TITLE = "LLM Engine  ·  source"
# Single unified Ollama models step. Replaces the previous pulled+library
# split, which produced two near-duplicate pages for localhost/external
# users (the library was a strict superset of /api/tags). Now: container
# sources show library only (nothing's pulled yet); localhost/external
# show a merged list with [pulled] / [library] badges.
OLLAMA_MODELS_TITLE = "Ollama  ·  models"
OLLAMA_CUSTOM_TITLE = "Ollama  ·  additional models to pull"

# Backward-compat aliases for any external consumers grepping the old
# names. Internal call sites have all moved to OLLAMA_MODELS_TITLE.
OLLAMA_LIVE_TITLE = OLLAMA_MODELS_TITLE
OLLAMA_CATALOG_TITLE = OLLAMA_MODELS_TITLE


def cloud_secret_title(provider_name: str) -> str:
    """Wizard step title for the per-provider API-key (secret) step.
    Kept in lockstep with the (matching) ``cloud_models_title`` so the
    splitter in ``integration._selections_to_args`` can find them by
    name without redoing the f-string in every call site.
    """
    return f"{provider_name} Cloud  ·  API key"


def cloud_models_title(provider_name: str) -> str:
    """Wizard step title for the per-provider model multiselect step."""
    return f"{provider_name} Cloud  ·  models"


# ─── helpers ───────────────────────────────────────────────────────────


def _selected_llm_source(env_vars: Dict[str, str], selections: dict) -> str:
    v = selections.get(LLM_ENGINE_TITLE)
    if v:
        return v.strip().lower()
    return (env_vars.get("LLM_PROVIDER_SOURCE", "ollama-container-cpu") or "").strip().lower()


def _is_localhost_or_external(src: str) -> bool:
    return "localhost" in src or "external" in src


def _is_container_ollama(src: str) -> bool:
    return src.startswith("ollama-container-")


# ─── Ollama steps ──────────────────────────────────────────────────────


def build_ollama_steps(
    env_vars: Dict[str, str],
    warn: Callable[[str], None] | None = None,
) -> List[PromptStep]:
    """Build the three Ollama variant steps. ``skip_if_prev`` predicates
    on each ensure exactly one fires per wizard run, picked by the
    selected ``LLM_PROVIDER_SOURCE``.

    ``warn`` is the same launch-log sink the cloud steps use — passed
    here so live-discovery failures (``/api/tags`` unreachable) get
    persisted to ``/tmp/genai-vanilla-launch-*.log`` instead of
    silently producing an empty multiselect.
    """
    _warn = warn or (lambda _msg: None)
    ollama_default_actives = default_active_names("ollama")
    ollama_existing = {
        s.strip()
        for s in (env_vars.get("OLLAMA_USER_MODELS", "") or "").split(",")
        if s.strip()
    }
    ollama_default_values = (
        sorted(ollama_existing) if ollama_existing else ollama_default_actives
    )
    existing_custom = (env_vars.get("OLLAMA_CUSTOM_MODELS", "") or "").strip()

    def _ollama_upstream_for_wizard(selections: dict) -> str:
        src = _selected_llm_source(env_vars, selections)
        url = (env_vars.get("LITELLM_OLLAMA_UPSTREAM", "") or "").strip()
        if "localhost" in src:
            return "http://localhost:11434"
        if "external" in src and url:
            return url
        return ""

    def _build_library_options(library_names: List[str]) -> List[PromptOption]:
        """Map a list of library names to PromptOptions, merging in
        catalog metadata (description / curated badges) when available.
        """
        curated_meta = {e.name: e for e in ollama_entries()}
        opts: List[PromptOption] = []
        for name in library_names:
            meta = curated_meta.get(name)
            opts.append(PromptOption(
                value=name, label=name,
                hint=meta.description if meta else "",
                badges=list(meta.badges) if meta else [],
            ))
        return opts

    def _merged_ollama_options(selections: dict) -> List[PromptOption]:
        """Build the unified Ollama models option list.

        Source-aware behavior:
          * ``ollama-container-*``: nothing is pulled yet (the in-stack
            container isn't running at wizard time), so just return the
            library scrape (with curated catalog as fallback).
          * ``ollama-localhost`` / ``ollama-external``: query the
            upstream's ``/api/tags`` AND scrape ollama.com/library, then
            merge:
              - already-pulled rows (from /api/tags) appear first with a
                ``pulled`` badge
              - library entries also present in /api/tags get the
                ``pulled`` badge too (in their library position)
              - library-only entries get a ``library`` badge

        On failure: degrades gracefully — if the library scrape fails we
        keep the pulled list (or curated catalog); if /api/tags fails
        we keep the library list with a placeholder note in the warn
        sink.
        """
        src = _selected_llm_source(env_vars, selections)

        # Library scrape is shared by every source.
        library_names = list_library_models(timeout=5.0)
        if not library_names:
            _warn(
                "[warn/ollama-fetch] ollama.com/library scrape returned no entries "
                "— falling back to curated OLLAMA_DEFAULT_CATALOG"
            )
            curated = [e.name for e in ollama_entries()]
            library_names = curated  # may still be empty in pathological cases

        if not _is_localhost_or_external(src):
            # Container modes: library only. Nothing to merge.
            if not library_names:
                return [PromptOption(
                    value="",
                    label="(catalog unreachable — ollama.com/library scrape failed)",
                    hint="check network access; ollama-pull will pull whatever is active in public.llms",
                    badges=[],
                )]
            return _build_library_options(library_names)

        # Localhost/external: merge /api/tags + library.
        url = _ollama_upstream_for_wizard(selections)
        pulled_names: List[str] = []
        if not url:
            _warn(
                "[warn/ollama-fetch] no Ollama upstream URL resolved for "
                f"{src!r} — showing library entries only"
            )
        else:
            pulled_names = list_pulled_models(url, timeout=2.0)
            if not pulled_names:
                _warn(
                    f"[warn/ollama-fetch] /api/tags at {url} returned 0 models — "
                    "showing library entries only (run `ollama pull <name>` "
                    "on the host to populate)"
                )

        pulled_set = set(pulled_names)
        library_set = set(library_names)
        curated_meta = {e.name: e for e in ollama_entries()}

        opts: List[PromptOption] = []
        # 1. Pulled-but-not-in-library: rare (custom local builds, dev
        #    versions). Show first so the user sees them on screen one.
        for name in pulled_names:
            if name in library_set:
                continue
            meta = curated_meta.get(name)
            opts.append(PromptOption(
                value=name, label=name,
                hint=meta.description if meta else "(local model, not in public library)",
                badges=["pulled"] + (list(meta.badges) if meta else []),
            ))
        # 2. Library entries (in scrape order). Items also pulled get
        #    the ``pulled`` badge prepended; library-only get ``library``.
        for name in library_names:
            meta = curated_meta.get(name)
            base_badges = list(meta.badges) if meta else []
            if name in pulled_set:
                badges = ["pulled"] + base_badges
            else:
                badges = ["library"] + base_badges
            opts.append(PromptOption(
                value=name, label=name,
                hint=meta.description if meta else "",
                badges=badges,
            ))
        if not opts:
            return [PromptOption(
                value="",
                label=f"(no Ollama models reachable at {url or '<no upstream>'})",
                hint="check the upstream URL or pull a model on the host with `ollama pull <name>`",
                badges=[],
            )]
        return opts

    return [
        # Single unified step. Container modes get library only;
        # localhost/external get a merged [pulled] + [library] view.
        # See _merged_ollama_options for details.
        PromptStep(
            title=OLLAMA_MODELS_TITLE,
            step_index=0, step_total=0,
            heading="Which Ollama models to register?",
            subtitle=(
                "Container: full ollama.com/library catalog (ollama-pull fetches checked at startup). "
                "Localhost/external: merged list — [pulled] = on disk, [library] = available; "
                "registering a [library]-only entry requires you to `ollama pull <name>` on the host. "
                "Space toggles, Enter confirms."
            ),
            options=[],
            default_values=ollama_default_values,
            service_name="",
            kind="multiselect",
            skip_if_prev=lambda sel: not _selected_llm_source(env_vars, sel).startswith("ollama-"),
            options_provider=_merged_ollama_options,
        ),
        PromptStep(
            title=OLLAMA_CUSTOM_TITLE,
            step_index=0, step_total=0,
            heading="Additional Ollama models to pull?",
            subtitle=(
                "Comma-separated names not in the catalog (e.g. 'llama3.3, deepseek-r1'). "
                "Press Enter to skip. Each gets pulled by ollama-pull at startup."
            ),
            options=[],
            default_value=existing_custom,
            service_name="",
            kind="text",
            skip_if_prev=lambda sel: not _is_container_ollama(
                _selected_llm_source(env_vars, sel)
            ),
        ),
    ]


# ─── Cloud steps ───────────────────────────────────────────────────────


def _make_cloud_options_provider(
    provider_key: str,
    secret_title: str,
    api_key_var: str,
    env_vars: Dict[str, str],
    warn: Callable[[str], None],
):
    """Return a PromptStep options_provider that fetches the live model
    list for the given cloud provider. Falls back to the curated
    catalog on any failure (network, auth, empty result).

    Resolution order for the API key:
      1. The secret-step value if it's a real key (not sentinel/empty).
      2. Existing value from .env (when secret step returned SECRET_KEEP).
      3. None — only OpenRouter works keyless; others return [].
    """
    def _resolve_key(selections: dict) -> str:
        v = selections.get(secret_title)
        if isinstance(v, str) and v and v not in (SECRET_KEEP, SECRET_CLEAR):
            return v
        return (env_vars.get(api_key_var, "") or "").strip()

    def _curated_options() -> List[PromptOption]:
        return [
            PromptOption(
                value=e.name, label=e.name,
                hint=e.description, badges=list(e.badges),
            )
            for e in cloud_entries(provider_key)
        ]

    def _provider(selections: dict) -> List[PromptOption]:
        try:
            if provider_key == "openrouter":
                live = list_openrouter_models(timeout=5.0, on_warn=warn)
            else:
                api_key = _resolve_key(selections)
                if provider_key == "openai":
                    live = list_openai_models(api_key, timeout=5.0, on_warn=warn)
                elif provider_key == "anthropic":
                    live = list_anthropic_models(api_key, timeout=5.0, on_warn=warn)
                else:
                    live = []
        except Exception as exc:  # noqa: BLE001
            warn(f"[warn/{provider_key}-fetch] unexpected error: {type(exc).__name__}: {exc}")
            live = []
        if not live:
            return _curated_options()
        return [
            PromptOption(value=m.id, label=m.label, hint=m.description, badges=[])
            for m in live
        ]

    return _provider


def _make_cloud_skip_predicate(
    secret_title: str,
    source_var: str,
    api_key_var: str,
    env_vars: Dict[str, str],
):
    """skip_if_prev: True when the user's secret-step result says the
    provider should stay disabled.

    Decision matrix (secret-step result × .env source × .env key):

      result == SECRET_CLEAR or ""
          → user explicitly disabled. Skip multiselect.
      result == SECRET_KEEP and .env source == 'enabled'
          → already enabled. Show multiselect.
      result == SECRET_KEEP and .env source != 'enabled' and key set
          → AMBIGUOUS. The user pressed Enter past a step that already
          had a key in .env but a disabled source. We treat that as
          "use existing key + enable provider" (the integration layer
          auto-promotes the source flag in _selections_to_args). Show
          multiselect so they can pick models.
      result == SECRET_KEEP and .env source != 'enabled' and no key
          → freshly disabled provider, nothing to enable with. Skip.
      result == real key string
          → user typed a new key. Show multiselect.
    """
    def _skip(selections: dict) -> bool:
        v = selections.get(secret_title)
        if v is None:
            return False
        if v == SECRET_CLEAR or v == "":
            return True
        if v == SECRET_KEEP:
            existing_source = (env_vars.get(source_var, 'disabled') or '').strip().lower()
            existing_key = (env_vars.get(api_key_var, '') or '').strip()
            if existing_source == 'enabled':
                return False
            # Disabled in .env. Skip unless there's an existing key to
            # auto-promote with.
            return not existing_key
        # Real key typed in.
        return False
    return _skip


def build_cloud_steps(
    env_vars: Dict[str, str],
    warn: Callable[[str], None],
) -> List[PromptStep]:
    """Build the three (secret + multiselect) pairs for OpenAI,
    Anthropic, OpenRouter."""
    cloud_steps: List[PromptStep] = []
    for provider in CLOUD_PROVIDERS:
        name, source_var, api_key_var = provider.name, provider.source_var, provider.api_key_var
        existing_key = (env_vars.get(api_key_var, "") or "").strip()
        existing_source = (env_vars.get(source_var, "disabled") or "").strip().lower()
        secret_title = cloud_secret_title(name)
        if existing_key and existing_source == "enabled":
            secret_subtitle = (
                f"{name} is already enabled. Press Enter to keep the saved key, "
                "type a replacement key, or type 'clear' to disable."
            )
            secret_keep_hint = (
                "key saved and provider enabled  ·  Enter keeps enabled  ·  "
                "type a new key to replace  ·  type \"clear\" + Enter to disable"
            )
        elif existing_key:
            secret_subtitle = (
                f"A {name} key is saved but {source_var} is disabled. "
                "Press Enter to enable with the saved key, type a replacement key, "
                "or type 'clear' to remove it."
            )
            secret_keep_hint = (
                "key saved but provider disabled  ·  Enter enables with saved key  ·  "
                "type a new key to replace  ·  type \"clear\" + Enter to remove"
            )
        else:
            secret_subtitle = (
                f"Paste your {name} API key to enable. "
                "Press Enter (empty) to leave disabled. The key is stored in .env."
            )
            secret_keep_hint = None
        cloud_steps.append(PromptStep(
            title=secret_title,
            step_index=0, step_total=0,
            heading=f"Use {name} through LiteLLM?",
            subtitle=secret_subtitle,
            options=[],
            default_value=existing_key,
            service_name="",
            kind="secret",
            secret_keep_hint=secret_keep_hint,
        ))
        provider_key = provider.key
        catalog_rows = cloud_entries(provider_key)
        existing_models = {
            s.strip()
            for s in (env_vars.get(provider.user_models_var, "") or "").split(",")
            if s.strip()
        }
        if existing_models:
            default_values = sorted(existing_models)
        else:
            curated = default_active_names(provider_key)
            default_values = curated or [e.name for e in catalog_rows]
        cloud_steps.append(PromptStep(
            title=cloud_models_title(name),
            step_index=0, step_total=0,
            heading=f"Which {name} models do you want available?",
            subtitle=(
                "Live from /v1/models (filtered). Space toggles, Enter confirms. "
                "Picks become active rows in public.llms."
            ),
            options=[],
            default_values=default_values,
            service_name="",
            kind="multiselect",
            skip_if_prev=_make_cloud_skip_predicate(
                secret_title, source_var, api_key_var, env_vars,
            ),
            options_provider=_make_cloud_options_provider(
                provider_key, secret_title, api_key_var, env_vars, warn,
            ),
        ))
    return cloud_steps
