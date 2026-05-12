# Changelog

All notable changes to the GenAI Vanilla Stack will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (Hermes Agent runtime)
- **New `hermes` service** (`nousresearch/hermes-agent:latest` — upstream publishes only `latest` + immutable `sha-<commit>` tags, no semver; production should pin to a specific sha per `docs/services/hermes.md`) — programmable AI agent runtime by Nous Research. Promoted from `docs/ROADMAP.md` Tier 2 to shipped. Container by default (3 SOURCE modes: `container`, `localhost`, `disabled`), ~2-4 GB RAM, no GPU. File-based persistence under `/opt/data` (`hermes-data` named volume) — no Postgres / Redis dependency. OpenAI-compatible API on port 8642 → host `63028`; web dashboard on 9119 → host `63029`, Kong-aliased as `hermes.localhost`.
- **New `hermes-init` companion** — renders `/opt/data/config.yaml` from environment before Hermes starts. Wires LiteLLM (`http://litellm:4000/v1`) for reasoning, Speaches / Chatterbox / Parakeet via OpenAI-compatible base-URL overrides for voice (`TTS_ENDPOINT` / `STT_ENDPOINT`), ComfyUI via a skill-override file at `/opt/data/skills/creative-comfyui-host-override.md`, and SearXNG for web search. Empty endpoint → block omitted from `config.yaml` (graceful degradation when a dependency is disabled). Bootstraps deps via inline `apk add` then re-execs under bash (matches openclaw-init / weaviate-init convention).
- **`hermes-agent` registered in the LiteLLM model_list** — `litellm-init/scripts/init.py` appends a `hermes-agent` row pointing at `${HERMES_ENDPOINT}/v1` when `HERMES_SOURCE != disabled`. Consequence: Open-WebUI, n8n, backend, jupyterhub, openclaw all see the new model automatically with no per-consumer wiring.
- **`HERMES_ENDPOINT` + `HERMES_API_KEY` plumbed to consumers** — backend, n8n, jupyterhub, openclaw-gateway env blocks for direct API / webhook access (LiteLLM-routed `hermes-agent` model is the default surface).
- **Bootstrapper integration** — new `hermes` entry in `bootstrapper/service-configs.yml` (`container` / `localhost` / `disabled` sources + cross-deps on stt_provider / tts_provider / comfyui / searxng for init-time URL wiring), `_generate_hermes_config()` in `bootstrapper/services/service_config.py` (mirror of `_generate_openclaw_config()`), `HERMES_ENDPOINT` in `bootstrapper/utils/endpoint_vars.py`, CLI flag `--hermes-source`, port-clear list, localhost validator, source override manager, dependency manager scale/source mappings, wizard tile (`bootstrapper/ui/state_builder.py`), service discovery name/description, hosts manager (`hermes.localhost` written by `--setup-hosts`), log-pane TOOL tag, `HERMES_API_KEY` auto-generation (32-byte URL-safe token, idempotent like LITELLM_MASTER_KEY).
- **Kong route `hermes.localhost` → `http://hermes:9119`** — added to `bootstrapper/utils/kong_config_generator.py:generate_hermes_service()`. Gated on `HERMES_SOURCE != disabled` AND `HERMES_DASHBOARD_ENABLED=true`.
- **Audit script extensions** — `docs/scripts/check-compose-source-deps.py` now enforces `(hermes, litellm)` and `(hermes-init, litellm)` `depends_on` pairs; `docs/scripts/check-kong-routes.py` enforces the `hermes.localhost → http://hermes:9119/` route.
- **docs**: new `docs/services/hermes.md` (full service doc), updated `docs/README.md`, `README.md` (5 OpenClaw parallels), `docs/deployment/ports-and-routes.md` (+rows for 63028/63029 and `hermes.localhost`), `docs/deployment/source-configuration.md` (table rows + dedicated subsection), `docs/quick-start/interactive-setup-wizard.md` (wizard table row), `docs/services/kong.md` (route + curl example), `docs/services/ollama.md` (LiteLLM consumer list), `docs/services/litellm.md` / `docs/services/openclaw.md` / `docs/services/open-webui.md` (cross-references), `docs/ROADMAP.md` (marks Tier-2 entry as shipped, corrects the wrong Supabase-dependency claim — Hermes is file-based).
- **runtime verification**: pulled and booted `nousresearch/hermes-agent:latest` (multi-arch — `linux/amd64` + `linux/arm64`); image is **~5.66 GB** on disk; OpenAI-compatible API responds at `/v1/models` with the bundled `hermes-agent` model id; 87 default skills sync into `~/.hermes/skills/` on every start; entrypoint refuses `HERMES_UID=0` (default `10000` is safe).

### Added (Ollama multi-select enrichments — capability tags, sizes, recency-bucket sort, filter chips)
- **Capability tag badges on every Ollama row** — `[embedding]`, `[thinking]`, `[vision]`, `[tools]`, `[audio]`. Scraped from each model card's `x-test-capability` spans on `ollama.com/library`. Curated catalog `embeddings` (plural) aliases to the live-scrape `embedding` (singular) so a row never shows both.
- **Single-select filter chip row** above the multi-select: `Filter  [ALL]  embedding  thinking  vision  tools  audio`. Click a chip to narrow the list; click `ALL` to reset. View-only — rows checked under one filter survive switching to another. New widget `bootstrapper/ui/textual/widgets/multiselect_filter_chips.py`; new fields `PromptStep.filter_tags`, `PromptPanel._filter_tag` / `_visible_indices`.
- **Approximate disk-size column** — every variant rendered as Q4_K_M footprint (`8b → 4.8GB`, `70b → 42GB`, `0.6b → 360MB`, `270m → 162MB`) via `option_row._approx_size`. Computed from Ollama's published parameter count (`params × 0.6 bytes/param` rule of thumb; real downloads are ±10–15% of the figure shown). On narrow terminals the column compresses to the first three variants + `…`, then drops entirely below the pull-count column.
- **Pull count column** — right-aligned, muted, formatted `K`/`M`/`B` (e.g. `114.2M`). Sourced from each card's `x-test-pull-count` span.
- **Two-bucket recency sort** — models updated within 365 days come first, sorted by total pulls descending; everything older gets a muted `[legacy]` badge and drops below in the same sort. This demotes year-old hits (`llama3.1` at 114M pulls) below newer-but-popular models (`deepseek-r1`, `gemma3`, `qwen3`). Threshold lives at `llm_steps._LEGACY_THRESHOLD_DAYS = 365`. `updated X ago` annotation appears in the hint line.
- **`OllamaLibraryEntry` dataclass replaces the names-only scrape** — `name`, `capabilities`, `sizes`, `pulls`, `updated`, `age_days`. Parser anchors on Alpine.js `x-test-*` test attributes (stable). `list_library_models()` removed (no callers).

### Added (wizard rework — DB-driven model_list, live model lists, multi-select prompts)
- **`public.llms` is now the single source of truth for the LiteLLM `model_list`**. Removed the hardcoded model lists in `bootstrapper/utils/litellm_config_generator.py`; the bootstrapper now writes only a stub `volumes/litellm/config.yaml` with empty `model_list`. The real config is rendered on every `docker compose up` by `litellm-init/scripts/init.py` from `SELECT … FROM public.llms WHERE active = true`.
- **`llm-catalog-init` container** (`llm-catalog-init/Dockerfile` + `scripts/sync-catalog.py`, python:3.12-slim): runs between `supabase-db-init` and `ollama-pull`/`litellm-init`. UPSERTs the curated catalog from `bootstrapper/utils/llm_catalog.py` and applies wizard / `.env`-driven model selections (`OPENAI_USER_MODELS`, `ANTHROPIC_USER_MODELS`, `OPENROUTER_USER_MODELS`, `OLLAMA_USER_MODELS`, `OLLAMA_CUSTOM_MODELS`). Pre-flight check verifies the `(provider, name)` unique constraint exists.
- **`bootstrapper/utils/llm_catalog.py`**: single source of truth for curated cloud + Ollama catalog. Each entry carries capability flags (`content`, `structured_content`, `vision`, `embeddings`), `context_window`, `default_active`. Cloud catalog includes gpt-5 family, claude-4.x line, and OpenRouter aggregator routes.
- **Schema migration** `supabase/db/scripts/05a-public-tables-migrations.sql`: drop `llms_name_key`, add composite `llms_provider_name_key UNIQUE (provider, name)` so models with the same bare name across providers can coexist.
- **Live cloud model fetch** in the wizard:
  - OpenAI `/v1/models` with the user's key + per-provider filter (see `bootstrapper/utils/cloud_models.py` for the current allow/deny lists; the filter is maintained there as new model families ship — DALL-E, Whisper, TTS, fine-tunes and snapshot variants are excluded).
  - Anthropic `/v1/models` with `x-api-key` — uses `display_name` for label, dedups snapshots.
  - OpenRouter `/api/v1/models` (no auth) — sorted alphabetically by label, capped at 50 entries to keep the picker usable.
  - All three fall back to `CLOUD_CATALOG` on network/auth/timeout/empty failure.
- **Live Ollama library scrape** of `https://ollama.com/library` (~230 entries) via `bootstrapper/utils/ollama_library.py`. Available for **every** ollama-* source (localhost, external, container) so users can browse and register additional models regardless of upstream type. Falls back to `OLLAMA_DEFAULT_CATALOG` on failure.
- **Live Ollama upstream discovery**: for `ollama-localhost` / `ollama-external`, `bootstrapper/utils/ollama_discovery.py` queries `${LITELLM_OLLAMA_UPSTREAM}/api/tags` to list models already pulled on the user's host.
- **Three new wizard prompt kinds** in `bootstrapper/ui/textual/widgets/prompt_panel.py`:
  - `kind="secret"` — masked `Input(password=True)`, with `<KEEP>` / `<CLEAR>` sentinels for re-runs (existing key + Enter = keep current; type `clear` to remove). Live "✓ N chars entered" counter via `on_input_changed` so the user can confirm a paste landed even when the dots scrolled out of view.
  - `kind="multiselect"` — checkbox list with `[✓]` / `[ ]` indicators. Space toggles the focused row; Enter confirms. Comma-joined CSV value. Optional `options_provider` for lazy/live fetch with `⏳ Fetching X models…` splash + worker + cache + back-invalidation.
  - `kind="text"` — free-text input with the same `<KEEP>` / `<CLEAR>` sentinels (used for `OLLAMA_CUSTOM_MODELS` so an empty Enter on re-run doesn't silently wipe an existing value).
- **CLI flags**: `--openai-models`, `--anthropic-models`, `--openrouter-models`, `--ollama-models`, `--ollama-custom-models` (comma-separated). Imply matching `--cloud-*-source=enabled` when paired with the corresponding `--*-api-key`.
- **`/tmp/genai-vanilla-launch-<YYYYMMDDTHHMMSS>.log`** — every wizard launch tees pipeline + docker compose output to this file. The session log is now opened at wizard start (not launch), so cloud `/v1/models` fetch failures during the setup phase are persisted too. On `docker compose up` non-zero exit, automatically captures `docker compose logs --tail=200` for every service. Path written as the first line in the wizard's log pane (`📝 session log: /tmp/genai-vanilla-launch-<…>.log`).
- **Per-service color-coded log pane**: `LogPane._write_record` now matches the compose `<container>   | <body>` pattern and colors the container-name prefix using `palette.color_for_source(rec.source)`. Hash-based fallback (md5) gives every service — including ones not in the curated `SOURCE_COLORS` map (jupyterhub, openclaw, local-deep-researcher, etc.) — a stable distinct hue.
- **Stack-overview Cloud APIs sub-section**: `bootstrapper/ui/textual/widgets/info_box.py:CloudApisRow` shows OpenAI / Anthropic / OpenRouter status (`enabled · key set ✓`, `disabled`, `enabled · key MISSING ⚠`) below the services grid. Footer count line gains a `N cloud apis on` segment.
- **Validator auto-disable for `enabled+empty-key`**: `services/source_validator.py:_enforce_cloud_keys_present` flips `CLOUD_*_SOURCE=enabled` back to `disabled` when the matching `*_API_KEY` is empty (with a warning), guarding against unusable launch state from hand-edited .env or CLI-flag misuse.
- **Cloud `/v1/models` fallback diagnostics**: `bootstrapper/utils/cloud_models.py` now accepts an `on_warn` callback. The wizard registers a sink (`integration._set_wizard_warn_sink`) that routes failures into `_safe_log` so they land in both the log pane and `/tmp/genai-vanilla-launch-*.log` — e.g. `[warn/openai-fetch] live /v1/models failed — falling back to catalog (cause: HTTP 401 Unauthorized)`. Distinguishes empty-key, transport, JSON, missing-`data[]`, and post-filter empty-set failures.

### Changed (wizard rework)
- **Wizard step ordering**: cloud secret + multi-select pairs (OpenAI / Anthropic / OpenRouter) are spliced **immediately after the LLM Engine + Ollama steps**, not after every other service-source step. New flow: base port → ComfyUI → LLM Engine → Ollama variants → cloud key+models pairs → other services → cold/hosts/confirm.
- **Cloud providers re-classified as APIs, not services**: removed from `bootstrapper/ui/state_builder.py:_SERVICES`. They no longer appear in the services grid, footer counts, or no-TUI pre-launch summary table — instead they render in their own "Cloud APIs" block.
- **Catalog mount path**: `llm-catalog-init` mounts `./bootstrapper/utils:/catalog:ro` (sibling to `/scripts`) instead of layering `llm_catalog.py` inside the `/scripts:ro` mount. Avoids a Docker file-on-dir overlay edge case that silently broke first-run launches.
- **`docker compose` flags in wizard launch**: `--ansi=always` → `--ansi=never`. The animated TTY-based progress is incompatible with our Popen-piped stdout (compose reports `failed to get console: provided file is not a console` and exits 1). Per-service coloring is now synthesized client-side via `palette.color_for_source` instead of relying on compose's embedded ANSI codes.

### Fixed (wizard regressions discovered + fixed during this round)
- **`DuplicateIds` crash on consecutive secret prompts** (`prompt_panel.py`): widgets were re-mounted per step but `Container.remove_children()` is async — the previous step's `Input(id="secret-input")` was still in the node list when the next step's mount tried to register the same id. Switched to widget-reuse: persistent `_number_input` / `_secret_input` / hint Statics created once and re-shown per step.
- **`NameError: PromptOption is not defined`** in `wizard_screen.py:_load_current_step` splash branch: missing import, now added.
- **`'NoneType' object has no attribute '__dict__'`** in `llm-catalog-init`'s `load_catalog()`: Python 3.12's `@dataclass` decorator (with `from __future__ import annotations`) calls `dataclasses._is_type` → `sys.modules.get(cls.__module__)`. Module loaded via `importlib.util.spec_from_file_location()` wasn't registered. Fix: `sys.modules["llm_catalog"] = module` before `exec_module()`.
- **Live logs not updating in the wizard pane** after launch: `_run_compose` was on the main async event loop, but `_safe_log` used `self.app.call_from_thread(...)` (designed for worker threads). Calling `call_from_thread` from the same thread silently failed to deliver UI updates. `_safe_log` now checks `threading.current_thread() is threading.main_thread()` and uses a direct `_log_pane.write_log` call when on the main thread, `call_from_thread` from workers.
- **`docker compose up` output not in launch log**: `_run_compose` and `_run_command` wrote directly to `_log_pane.write_log()` instead of routing through `_safe_log()`, so the tee path was bypassed. Fixed.
- **Multi-select state lost on back-then-forward** navigation: `_load_current_step` always rebuilt `default_values` from `original.default_values` instead of honoring the user's prior selection in `self._selections`. Fixed.
- **Text-step empty Enter destroyed existing value**: an empty input on a step with a non-empty `default_value` returned `""` instead of a `<KEEP>` sentinel, silently wiping `OLLAMA_CUSTOM_MODELS` on re-runs. Now uses the same keep-current sentinel as the secret step.
- **`will_run_wizard` ignored `--*-models` flags**: passing `--openai-models gpt-5` alone (no source flag) triggered the wizard, silently overriding the CLI value. The detection now also considers `user_model_selections` and `cloud_api_keys`.
- **Cloud provider "enabled but unusable" on CLI-flag mode**: `--openai-api-key sk-…` without `--openai-models` left zero rows active in `public.llms` (cloud entries default to `default_active=False`). `apply_cloud_selection` now activates the catalog's `default_active=True` set when the user enables a provider with no model override.
- **`skip_if_prev` could crash the wizard**: any exception in the predicate would propagate. Both forward (`_load_current_step`) and backward (`action_back`) navigation now catch exceptions and treat them as "don't skip".
- **`OLLAMA_PULL_SCALE` ran for host-side Ollama upstreams**: `service_config.py` set the scale to `1` whenever `LLM_PROVIDER_SOURCE != 'none'`, so `ollama-pull` would attempt `/api/pull` against the user's `ollama-localhost` / `ollama-external` instance — surprising behaviour, and contradicted the `.env.example` text + `docs/services/ollama.md`. Restricted to `ollama-container-*` only. (Subsequent change registers host-side custom Ollama rows in `public.llms` with a warning that the operator must `ollama pull` themselves; see the Changed section below.)
- **`litellm-init` torn-write hazard**: a crash between writing the sentinel header and `yaml.safe_dump` left a sentinel-marked but body-less `config.yaml`, which `litellm_config_generator._is_litellm_init_managed` would *preserve* on subsequent runs — persisting a broken config indefinitely. `write_config` now writes to `config.yaml.tmp` and `os.replace()`s atomically.
- **Backend memory extraction broken in cloud-only setups**: `MemoryService._get_extraction_model` queried `WHERE provider='ollama'`, so cloud-only setups (Ollama rows deactivated) fell through to the hardcoded `ollama/qwen3.6:latest` — a model not in LiteLLM's model_list, causing extraction to fail. Now queries all providers; per-provider name mapping mirrors `litellm-init/scripts/init.py:render_model_list`.
- **Wizard could record inert cloud model selections**: when `CLOUD_*_SOURCE=disabled` in .env but the API key was already set, the secret-step's "keep current" sentinel let the multi-select render → user picked models → `_selections_to_args` recorded `*_USER_MODELS` but didn't enable the source → `llm-catalog-init` then deactivated everything for that provider. Skip predicate now consults the .env source state; auto-promotes to `enabled` when the user proceeds past a SECRET_KEEP step that already has a key.
- **Stale async fetch worker pollutes provider cache**: a slow `/v1/models` worker dispatched before the user pressed Esc → changed key → revisited the step would write its (now-stale) options into the cache the user had just invalidated. Added a generation token bumped by `action_back`; workers compare-then-write and silently drop on mismatch.
- **Setup-phase wizard warnings dropped from session log**: the launch-log file was only opened during the setup→launch transition, so cloud `/v1/models` fetch failures during the wizard's setup phase were silently lost — contradicting troubleshooting docs that promised the file captured everything. Tee now opens at wizard start; the announce-in-pane line moves to the launch transition (when the pane exists). The file is also closed on setup-phase quit.
- **Migration constraint check could falsely no-op**: `05a-public-tables-migrations.sql` and `sync-catalog.py:verify_constraint` checked only `pg_constraint.conname`; if any other table somehow had the same constraint name, the guard would skip the ALTER. Both call sites now scope by `conrelid = 'public.llms'::regclass`.

### Changed
- **Validator side effects split off**: `SourceValidator.validate_all_sources()` is now read-only. The auto-disable-cloud-providers-with-missing-keys behaviour moved to `enforce_runtime_invariants()` — `start.py` calls both, but pure-tooling callers (linters, dry-runs) can validate without mutating .env.
- **Cloud APIs overview live-updates on multi-select 0-selection**: unchecking every model in a cloud provider's multi-select now flips the matching Cloud APIs row to `disabled` immediately (matching the `_selections_to_args` policy that treats empty CSV as "user wants this provider off"), instead of waiting until launch to surprise the user.
- **Command summary covers cloud + Ollama selections**: `--cloud-X-source enabled/disabled`, `--X-api-key <set>` (sanitized; never the raw key), `--X-models N selected (...)`, `--ollama-models`, `--ollama-custom-models`. The "equivalent CLI" preview is equivalent again.
- **Better Ollama-discovery UX on failure**: the unified Ollama multiselect's options provider no longer returns an empty list silently. On `/api/tags` failure or empty result, surfaces a placeholder row explaining what went wrong and routes the diagnostic through the same launch-log sink the cloud steps use.
- **Custom Ollama models on host-side upstreams**: previously dropped silently with a warning. Now registered + active in `public.llms` with a loud warning that the operator must `ollama pull <name>` themselves on the host (since `ollama-pull` doesn't run for host-side sources). Matches the wizard's catalog-multiselect behaviour for localhost/external.
- **Stale-actives warning on Ollama upstream switch**: switching `LLM_PROVIDER_SOURCE` (e.g. container → localhost) without supplying `OLLAMA_USER_MODELS` now warns about every preserved active row that may not exist on the new upstream.
- **`volumes/api/kong-dynamic.yml` is now a pure runtime artifact** (`.gitignore`d, regenerated on every `./start.sh`). Direct `docker compose up` from a clean checkout is unsupported — `docs/services/kong.md` updated; `docs/scripts/check-kong-routes.py` was rewritten to invoke the kong generator against `.env.example` in a tmp dir and validate that, instead of reading the user's runtime file.
- **`bootstrapper/utils/cloud_providers.py`** — single source of truth for cloud LLM provider tuples (display name, source var, API key var, enabled flag var). Replaces three separate per-shape lists in `state_builder.py`, `source_validator.py`, and `service_config.py`.
- **Source-aware secret-step hints** — cloud key prompts now show distinct wording for `enabled+key` ("Enter keeps enabled"), `disabled+key` ("Enter enables with saved key"), and `disabled+no-key` ("Press Enter (empty) to leave disabled"). Driven by a new optional `secret_keep_hint` field on `PromptStep`.
- **Live-discovered cloud / Ollama models now insert if missing** — `llm-catalog-init/scripts/sync-catalog.py:insert_live_only` adds rows for selections that aren't in the curated catalog with provider-specific generic capability defaults (`LIVE_DEFAULTS`). Per-provider routing in `litellm-init` is unchanged. Logs report `N requested, M matched in catalog, K inserted as live-only`.
- **`MemoryService` raises instead of silent fallback** — `_get_extraction_model` previously returned `ollama/qwen3.6:latest` on any DB error, which is unroutable in cloud-only setups. Now logs the underlying exception and raises `RuntimeError` with a clear message about setting `LITELLM_DEFAULT_MODEL` or activating a content row.
- **Multi-select hidden-defaults guard** — `prompt_panel.py` now intersects `default_values` with the visible option set when loading a multi-select step. Previously, default values not present in the live-fetched options stayed invisibly checked and leaked into the saved CSV at confirm.
- **Compose `${VAR-default}` semantics** — `docker-compose.yml` switched both `LITELLM_OLLAMA_UPSTREAM` substitutions from `${VAR:-default}` to `${VAR-default}` (no colon) so an explicit empty value reaches the LiteLLM container as `""`. The `:-` form silently substituted the default for empty too, breaking the documented "none → empty → no Ollama upstream" semantic.
- **OpenRouter ID double-prefix guard** — `cloud_models.py:list_openrouter_models` now skips the `openrouter/` prefix when the upstream's `id` already starts with it, preventing `openrouter/openrouter/...` if the API response shape ever changes.
- **Cloud APIs overview live-updates on auto-promote** — when the user proceeds past a `disabled+key` cloud secret step (SECRET_KEEP) and the multiselect renders, `_apply_secret_step_to_cloud_apis` and `_apply_models_step_to_cloud_apis` now flip the overview row to "enabled" immediately so the live state mirrors the launch outcome. Also extracted `_refresh_info_panel` to consolidate four duplicated update blocks.
- **Single unified Ollama models picker with `[pulled]` / `[library]` badges** — replaces the previous two-page `pulled` + `library` split, which produced two near-duplicate multi-select pages for `ollama-localhost` / `ollama-external` users (the library was a strict superset of `/api/tags`). Now: container modes show the library scrape only; localhost/external show a merged view where `[pulled]` rows are on disk on the user's upstream and `[library]` rows are catalog entries that need a manual `ollama pull`. Step constants `OLLAMA_LIVE_TITLE` and `OLLAMA_CATALOG_TITLE` collapse into a single `OLLAMA_MODELS_TITLE`.
- **Multi-select scrolling fix** — the option-list container is now a `VerticalScroll` with `max-height: 18` and the focused row is `scroll_visible()`'d after every `move()`. Previously a 230-entry library scrape grew the panel past the viewport and pressing Down moved the cursor off-screen invisibly.

### Deferred / known limitations
- **`utils/cloud_models.py --check` self-test CLI** — useful for triage; not shipped this round.

### Cleanup
- **Dropped 7 non-default Ollama catalog entries** (`llama3.3`, `llama3.2`, `mistral-small`, `phi4`, `qwen3.6:7b`, `deepseek-r1`, `mxbai-embed-large`). Superseded by the live `ollama.com/library` scrape; never sat in `default_active`. `OLLAMA_DEFAULT_CATALOG` now contains only the default-active trio.
- **Removed dead `_changed_count` method** (`wizard_screen.py`) — defined but never called from anywhere. Pre-existing dead code.
- **Removed dead `ensure-litellm-db.sh`** — replaced by `litellm-init/scripts/init.py`.
- **Removed `LITELLM_INIT_IMAGE` from `.env.example`** — no longer used since `litellm-init` builds from a Dockerfile instead of `image:`.
- **Splash label deduplication** — wizard's `⏳ Fetching <provider> models…` splash now strips the redundant " Cloud" suffix from cloud provider names.

### Added
- **LiteLLM Gateway** (mandatory core service): always-on OpenAI-compatible front door for every LLM provider. Pinned image `ghcr.io/berriai/litellm:v1.83.14-stable.patch.2`, listening on port 63012 (the slot formerly held by Ollama). Persistence on a dedicated `litellm` database in the existing Supabase Postgres (Prisma migrations run automatically); response caching + rate-limit state in Redis.
  - **Wizard model**: LiteLLM is a locked tile (no source toggle). A separate **LLM Engine** tile single-selects the local Ollama upstream (`ollama-container-cpu`, `ollama-container-gpu`, `ollama-localhost`, `ollama-external`, `none`). Three new **Cloud APIs** (OpenAI / Anthropic / OpenRouter) appear in a dedicated overview block rather than as service tiles — each is a secret-input + multiselect pair that toggles the corresponding provider in LiteLLM's `model_list`. Bootstrapper refuses to start when no upstream is configured (engine=`none` + every cloud provider disabled).
  - **CLI flags**: `--llm-provider-source` enum dropped `api`/`disabled`, added `none`. New flags `--cloud-openai-source`, `--cloud-anthropic-source`, `--cloud-openrouter-source` (each `enabled`/`disabled`).
  - **Master key**: bootstrapper auto-generates `LITELLM_MASTER_KEY` (`sk-…`) on first start and never overwrites it on subsequent runs.
  - **Documented backup**: Portkey AI Gateway (Apache-2.0) — switch path noted in `docs/services/litellm.md`.
- **`vllm-container-gpu` upstream** is deferred to a follow-up plan (tracked in ROADMAP).
### Changed (LiteLLM migration)
- **Consumer env-var rename (breaking)**: every service that talks to an LLM now reads `LITELLM_BASE_URL` + `LITELLM_API_KEY`. The legacy `OLLAMA_BASE_URL` / `OLLAMA_ENDPOINT` env vars are removed from all consumer compose blocks (`open-web-ui`, `backend`, `n8n`, `n8n-worker`, `n8n-init`, `jupyterhub`, `local-deep-researcher`, `openclaw-gateway`, `weaviate-init`, `weaviate`).
- **`LLM_PROVIDER_PORT` renamed to `LITELLM_PORT`** (same default 63012). `bootstrapper/core/port_manager.py` and `.env.example` updated.
- **Backend memory service refactored** (`backend/app/memory_service.py`, `memory_store.py`): switched from Ollama's native `/api/generate` + `/api/embeddings` to LiteLLM's OpenAI-compatible `/v1/chat/completions` + `/v1/embeddings`. All 7 Weaviate collection schemas migrated from `text2vec-ollama` (with `apiEndpoint`) to `text2vec-openai` (with `baseURL` pointed at LiteLLM). New helper `_litellm_complete()` consolidates the chat completion call sites.
- **Local Deep Researcher** now uses the OpenAI-compatible LangGraph client pointed at LiteLLM (`init-config.py` writes `llm_provider=openai`; entrypoint healthchecks `LITELLM_BASE_URL/health/liveliness`).
- **Weaviate** default vectorizer is now `text2vec-openai` (LiteLLM-backed). `text2vec-ollama` is left enabled for backward-compat with un-migrated collections.
- **n8n research workflow** (`searxng-research-workflow.json`) now POSTs to `${LITELLM_BASE_URL}/v1/chat/completions` with `Authorization: Bearer …`; response parsing handles OpenAI's `choices[].message.content` shape.
- **JupyterHub startup script and notebooks** rewritten to expose `LITELLM_BASE_URL` / `LITELLM_API_KEY` and `OPENAI_API_BASE` / `OPENAI_API_KEY` (so the `openai` Python SDK and LangChain OpenAI clients work unchanged). `01_ollama_basics.ipynb` renamed to `01_litellm_basics.ipynb`. The deeper `ollama.chat` / `ChatOllama` examples in `01_litellm_basics.ipynb` and `02_langchain_rag.ipynb` still need a content rewrite to use `OpenAI()` / `ChatOpenAI()` clients (env vars are correct, code samples need a follow-up pass).
- **`check-compose-source-deps.py`** gained 12 new `REQUIRED_DEPENDS_ON` tuples enforcing that every LLM consumer hard-depends on `litellm`. Ollama remains in `FORBIDDEN_OPTIONAL_DEPENDS_ON` (still source-replaceable).
- **Migration note for existing users**: bump your `.env` by either copying the new `.env.example` or running `./start.sh --cold`. `OLLAMA_ENDPOINT` is gone; `LLM_PROVIDER_PORT` becomes `LITELLM_PORT` (same value).
- **OpenClaw AI Agent**: AI agent for messaging platforms (WhatsApp, Telegram, Discord, etc.)
  - Connects to messaging apps for AI-powered chat, file management, and task automation
  - Web dashboard for administration at `openclaw.localhost`
  - LLM integration: inherits stack's Ollama endpoint, supports Anthropic/OpenAI API keys
  - SOURCE options: `container`, `localhost` (Node.js 22+), `disabled` (default)
  - CLI option: `--openclaw-source [container|localhost|disabled]`
  - Default ports: 63024 (gateway, offset +24), 63025 (bridge, offset +25)
  - Kong routing via `openclaw.localhost` subdomain
- **JupyterHub Data Science IDE**: Interactive Jupyter Lab environment with pre-configured AI/ML libraries
  - 7 sample notebooks demonstrating all service integrations (Ollama, Weaviate, Neo4j, Supabase, ComfyUI, n8n, SearxNG)
  - Pre-installed libraries: Ollama, LangChain, LlamaIndex, Transformers, Weaviate client, Neo4j driver, and more
  - Kong routing support via `jupyter.localhost` domain
  - Persistent workspace with Docker volumes (`jupyterhub-data`)
  - Adaptive service that auto-configures based on available AI services
  - CLI option: `--jupyterhub-source [container|disabled]`
  - Default port: 63048 (offset +48 from base port)
  - Environment check notebook for service connectivity verification
- **Textual-based bootstrapper TUI**: A single Textual app (`bootstrapper/ui/textual/`) now owns the entire interactive experience — wizard prompts, the CLI-flag launch screen, the pre-launch pipeline (apply overrides → validate → ports → kong → supabase keys → hosts → encryption → localhost), and the live `docker compose` build / up / verify / `logs -f` stream — all rendered in one screen with a pinned info-box, a service overview, and a bordered log pane with filter chips. Press `ctrl+q` to detach (the stack keeps running). `--no-tui` falls back to a linear stdout flow for CI / non-TTY shells.
- **Brand customization via `BRAND_*` env vars**: The wizard's brand panel and info-box title / subtitle metadata (brand name, tagline, version, author, author email, license, repo URL) is overridable via `BRAND_NAME`, `BRAND_TAGLINE`, `BRAND_VERSION`, `BRAND_AUTHOR`, `BRAND_AUTHOR_EMAIL`, `BRAND_LICENSE`, `BRAND_REPO_URL` in `.env`. Defaults are GenAI Vanilla; forks can rebrand without code changes.
- **Always-on Supabase services in the bootstrapper overview**: `Supabase Auth`, `Supabase API`, `Supabase Realtime`, `Supabase Storage`, and `Supabase Meta` are now surfaced as rows in both the Textual `ServiceTable` and the `--no-tui` summary table, alongside Supabase DB and Studio.
- **`docs/scripts/check-compose-source-deps.py`**: Preventative linter that verifies `docker-compose.yml` does not declare hard `depends_on` edges from any service to a SOURCE-replaceable provider, and that core `depends_on` edges are still in place.
- **`docs/scripts/check-kong-routes.py`**: Preventative linter that verifies the Kong route generator (`bootstrapper/utils/kong_config_generator.py`) produces the documented default routes for `comfyui.localhost`, `n8n.localhost`, `search.localhost`, `jupyter.localhost`, `api.localhost`, and `chat.localhost`. (Initially validated a checked-in Kong fallback file; rewritten later in this same release to invoke the generator against `.env.example` in a tmp dir — see the matching entry under `### Changed`. Both entries describe the same checker; the file is now generated-only.)
- **`docs/deployment/ports-and-routes.md`**: Canonical reference for `BASE_PORT` math, every service's direct localhost URL, and Kong host routes.
- **Per-service documentation expansion** under `docs/services/`: `backend.md`, `comfyui.md`, `local-deep-researcher.md`, `multi2vec-clip.md`, `n8n.md`, `ollama.md`, `open-webui.md`, `redis.md`, `searxng.md`, `weaviate.md` now have their own pages alongside the existing in-depth docs.
- **ROADMAP additions**: Tier 1 — unified LLM gateway (LiteLLM, or equivalent) and per-service configuration modularization. Tier 2 — Hermes Agent (Nous Research's programmable agent runtime, with Open WebUI integration link) and MinIO (S3-compatible object storage).
- New documentation structure under `/docs/`, ROADMAP.md, and this CHANGELOG.

### Changed
- **Loosened `depends_on` edges for SOURCE-replaceable providers**: `n8n`, `n8n-worker`, and `jupyterhub` no longer hard-depend on `weaviate` (`jupyterhub` also no longer hard-depends on `ollama` or `neo4j-graph-db`); `weaviate` no longer hard-depends on `multi2vec-clip`. `n8n` / `n8n-worker` / `jupyterhub` now depend on `supabase-db-init` instead of `supabase-db`. Optional consumers use `WEAVIATE_URL` (and equivalent endpoint env vars) plus runtime readiness checks instead of static compose dependencies — the stack still starts when those providers are disabled, localhost-backed, or externalized.
- **Weaviate module configuration now `.env`-driven**: `WEAVIATE_ENABLE_MODULES` and `CLIP_INFERENCE_API` are exposed in `.env.example` and consumed by the Weaviate compose service. Disabling the CLIP provider no longer requires editing `docker-compose.yml` — set `MULTI2VEC_CLIP_SOURCE=disabled`, drop `multi2vec-clip` from `WEAVIATE_ENABLE_MODULES`, and clear `CLIP_INFERENCE_API`.
- **Service-definition consolidation**: `bootstrapper/ui/state_builder.all_services()` is the single source of truth for the canonical service list, consumed by both the Textual `ServiceTable` and the `--no-tui` summary table. No duplicated inline service tables.
- **Single `DEFAULT_BASE_PORT`**: Lives in `bootstrapper/core/config_parser.py`; `start.py` and the wizard import the same constant.
- **README.md restructuring** for better usability and new documentation organization / navigation.
- **Architecture diagrams updated** to include JupyterHub and other recently added services.

### Removed
- **Legacy Rich-based bootstrapper UI** (the Rich `Live` + `readchar` wizard, the `Textual` post-wizard log app, and all of their supporting modules): `bootstrapper/ui/presentation_app.py`, `bootstrapper/ui/log_stream_app.py`, `bootstrapper/ui/select_widget.py`, `bootstrapper/ui/number_widget.py`, `bootstrapper/ui/status_ribbon.py`, `bootstrapper/ui/log_pane.py`, `bootstrapper/ui/info_box.py`, `bootstrapper/ui/palette.py`, `bootstrapper/ui/logo.py`, and `bootstrapper/wizard/tui_wizard.py`. The `GENAI_USE_LEGACY_WIZARD=1` env-var fallback that briefly let users opt back into the Rich Live wizard during the migration is also gone.
- **Earlier obsolete bootstrapper modules folded into the wizard rebuild**: `wizard/interactive_wizard.py`, `wizard/prompts.py`, `wizard/ui_renderer.py`, `utils/scroll_pin.py`, `utils/ansi_filter.py`, `ui/services_poller.py`, `ui/confirm_widget.py`. Pruned dead methods (`up_with_build`, `set_service_state`, `apply_service_snapshot`, `clear_status`, `prompt_confirm`), dead palette helpers (`style_for_service_state`, `dot_for_service_state`, `DOT_STARTING`, `DOT_OFF`, `DOT_UNHEALTHY`, `COLOR_STARTING`), and unused state constants / `ServiceEntry` fields (`SERVICE_STATE_*`, `GROUP_*`, `CATEGORY_*`, `state`, `group`, `category`, `is_default_source`, `endpoints`).

### Fixed
- **Kong route generator now honors `COMFYUI_LOCALHOST_URL`**: `bootstrapper/utils/kong_config_generator.py` previously hardcoded `http://host.docker.internal:8000/` for the `comfyui-api` route under `COMFYUI_SOURCE=localhost`, ignoring any `.env` override. It now parses `COMFYUI_LOCALHOST_URL` and uses its host:port for both the Kong service URL and the localhost reachability probe (matching the openclaw generator's per-service env-var pattern).
- **LiteLLM crash-loop on first launch via the TUI**: the wizard pipeline (`bootstrapper/ui/textual/screens/wizard_screen.py`) never called `generate_litellm_configuration`, so `volumes/litellm/config.yaml` was never written before `docker compose up`. Docker's bind-mount then created an empty *directory* at the source path, and the LiteLLM container died with `IsADirectoryError: '/app/config.yaml'`. The wizard's `steps` list now runs the generator right after Kong (matching the linear `start.py` flow), and `LiteLLMConfigGenerator.write_config` self-heals: if the destination already exists as an empty directory, it `rmdir`s it and writes a real file. Non-empty directories raise a clear error rather than silently no-oping.
- **Supabase keys now auto-generate on first launch without `--cold`**: `bootstrapper/start.py:validate_supabase_keys` previously generated missing JWT keys only on cold start, leaving fresh-clone users with an opaque "Missing Supabase keys" error on no-flag `./start.sh`. It now auto-generates whenever all three of `SUPABASE_JWT_SECRET` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_KEY` are blank — the fresh-clone case. Mixed state (some set, some blank) is detected and refused with a directive to run `./bootstrapper/generate_supabase_keys.sh`, since the generator HMAC-signs the anon and service keys with the JWT secret and silently rewriting all three would clobber hand-pasted values. Cold start is unaffected (it wipes `.env` first, so its keys come back via the same all-blank path).

### Dependencies
- Added `textual >= 0.85` — owns the entire wizard / launch / log-streaming experience.
- Removed `readchar` (was used by the now-deleted Rich Live prompt widgets).
- Removed `InquirerPy` (replaced earlier in this `[Unreleased]` cycle).
- Bumped `requires-python` from `>=3.8` to `>=3.10` (Textual minimum and current LTS floor; the intermediate `>=3.9` bump landed first then was tightened to `>=3.10` when the dependency upgrade pass below required it).

## [2.0.0] - 2025-08-31 (Python Migration & Modular Architecture)

### Added

#### Python migration
- **Cross-platform Python bootstrapper**: Complete migration from Bash to Python for start/stop scripts
- **UV package manager support**: Automatic detection and use of UV for better dependency management
- **Enhanced error handling**: Better error messages and recovery mechanisms
- **Consistent behavior**: Same functionality across Windows, macOS, and Linux

#### Dynamic Kong configuration
- **Intelligent routing**: Kong routes dynamically generated based on SOURCE values
- **Health checking**: Automatic localhost service availability checking
- **Adaptive configuration**: Routes automatically removed for disabled services
- **No manual configuration**: Replaced static kong.yml/kong-local.yml files

#### CLI SOURCE overrides
- **Command-line configuration**: Override .env settings via CLI arguments
- **Temporary sessions**: CLI overrides don't modify .env file
- **All SOURCE types supported**: Complete CLI coverage for all service sources
- **Usage examples**: CLI documentation with common patterns

#### Enhanced service management
- **ComfyUI-init for all sources**: Model downloading for both container and localhost setups
- **Better dependency resolution**: Automatic service dependency management
- **Improved startup order**: Cold start cleanup moved to proper execution phase

### Changed

#### Project structure
- **Reorganized bootstrapper**: New `bootstrapper/` directory with Python modules
- **Service utilities**: `bootstrapper/utils/kong_config_generator.py` for dynamic configuration
- **Moved scripts**: `generate_supabase_keys.sh` relocated to `bootstrapper/`
- **Modular architecture**: Clear separation of concerns in codebase

#### Kong gateway
- **Dynamic route generation**: Routes created based on active services
- **SOURCE-aware**: Different routing strategies for container/localhost/external sources
- **WebSocket support**: Proper WebSocket routing for realtime services
- **Authentication handling**: Dynamic auth configuration per service

#### Service configuration
- **SOURCE system refinement**: Clear documentation of which services support localhost
- **Localhost support clarification**: Only Ollama, ComfyUI, and Weaviate support localhost SOURCE
- **Container-only services**: N8N, SearxNG, Open-WebUI, Backend API are container-only
- **External URL support**: Proper handling of external service configurations

### Fixed

#### Startup issues
- **Cold start port conflicts**: Fixed cleanup order to occur before port checking
- **Service initialization**: ComfyUI-init now runs for localhost ComfyUI setups
- **Port management**: Better handling of port conflicts and base port configuration

#### Integration issues
- **Kong routing**: Fixed localhost service routing through Kong gateway
- **Service discovery**: Proper health checking for localhost services
- **Cross-service communication**: Improved service-to-service connectivity

#### Documentation
- **Corrected SOURCE support**: Fixed incorrect localhost support claims
- **Updated examples**: All examples reflect new dynamic configuration approach
- **Consistent terminology**: Standardized language throughout documentation

### Removed

#### Obsolete files
- **Static Kong configuration**: Removed `volumes/api/kong.yml` and `volumes/api/kong-local.yml`
- **Dual configuration approach**: Eliminated the "relic" dual Kong config system
- **Manual route configuration**: Removed need for manual Kong route management

#### Cleanup
- **Unnecessary Kong routes**: Removed routes for Weaviate and Neo4j (not user-facing)
- **Duplicate documentation**: Consolidated multiple sections about same services
- **Outdated references**: Removed references to legacy Bash-only approach

## [1.5.0] - 2025-07-29 (Service Integration & Workflow Enhancement)

### Added

#### n8n workflow automation
- **Complete n8n integration**: Workflow automation with queue management
- **Redis queue backend**: Distributed task processing with n8n-worker
- **Pre-built workflows**: Ready-to-use AI workflow templates
- **Kong gateway routing**: Access via n8n.localhost subdomain

#### ComfyUI image generation
- **Full ComfyUI integration**: AI image generation with workflow support
- **Multiple deployment options**: Container CPU/GPU and localhost support
- **Model management**: Automatic model downloading and caching
- **API integration**: REST API access and workflow execution

#### SearxNG privacy search
- **Privacy-focused search**: Local search aggregation without tracking
- **Multiple search engines**: Aggregated results from various sources
- **API access**: Programmatic search capabilities for AI workflows
- **Rate limiting**: Built-in protection against abuse

#### Open WebUI enhancement
- **Research tools integration**: AI-powered research capabilities
- **ComfyUI tool integration**: Direct image generation from chat
- **Multi-LLM support**: Support for various LLM providers
- **Custom tool development**: Framework for adding new AI tools

### Changed

#### Architecture improvements
- **Service modularity**: Better separation between services
- **Docker network optimization**: Improved inter-service communication
- **Volume management**: More efficient data persistence
- **Resource allocation**: Better memory and CPU management

#### Configuration enhancement
- **Environment-based scaling**: Services scale based on SOURCE configuration
- **Dependency management**: Automatic service dependency resolution
- **Health monitoring**: Better service health checking and recovery

### Fixed

#### Bug fixes
- **Service startup order**: Fixed dependency-based startup sequencing
- **Memory management**: Resolved OOM issues with large models
- **Network connectivity**: Fixed inter-service communication issues
- **Volume permissions**: Resolved file permission problems

## [1.0.0] - 2025-04-26 (Initial Release)

### Added

#### Core foundation
- **Supabase ecosystem**: Complete database, auth, and storage solution
- **Kong API Gateway**: Centralized API management and routing
- **Ollama integration**: Local LLM inference with CPU/GPU support
- **Docker Compose architecture**: Complete containerized environment

#### Database services
- **PostgreSQL**: Primary database with Supabase extensions
- **Neo4j**: Graph database for relationship modeling
- **Redis**: Caching and session management
- **Real-time subscriptions**: WebSocket-based live data updates

#### Authentication and security
- **Supabase Auth**: Complete authentication system
- **JWT token management**: Secure API access tokens
- **Role-based access**: User roles and permissions
- **API key authentication**: Service-to-service security

#### Development tools
- **Supabase Studio**: Database management interface
- **Environment configuration**: Flexible .env-based setup
- **Docker orchestration**: Multi-service container management
- **Development scripts**: Easy start/stop scripts

### Infrastructure

#### Container architecture
- **Service isolation**: Each component in dedicated container
- **Network segmentation**: Proper Docker networking
- **Volume persistence**: Data persistence across restarts
- **Resource management**: Memory and CPU optimization

#### Configuration management
- **Environment variables**: Centralized configuration
- **Service discovery**: Automatic service registration
- **Port management**: Configurable port assignments
- **Cross-platform support**: Works on macOS, Linux, and Windows

---

## Migration Guide

### From 1.x to 2.0 (Python Migration)

**Required Actions:**
1. **Update start/stop usage**: New CLI arguments available
2. **Check SOURCE configurations**: Verify localhost support for your services
3. **Update hosts file**: Run `./start.sh --setup-hosts` for *.localhost domains
4. **Review Kong routes**: Routes now generated dynamically

**Optional Improvements:**
- Install UV package manager for better dependency management
- Use new CLI SOURCE overrides for easier configuration
- Leverage new troubleshooting documentation

**Breaking Changes:**
- Static `kong.yml` files no longer used (automatically migrated)
- Some services no longer support localhost SOURCE (see documentation)
- `generate_supabase_keys.sh` moved to `bootstrapper/` directory

### Compatibility Notes

- **Environment files**: Existing `.env` files remain compatible
- **Data volumes**: All data preserved across updates
- **Service APIs**: No changes to service endpoints or functionality
- **Docker images**: Updated but backward compatible

---

## Acknowledgments

### Contributors
- Core development team
- Community contributors
- Beta testers and early adopters

### Special Thanks
- Open source projects that make this stack possible
- Community feedback and feature requests
- Documentation contributors and reviewers

---

*For more details on any release, see the corresponding [GitHub release](https://github.com/thekaveh/genai-vanilla/releases) or [documentation](README.md).*