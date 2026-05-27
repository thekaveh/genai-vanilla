# Overnight Audit Findings Log

Branch: `worktree-overnight-audit-2026-05-27`
Started: 2026-05-27

Each iteration's findings are appended below. Format:
- **F-NNN** [iter / domain / severity] location — description (status)

## Iteration 1 (broad parallel sweep)

### Pre-audit baseline finding

- **F-001** [iter-1 / scripts / Medium] `scripts/check-compose-source-deps.py` — Silently falls back to raw `docker-compose.yml` parse (which only has an empty `services:` block due to `include:`) when (a) `docker compose config` returns non-zero or (b) `docker` is missing on PATH, producing wrong-answer FAIL output. Root cause: `load_compose()` silently swallows non-zero exit (lines 86-91) and the raw fallback returns the wrapper without included fragments. Reproduces locally when `.env` is absent. Fix: distinguish "docker unavailable" from "docker config failed", surface stderr, and/or fall back to `.env.example`. Status: PENDING.

### Shell scripts (subagent: shell-audit)

- **F-002** [iter-1 / shell / Important] `services/jupyterhub/build/scripts/startup.sh:118` — Welcome README hardcodes `http://localhost:63009 (Supabase Studio)`, but current default is `SUPABASE_STUDIO_PORT=63016` per `.env.example:703`. Users hit connection-refused. Fix: template via `${SUPABASE_STUDIO_PORT}` (heredoc is non-quoted; substitution works) or drop the line. Status: PENDING.
- **F-003** [iter-1 / shell / Important] `services/ollama/pull/scripts/pull.sh:40-48` AND `services/n8n/init/scripts/install-nodes.sh:106-127` — `set -e` + `curl_output=$(curl ...); curl_exit_code=$?` is unreachable because `set -e` aborts before the `$?` capture. The "continue on failure" branches never run, contradicting the explicit comment. Fix: wrap with `|| true` on the assignment, or `set +e; ...; set -e` guard around the curl block. Status: PENDING.
- **F-004** [iter-1 / shell / Minor] `services/comfyui/init/scripts/download_models.sh:200` — `find -type f -name X -o -name Y …` without parens binds `-type f` only to the first pattern. Cosmetic only (informational listing). Fix: `\( -name X -o -name Y … \)`. Status: PENDING.
- **F-005** [iter-1 / shell / Minor] `start.sh:9`, `stop.sh:9` — `cd "$(dirname "$0")"` without error check produces opaque `sh: bootstrapper/_run.sh: No such file or directory` if cd fails. Fix: append `|| { echo "..."; exit 1; }`. Status: PENDING.
- **F-006** [iter-1 / shell / Minor] `services/supabase/db/scripts/db-init-runner.sh:22` — `while read f` without `-r`. Idiomatic only (filenames are `*.sql` with no backslashes). Fix: `while IFS= read -r f; do`. Status: PENDING.

### Per-service READMEs (subagent: readme-audit)

- **F-007** [iter-1 / docs / Important] `services/tts-provider/README.md` (lines 43, 83, 89, 92, 120, 134) — Stale port literals: `TTS_PROVIDER_PORT 63023` → should be `63044`; `SPEACHES_PORT 63026` → `63046`; `CHATTERBOX_PORT 63027` → `63045`. Quick-start curl on line 43 uses stale `localhost:63026`. NEEDS VERIFICATION against `.env.example`. Status: PENDING.
- **F-008** [iter-1 / docs / Important] `services/stt-provider/README.md` (lines 42, 80) — `STT_PROVIDER_PORT 63022` → should be `63042` per `.env.example`; quick-start curl uses stale `localhost:63026`. NEEDS VERIFICATION. Status: PENDING.
- **F-009** [iter-1 / docs / Minor] `services/hermes/init/templates/config.yaml.tmpl:42` — Comment references retired path `docs/services/hermes.md`. Fix: point at `services/hermes/README.md`. Status: PENDING.
- **F-010** [iter-1 / docs / Minor] `services/hermes/README.md:11` — Container-internal ports 8642/9119 listed alongside host ports 63060/63061 without "(container internal)" disambiguation. Fix: add "(container internal — host-mapped to 63060/63061)". Status: PENDING.
- **F-011** [iter-1 / docs / Minor] `services/openclaw/README.md:21` — Single sentence packs 3 port defaults (63063 container / 63024 localhost / 18789 native). Reader friction only. Fix: split into bullets or move native-default caveat to localhost-mode section. Status: PENDING.
- **F-012** [iter-1 / docs / Important] CHANGELOG line 74 claims `services/{parakeet,speaches,chatterbox,docling}/README.md` were "removed" but they still exist (50-60 lines each, pointer stubs). VERIFIED via `ls + wc -l`. Either CHANGELOG is wrong, or removal was reverted. Fix: update CHANGELOG to reflect they're pointer stubs ("reduced to ~2-section pointer stubs"). Status: PENDING.

### Cross-cutting (subagent: cross-cutting-audit)

- **F-013** [iter-1 / docs / Important] `docs/research/candidates/imgproxy.md:18` AND `docs/specs/2026-05-25-localhost-port-override-design.md:17` — `OpenWebUI` (no space) is a 4th variant beyond canonical `Open WebUI`/`open-webui`/`open-web-ui`. imgproxy.md mixes both in adjacent sentences. Fix: replace `OpenWebUI` → `Open WebUI`. Status: PENDING.
- **F-014** [iter-1 / code+docs / Important] Stale top-level path `litellm-init/init.py` in active code/docs:
  - `services/litellm/init/scripts/init.py:3` (docstring of the file itself!)
  - `services/litellm/compose.yml:87,141` (may be container name `litellm-init` — verify)
  - `services/litellm/README.md:142`
  - `services/litellm/catalog-init/scripts/sync-catalog.py:151,348`
  - `services/backend/app/app/memory_service.py:74`
  - `bootstrapper/utils/litellm_config_generator.py:54`
  - `docs/ROADMAP.md:601`
  NEEDS PER-SITE VERIFICATION — `litellm-init` is also the live container name, so some hits may be valid container refs not stale paths. Fix: update only the stale file-path comments, keep container-name refs. Status: PENDING.
- **F-015** [iter-1 / docs / Minor] `Open-WebUI` (hyphenated, 5th variant) appears in: `services/hermes/README.md:53,115`; `docs/deployment/source-configuration.md:373,381`; `docs/ROADMAP.md:468,595,1254`; `docs/research/candidates/keycloak.md:18,23`. Fix: replace with `Open WebUI`. Status: PENDING.

Subagent reports NO findings in: port literals (200+ checked), `_LOCALHOST_URL` leftovers, SOURCE variants, `*.localhost` aliases, retired directory paths, typos.

### Main README + ROADMAP + CONTRIBUTING (subagent: top-docs-audit)

- **F-016** [iter-1 / docs / Important] `README.md:490-498` (§9 Documentation hub) — Missing inbound links from main README to: `SECURITY.md` (zero links repo-wide), `docs/CONTRIBUTING-services.md`, `docs/research/integration-matrix.md`, `docs/deployment/source-configuration.md`, `docs/deployment/submodule-usage.md`, `docs/deployment/expected-startup-warnings.md`, `docs/quick-start/interactive-setup-wizard.md`, `docs/quick-start/troubleshooting.md`. Per `/goal` spec, README must be the navigation hub. Fix: expand §9 to enumerate every deployment/, quick-start/, and root-level doc with one-liners; add SECURITY + CONTRIBUTING links. Status: PENDING.
- **F-017** [iter-1 / docs / Important] `docs/README.md:11-32` — Missing Ray service entry in the Service documentation block. Ray is a shipped Tier-1 feature (RAY_SOURCE, /api/ray/*). Fix: add `- [Ray](../services/ray/README.md) — distributed compute substrate`. Status: PENDING.
- **F-018** [iter-1 / docs / Important] `README.md:117` — §2.1 lists "Ray (distributed compute)" under "Core services" framed as always-on, but `RAY_SOURCE=disabled` is the actual default (verified in `.env.example:562`). README.md:254 says "Disabled by default; opt-in". Internal contradiction. Fix: remove Ray from "always-on" or split into always-on + opt-in sub-bullets. Status: PENDING.
- **F-019** [iter-1 / docs / Important] `docs/CONTRIBUTING-services.md:42-83` — Two conflicting "Adding a new service" step lists: 9-step terse list (lines 42-83) AND canonical 5-command "After you save the files" block (line 509). Step 7-8 of the terse list miss `env_assembler` (required after any env-block change). Fix: drop terse list OR rewrite it to match canonical 5-command order. Status: PENDING.
- **F-020** [iter-1 / docs / Minor] `docs/CONTRIBUTING-services.md` — Uses bare `## Title` (not `## N. Title`). Inconsistent with main README's numbered convention. Service READMEs use numbering, top-level docs don't. Fix: pick a side — either add numbering to top-level docs, or explicitly document that numbering applies only to README + service READMEs. Status: PENDING (low-priority decision).
- **F-021** [iter-1 / docs / Minor] `docs/quick-start/troubleshooting.md:113` — Suggests `ollama pull llama2:7b` as smaller-model hint. llama2 is 2023; current defaults (qwen3.6, qwen3-embedding, nomic-embed-text) per `bootstrapper/utils/llm_catalog.py`. Fix: replace with `qwen3:1.7b` or similar. Status: PENDING.
- **F-022** [iter-1 / docs / Minor] `docs/deployment/submodule-usage.md:196` — Compose example starts with `version: '3.8'` (deprecated in Compose v2). Fix: remove the version line. Status: PENDING.
- **F-023** [iter-1 / docs / Minor] `docs/deployment/submodule-usage.md:101-106` — Directory tree shows pre-refactor top-level service entries (`backend/`, `supabase/`, `n8n/`, `jupyterhub/`) — should be under `services/`. Fix: rewrite as `services/{backend,supabase,n8n,jupyterhub}/`. Status: PENDING.
- **F-024** [iter-1 / docs / Minor] `docs/deployment/ports-and-routes.md:10` — References "§ 3.1" of README, but actual location is "§ 4.1 Service overview" (README:236). Fix: update cross-ref. Status: PENDING.

### Specs/plans/research/CHANGELOG (subagent: specs-audit)

- **F-025** [iter-1 / docs / Minor] `docs/specs/2026-05-25-localhost-port-override-design.md:197` — Lists `services/whisper-cpp/service.yml` as if it's a top-level service, but whisper-cpp lives at `services/parakeet/provider/whisper-cpp/` and its URL var is in `services/parakeet/service.yml`. Spec is marked Implemented (historical). Fix: leave OR add a one-line footnote. Status: DEFER (historical spec).
- **F-026** [iter-1 / docs / Minor] `docs/specs/2026-05-24-ray-cluster-design.md:54-450` — Uses file-path subheadings (`### services/ray/service.yml`) instead of numbered `### N.M`. Spec marked Implemented (historical). Status: DEFER.
- **F-027** [iter-1 / docs / Minor] `docs/CHANGELOG.md:8` — Missing Keep-a-Changelog anchor footers (`[3.0.0]: <github-compare-url>`). Bracketed version headings render as dead anchors on GitHub. Fix: optionally add anchor block at footer — skip if releases aren't tagged in git. Status: DEFER (low-priority cosmetic).

### Tests (subagent: tests-audit)

- **F-028** [iter-1 / tests / Important] `bootstrapper/tests/test_regen.py:47-50` — `test_check_mode_exits_2_on_drift` docstring claims to verify "drift detection on committed artifacts", but actually points `--check` at an empty `tmp_path` so `existing=""` always differs. The contract being asserted is weaker than the docstring (real drift-logic regression would NOT be caught — only "any output != empty"). Fix: either seed a known-stale fixture into `tmp_path/<name>/README.md` first, or rename to `test_check_mode_exits_2_when_artifacts_missing`. Status: PENDING.
- **F-029** [iter-1 / tests / Minor] `bootstrapper/tests/test_regen.py:18` — `test_help_works` is a vague name. Fix: rename to `test_help_flag_prints_usage_and_exits_zero`. Status: PENDING.
- **F-030** [iter-1 / tests / Minor] `bootstrapper/tests/test_diagram_renderer.py:84` — Tautological `or`: `assert "required" not in svg.lower() or svg.lower().count("required") == 0`. Both clauses equivalent. Fix: drop the `or` clause. Status: PENDING.
- **F-031** [iter-1 / tests / Minor] Unused imports: `bootstrapper/tests/test_doc_links.py:9` (`import pytest`), `bootstrapper/tests/test_diagram_renderer.py:5` (`import re`). Fix: remove. Status: PENDING.
- **F-032** [iter-1 / tests / Minor] `services/backend/app/app/tests/test_ray_routes.py:31-51` duplicates env-stub setup loop from `conftest.py:83-91`. Fix: extract a `ray_disabled_fastapi_client` fixture in conftest.py. Status: PENDING.

Subagent reports the 3 skipped tests (`test_live_catalog_sync.py:144,150`) are legitimately gated on live Ollama+LiteLLM endpoints — not bogus skips. Port literals in tests all match current `.env.example` or are deliberate synthetic values.

### YAML configs + CI (subagent: yaml-ci-audit)

- **F-033** [iter-1 / deps / Important] `services/parakeet/provider/gpu/requirements.txt:1-12` (and mlx sibling) — Every line is `>=` or fully unpinned (`soundfile`, `librosa`, `numpy`, `fastapi`, `uvicorn[standard]`, `pydantic`, `python-multipart`, `huggingface_hub`). Dependabot can't propose patch/minor bumps. NeMo has had breaking minors. Fix: pin to a snapshot via `pip freeze` inside the container, OR add `<X` upper bounds. Status: PENDING.
- **F-034** [iter-1 / deps / Important] `services/backend/app/app/requirements.txt:24` — `pydantic-ai<=0.0.44` is a hard cap at an old 0.0.x version, surrounded by floats, with NO inline comment explaining why. Risk of bit-rot: future contributor will either drop it (regression) or keep it without context. Fix: drop the cap if obsolete, OR add `# cap until <reason>` comment. Status: PENDING.
- **F-035** [iter-1 / manifests / Minor] `services/ollama/service.yml:160-163` (`data_flow.calls: [supabase, litellm]`) and `services/neo4j/service.yml:106-108` (`[supabase]`). Schema description (`schemas/service.schema.json:56`) says `data_flow.calls` is "runtime in the request path" and explicitly EXCLUDES "init-time bootstrap calls". Ollama serves /api at runtime; supabase/litellm contact is in `ollama-pull` init container only. NEEDS VERIFICATION. Fix: change to `[]` and re-run regen, OR amend schema description if maintainer wants init-time edges. Status: NEEDS_VERIFICATION.
- **F-036** [iter-1 / manifests / Minor] `services/open-webui/service.yml:103-108,129-132` — Container env block sets `COMFYUI_BASE_URL`, `STT_ENDPOINT`, `TTS_ENDPOINT`, `DOCLING_ENDPOINT`; runtime_deps lists `local-deep-researcher`. `data_flow.calls` only lists `litellm` and `searxng`. Diagram understates surface area. Fix: append optional-adaptive calls. Status: PENDING.
- **F-037** [iter-1 / deps / Minor] `services/docling/provider/localhost/` has BOTH `pyproject.toml` (`>=` floors) AND `requirements.txt` (`==` pins) declaring same deps. Drift potential. Fix: pick one canonical, delete or generate the other. Status: PENDING.
- **F-038** [iter-1 / deps / Minor] `services/docling/provider/gpu/requirements.txt:6` pins docling `2.95.0`; `services/docling/provider/localhost/requirements.txt:6` pins `2.93.0`. No inline comment. Fix: align both OR add `# pinned behind GPU due to <reason>` comment. Status: PENDING.
- **F-039** [iter-1 / config / Minor] `.env.example` port-default collisions in localhost-mode defaults: `DOCLING_LOCALHOST_PORT=63021` matches `REDIS_PORT=63021`; `PARAKEET_LOCALHOST_PORT=63022` matches `WEAVIATE_PORT=63022`. If user picks localhost source + keeps default, real host-port conflict on stack startup. NEEDS VERIFICATION — does pre-launch summary already flag this? Fix: move localhost-port defaults outside the allocated stack range. Status: NEEDS_VERIFICATION.
- **F-040** [iter-1 / ci / Minor] `.github/workflows/services-lint.yml:77,115` — CI runs `cp .env.example .env` but doesn't set `HOST_GATEWAY_IP`. Compose interpolates `host.docker.internal:${HOST_GATEWAY_IP}` → literal `host.docker.internal:` in 11 extra_hosts entries. Currently tolerated by `docker compose config -q`. Fix: pre-step `sed -i 's/^HOST_GATEWAY_IP=$/HOST_GATEWAY_IP=host-gateway/' .env`. Status: PENDING.
- **F-041** [iter-1 / docs / Minor] `CLAUDE.md` says backend deps at `app/requirements.txt`; actual is `app/app/requirements.txt`. CLAUDE.md is gitignored (per commit `1f92f53`) — local-only. Status: SKIP (not in repo).

### Python code (subagent: py-audit)

- **F-042** [iter-1 / py / CRITICAL] `services/backend/app/app/research_service.py:262-263, 365` — JSONB columns (`sources`, `metadata`, `data`) returned by asyncpg as raw `str` (no `set_type_codec("jsonb", ...)` registered) but handed to Pydantic models declaring `List[Dict[str, Any]]` / `Dict[str, Any]`. Pydantic validation raises → `/research/{session_id}/result` and `/research/{session_id}/logs` return 500 on real data. Fix: set a JSONB codec per-connection OR `json.loads()` each JSONB column at read time. NEEDS VERIFICATION (schema confirms JSONB; need to verify no global codec is set). Status: PENDING.
- **F-043** [iter-1 / py / Important] `services/backend/app/app/ray_client.py:87-90` (sync `urllib.request.urlopen` in `cluster_status`) + `ray_routes.py:84-87` — sync HTTP / sync Ray SDK calls inside async FastAPI handlers block the event loop. Under load a single in-flight Ray op freezes the FastAPI worker. Fix: wrap in `await asyncio.to_thread(...)`. Status: PENDING.
- **F-044** [iter-1 / py / Important] `services/backend/app/app/main.py:204` AND `:580` — Two handlers both named `async def execute_workflow` (one for n8n, one for ComfyUI). FastAPI routes by path so API works, but module-level binding shadows. Fix: rename to `execute_n8n_workflow` and `execute_comfyui_workflow`. Status: PENDING.
- **F-045** [iter-1 / py / Minor] Unused imports:
  - `bootstrapper/core/config_parser.py:9` (`import yaml`)
  - `bootstrapper/stop.py:10`, `bootstrapper/generate_supabase_keys.py:10` (`import os`)
  - `services/backend/app/app/comfyui_client.py:5` (`import json`)
  - `services/backend/app/app/memory_service.py:12` (`Union`)
  - `bootstrapper/ui/textual/widgets/block_logo.py:24` (`from .. import palette as P`)
  - `bootstrapper/ui/textual/widgets/log_filter_chips.py:26` (same)
  - `bootstrapper/ui/textual/widgets/prompt_panel.py:52` (`from rich.text import Text`)
  - `bootstrapper/ui/textual/widgets/option_row.py:57` (`Input`, only used as string annotation under `from __future__`)
  Status: PENDING.
- **F-046** [iter-1 / py / Minor] Deprecated `asyncio.get_event_loop().time()` in `services/backend/app/app/comfyui_client.py:256,260` and `services/backend/app/app/research_client.py:259,271`. Fix: use `time.monotonic()`. Status: PENDING.
- **F-047** [iter-1 / py / Minor] `bootstrapper/services/topology.py:137,153` — hardcoded `base_port: int = 63000` defaults duplicate `DEFAULT_BASE_PORT = 63000` in `bootstrapper/core/config_parser.py:17`. Fix: import/share. Watch for circular import. Status: PENDING.
- **F-048** [iter-1 / py / Minor] Inconsistent logger usage in backend: `main.py`, `n8n_client.py`, `research_service.py`, `research_client.py` lack `logger = logging.getLogger(__name__)`; `comfyui_client.py`, `memory_service.py`, `memory_store.py`, `ray_routes.py` have them. Failures go to HTTP body only. Fix: add loggers to silent files and `logger.exception(...)` in generic except blocks. Status: PENDING.
- **F-049** [iter-1 / py / Minor] `services/backend/app/app/research_client.py:229` — `import json` inside `stream_research_logs` generator (per-line). Fix: hoist to top. Status: PENDING.
- **F-050** [iter-1 / py / Minor] UUID validation inconsistency in `services/backend/app/app/main.py`. Memory endpoints (`memory_list:967`, `memory_update:990`, `memory_delete:1016`) call `_validate_uuid_param`; research endpoints (`get_research_status:334`, `get_research_result:354`, `cancel_research:374`, `get_research_logs:398`) skip it. Invalid UUIDs become 500 instead of 400. Fix: call `_validate_uuid_param` in research handlers. Status: PENDING.
- **F-051** [iter-1 / py / Minor] `services/backend/app/app/n8n_client.py:13` instantiated as module-level singleton; `main.py:130` (`n8n_client = N8nClient()`) never `.aclose()`'d. Inconsistent with `research_client`/`memory_service` per-request patterns. Fix: FastAPI lifespan handler to aclose on shutdown, OR drop singleton. Status: PENDING.
- **F-052** [iter-1 / gitignore / Minor] `.gitignore:7` `build/` (a Python-build-artifact glob) accidentally matches `services/jupyterhub/build/` (which is a tracked, intentional directory). Tracked files keep working but `git add` on them prints an ignore warning and exits non-zero, breaking `git add … && git commit …` chains. Fix: tighten pattern (e.g. `/build/` for repo-root only) or add `!services/jupyterhub/build` exception. Status: PENDING.

