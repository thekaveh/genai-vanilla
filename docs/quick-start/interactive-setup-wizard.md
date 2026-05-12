# Interactive Setup Wizard

The GenAI Vanilla Stack includes an interactive Textual TUI wizard that guides you through configuring all services step by step. It launches automatically when you run `./start.sh` with no arguments.

## Quick Start

```bash
./start.sh
```

That's it. The wizard handles everything from there.

## Step Order

The wizard's question order isn't fixed — service-source steps are sorted by each service's resolved port (so the wizard's order matches the stack-overview panel beside it), with the LLM cluster spliced in immediately after the LLM Engine step. The shape is roughly:

```
first  Base port
…      Service-source steps, sorted by resolved port
       (ComfyUI, LLM Engine, ollama-related, Weaviate, …)
…      LLM cluster (spliced right after the LLM Engine step):
         Ollama  ·  models               (single unified multiselect)
         Ollama  ·  additional models    (free-text, container only)
         OpenAI key + models
         Anthropic key + models
         OpenRouter key + models
…      Remaining service-source steps
near-end  Cold start
near-end  Hosts file
last   Confirm — Launch the stack with this configuration?
```

Steps gated by `skip_if_prev` predicates simply vanish from the flow when their precondition isn't met (e.g. each cloud key/model pair only renders when its `CLOUD_*_SOURCE` is `enabled` after the prior secret step; Ollama variant steps only render when `LLM_PROVIDER_SOURCE` is an `ollama-*` value).

## Prompt Kinds

Each wizard step renders one of five prompt widgets, picked based on the question type:

| Kind | Used for | UX |
|---|---|---|
| `options` | Single-select with a small fixed option set (every `*_SOURCE`, the `Cold start` toggle, the `Hosts file` choice). | Up/Down arrows + Enter; the current `.env` value is pre-highlighted. |
| `number` | Numeric prompts (`Base port`). | Single-line input restricted to digits; range-validated. |
| `secret` | API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`). | Masked password Input + a live char-count hint as you paste. When a key is already set, the hint shows the source-aware action: press Enter to keep the saved key, type a new key to replace, type `clear` + Enter to remove. No sentinel rows are rendered — the input field IS the prompt. |
| `multiselect` | Cloud and Ollama model lists. | `[✓]` / `[ ]` rows in a scrollable viewport (capped height; the cursor follows the selection so a 230-row library scrape stays usable). Space toggles, Enter confirms. **Cloud** multiselect: default-active set (intersected with what your account actually returns) is pre-checked on first visit. **Ollama** multiselect: source-aware — container shows the library only, localhost/external shows a merged `[pulled]` + `[library]` view. Purely additive; the default-active baseline is already active via `08-seed-data.sql`. |
| `text` | Free-text additions (the Ollama "additional models to pull" step). | Comma-separated input; trimmed and merged into selections. |

Throughout: `Up/Down` to move, `Enter` to confirm, `Space` to toggle multiselect rows, `Esc` returns to the previous step, `Ctrl+C` (or `Ctrl+Q`) quits.

## LLM Cluster Steps in Detail

### LLM Engine (single-select)

`LLM_PROVIDER_SOURCE` choice — `ollama-container-cpu`, `ollama-container-gpu`, `ollama-localhost`, `ollama-external`, or `none` (cloud-only). LiteLLM is locked / always-on and is **not** a separate prompt — it's the mandatory front door for every LLM consumer.

The wizard refuses to launch when **LLM Engine = `none`** **and** every cloud provider is `disabled` — that combination would leave LiteLLM with nothing to route to.

### Ollama  ·  models (multiselect)

A single unified multi-select shown for every `ollama-*` source. The option list is **source-aware**:

- **`ollama-container-*`** — only the live scrape of `https://ollama.com/library` (a few hundred entries). Nothing is pulled yet (the in-stack container isn't running at wizard time), so the library is the primary discovery surface. The `ollama-pull` init container fetches checked entries at startup.
- **`ollama-localhost`** / **`ollama-external`** — the upstream's `/api/tags` (already-pulled models) merged with the library scrape. Each row carries a badge:
  - `[pulled]` — the model is on disk on your upstream right now. Checking activates it in `public.llms` and LiteLLM serves it immediately.
  - `[library]` — the model exists in the public catalog but is **not** pulled on your upstream. Checking it registers a row in `public.llms` for routing, but you must `ollama pull <name>` on the host yourself before requests will succeed.

Selections persist as `OLLAMA_USER_MODELS`.

When the library scrape fails (rare), the wizard falls back to the curated default-active baseline in `bootstrapper/utils/llm_catalog.py` (qwen3.6:latest, qwen3-embedding:0.6b, nomic-embed-text). When `/api/tags` fails for a localhost/external source, the merge degrades to library-only with a warning in the session log.

The default-active baseline is already activated in `public.llms` from `08-seed-data.sql`, so checking items here is **purely additive** — leaving everything unchecked still leaves the baseline active. Pre-checking behaviour:

- **First visit** (`OLLAMA_USER_MODELS` empty): the wizard pre-checks the default-active baseline (`default_active_names("ollama")` → `qwen3.6:latest`, `qwen3-embedding:0.6b`, `nomic-embed-text`). The user sees the baseline already ticked.
- **Subsequent visit** (`OLLAMA_USER_MODELS` set): the saved selection is restored, intersected with the visible options. Names no longer in the merged list are dropped silently.

### Ollama  ·  additional models to pull (text)

Shown only for `ollama-container-*` sources. Free-text comma-separated list, e.g. `mistral:7b,phi4:latest`. Used when an entry isn't surfaced by the library scrape but you still want it pulled at startup. Persists as `OLLAMA_CUSTOM_MODELS`.

### Cloud key + model pairs (secret + multiselect)

Each enabled cloud provider gets two consecutive steps:

1. **API key** (`secret` kind). The widget is a masked password Input — no sentinel rows are rendered. When a key is already saved: press **Enter** to keep it, type a new key + Enter to replace it, or type `clear` + Enter to remove it. When no key is saved: type a key + Enter to enable, or press Enter (empty) to leave the provider disabled. The hint line below the input always tells you which action Enter will take.
2. **Models** (`multiselect`). Live fetch from the provider's models endpoint:
   - **OpenAI** — `GET /v1/models` (filtered to the chat / o-series / `text-embedding-3-*` set).
   - **Anthropic** — `GET /v1/models` (Anthropic's documented endpoint).
   - **OpenRouter** — `GET /api/v1/models` (no auth required for the listing — anyone can browse the model catalog). **Enabling OpenRouter as a usable LiteLLM provider still requires `OPENROUTER_API_KEY`** for actual request routing; the listing is a convenience, not a green light to skip the key step.

   The default-active subset of `bootstrapper/utils/llm_catalog.py` is intersected with what your account actually returns; the result is pre-checked. Selections persist as `OPENAI_USER_MODELS`, `ANTHROPIC_USER_MODELS`, `OPENROUTER_USER_MODELS`.

If the live fetch fails (network outage, key rejected, 5xx), the wizard falls back to the curated catalog so you can still proceed; the failure reason appears in the launch log (see [Troubleshooting](troubleshooting.md)).

### Splash + cache + back-invalidation

Live fetches run in a background worker so the wizard stays responsive (Esc still works). While the request is in flight, the multiselect renders a single `⏳ Fetching <provider> models…` row (the **fetch splash**). Once data arrives, the splash is replaced with the real options. The fetched list is cached for the lifetime of the wizard process and re-used if you navigate forward and back. Pressing **Esc** to return to a prior step **invalidates** the cache for any provider step at or after the new position AND bumps a generation counter so any in-flight worker that has since become stale silently drops its result instead of polluting the now-empty cache. Re-entry triggers a fresh fetch with the (possibly updated) key.

## Stack Options

After service configuration, the wizard prompts for:

- **Base port** for all services (default: 63000) — collected at the very start of the wizard so all subsequent port displays reflect the chosen base.
- **Cold start** option to remove volumes and rebuild from scratch.
- **Hosts file configuration** to enable friendly URLs like `chat.localhost` and `n8n.localhost`.

## Pre-Launch Summary

Before launching, a configuration summary inside the same anchored info-box shows:

- Every service with its selected source, alias (when hosts are configured), and direct port.
- Hosted endpoints (e.g., `chat.localhost:63002`) if hosts file entries are configured.
- A separate **Cloud APIs** sub-section lists OpenAI / Anthropic / OpenRouter status (`enabled · key set ✓`, `disabled`, `enabled · key MISSING ⚠`). Cloud providers don't run as containers, so they render below the services grid rather than alongside real services.
- Color-coded source choices (container = green, localhost / external / cloud = cyan, off = slate).

You confirm to launch (the **Launch the stack with this configuration?** step is the wizard's final question), or cancel to exit without changes.

## Streaming Logs

After confirmation, the wizard transitions in-place from prompts to the launch phase:

- The brand panel and pre-launch summary stay **pinned** at the top — they never move while logs flow.
- Below them, a bordered **Logs** pane streams `docker compose` build / up / port-verify / `logs -f` output, line-by-line.
- Per-service container names (e.g. `genai-supabase-db`, `genai-ollama-pull`) are **color-coded** based on `bootstrapper/ui/textual/palette.py::SOURCE_COLORS`. Unknown service names get a stable hue from a small md5-based palette so every service in the stack remains visually distinguishable.
- The full launch-phase output is also tee'd to `/tmp/genai-vanilla-launch-<timestamp>.log` for post-mortem inspection. See [Troubleshooting](troubleshooting.md#launch-log).
- Press `Ctrl+Q` to detach cleanly from the wizard UI. `Ctrl+C` sends SIGINT — fine after services are up (already-detached compose containers keep running) but during the launch pipeline it may interrupt a compose step mid-flight, leaving the stack in a partial state. Either way, services that have finished starting keep running; resume log streaming with `docker compose logs -f <service>`.

## Navigation

| Key | Action |
|-----|--------|
| `Up/Down` | Navigate between options or rows |
| `Space` | Toggle a row in a multiselect |
| `Enter` | Confirm the current selection |
| `Esc` | Return to the previous step (and from the first step, exit) |
| `Ctrl+Q` | Quit the wizard |

## Progress Tracking

A progress bar at the top of each screen shows how far you are through the configuration process. It starts at 0% and reaches 100% after all steps (services + stack options) are completed.

## When to Use the Wizard vs CLI Flags

| Scenario | Approach |
|----------|----------|
| First time setting up the stack | Wizard (`./start.sh`) |
| Exploring available service options | Wizard |
| Changing one or two services | CLI flags (`./start.sh --llm-provider-source ollama-localhost`) |
| CI/CD or scripted deployments | CLI flags or `.env` file |
| Repeating a previous configuration | CLI flags (copy from wizard's command preview) |

## Relationship to .env and CLI Flags

The wizard reads your current `.env` values as defaults and produces the same `--*-source` overrides that CLI flags would. After confirmation, these overrides are applied to `.env` and the stack launches normally.

- **Wizard selections are persistent** in `.env` and carry over to future runs
- **CLI flags always skip the wizard** and apply directly
- **Any flag** (including `--cold`, `--base-port`, etc.) skips the wizard

## Requirements

The TUI uses two Python libraries — both included in `bootstrapper/pyproject.toml`:

- **textual** — owns the wizard prompts and the post-confirm launch phase (pinned summary + log pane + filter chips), all hosted in a single Textual app.
- **rich** — used for styled spans inside Textual widgets and for the `--no-tui` linear pre-launch summary table.

Python ≥ 3.10 is required (see `bootstrapper/pyproject.toml`). The wizard automatically falls back to the linear stdout flow when `stdin` isn't a TTY, when the terminal is too small to host the Textual app, or when the user passes `--no-tui`. In that mode `./start.sh` prints a pre-launch summary table and streams docker compose output directly.

## Brand Customization

The metadata on the pinned info-box's border (brand name, tagline, version, author, license, repo URL) is overridable via `BRAND_*` environment variables. Defaults are the GenAI Vanilla project's identity; forks can rebrand the wizard by editing the `BRAND_*` block in `.env`:

```
BRAND_NAME=GenAI Vanilla
BRAND_TAGLINE=AI Development Suite
BRAND_VERSION=
BRAND_AUTHOR=Kaveh Razavi
BRAND_LICENSE=Apache License 2.0
BRAND_REPO_URL=github.com/thekaveh/genai-vanilla
```

Empty values fall back to the canonical defaults (encoded in `bootstrapper/ui/state.py::AppState`). See `.env.example` for the latest documented block.

## Configurable Services

The wizard automatically discovers all configurable services from `service-configs.yml`. Currently these include:

| Service | Options |
|---------|---------|
| LiteLLM Gateway | locked / always-on (no choice; mandatory front door for every LLM consumer) |
| LLM Engine (Ollama upstream) | ollama-container-cpu, ollama-container-gpu, ollama-localhost, ollama-external, none |
| ComfyUI | container-cpu, container-gpu, localhost, external, disabled |
| Weaviate | container, localhost, disabled |
| Multi2Vec CLIP | container-cpu, container-gpu, disabled |
| Neo4j Graph DB | container, localhost, disabled |
| STT Provider (Parakeet) | container-gpu, localhost, disabled |
| TTS Provider (XTTS) | container-gpu, localhost, disabled |
| Document Processor (Docling) | container-gpu, localhost, disabled |
| OpenClaw | container, localhost, disabled |
| Hermes Agent | container, localhost, disabled |
| n8n | container, disabled |
| SearxNG | container, disabled |
| JupyterHub | container, disabled |

### Cloud LLM providers (not auto-discovered)

OpenAI, Anthropic, and OpenRouter are **not** regular services — they don't run as containers (scale: 0 in `service-configs.yml`). Instead, the wizard injects them via `bootstrapper/wizard/llm_steps.py:build_cloud_steps` as bespoke (secret + multiselect) pairs spliced after the LLM Engine step:

| API | Key var | Wizard step |
|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `OpenAI Cloud  ·  API key` then `OpenAI Cloud  ·  models` |
| Anthropic | `ANTHROPIC_API_KEY` | `Anthropic Cloud  ·  API key` then `Anthropic Cloud  ·  models` |
| OpenRouter | `OPENROUTER_API_KEY` | `OpenRouter Cloud  ·  API key` then `OpenRouter Cloud  ·  models` |

Source toggles are persisted as `CLOUD_OPENAI_SOURCE` / `CLOUD_ANTHROPIC_SOURCE` / `CLOUD_OPENROUTER_SOURCE` (`enabled` / `disabled`). They render in the **Cloud APIs** sub-section of the stack overview, separate from the services grid.

New services added to `service-configs.yml` are automatically picked up by the wizard.

## Dependency Validation

The wizard validates service dependencies in real time. For example, if you enable n8n but disable Weaviate (which n8n requires), the wizard warns you and offers to either enable the dependency or disable the dependent service. The same machinery enforces the "LiteLLM must have an upstream" rule (LLM Engine != `none`, or at least one cloud provider is `enabled`).

## Hosts File Setup

The hosts file configuration step enables friendly URLs routed through Kong API Gateway:

| Option | Behavior |
|--------|----------|
| **Default** | Checks `/etc/hosts` for required entries, warns if missing |
| **Setup hosts now** | Adds entries to `/etc/hosts` (requires `sudo`) |
| **Skip** | No hosts check, use `localhost:PORT` URLs only |

When hosts are configured, the pre-launch summary table shows both the direct `localhost:PORT` URL and the friendly `service.localhost:KONG_PORT` URL for applicable services.
