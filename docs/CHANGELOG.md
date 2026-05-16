# Changelog

All notable changes to the GenAI Vanilla Stack will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-05-15 (Topology-Driven Ordering & Port Layout v1)

**Visual:** every service row in the setup wizard now leads with a thin category-color bar; six categories (Infra, Data, LLM Core, Media, Agents & Workflows, Apps & UIs) explained in a legend below the grid. Unanswered configurable services show a yellow ◌ placeholder ("pending") instead of guessing their port/source/alias before you've picked them.

**Ordering:** display order — and the wizard's question sequence — is now derived from each `service.yml`'s `depends_on:` and `category:` fields. The hand-edited `services/_order.yml` has been retired.

**Port renumbering:** default ports are computed from a per-category slot allocator, not hand-edited per manifest. On first start after this upgrade, your existing `.env` is auto-rewritten with the new defaults (a backup is taken to `.env.backup.<timestamp>`). User-customized port values (i.e., not matching the old default) are preserved untouched. Pass `--no-port-migrate` if you want to opt out of the rewrite.

To roll back: `cp .env.backup.<timestamp> .env && sed -i '' '/BOOTSTRAPPER_PORT_LAYOUT_VERSION/d' .env` (or simply delete the sentinel line so the migration re-applies on next start).

**Aliases:** eight new `*.localhost` aliases — studio, graph, weaviate, ollama, stt, tts, docling, research. Total alias count goes from 10 to 18. Run `--setup-hosts` to add them to `/etc/hosts`. Each alias works in both container and host-install (`-localhost`) modes — Kong proxies through `host.docker.internal` to the user's host port when the source is `-localhost` (Kong's compose now declares `extra_hosts: ["host.docker.internal:${HOST_GATEWAY_IP}"]` so this works on Linux Docker too). `*-external` sources don't get a Kong route — LiteLLM forwards those itself.

**Internals:** eight scattered metadata constants across `bootstrapper/` (`_SERVICES`, `_HOST_ALIAS`, `DISPLAY_NAME_OVERRIDES`, `SERVICE_DESCRIPTIONS`, `LOCKED_SERVICES`, `LOCALHOST_ENDPOINT_VARS`, `GENAI_HOSTS`, `services/_order.yml`) have collapsed into manifest fields. Adding a new service is now a one-folder operation.

## [Unreleased]

> **Path-reference note:** entries written before the per-service
> configuration-modularization change below reference top-level directory
> names (`hermes-init/`, `litellm-init/`, `llm-catalog-init/`,
> `comfyui-init/`, `n8n-init/`, `weaviate-init/`, `minio-init/`,
> `ollama-pull/`, `open-webui-init/`, `searxng/`, `stt-provider/`,
> `tts-provider/`, `doc-processor/`, `graph-db/`, `backend/`,
> `local-deep-researcher/`, `jupyterhub/`, `n8n/`, `open-webui/`,
> `supabase/`). After this refactor they live under their owning service's
> manifest folder, e.g. `services/litellm/init/scripts/init.py`,
> `services/n8n/init/`, `services/supabase/db/`. The original wording is
> preserved to keep the historical record honest; use `git log --follow`
> on the new path to trace the move.
>
> **Naming:** the doc-processing surface uses three names that all refer
> to the same thing — the retired top-level dir was `doc-processor/`,
> the post-refactor folder is `services/docling/`, the env-var selector
> is `DOC_PROCESSOR_SOURCE` (chooses between `docling-container-gpu` /
> `docling-localhost`), and the human-facing virtual-service docs live
> at `docs/services/doc-processor.md`. The `doc-processor` name is the
> stable public API; `docling` is the single engine implementing it.

### Added (Dependency vulnerability monitoring)
- **`.github/dependabot.yml`** — weekly pip + GitHub Actions scans on every active manifest (`bootstrapper/`, `services/backend/app/`, `services/jupyterhub/build/`, `services/docling/provider/{gpu,localhost}/`, `services/parakeet/provider/{gpu,mlx}/`). Alerts grouped by ecosystem to reduce PR noise. `directories:` deliberately enumerates ALL active manifests so an omission doesn't silently drop coverage from the scan.
- **`SECURITY.md` threat model** — published threat tiers, supported versions, and the responsible-disclosure address. Aligns with the dependabot scan-coverage list.
- **Bulk-dismiss tooling** — operators triaging stale alerts on deleted/moved manifests can use the GitHub REST API with `reason=not_used`; the `docs/security/2026-05-14-dependabot-remediation-report.md` captures the playbook from the May 2026 cleanup (77 alerts triaged, 62 phantom dismissals).

### Added (LiteLLM Kong alias for the admin dashboard)
- **Kong route `litellm.localhost` → `http://litellm:4000/`** — added to `bootstrapper/utils/kong_config_generator.py::generate_litellm_service()` and wired into `get_adaptive_services()`. Always-on (LiteLLM is mandatory; no SOURCE variation, no dashboard-disable toggle). The same alias exposes `/ui/` (admin dashboard with per-model spend, key/team management, request logs), `/v1/*` (proxy API), and `/spend/*` (raw usage telemetry rollups) — Kong routes the entire LiteLLM surface, not just the dashboard path.
- **`litellm.localhost` added to** `bootstrapper/utils/hosts_manager.py::GENAI_HOSTS` so `./start.sh --setup-hosts` writes the `/etc/hosts` entry.
- **Wizard service box** now shows `http://litellm.localhost:${KONG_HTTP_PORT}` in the URL column on the LiteLLM row (was `—` before). Wired via a single `"LiteLLM": "litellm.localhost"` line in `bootstrapper/ui/state_builder.py::_HOST_ALIAS`; downstream rendering (`integration.py` → `service_table.py`) picks it up automatically.
- **Auto-redirect `/` → `/ui/` on the LiteLLM alias** — LiteLLM serves Swagger UI at its root and the admin dashboard at `/ui/`. A bare visit to `http://litellm.localhost:${KONG_HTTP_PORT}/` would otherwise land on Swagger, which is not what operators reaching for the alias expect. A `pre-function` Lua snippet on the Kong route short-circuits the request with a 302 to `/ui/` only when the path is exactly `/`; `/v1/*`, `/spend/*`, and `/openapi.json` fall through to the upstream unchanged. Requires `pre-function` in `KONG_PLUGINS` (already allowlisted in `services/kong/compose.yml`). Operators who want Swagger UI directly can still reach it at the direct port `http://localhost:${LITELLM_PORT}/`.
- **`preserve_host: True` on the LiteLLM Kong route** — without this, Kong rewrites the `Host` header from `litellm.localhost:${KONG_HTTP_PORT}` (the browser's URL) to `litellm:4000` (the internal upstream). LiteLLM's SPA reads the `Host` header when constructing the SSO login-redirect URL, so it embedded the internal Docker hostname, producing a `Location: http://litellm:4000/ui/login/...` that the browser cannot resolve. Setting `preserve_host: True` makes LiteLLM see the real browser-facing hostname and build correct redirects. Same pattern n8n's route uses.
- **Admin-dashboard login credentials made explicit** — modern LiteLLM versions retired the "master key alone authenticates the UI" fallback; without explicit `UI_USERNAME` + `UI_PASSWORD`, `/v2/login` raises `ProxyException`. Compose now sets `UI_USERNAME: ${LITELLM_UI_USERNAME:-admin}` and `UI_PASSWORD: ${LITELLM_MASTER_KEY}` (reusing the auto-generated master key so operators don't have to remember a second secret). New env `LITELLM_UI_USERNAME` added to `.env.example` and `services/litellm/service.yml`. Login is `admin` / `${LITELLM_MASTER_KEY}` by default; override the username via `.env`.

### Added (MinIO Kong alias for the admin console)
- **Kong route `minio.localhost` → `http://minio:9001/`** — added to `bootstrapper/utils/kong_config_generator.py::generate_minio_service()` and wired into the route orchestrator alongside the other host-aliased services. Gated on `MINIO_SOURCE != disabled`. Uses `preserve_host: True` so the MinIO console SPA constructs login/session URLs against the browser's real hostname instead of the internal `minio:9001` (same pattern n8n / Hermes / LiteLLM use). The S3 API at port 9000 is deliberately NOT aliased — S3 clients use full URLs with explicit ports anyway, and Kong proxying introduces unhelpful preserve-host complications for the S3-signature workflow.
- **`minio.localhost` added to** `bootstrapper/utils/hosts_manager.py::GENAI_HOSTS` (so `./start.sh --setup-hosts` writes the `/etc/hosts` entry) and `bootstrapper/ui/state_builder.py::_HOST_ALIAS` (so the wizard service-box shows `http://minio.localhost:${KONG_HTTP_PORT}` on the MinIO row alongside the direct port). The cross-surface agreement test in `test_kong_and_hosts_wiring.py` enforces the parity automatically.
- **`docs/scripts/check-kong-routes.py::EXPECTED_HOST_ROUTES`** gained the new entry so the audit script enforces the route's continued presence.
- **docs**: `docs/services/minio.md` got an expanded "Endpoints" table covering the new alias + the preserve-host plumbing rationale; `docs/deployment/ports-and-routes.md` gained the Kong column on the MinIO Console row; `docs/services/kong.md` added the dynamic-route bullet + curl example; `services/minio/README.md` got a new `## Access` section; root `README.md` got the alias row in the service table and a quick-start hint.

### Added (Tests for Ollama-LiteLLM-wizard catalog-sync invariants)
- **4 new test files / 19 regression tests** that codify the recent Ollama-discovery bugs as a permanent guard:
  - `bootstrapper/tests/test_wizard_ollama_options.py` (5 tests) — exercises the wizard's `_merged_ollama_options` closure with mocked `/api/tags` + library scrape. Asserts: (a) every host-pulled tag lands in the family's `pulled_variants`; (b) family parent's `[pulled]` badge fires when ANY tag is on host (the "bare family name in pulled_set" bug); (c) bucket-1 fallback for tags whose family isn't in `ollama.com/library` at all; (d) options carry enough info for pre-check seeding.
  - `bootstrapper/tests/test_prompt_panel_leaf_badges.py` (4 tests) — exercises `PromptPanel._leaf_render_data` on a stub. Asserts: per-leaf `[pulled]`/`[library]` reflects `opt.pulled_variants` independently of the parent's status; mixed-status leaves within one family render correctly; empty `pulled_variants` leaves the leaf status-less (fallback to parent).
  - `bootstrapper/tests/test_live_catalog_sync.py` (3 tests, skip-aware) — integration: queries the live host Ollama `/api/tags` and the live LiteLLM `/v1/models`, asserts every host model is published by LiteLLM (auto-import fix), no phantom Ollama models in LiteLLM that aren't on the host or declared in `OLLAMA_USER_MODELS`/`OLLAMA_CUSTOM_MODELS`, AND runs the wizard's actual `options_provider` against the live host to confirm `pulled_variants` matches `/api/tags` reality. Skips cleanly when the stack isn't up.
  - `bootstrapper/tests/test_catalog_init_auto_import.py` (7 tests) — unit tests for `services/litellm/catalog-init/scripts/sync-catalog.py::_fetch_ollama_tags`. Loads the script via `importlib.util.spec_from_file_location` with `psycopg2` stubbed in `sys.modules` so the test runs without the catalog-init container's deps. Covers: happy path, alternate `model` field name, empty upstream, unreachable upstream, malformed JSON, empty URL short-circuit, garbage-entry tolerance.
- Tests are wired into the existing pytest infrastructure; total suite count grew from 126 to **145** (all passing).

### Fixed (Wizard Ollama-models pre-check + per-variant pulled badge)
- **Per-variant `[pulled]` badge under a [library] parent** — the wizard's Ollama-models step computed leaf badges via `_inherited_leaf_badges`, which strips status tags (`pulled`, `library`, `legacy`) under the assumption *"every leaf of a [library] parent is library; the user already sees that on the parent right above"*. That assumption fails when only some specific tags of a family are pulled — e.g. a host with `qwen3.6:35b-a3b-coding-mxfp8` pulled but not `qwen3.6:27b`/`35b`/etc. The family's parent gets `[library]` but the one pulled tag should render `[pulled]` to match reality. Fix: added `pulled_variants: frozenset[str]` to `PromptOption` (populated by the wizard's `_merged_ollama_options` from `/api/tags`), and made `_leaf_render_data` emit per-leaf status (`[pulled]` when `tag in opt.pulled_variants`, else `[library]`). Family parents now show `[pulled]` whenever ANY tag of that family is on the host (was: only when the bare family name itself appeared in `/api/tags`, which it never does).
- **Wizard auto-pre-checks every pulled host model** — `PromptPanel._load_step` for multiselect now seeds `_checked_values` from each option's `pulled_variants` in addition to the static `default_values`. Mirrors the runtime `OLLAMA_AUTO_IMPORT_LOCAL_MODELS` behaviour so the wizard UI tells the same story as `public.llms` will after confirmation. The post-confirm CSV is still the final word — operators who want a model hidden can uncheck it before pressing Enter.

### Added (Ollama auto-import for host-side sources)
- **`llm-catalog-init` auto-imports every model on the host's Ollama** when `LLM_PROVIDER_SOURCE=ollama-localhost` or `ollama-external`. The catalog-init container queries the upstream's `/api/tags` at boot and unions the result with `OLLAMA_USER_MODELS`, so any `ollama pull <name>` you do on the host propagates to `public.llms` → LiteLLM → every consumer on the next `./start.sh` — no wizard re-run required. This makes the host's Ollama instance the authoritative source for which models the stack exposes, instead of relying on the wizard's multiselect to be re-run every time the host catalog changes. Container sources (`ollama-container-*`) skip auto-import because their upstream is populated FROM `OLLAMA_USER_MODELS` by `ollama-pull` (querying it would be circular).
- **`OLLAMA_AUTO_IMPORT_LOCAL_MODELS` env var** (default: `true`) added to `services/ollama/service.yml` + `.env.example`. Set to `false` to keep strict wizard-only control of which models are exposed — useful when you have private fine-tunes on the host that shouldn't be exposed across every stack consumer.
- **`llm-catalog-init` now reaches `host.docker.internal`** — added `extra_hosts: ["host.docker.internal:${HOST_GATEWAY_IP}"]` to the catalog-init container so the new `/api/tags` query works for `ollama-localhost`. The container also receives `LITELLM_OLLAMA_UPSTREAM` (same env-var litellm-init consumes for its rendering), so `ollama-external` is supported through the same code path.
- **`_fetch_ollama_tags()` helper** in `services/litellm/catalog-init/scripts/sync-catalog.py` mirrors `bootstrapper/utils/ollama_discovery.py::list_pulled_models` in shape and failure mode (empty list on any error), so the two sites — the wizard's option list and the catalog's auto-import — fail consistently against the same `/api/tags` endpoint.

### Fixed (log-stream cleanup)
- **Kong DNS error noise during stack restart** — Kong's default `KONG_DNS_NOT_FOUND_TTL=30s` made it cache "name not found" verdicts for half a minute, so an active websocket retry loop (e.g. an Open WebUI tab reconnecting during `./start.sh`) flooded the Kong log with DNS errors until the cache expired. `services/kong/compose.yml` now sets `KONG_DNS_NOT_FOUND_TTL=1` and `KONG_DNS_STALE_TTL=4`, so Kong picks up newly-registered service containers within ~1s instead of ~30s. Error window dropped from 37 seconds / ~18 entries to single-digit retries.
- **Searxng `missing config file: /etc/searxng/limiter.toml`** — Searxng's bot-detection module wants an explicit `limiter.toml` next to `settings.yml`. Without it, Searxng logs the warning on every boot. Added `services/searxng/config/limiter.toml` using the current upstream schema (`[botdetection]` / `botdetection.trusted_proxies`, not the deprecated `[real_ip]` form). Trusted proxies set to Docker bridge subnets only (172.16/12, 192.168/16, 10.0/8); deliberately NOT including 127.0.0.0/8 so Searxng's own loopback healthcheck doesn't trip the X-Forwarded-For warning every check.
- **Searxng Wikidata 403 spam at boot** — Wikidata's SPARQL endpoint rate-limits aggressively and returns 403 with 24-hour suspension on initial engine probe from a new IP. The Searxng wikidata engine eagerly probes the endpoint at `init()`, which fired before any `disabled: true` flag was honored (the disable check is for query-time, not init-time). Removed the engine block entirely from `services/searxng/config/settings.yml`. DuckDuckGo's infobox covers the same UX role. Block-removal commentary inline so operators can restore the engine if they have a dedicated Wikidata arrangement.
- **Searxng X-Forwarded-For "fires once per boot" log line** — this is *not* fixable from outside Searxng. The `log_error_only_once()` call in `/usr/local/searxng/searx/botdetection/trusted_proxies.py:141` is gated to fire exactly once per worker lifetime on the first request that lacks both `X-Forwarded-For` and `X-Real-IP`. Searxng's own internal startup probe (granian's warm-up) hits the worker with no headers before the user's first browser request arrives, so the error always fires once at boot regardless of upstream proxy config. The logger then silences itself for the rest of the container's lifetime. Documented as expected boot-noise; no functional impact.
- **`docs/scripts/check-kong-routes.py::EXPECTED_HOST_ROUTES`** gained the new entry so the audit script enforces the route's continued presence.
- **docs**: `docs/services/litellm.md` got a new `## Access` table; `docs/deployment/ports-and-routes.md` gained the Kong column on the LiteLLM row; `docs/services/kong.md` added the dynamic-route bullet + curl example; `services/litellm/README.md` got a matching `## Access` table for the service-folder reader; root `README.md` got the alias row in the service table.

### Fixed (LiteLLM gateway: empty chat responses, broken tool calls, duplicate Hermes provider)
- **Ollama chat completions returned empty `content`** — every Ollama model was registered in LiteLLM's `model_list` as `model: ollama/<name>`, which makes LiteLLM hit Ollama's `/api/generate` endpoint. That endpoint (a) does not support tool calls, (b) flattens multi-turn message history into a single prompt, and (c) silently drops the Ollama-native `think` parameter. So any thinking-capable model (qwen3, gpt-oss, deepseek-r1) got cut off mid-`<think>` block and returned empty `content`. Hermes Agent, Open WebUI's chat surface, n8n's LLM nodes, and the backend's agentic paths were all affected. Fix: `services/litellm/init/scripts/init.py::render_model_list` now writes `model: ollama_chat/<name>` for chat models (uses `/api/chat`, which supports tool calls, multi-turn, vision payloads, and the `think` param) and keeps `model: ollama/<name>` only for embedding models (the `/v1/embeddings` route refuses the `ollama_chat/` adapter). Detection is name-based: any catalog model with `"embed"` in its name is an embedding model. Additionally, `think: false` is set on every chat entry so thinking models always populate `content` rather than the side-channel `reasoning` field; consumers that want the trace can opt back in per-request with `"think": true`. See `docs/services/litellm.md` → "Ollama adapter choice" and "Thinking models".
- **Hermes Agent registered LiteLLM twice in its provider picker** — `services/hermes/init/templates/config.yaml.tmpl` declared the gateway via both `model.provider: custom` + `base_url: http://litellm:4000/v1` AND a named `custom_providers[] = {name: litellm, base_url: http://litellm:4000/v1}` entry. Hermes's `get_compatible_custom_providers()` dedupe path did not collapse the inline anonymous entry against the named one, so the provider picker showed two `litellm` rows — one with the default model bound, the second orphaned at "0 models". Fix: kept the inline `model.provider: custom` block (Hermes's documented enum is `auto | openrouter | nous | codex | custom` — there's no `litellm` enum value) and emptied `custom_providers`. Future skills that need to address LiteLLM by an explicit named alias can add it back under a non-colliding name (e.g. `litellm-aux`).

### Changed (Per-service configuration modularization)
- **Monolithic `docker-compose.yml` retired** — the 1,425-line file split into per-service fragments under `services/<name>/compose.yml` merged at the top level via native Docker Compose `include:` directive. The new root `docker-compose.yml` is a 55-line shell. Requires Compose v2.21+ (v2.26+ recommended). Byte-equivalent rendering preserved across the full 36-container stack via the golden baseline at `bootstrapper/tests/fixtures/rendered_config_baseline.yml`.
- **`bootstrapper/service-configs.yml` deleted** — each service's runtime data (source variants, adaptive bindings, dependency declarations) now lives in its manifest at `services/<name>/service.yml` under `runtime_sc:`, `runtime_adaptive:`, `runtime_deps:` blocks; the stack-wide tier ordering moved to `services/globals/service.yml` under `runtime_dependency_tiers:`. A new `bootstrapper/services/sc_synthesizer.py` concatenates these slices into the dict shape consumers (`service_config.py`, `source_validator.py`, `dependency_manager.py`, `ui/state_builder.py`, `wizard/llm_steps.py`) used to load from YAML. `ConfigParser.load_yaml_config()` now calls the synthesizer.
- **Each service is now a folder** (`services/<name>/`) containing `service.yml` (manifest — env vars, source variants, image refs, dependencies, plus per-source bootstrapper runtime data under `runtime_sc:`) and `compose.yml` (Compose fragment). 24 manifests total — 21 container-backed + 3 virtual (cloud-providers, tts-provider, globals). Schema-validated against `bootstrapper/schemas/service.schema.json`.
- **`docs/CONTRIBUTING-services.md`** documents how to add a new service.

### Added (config modularization safety net)
- **`bootstrapper/services/manifest_validator.py`** — 8 cross-manifest checks (duplicate env vars, duplicate containers, dangling dependencies, undeclared exports/effects, source-var consistency, unknown consumer references). Runs in CI.
- **`bootstrapper/services/env_assembler.py`** — pure-function .env.example assembler from manifests (library-only).
- **`bootstrapper/tools/validate_fragments.py`** — `python -m tools.validate_fragments` CLI entry.
- **`bootstrapper/tests/`** — 110+ tests: loader, cross-manifest validator, env assembler, validate_fragments CLI, fragment-equivalence (byte-equiv vs golden baseline), source-permutation matrix, env-example consistency (manifest ↔ .env.example parity), backfill interplay (manifest change → backfill → user .env propagation).
- **`.github/workflows/services-lint.yml`** — two CI jobs: `lint` (unit tests + validator + audit scripts) and `compose-equivalence` (rendered byte-equiv + source-permutation matrix).
- **`docs/scripts/check-compose-source-deps.py`** updated to render compose via `docker compose config` so it sees the merged shape rather than only the thin include shell.

### Added (Hermes Agent — auto-pick default model, embedded Chat tab, dual Ollama aliases in LiteLLM)
- **`hermes-init` auto-picks `HERMES_DEFAULT_MODEL` when blank** — without a default, Hermes's rendered `config.yaml` had `model.default: null`, every dispatch 500'd, and Open WebUI's `hermes-agent` proxy route returned errors that looked like "Hermes can't see any models". The init script now queries `http://litellm:4000/v1/models` and picks the first match from a priority list (`ollama/qwen3.6:latest` → `claude-sonnet-4-6` → `claude-opus-4-7` → `gpt-5` → `gpt-5-codex` → `gpt-5-mini` → first-non-`hermes-agent` fallback). Cheapest-local-first, then big-context-cloud. Choice is logged in the init log for traceability. Operator override via `HERMES_DEFAULT_MODEL` in `.env` is preserved verbatim (auto-pick only fires when blank).
- **Ollama models now registered under bare model_name in LiteLLM (in addition to the prefixed form)** — `litellm-init/scripts/init.py:render_model_list` was emitting `model_name: ollama/{name}` for Ollama rows while cloud providers used bare names (`gpt-5`, not `openai/gpt-5`). When a client like Hermes Agent strips the `ollama/` prefix on outbound (treating it as a provider hint) and forwards `qwen3.6:latest` to LiteLLM, the gateway 400'd with `Invalid model name`. Each Ollama row now emits **two** `model_list` entries pointing at the same upstream — `ollama/{name}` (kept for backwards compat: `backend`'s `LITELLM_EMBEDDING_MODEL=ollama/nomic-embed-text`, `weaviate-init`'s `/shared/weaviate-config.env`) plus bare `{name}` (for prefix-stripping clients). Both names route through the same `litellm_params`, so latency/spend tracking stays single-counted.
- **Embedded Chat tab in the Hermes dashboard** — set `HERMES_DASHBOARD_TUI=1` (now the default) to expose the upstream-supported `/chat` route + `/ws/chat` WebSocket inside the dashboard, with a PTY-backed `hermes --tui` session as the backing terminal. Users can talk to the agent directly from the web UI without round-tripping through Open WebUI / curl. Documented in [upstream docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-dashboard); the `ptyprocess` extra ships in `nousresearch/hermes-agent:latest`. Flip to `0` in `.env` for a read-only dashboard.

### Added (Ollama wizard step — search box, MLX badge, cloud-only filter, tag column alignment)
- **Inline search box** above the filter-chip row on the Ollama models step: a 1-cell `Input` (placeholder `Tab or /  to filter models by name…`) that narrows the visible list by case-insensitive substring match against the model name. `Tab`, mouse click, and `/` all focus it; `Tab`, `Enter`, or `Esc` return focus to the option list. The substring filter STACKS with the chip filter — both must match for a row to render. Lives as a persistent `Input` on `PromptPanel` (mounted once, display toggled) to dodge a `DuplicateIds` race on the splash → real-options re-render that the lazy-fetch flow triggers for `options_provider` steps. Focus is explicitly parked on the option list immediately after mount so a freshly-mounted Input never swallows a Space/`j`/`k` the user thought was driving the cursor; the input lights up in bold cyan-on-tinted-bg when it actually has focus.
- **Keystroke routing while search is focused** — `WizardScreen.check_action` whitelists `back` (Esc), `quit_wizard` (Ctrl+Q), `move` (arrow keys), and `toggle_search_focus` (Tab); every other priority-binding (`f`, `a`, `e`, `w`, `i`, `space`, vim-style `j`/`k`) is suppressed so the keystrokes land in the Input as text. The `j`/`k` bindings were split off into a new `vim_move` action specifically so they can be suppressed independently of the arrow-key `move` action. Enter on the focused search input unfocuses (via `PromptPanel.on_input_submitted`) instead of confirming the whole step.
- **`[mlx]` capability badge** — Apple-Silicon-optimised MLX variants are now flagged per-leaf in the variant tree. New parser regex `_VARIANT_MLX_RE` in `bootstrapper/utils/ollama_library.py` detects the upstream `border-neutral-600 … MLX` chip on each variant block of `ollama.com/library/{model}`; `OllamaVariant.mlx: bool` plus the existing `capabilities` property surface the tag. `mlx` is added to `_PER_VARIANT_CAPS` in `prompt_panel.py` so it stays per-variant (NOT inherited from parent to all leaves) since only specific quant tags carry it.
- **Capability column alignment** — capability tags now render in a fixed canonical column order (`embedding · thinking · vision · tools · audio · mlx`) with reserved per-slot widths; absent tags reserve their column so the same capability lands at the same horizontal position across every visible row. Status tags (`pulled` / `library` / `legacy` / `default`) follow with variable width. Start column is computed dynamically by `PromptPanel._mount_visible_rows` — it walks the visible row set, finds the longest prefix+label content, and passes that column to every `OptionRow` so even outlier-length variants like `qwen3.6:35b-a3b-coding-mxfp8 (38GB · 256K ctx)` keep the tag block flush with shorter siblings. Narrow terminals (< 100 cells for parents, < 130 for leaves) fall back to inline variable-width tags to avoid pushing the pull-count column off-screen.
- **Ollama Cloud-exclusive models filtered out** — the live listing-page scrape now flags entries that carry the `cloud` chip AND publish no `x-test-size` variants (e.g. `glm-5`, `minimax-m2`, `kimi-k2`, `deepseek-v4-pro`, …). These cannot be `ollama pull`-ed, so the wizard drops them from the multiselect before render and writes `[info/ollama-fetch] excluded N cloud-only Ollama Cloud model(s) — not pullable: …` to the session log. Hybrid models that publish both cloud and pullable local variants (`gemma3`, `gpt-oss`, `qwen3-coder`, `deepseek-v3.1`, …) keep `cloud_only=False` and remain in the list with their local variants intact. New field `OllamaLibraryEntry.cloud_only: bool`; new regex `_CLOUD_BADGE_RE`; filter applied in `bootstrapper/wizard/llm_steps.py:_fetch_ollama_options`.

### Added (env-file backfill helper)
- **`backfill_missing_env_vars()` on `GenAIStackStarter`** — appends keys present in `.env.example` but missing from the user's `.env`, preserving every existing value. Catches the upstream-merge case where new services land in `.env.example` (MinIO, Hermes, Speaches, Chatterbox, Whisper.cpp) but the user's pre-existing `.env` predates the merge; without backfill, `docker compose up` failed with `service "minio" has neither an image nor a build context specified` because `${MINIO_IMAGE}` was empty. Preserves the source file's section organisation — missing vars are emitted under their original `# === SECTION ===` heading with their immediate context comments intact, ordered by where they appear in `.env.example`. Idempotent; called four times (once at every entry to the `setup_env_file` pipeline + a final defensive call before `docker compose up` so any intermediate write that drops keys is recovered).

### Fixed (service startup)
- **`speaches` restart loop** — the `PRELOAD_MODELS` env in `docker-compose.yml` was a comma-separated CSV (`hexgrad/Kokoro-82M,Systran/faster-distil-whisper-large-v3`), but Speaches types the field as `list[str]` on a `pydantic_settings.BaseSettings` model whose `EnvSettingsSource` decodes complex fields via `json.loads`. The CSV blew up with `JSONDecodeError: Expecting value`. Switched to a JSON-array literal `'[]'` (empty) — the names Speaches expects in `PRELOAD_MODELS` are internal `executor_registry` ids (e.g. `kokoro`), not the HuggingFace ids we keep in `SPEACHES_TTS_MODEL`/`SPEACHES_STT_MODEL` (those go on the request, not the preload). Empty preload matches the existing "lazy-loads on first /v1/audio/* request" comment; users wanting preload can edit the line directly with registry ids.
- **`hermes` healthcheck failing** — the historic `wget -q -O- http://127.0.0.1:8642/v1/models …` probe exited `wget: not found`, and the obvious python fallback hit `python: not found` (the image only ships `python3`). Verified the image actually does ship `curl` (the previous compose comment was wrong on both counts). Switched to `curl --fail --silent --show-error -H "Authorization: Bearer $$API_SERVER_KEY" http://127.0.0.1:8642/v1/models`. Container now `(healthy)`.
- **`hermes-init` was a no-op** — the compose block mounted `./hermes-init/scripts:/scripts:ro` + `./hermes-init/templates:/templates:ro` against an `alpine:latest` image but had **no `entrypoint` or `command`** — the container started, found nothing to run, exited 0 in ~150ms, and `docker compose ps` reported `Exited (0)` looking exactly like a successful init. `/opt/data/config.yaml` was never rendered; `hermes` then fell back to its image's bundled default (`provider: openrouter, default: anthropic/claude-opus-4.7`) and 401-spammed the log indefinitely because `OPENROUTER_API_KEY` was empty. Added `entrypoint: ["/scripts/init-hermes.sh"]` matching the existing `weaviate-init` / `openclaw-init` pattern. The script now actually runs, `/opt/data/config.yaml` renders against the LiteLLM-routed template, no more 401s.
- **`local-deep-researcher` flapping unhealthy on first launch** — the Dockerfile's `HEALTHCHECK --start-period=60s` expired while the entrypoint was still cloning the upstream repo and `uv pip install`-ing 72 packages (numpy, lxml, langchain, langgraph, openai, …) — routinely 2-5 minutes on a clean machine. Bumped to `--start-period=300s`; subsequent restarts hit the cached venv and pass in <10s, so the higher ceiling costs nothing in steady state.
- **`supabase-realtime` libcluster spam every 5 seconds** — the upstream `supabase/realtime:v2.33.72` image hardcodes `Cluster.Strategy.DNSPoll` (the `fly6pn` topology) and ignored our `LIBCLUSTER_STRATEGY` / `LIBCLUSTER_TOPOLOGIES` overrides. With no `DNS_NODES` env set, libcluster logged `query or basename param is invalid: query: nil` on a 5-second cadence. Pointing `DNS_NODES` at the container's own hostname created a different warning (`unable to connect to :realtime@<container-ip>` — Erlang node mismatch). Final fix: `DNS_NODES: supabase-realtime-noop.invalid` — the `.invalid` TLD (RFC 6761) returns NXDOMAIN, libcluster's empty-peer-list path is silent, the env var is set so libcluster considers itself "configured". Dropped the two ineffective `LIBCLUSTER_*` vars.
- **`n8n` / `n8n-worker` migration race** — both containers were depending on `supabase-db-init: service_completed_successfully` but not on each other, so both started concurrently and both ran TypeORM migrations against the shared `n8n` schema. One container would lose on `CreateWorkflowHistoryTable1692967111175` with `duplicate key value violates unique constraint "pg_type_typname_nsp_index"`, retry, succeed; while n8n recovered automatically the boot logs printed scary `error running database migrations` lines on every cold start. Added a healthcheck to `n8n` (`wget -qO- http://127.0.0.1:5678/healthz`, 15s interval / 90s start_period) and changed `n8n-worker.depends_on.n8n` from `service_started` to `service_healthy` so the worker waits for n8n's migration phase to finish before starting its own.

### Added (MinIO artifact-tier object storage)
- **MinIO object storage**: S3-compatible artifact-tier storage service with five pre-provisioned buckets (`comfyui`, `backend`, `n8n`, `jupyter`, `docling`) and scoped service-account credentials surfaced as `MINIO_<NAME>_ACCESS_KEY` / `MINIO_<NAME>_SECRET_KEY` in `.env`. Admin console at `http://localhost:63031`; S3 API at `http://localhost:63030`. Consumer code is unchanged in this release; each consumer integration ships in a dedicated follow-up. Pinned to `minio/minio:RELEASE.2025-09-07T16-13-09Z` (most recent stable Docker Hub tag; note that the upstream service-account-CVE fix `RELEASE.2025-10-15T17-29-55Z` is published on GitHub only and not yet on Docker Hub — operators handling untrusted credentials should rebuild from source or pin a later tag once available).
- **`minio-init` provisioner**: one-shot container running `minio/mc` that creates buckets, named IAM policies (`<consumer>-policy`), and service accounts on every `./start.sh`. Idempotent — re-runs are no-ops.
- **Bootstrapper integration**: `MINIO_PORT=63030` / `MINIO_CONSOLE_PORT=63031` registered in `PortManager.PORT_MAPPING` (recomputed correctly under `--base-port`); `KeyGenerator` extended with `MINIO_ROOT_PASSWORD` + 10 per-consumer service-account credentials (idempotent — hand-edits stick); `--minio-source [container|disabled]` Click flag plumbed through `SourceOverrideManager`; wizard surfaces MinIO as a DATA-tier service via the manifest at `services/minio/service.yml` (synthesized by `bootstrapper/services/sc_synthesizer.py`) plus display-name / description / tag registrations.

### Added (Hermes Agent runtime)
- **New `hermes` service** (`nousresearch/hermes-agent:latest` — upstream publishes only `latest` + immutable `sha-<commit>` tags, no semver; production should pin to a specific sha per `docs/services/hermes.md`) — programmable AI agent runtime by Nous Research. Promoted from `docs/ROADMAP.md` Tier 2 to shipped. Container by default (3 SOURCE modes: `container`, `localhost`, `disabled`), ~2-4 GB RAM, no GPU. File-based persistence under `/opt/data` (`hermes-data` named volume) — no Postgres / Redis dependency. OpenAI-compatible API on port 8642 → host `63028`; web dashboard on 9119 → host `63029`, Kong-aliased as `hermes.localhost`.
- **New `hermes-init` companion** — renders `/opt/data/config.yaml` from environment before Hermes starts. Wires LiteLLM (`http://litellm:4000/v1`) for reasoning, Speaches / Chatterbox / Parakeet via OpenAI-compatible base-URL overrides for voice (`TTS_ENDPOINT` / `STT_ENDPOINT`), ComfyUI via a skill-override file at `/opt/data/skills/creative-comfyui-host-override.md`, and SearXNG for web search. Empty endpoint → block omitted from `config.yaml` (graceful degradation when a dependency is disabled). Bootstraps deps via inline `apk add` then re-execs under bash (matches openclaw-init / weaviate-init convention).
- **`hermes-agent` registered in the LiteLLM model_list** — `litellm-init/scripts/init.py` appends a `hermes-agent` row pointing at `${HERMES_ENDPOINT}/v1` when `HERMES_SOURCE != disabled`. Consequence: Open-WebUI, n8n, backend, jupyterhub, openclaw all see the new model automatically with no per-consumer wiring.
- **`HERMES_ENDPOINT` + `HERMES_API_KEY` plumbed to consumers** — backend, n8n, jupyterhub, openclaw-gateway env blocks for direct API / webhook access (LiteLLM-routed `hermes-agent` model is the default surface).
- **Bootstrapper integration** — new `services/hermes/service.yml` manifest (`container` / `localhost` / `disabled` sources + cross-deps on stt_provider / tts_provider / comfyui / searxng for init-time URL wiring, all under `runtime_sc:` / `runtime_adaptive:` / `runtime_deps:` blocks; synthesized into the legacy dict shape by `bootstrapper/services/sc_synthesizer.py`), `_generate_hermes_config()` in `bootstrapper/services/service_config.py` (mirror of `_generate_openclaw_config()`), `HERMES_ENDPOINT` in `bootstrapper/utils/endpoint_vars.py`, CLI flag `--hermes-source`, port-clear list, localhost validator, source override manager, dependency manager scale/source mappings, wizard tile (`bootstrapper/ui/state_builder.py`), service discovery name/description, hosts manager (`hermes.localhost` written by `--setup-hosts`), log-pane TOOL tag, `HERMES_API_KEY` auto-generation (32-byte URL-safe token, idempotent like LITELLM_MASTER_KEY).
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
- **ROADMAP additions**: Tier 1 — unified LLM gateway (LiteLLM, or equivalent) and per-service configuration modularization. Tier 2 — Hermes Agent (Nous Research's programmable agent runtime, with Open WebUI integration link).
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