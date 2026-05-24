# Adding-a-Service Runbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand `docs/CONTRIBUTING-services.md` from a 234-line terse reference into an ~870-line decision-driven runbook so a contributor can land a new service correctly on the first try.

**Architecture:** In-place expansion of one file. Each task inserts one section, runs the link validator + a focused read-back, and commits. The worked example (fictional `qdrant` vector DB) threads through every new section. The existing reference sections (schema cheatsheet, validator rules, byte-equivalence, `_user/` overlay, doc-only manifest fields) stay verbatim — they're moved to the end so the new walkthrough material flows first.

**Tech Stack:** Markdown (GitHub-flavored), YAML snippets for manifests and compose fragments, the genai-vanilla audit scripts for verification (`scripts/check_doc_links.py`, `bootstrapper.docs.regen --check`).

**Spec:** `docs/specs/2026-05-24-adding-a-service-runbook-design.md`. Tasks below cite spec section numbers (§6.X) as the authoritative content source — engineers must read each cited section before writing that task's content.

**Conventions used throughout this plan:**
- `<<<INSERT-NEW-CONTENT-BLOCK>>>` markers indicate where to insert content. Real edits use the Edit tool with the surrounding context as `old_string`.
- "Verify links" = `python scripts/check_doc_links.py` from repo root, expect exit 0.
- Commits use the genai-vanilla style: terse third-person verb prefix (`docs: …`), no Claude trailer (per memory `feedback_commits`).
- Each task is committed independently so review per-section is cheap.

---

## Task 0: Setup — read the spec, snapshot the baseline

**Files:**
- Read: `docs/specs/2026-05-24-adding-a-service-runbook-design.md` (in full)
- Read: `docs/CONTRIBUTING-services.md` (in full)
- Reference: `bootstrapper/services/topology.py` lines 1-100 (for `CATEGORY_SLOTS` constant)
- Reference: `bootstrapper/schemas/service.schema.json` (skim the top-level properties)

- [ ] **Step 1: Read the spec end-to-end.** Make notes on each `§6.X` content block. The spec is the SUBSTANCE; this plan only sequences and verifies.

- [ ] **Step 2: Confirm baseline state.** Run from repo root:

```bash
wc -l docs/CONTRIBUTING-services.md
# Expected: 234 lines

python scripts/check_doc_links.py
echo "exit: $?"
# Expected: exit 0
```

- [ ] **Step 3: Confirm test infrastructure.** Run from `bootstrapper/`:

```bash
cd bootstrapper && uv run pytest -q --tb=no 2>&1 | tail -5
# Expected: 315 passed (the docs work won't change this number)
```

- [ ] **Step 4: Confirm working tree is clean except for the spec.**

```bash
git status -s
# Expected: only `?? docs/specs/2026-05-24-adding-a-service-runbook-design.md` (and optional docs/plans/<this file>) plus user's pre-existing ROADMAP.md WIP. Anything else means there's uncommitted work to land first.
```

- [ ] **Step 5: NO COMMIT yet — Task 0 is just setup.** Proceed to Task 1.

---

## Task 1: Insert TL;DR + six-decision overview at the top of the doc

**Files:**
- Modify: `docs/CONTRIBUTING-services.md` (insert two new top-level sections at the very top, after the H1)
- Reference: spec §6.1 (TL;DR) + §6.2 (six decisions table)

**Insertion point:** After the H1 line (`# Adding & Modifying Services` or whatever the existing title is — read first), before the existing `## Adding a new service` heading.

- [ ] **Step 1: Read the current top of the file** to identify the exact existing heading text for the `old_string` anchor.

```bash
head -15 docs/CONTRIBUTING-services.md
```

- [ ] **Step 2: Insert the TL;DR section + six-decision overview.** Insert ABOVE the existing `## Adding a new service` heading. The content is two new H2 sections back-to-back.

Content to insert (matches spec §6.1 + §6.2 verbatim — the TL;DR checklist and the decision table):

```markdown
## TL;DR — the 60-second checklist

A maintainer who already understands the stack can land a new service in under an hour by following this list. Each step links to the relevant deep-dive section.

- [ ] **Pick a folder flavor** → [Decision 1](#decision-1--folder-flavor-container-virtual-or-doc-only)
- [ ] **Pick a category** → [Decision 2](#decision-2--category)
- [ ] **Pick your sources** → [Decision 3](#decision-3--source-variants)
- [ ] **Write `services/<name>/service.yml`** → [Mechanics](#mechanics--putting-it-all-together)
- [ ] **Write `services/<name>/compose.yml`** (only if folder flavor = container) → [Mechanics](#mechanics--putting-it-all-together)
- [ ] **Add the `include:` line to `docker-compose.yml`** (only if you wrote a compose fragment)
- [ ] **Run the four-command regen + lint chain** → [After you save the files](#after-you-save-the-files--regen--lint-commands-in-order)
- [ ] **Update audit-script allowlists** if your service has hard deps → [Audit-script + CI implications](#audit-script--ci-implications)
- [ ] **Commit and push.** CI's three jobs (manifest-lint+pytest, compose-equivalence+permutation matrix, docs-drift+audit-scripts) gate the change.

If you're new to this codebase, read the six decisions sections in order before touching code. The worked example threads through them.

## The six decisions you have to make

| # | Decision | Default if you're unsure | Drill-down |
|---|----------|--------------------------|------------|
| 1 | Folder flavor | `container` | [Decision 1](#decision-1--folder-flavor-container-virtual-or-doc-only) |
| 2 | Category | the category of the service you're most similar to | [Decision 2](#decision-2--category) |
| 3 | Source variants | `container` + `disabled` (minimum); add `localhost` if users might run this themselves | [Decision 3](#decision-3--source-variants) |
| 4 | Port allocation | nothing — it's auto-assigned. Just declare `<NAME>_PORT` in the env block. | [Decision 4](#decision-4--port-allocation) |
| 5 | Dependencies | the manifest of the closest sibling in your category, to preserve display order | [Decision 5](#decision-5--dependencies-depends_onrequired--optional) |
| 6 | Adaptive / hooks | none — start with declarative `runtime_sc`, escalate to a Python helper only when YAML can't express it | [Decision 6](#decision-6--adaptive-behavior--when-to-write-a-hook) |

> **Worked example throughout:** Adding **Qdrant**, a self-hosted vector database. (Qdrant is real software but NOT currently in the stack — Weaviate is our vector DB. Used here purely as an instructional example, not a proposal.)
```

- [ ] **Step 3: Verify links resolve.** All in-doc anchors should resolve once their target sections are added. Until then, run:

```bash
python scripts/check_doc_links.py
# Expected: exit 0 — the validator only checks file existence, not in-doc anchors. Anchors are verified manually in Task 15.
```

- [ ] **Step 4: Visually verify formatting.** Open the file or use:

```bash
head -50 docs/CONTRIBUTING-services.md
# Expected: H1 still at line 1; new H2 "TL;DR" starts around line 3; new H2 "The six decisions" follows; existing "## Adding a new service" comes after.
```

- [ ] **Step 5: Commit.**

```bash
git add docs/CONTRIBUTING-services.md
git commit -m "docs: add TL;DR checklist + six-decisions overview to service-addition runbook"
```

---

## Task 2: Replace existing "Folder flavors" with expanded Decision 1

**Files:**
- Modify: `docs/CONTRIBUTING-services.md` — replace the existing `## Folder flavors: container, virtual, doc-only` section (added in commit `80ad83e`) with an expanded Decision 1.
- Reference: spec §6.3.

**Strategy:** The existing section is short (the 4-row table + a paragraph). Replace it entirely. Heading text changes from `## Folder flavors: container, virtual, doc-only` to `## Decision 1 — Folder flavor: container, virtual, or doc-only` so it matches the TL;DR anchor.

- [ ] **Step 1: Read the existing section to capture exact content for `old_string`.**

```bash
sed -n '/^## Folder flavors/,/^## /p' docs/CONTRIBUTING-services.md | head -20
```

- [ ] **Step 2: Replace the section** with spec §6.3 content. Replacement content:

```markdown
## Decision 1 — Folder flavor: container, virtual, or doc-only

Three legitimate flavors of folder live under `services/`. Pick the right one before writing anything else.

| Flavor | `service.yml`? | `virtual: true`? | `compose.yml`? | Examples in this repo |
|---|---|---|---|---|
| **Container service** | yes | absent / false | yes | most services — backend, supabase, ollama, weaviate, … |
| **Virtual manifest** | yes | `true` | no | `cloud-providers/` (LiteLLM-routed APIs), `globals/` (project + branding env), `tts-provider/` (engine selector) |
| **Doc-only folder** | no | n/a | no | `stt-provider/`, `doc-processor/`, `multi2vec-clip/` — aggregator docs + diagrams for a role whose engines live in sibling folders |

**Flowchart:**

1. Does it run as a container with its own image? → **container**.
2. Does it own env vars / `SOURCE` toggles but with no compose fragment of its own? → **virtual**. Set `virtual: true`; omit `compose.yml`. The validator enforces this.
3. Is it documentation-only — aggregating other manifests under one user-facing role? → **doc-only**. No `service.yml`, no `compose.yml`, just `README.md` + `architecture.svg` / `architecture.html`.

> **Worked example — Qdrant:** Qdrant ships as a container image (`qdrant/qdrant:v1.12.0`), exposes a real HTTP API, and has its own env vars → **container flavor**.

**Common mistakes:**
- Adding a virtual manifest with a compose fragment — the schema validator will reject it (`virtual: true` requires no `compose.yml`).
- Adding a doc-only folder when the role has env vars to manage — use a virtual manifest instead.
```

- [ ] **Step 3: Verify links.**

```bash
python scripts/check_doc_links.py
# Expected: exit 0
```

- [ ] **Step 4: Verify section position.** The new Decision 1 should land where the old "Folder flavors" was. Check:

```bash
grep -n "^## " docs/CONTRIBUTING-services.md | head -10
# Expected: TL;DR at top, then "The six decisions", then "Adding a new service" (existing), then "Decision 1 — Folder flavor"
```

- [ ] **Step 5: Commit.**

```bash
git add docs/CONTRIBUTING-services.md
git commit -m "docs: expand 'Folder flavors' into Decision 1 of service-addition runbook"
```

---

## Task 3: Add Decision 2 — Category

**Files:**
- Modify: `docs/CONTRIBUTING-services.md` — insert new H2 section directly after Decision 1.
- Reference: spec §6.4.

- [ ] **Step 1: Identify the insertion anchor.** Decision 2 goes after Decision 1's last line, before the next existing H2 (whichever that is now — likely "Cross-referencing sections in service READMEs" or "Schema cheatsheet"). Use the trailing portion of Decision 1's content as the `old_string`:

```bash
tail -5 <(sed -n '/^## Decision 1 — Folder flavor/,/^## /p' docs/CONTRIBUTING-services.md)
```

- [ ] **Step 2: Insert Decision 2 content** matching spec §6.4:

```markdown
## Decision 2 — Category

Every manifest declares one of six categories. The category drives two things: the wizard block your row renders in, and the port-slot block your service draws from.

| Category | Wizard block | Services currently in this category | When to pick |
|---|---|---|---|
| `infra` | Infrastructure | Kong, globals | Gateways, project-wide config, observability |
| `data` | Data | Supabase, Redis, MinIO, Neo4j, Weaviate | Databases, caches, object storage |
| `llm` | LLM Core | LiteLLM, Ollama, cloud-providers | LLM gateways / engines |
| `media` | Media | ComfyUI, parakeet, speaches, chatterbox, docling, searxng, multi2vec-clip, tts-provider | Multimodal AI (image / audio / doc / search) |
| `agents` | Agents & Workflows | Hermes, n8n, openclaw | Programmable AI agents, workflow runners |
| `apps` | Apps & UIs | Backend, Open WebUI, JupyterHub, Local Deep Researcher | User-facing UIs |

**Effects of the category:**
- **Wizard placement.** Categories render in fixed order (`infra` → `data` → `llm` → `media` → `agents` → `apps`). Within a category, services follow topological order (driven by `depends_on.required`).
- **Port-slot block.** Each category gets its own port-offset range — see [Decision 4](#decision-4--port-allocation).
- **Architecture-diagram clustering.** The generated `docs/diagrams/architecture.svg` clusters services by category.

> **Worked example — Qdrant:** Qdrant is a vector database. Its closest siblings in the stack are Weaviate and Supabase (which are also `data`-tier). → **`category: data`**.

**How to pick when you're unsure:** find the most-similar existing service and use its category. If your service genuinely doesn't fit any of the six, that's a design conversation, not a category decision — open an issue first.
```

- [ ] **Step 3: Verify links.**

```bash
python scripts/check_doc_links.py
```

- [ ] **Step 4: Verify section order.**

```bash
grep -n "^## " docs/CONTRIBUTING-services.md
# Expected: TL;DR → six decisions → Adding a new service (existing) → Decision 1 → Decision 2
```

- [ ] **Step 5: Commit.**

```bash
git add docs/CONTRIBUTING-services.md
git commit -m "docs: add Decision 2 (Category) to service-addition runbook"
```

---

## Task 4: Add Decision 3 — Source variants

**Files:**
- Modify: `docs/CONTRIBUTING-services.md` — insert directly after Decision 2.
- Reference: spec §6.5.

- [ ] **Step 1: Locate insertion anchor** (last line of Decision 2 / next H2).

- [ ] **Step 2: Insert Decision 3** content matching spec §6.5:

```markdown
## Decision 3 — Source variants

Every user-configurable service has an `<SVC>_SOURCE` env var. The wizard reads its values from the `sources.options` block in your manifest.

**Standard option names** (use these; don't invent new ones unless your service genuinely needs them):

| Option | Meaning | When to offer it |
|---|---|---|
| `container` | Run as a Docker container alongside the stack | Always, for container-flavor services |
| `container-cpu` / `container-gpu` | Split when the container has CPU/GPU variants | When you publish a GPU variant of the image |
| `localhost` | Connect to a user-managed instance on the host | When users typically already have this software installed locally (e.g. Ollama, ComfyUI) |
| `external` | Connect to a remote URL | When users may point at a managed cloud version |
| `api` | Use a hosted cloud API (no container) | LLM gateways only |
| `disabled` | Excluded from compose entirely | Always — every optional service must support this |
| `<engine>-*` | Engine-specific sub-variants | For aggregator services that pick from multiple engines (STT/TTS) |

**Implications of your choices:**

- **Locked vs. user-choice.** A service with only one source variant is "locked" — the wizard skips its prompt entirely. The `_is_locked` helper in `bootstrapper/services/topology.py` enforces this. Services like Backend, Kong, LiteLLM are locked because they're always-on.
- **`requires:` per option.** Use `requires: [<ENV_VAR>]` on a source option to declare prerequisite env vars (e.g. `external` typically requires `<SVC>_EXTERNAL_URL`).
- **`<SVC>_LOCALHOST_URL` symmetry.** If you offer `localhost`, BOTH the in-container consumers (`runtime_sc.<svc>.localhost.environment`) AND the Kong route generator (`bootstrapper/utils/kong_config_generator.py`) must read the SAME `<SVC>_LOCALHOST_URL` env var. Otherwise Kong and in-container clients silently disagree about where the localhost upstream lives. See [Common gotchas](#common-gotchas--anti-patterns).
- **`runtime_sc` slice per source.** Every source variant declared in `sources.options` must have a matching `runtime_sc.<key>.<source>` slice with `scale`, `environment`, `deploy`, `extra_hosts`. The manifest validator enforces this.

> **Worked example — Qdrant:** Most users won't already run Qdrant locally, so `container` is the primary path. But we offer all four anyway for flexibility:
> - `container` — default, scale=1
> - `localhost` — `QDRANT_LOCALHOST_URL` defaults to `http://host.docker.internal:6333` (Qdrant's standard host port)
> - `external` — `requires: [QDRANT_EXTERNAL_URL]`
> - `disabled` — scale=0
```

- [ ] **Step 3: Verify links.**

```bash
python scripts/check_doc_links.py
```

- [ ] **Step 4: Commit.**

```bash
git add docs/CONTRIBUTING-services.md
git commit -m "docs: add Decision 3 (Source variants) to service-addition runbook"
```

---

## Task 5: Add Decision 4 — Port allocation

**Files:**
- Modify: `docs/CONTRIBUTING-services.md` — insert directly after Decision 3.
- Reference: spec §6.6.

- [ ] **Step 1: Insert Decision 4** content matching spec §6.6. Note: the `CATEGORY_SLOTS` numbers were verified at spec-write time against `bootstrapper/services/topology.py` (2026-05-24). Re-verify before insertion:

```bash
grep -A8 "^CATEGORY_SLOTS" bootstrapper/services/topology.py
# Expected: infra (0,10), data (10,20), llm (30,10), media (40,20), agents (60,20), apps (80,20)
# If different: update the numbers in the content below before inserting.
```

- [ ] **Step 2: Insert Decision 4 content:**

```markdown
## Decision 4 — Port allocation

**The bootstrapper auto-assigns ports. You do not pick a port.**

**How it works:**
- `BASE_PORT` (default `63000`) is the bottom of the port range. Users can override with `./start.sh --base-port 64000`.
- `CATEGORY_SLOTS` in `bootstrapper/services/topology.py` assigns each category an `(offset, block_size)` tuple. Current values (accurate as of 2026-05-24):

  | Category | Offset | Block size | Resolved range with default `BASE_PORT=63000` |
  |---|---:|---:|---|
  | `infra` | 0 | 10 | 63000-63009 |
  | `data` | 10 | 20 | 63010-63029 |
  | `llm` | 30 | 10 | 63030-63039 |
  | `media` | 40 | 20 | 63040-63059 |
  | `agents` | 60 | 20 | 63060-63079 |
  | `apps` | 80 | 20 | 63080-63099 |

- Within each category block, services consume slots in **topological order** (driven by `depends_on.required` — see Decision 5). Multi-port services (e.g. Supabase's 8 containers, Weaviate's HTTP + gRPC pair, MinIO's API + Console pair) get a contiguous run.
- A category-overflow lint trips if you blow past your block. Fixes: move manifests to a different category (rare), or extend the block size in `CATEGORY_SLOTS` (also rare — coordinate with maintainers).

**How to declare a port:**

In your `env:` block, declare `name: <SVC>_PORT` with NO `default:` line. Convention is a single-line comment:

```yaml
env:
  - name: QDRANT_PORT
    # default removed — computed by services/topology.py slot allocator
```

The `services/env_assembler.py` regen step emits the resolved port into `.env.example`. Never hand-edit `.env.example` — it's a generated artifact (byte-equivalence-tested in CI).

> **Worked example — Qdrant:** Qdrant declares `QDRANT_PORT` with no default. Topology slots it into the `data` block at the next free offset, determined by where it lands in the topo sort relative to its siblings (Supabase microservices, Redis, MinIO, Neo4j, Weaviate). The exact number is auto-resolved at every regen — don't pin it.
```

- [ ] **Step 3: Verify links.**

```bash
python scripts/check_doc_links.py
```

- [ ] **Step 4: Commit.**

```bash
git add docs/CONTRIBUTING-services.md
git commit -m "docs: add Decision 4 (Port allocation) to service-addition runbook"
```

---

## Task 6: Add Decision 5 — Dependencies (the most nuanced section)

**Files:**
- Modify: `docs/CONTRIBUTING-services.md` — insert directly after Decision 4.
- Reference: spec §6.7. This section is the longest and most subtle; read the spec carefully.

- [ ] **Step 1: Insert Decision 5** content matching spec §6.7:

```markdown
## Decision 5 — Dependencies (`depends_on.required` / `optional`)

This is the most nuanced decision. The field `depends_on.required` in `service.yml` has **two semantics that get conflated**:

**Runtime semantics (intended):** "These services must be up before this one boots." Maps to the corresponding `depends_on:` block in your `compose.yml` fragment.

**Display-ordering semantics (overloaded):** The bootstrapper uses `depends_on.required` as the canonical-order backbone for the wizard's row order and the overview-box display. Within a category, services sort topologically; an edge from A → B means A appears AFTER B in the same category's wizard block.

### Why this matters — the footgun

Kong's manifest used to list 19 services in `required` because Kong **proxies** to them — but Kong doesn't need them to **boot** (only Supabase + Redis). Trimming the list to its real boot dependencies was correct.

But trimming `litellm` from `ollama.depends_on.required` correctly removed a fake runtime edge — and broke a UI ordering test (`test_row_order_stability.py`), because `ollama` was relying on that edge to pin its position in the wizard's LLM block. Removing it shifted port slots throughout the LLM and media blocks.

### Current convention (codified in manifest comments in commit `d98bc5a`)

- Use `required` for **genuine bootstrap blockers** AND for **cross-category display-ordering pins**.
- Comment any non-runtime edge inline as a display-ordering pin so readers don't try to "fix" it. Example from `services/ollama/service.yml`:

  ```yaml
  depends_on:
    # `litellm` is listed here NOT because the ollama container calls
    # LiteLLM (the call direction is the opposite), but because the
    # bootstrapper uses `depends_on.required` as the canonical-order
    # backbone for the wizard / overview-box display. […]
    required:
      - supabase
      - litellm
  ```

- A future schema change may add a separate `display_order:` field that takes over the ordering job; until then, comment the intent.

### Things to avoid

- **Don't** list every service you *call* in `required`. Use `data_flow.calls` for that (it drives the architecture diagram and the per-service README's Dependencies & Integrations block — not topology).
- **Don't** depend on virtual aggregates (`globals`, `cloud-providers`) in `required`. They have no runtime presence; the audit removed phantom `globals` edges from `supabase` and `docling`.
- **Don't** list `optional` deps that compose doesn't enforce. The `optional` list is documentation; if compose doesn't gate on it, it has no effect.
- **Don't** list a depends-on for a service that's source-replaceable (`localhost`, `external`, `disabled`). The audit script `scripts/check-compose-source-deps.py` enforces this; SOURCE-replaceable consumers should reach their target via endpoint env vars + runtime readiness checks, not via compose `depends_on`.

> **Worked example — Qdrant:** Qdrant's only data-tier sibling that always runs is Supabase (the substrate the bootstrapper provisions before any other service starts). Listing it as a required dep pins Qdrant's position in the data block topologically. → `required: [supabase]`, `optional: []`.

### `data_flow.calls` is separate

The `data_flow.calls` field is a runtime call graph that drives the architecture diagram and the per-service README's Dependencies & Integrations block. It is **independent** of `depends_on`. Use it to describe which services this one calls at runtime in the request path (excluding init-time bootstrap calls).
```

- [ ] **Step 2: Verify links.**

```bash
python scripts/check_doc_links.py
```

- [ ] **Step 3: Commit.**

```bash
git add docs/CONTRIBUTING-services.md
git commit -m "docs: add Decision 5 (Dependencies) to service-addition runbook"
```

---

## Task 7: Add Decision 6 — Adaptive behavior + when to write a hook

**Files:**
- Modify: `docs/CONTRIBUTING-services.md` — insert directly after Decision 5.
- Reference: spec §6.8.

- [ ] **Step 1: Insert Decision 6** content matching spec §6.8:

```markdown
## Decision 6 — Adaptive behavior + when to write a hook

Most services express their per-source behavior with declarative `runtime_sc` YAML. The synthesizer in `bootstrapper/services/sc_synthesizer.py` concatenates all manifests' `runtime_sc` slices into the runtime service-config dict the bootstrapper consumes.

**Declarative example** (suffices for ~90% of services):

```yaml
runtime_sc:
  qdrant:
    container:
      scale: 1
      environment:
        QDRANT_LOG_LEVEL: info
      deploy: {}
      extra_hosts: []
    localhost:
      scale: 0
      environment:
        QDRANT_ENDPOINT: ${QDRANT_LOCALHOST_URL}
      deploy: {}
      extra_hosts:
        - host.docker.internal:host-gateway
    disabled:
      scale: 0
      environment: {}
      deploy: {}
      extra_hosts: []
```

### When you need a `_generate_<svc>_config()` Python helper

Write a helper in `bootstrapper/services/service_config.py` and wire it into `generate_service_environment()` ONLY when one of these is true:

1. **Multi-input SOURCE dependencies.** Your output depends on more than one `<SVC>_SOURCE` value. Example: `_generate_stt_provider_config` reads BOTH `STT_PROVIDER_SOURCE` and `TTS_PROVIDER_SOURCE` to dedupe Speaches when it's selected for both roles.
2. **Derived / aggregated state.** You need to compute env vars from a set of toggles. Example: `_generate_cloud_providers_config` reads three `CLOUD_*_SOURCE` toggles + their API keys and emits `LITELLM_ENABLED_PROVIDERS` as a comma-separated string.
3. **Runtime-computed values.** You need an env var whose value depends on another service's port, computed at runtime from `BASE_PORT`.

For everything else, stay declarative. Adding a hook means writing Python, adding a unit test for it, and giving future maintainers an extra place to read.

> **Worked example — Qdrant:** Single SOURCE, no cross-service dependencies, no derived state. → **No hook needed.** The declarative `runtime_sc` covers all four sources.

### `runtime_adaptive` and `runtime_deps`

Two adjacent fields that occasionally apply:

- **`runtime_adaptive`** — for services like `backend` that adapt their behavior based on which upstream services are enabled. Declares `adapts_to:` (a list of provider keys) and `environment_adaptation:` (env vars conditionally set when those providers are active). See `services/backend/service.yml` for the reference pattern.
- **`runtime_deps`** — declares optional runtime dependencies (services this one calls only if they're enabled). Drives the info-message shown to the user during the wizard.

Use these only if your service is genuinely adaptive (backend + open-webui are the only two today). Don't reach for them by default.
```

- [ ] **Step 2: Verify links.**

```bash
python scripts/check_doc_links.py
```

- [ ] **Step 3: Commit.**

```bash
git add docs/CONTRIBUTING-services.md
git commit -m "docs: add Decision 6 (Adaptive / hooks) to service-addition runbook"
```

---

## Task 8: Add Mechanics — the full qdrant manifest + compose

**Files:**
- Modify: `docs/CONTRIBUTING-services.md` — insert directly after Decision 6.
- Reference: spec §6.9.
- Verify: the qdrant `service.yml` snippet must validate against `bootstrapper/schemas/service.schema.json` once formally checked in Task 15.

- [ ] **Step 1: Insert Mechanics section** matching spec §6.9. This is the longest single section (~90 lines) — it contains the full result of the six decisions as the two files you actually save.

```markdown
## Mechanics — putting it all together

After making the six decisions, you write two files. Here's the full result for Qdrant. Line callouts (`# ← Decision N`) point back to the decision section that explains the choice.

### `services/qdrant/service.yml`

```yaml
# services/qdrant/service.yml — Qdrant vector database
name: qdrant
label: "Qdrant (vector database)"
category: data                                # ← Decision 2
docs: services/qdrant/README.md

containers:
  - qdrant

images:
  - var: QDRANT_IMAGE
    default: "qdrant/qdrant:v1.12.0"
    container: qdrant

sources:                                      # ← Decision 3
  var: QDRANT_SOURCE
  default: disabled                           # off by default; user opts in
  options:
    - id: container
      label: "Container"
    - id: localhost
      label: "Host (existing Qdrant)"
    - id: external
      label: "External (custom URL)"
      requires: [QDRANT_EXTERNAL_URL]
    - id: disabled
      label: "Disabled"

env:
  - name: QDRANT_SOURCE
    default: disabled
  - name: QDRANT_PORT                         # ← Decision 4 (no default — auto-assigned)
    # default removed — computed by services/topology.py slot allocator
  - name: QDRANT_LOCALHOST_URL
    default: "http://host.docker.internal:6333"
    description: "Used when QDRANT_SOURCE=localhost. Same var consumed by Kong's qdrant.localhost route."
  - name: QDRANT_EXTERNAL_URL
    default: ""
    description: "Required when QDRANT_SOURCE=external."
  - name: QDRANT_ENDPOINT
    auto_managed: true
  - name: QDRANT_SCALE
    auto_managed: true

depends_on:                                   # ← Decision 5
  required:
    - supabase
  optional: []

exports: []

rows:
  - display_name: "Qdrant"
    source_var: QDRANT_SOURCE
    port_var: QDRANT_PORT
    scale_var: QDRANT_SCALE
    alias: qdrant.localhost
    description: "Vector database (Qdrant)."
    localhost_endpoint_var: QDRANT_ENDPOINT

runtime_sc:                                   # ← Decision 6 (declarative, no hook)
  qdrant:
    container:
      scale: 1
      environment:
        QDRANT_ENDPOINT: http://qdrant:6333
      deploy: {}
      extra_hosts: []
    localhost:
      scale: 0
      environment:
        QDRANT_ENDPOINT: ${QDRANT_LOCALHOST_URL}
      deploy: {}
      extra_hosts: [host.docker.internal:host-gateway]
    external:
      scale: 0
      environment:
        QDRANT_ENDPOINT: ${QDRANT_EXTERNAL_URL}
      deploy: {}
      extra_hosts: []
    disabled:
      scale: 0
      environment:
        QDRANT_ENDPOINT: ''
      deploy: {}
      extra_hosts: []

data_flow:
  calls: []
```

### `services/qdrant/compose.yml`

```yaml
# services/qdrant/compose.yml — Qdrant vector database
services:
  qdrant:
    image: ${QDRANT_IMAGE}
    container_name: ${PROJECT_NAME}-qdrant
    restart: unless-stopped
    deploy:
      replicas: ${QDRANT_SCALE:-0}
    ports:
      - "${QDRANT_PORT}:6333"
    volumes:
      - qdrant-data:/qdrant/storage
    healthcheck:
      test: ["CMD", "wget", "-q", "-O-", "http://localhost:6333/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - backend-network

volumes:
  qdrant-data:
    name: ${PROJECT_NAME}-qdrant-data
    driver: local
```

### `docker-compose.yml` — one new include line

Add to the top-level `include:` block in the `# Data tier` section:

```yaml
  # Data tier
  - services/supabase/compose.yml
  - services/redis/compose.yml
  - services/minio/compose.yml
  - services/neo4j/compose.yml
  - services/qdrant/compose.yml              # ← new
```
```

- [ ] **Step 2: Verify links.**

```bash
python scripts/check_doc_links.py
```

- [ ] **Step 3: Verify the YAML in the snippet is internally consistent.** Eyeball the snippet against `bootstrapper/schemas/service.schema.json` — every key used should be in the schema. Specifically check: `virtual` (optional), `name`, `label`, `category`, `docs`, `containers`, `images`, `sources`, `env`, `depends_on`, `exports`, `rows`, `runtime_sc`, `data_flow`.

- [ ] **Step 4: Commit.**

```bash
git add docs/CONTRIBUTING-services.md
git commit -m "docs: add Mechanics section with full qdrant manifest + compose example"
```

---

## Task 9: Add "After you save the files — regen + lint commands" section

**Files:**
- Modify: `docs/CONTRIBUTING-services.md` — insert directly after Mechanics.
- Reference: spec §6.10.

- [ ] **Step 1: Insert the section** matching spec §6.10:

````markdown
## After you save the files — regen + lint commands in order

Five commands, in this order:

```bash
cd bootstrapper

# 1. Regenerate .env.example from manifests
uv run python -m services.env_assembler

# 2. Regenerate README.md TOPOLOGY block (auto-includes the new row)
uv run python -m tools.generate_readme_topology

# 3. Regenerate docs/diagrams/architecture.dot (+ render the SVG via Graphviz)
uv run python -m tools.generate_architecture_diagram
dot -Tsvg ../docs/diagrams/architecture.dot > ../docs/diagrams/architecture.svg

# 4. Lint — fails if any of steps 1-3 were skipped
uv run python -m tools.validate_fragments

# 5. (Optional, recommended for new manifests) Regen per-service README + diagram
PYTHONPATH=. uv run python -m docs.regen qdrant
# After this, services/qdrant/{README.md, architecture.svg, architecture.html} exist.
```

**When to re-run each step:**

- **`env_assembler`** — after any change to a manifest's `env:` block, port allocation, or source variants.
- **`generate_readme_topology`** — after any change to a manifest's `rows:`, `display_name`, `category`, or `alias`.
- **`generate_architecture_diagram` + `dot -Tsvg`** — after any change to a manifest's `depends_on` or `data_flow.calls`.
- **`validate_fragments`** — always, as the final check before committing.
- **`docs.regen`** — only after creating a new service, or after editing `data_flow.calls` on an existing service. The drift gate in CI (`bootstrapper.docs.regen --all --check`) catches stale per-service READMEs/SVGs/HTMLs.

**Graphviz prerequisite:** the `dot` command requires Graphviz. Install with `brew install graphviz` (macOS), `sudo apt-get install graphviz` (Debian/Ubuntu), or `choco install graphviz` (Windows). See `docs/diagrams/README.md`.
````

- [ ] **Step 2: Verify links.**

```bash
python scripts/check_doc_links.py
```

- [ ] **Step 3: Commit.**

```bash
git add docs/CONTRIBUTING-services.md
git commit -m "docs: add regen + lint command sequence to service-addition runbook"
```

---

## Task 10: Add "Audit-script + CI implications" section

**Files:**
- Modify: `docs/CONTRIBUTING-services.md` — insert directly after the regen/lint section.
- Reference: spec §6.11.

- [ ] **Step 1: Insert the section** matching spec §6.11:

```markdown
## Audit-script + CI implications

After adding a service, check these allowlists. Skipping them means CI fails on the next push.

### `scripts/check-compose-source-deps.py` — two allowlists

- **`REQUIRED_DEPENDS_ON`** — set of `(service, dependency)` tuples that MUST appear in compose `depends_on`. Add entries here if your compose fragment hard-depends on `litellm`, `redis`, `supabase-db`, `weaviate-init`, etc. The script fails CI if your manifest claims a hard dep that compose doesn't enforce, OR vice versa.
- **`FORBIDDEN_OPTIONAL_DEPENDS_ON`** — set of edges that MUST NOT exist (depending on a SOURCE-replaceable service via `depends_on` is unsafe because that service may not run as a container). Add entries here if you have an intentional exception with documented justification.

### `scripts/check-kong-routes.py` — baseline-default audit

If your service publishes a `*.localhost` alias, the generated Kong route is checked against a baseline. Add an entry to the script's allowlist if your route uses non-default settings (e.g. `preserve_host: True` for browser SPAs, custom plugin chain, custom timeout).

### `.github/dependabot.yml` — `directories:` list

If your service ships a `requirements.txt` / `pyproject.toml` in a `build/` or `provider/` subdirectory, add the path to the `directories:` list of the `pip` ecosystem block. **Memory note:** all active manifests must be enumerated; omitted paths drop from scan coverage and silent vulnerabilities accumulate.

### CI gates that run on every push

The `.github/workflows/services-lint.yml` workflow has three jobs:

| Job | What it catches |
|---|---|
| **Manifest lint + unit tests** | `validate_fragments` lint + 315+ pytest tests. Catches: manifest schema violations, dependency cycles, env-example drift, category overflow. |
| **Compose merge + byte-equivalence + source-permutation matrix** | Renders `docker compose config` for the merged fragment list + verifies it matches the golden baseline + tests every source variant of every service. Catches: compose-syntax errors, source-permutation regressions. |
| **Docs drift + audit scripts** | `regen --all --check` + the 5 audit scripts (`check_doc_links`, `check-compose-source-deps`, `check-docs-drift`, `check-kong-routes`, `validate_research_schema`). Catches: stale per-service docs, missing `REQUIRED_DEPENDS_ON` entries, Kong route default drift, broken markdown links, research-schema violations. |

Run the equivalent of all three locally before pushing:

```bash
cd bootstrapper && uv run pytest -q                                    # job 1 + 2 (minus byte-equivalence)
cd bootstrapper && uv run python -m tools.validate_fragments           # job 1 lint
cp .env.example .env && docker compose -f docker-compose.yml config -q # job 2 merge check
cd .. && PYTHONPATH=bootstrapper uv run --project bootstrapper python -m bootstrapper.docs.regen --all --check  # job 3 docs drift
python scripts/check_doc_links.py                                      # job 3 link check
python scripts/check-compose-source-deps.py                            # job 3 deps audit
python scripts/check-kong-routes.py                                    # job 3 kong audit
```
```

- [ ] **Step 2: Verify links.**

```bash
python scripts/check_doc_links.py
```

- [ ] **Step 3: Commit.**

```bash
git add docs/CONTRIBUTING-services.md
git commit -m "docs: add audit-script + CI implications section to service-addition runbook"
```

---

## Task 11: Add "Common gotchas + anti-patterns" section

**Files:**
- Modify: `docs/CONTRIBUTING-services.md` — insert directly after the audit-scripts section.
- Reference: spec §6.12.

- [ ] **Step 1: Insert the gotchas section** matching spec §6.12:

```markdown
## Common gotchas + anti-patterns

Distilled from real audit findings — each entry cites the commit, PR, or memory note it came from.

### Dependency-list gotchas

- **Cross-category `depends_on.required` is a display-order pin.** Removing `litellm` from `ollama.required` is correct from a runtime POV but shifts the wizard's row order and reshuffles port slots in the media block. Keep cross-category edges and document the intent inline. See commit `d98bc5a`.
- **Don't depend on virtual aggregates in `required`.** `globals`, `cloud-providers`, `tts-provider` are virtual — no container, no compose. Depending on them adds a phantom node to the topo sort. The audit removed phantom `globals` edges from `supabase` and `docling`.
- **Compose-only deps vs. manifest deps must align both ways.** Kong's manifest used to list 19 proxy targets in `required` but compose only had 5 (truly correct — over-claimed). Backend's manifest only listed `[supabase, redis]` but compose waited for `litellm` health (under-claimed). The audit corrected both; `scripts/check-compose-source-deps.py` now catches missing edges.

### URL / localhost handling

- **`<SVC>_LOCALHOST_URL` overrides must be symmetric.** If you read it in a new in-container consumer, Kong's route generator must read the same var too. Otherwise the two paths silently disagree about where the upstream lives.
- **Kong routes fronting browser SPAs need `preserve_host: True`.** Without it the SPA emits unreachable redirect URLs containing the internal Docker hostname.

### Init-container patterns

- **Init containers use vanilla `alpine:latest` + inline `apk add`.** Don't ship a Dockerfile that builds a custom init image — the global `alpine:latest` tag gets clobbered.
- **TTS/STT engine in-container ports are NOT all 8000.** Parakeet, Speaches, Docling listen on `8000`; Chatterbox listens on `4123`. Don't assume.

### Regen / test gotchas

- **`.env.example` is byte-equivalence-tested.** After any manifest change affecting env vars or port allocation, regen `.env.example` or `test_env_example_consistency` will fail CI.
- **`test_fragment_equivalence` is sensitive to Compose-version defaults.** Don't regenerate the golden baseline reflexively when this test fails. Extend `_strip_volatile_defaults` in the test fixture instead.
- **`docker compose config` needs `.env` to render properly.** In CI, the audit-scripts job copies `.env.example` to `.env` before running the source-deps audit. Locally, you have a real `.env` so this is invisible — but if you remove your `.env`, the audit script's fallback to raw parsing of the top-level `docker-compose.yml` (which is an `include:`-only shell) produces spurious "missing required core dependency" failures.

### Topology / category gotchas

- **A new service in a near-full category block can trip the category-overflow lint.** `data` and `media` blocks are 20 slots each but Supabase alone uses 7. Check current utilization before assuming there's room.
- **Renaming a `row.display_name` breaks tests that hardcode it.** `test_wizard_app_discovery.py` has an `EXPECTED_DISCOVERED` frozenset; update it when renaming.
```

- [ ] **Step 2: Verify links.**

```bash
python scripts/check_doc_links.py
```

- [ ] **Step 3: Commit.**

```bash
git add docs/CONTRIBUTING-services.md
git commit -m "docs: add common-gotchas section to service-addition runbook"
```

---

## Task 12: Reorder existing reference sections to flow at the end

**Files:**
- Modify: `docs/CONTRIBUTING-services.md` — move the kept-verbatim sections after the gotchas section.
- Reference: spec §6.13.

The existing sections should appear in this order at the end of the doc:
1. Subdirectory naming convention (existing — keep)
2. Modifying an existing service (existing — keep)
3. Schema cheatsheet (existing — keep)
4. Validator rules (what the lint catches) (existing — keep)
5. Byte-equivalence (existing — keep)
6. `services/_user/` overlay slot (existing — keep)
7. Documentation-only manifest fields (existing — keep)

The current order has these sections scattered through the file. Move them so they all appear AFTER the gotchas section, in the order above.

- [ ] **Step 1: List current section order.**

```bash
grep -n "^## " docs/CONTRIBUTING-services.md
```

- [ ] **Step 2: For each existing section in the order above, locate its current line range and verify it still has the correct content.** Use:

```bash
sed -n '/^## Subdirectory naming convention/,/^## /p' docs/CONTRIBUTING-services.md | head -25
```

- [ ] **Step 3: Move sections using `git mv`-style edits.** This is a manual reorder — use the Edit tool with each section as `old_string` and the new section position as the insertion point. Take it one section at a time.

- [ ] **Step 4: Verify final section order with grep.**

```bash
grep -n "^## " docs/CONTRIBUTING-services.md
# Expected order:
# 1. TL;DR — the 60-second checklist
# 2. The six decisions you have to make
# 3. Adding a new service                       (existing — keep its position immediately after the overview)
# 4. Decision 1 — Folder flavor
# 5. Decision 2 — Category
# 6. Decision 3 — Source variants
# 7. Decision 4 — Port allocation
# 8. Decision 5 — Dependencies
# 9. Decision 6 — Adaptive / hooks
# 10. Mechanics — putting it all together
# 11. After you save the files — regen + lint commands in order
# 12. Audit-script + CI implications
# 13. Common gotchas + anti-patterns
# 14. Subdirectory naming convention
# 15. Modifying an existing service
# 16. Schema cheatsheet
# 17. Validator rules (what the lint catches)
# 18. Byte-equivalence
# 19. `services/_user/` overlay slot
# 20. Documentation-only manifest fields
```

- [ ] **Step 5: Verify links one more time.**

```bash
python scripts/check_doc_links.py
```

- [ ] **Step 6: Commit.**

```bash
git add docs/CONTRIBUTING-services.md
git commit -m "docs: reorder reference sections to flow after walkthrough material"
```

---

## Task 13: Update "Modifying an existing service" with additional notes subsection

**Files:**
- Modify: `docs/CONTRIBUTING-services.md` — append a new subsection to the existing `## Modifying an existing service` section.
- Reference: spec §6.14.

- [ ] **Step 1: Locate the current end of "Modifying an existing service"** (just before the next `## `).

```bash
sed -n '/^## Modifying an existing service/,/^## /p' docs/CONTRIBUTING-services.md
```

- [ ] **Step 2: Append the new subsection** at the end of the existing section, just before the next `## `:

```markdown
### Common modification flows

Short walk-throughs for the modifications you'll do most often:

- **Add a new source variant to an existing service.** Edit `sources.options` + `runtime_sc.<key>` to include the new source. Regen `.env.example`. The source-permutation matrix in CI will exercise every variant — make sure your new variant has a valid `runtime_sc` slice.
- **Rename a service's display name (`rows[].display_name`).** Update the row, then regen the README topology block. Search the test suite for the old name — `bootstrapper/tests/test_wizard_app_discovery.py::EXPECTED_DISCOVERED` is the most common dependency.
- **Bump a container image version.** Edit `images[].default` only. The compose fragment uses `${X_IMAGE}` interpolation, so nothing else changes. Don't forget to test the new image locally before committing.
- **Split a service family into multiple manifests.** Non-trivial. The supabase manifest (8 containers in one family) is the reference pattern; consult it before splitting.
```

- [ ] **Step 3: Verify links.**

```bash
python scripts/check_doc_links.py
```

- [ ] **Step 4: Commit.**

```bash
git add docs/CONTRIBUTING-services.md
git commit -m "docs: add common modification flows subsection"
```

---

## Task 14: Update existing "Adding a new service" 9-step list to cross-link the runbook

**Files:**
- Modify: `docs/CONTRIBUTING-services.md` — prepend a pointer to the TL;DR at the top of the existing `## Adding a new service` section.

The existing 9-step list is still useful as a terse "I know what I'm doing" path. Add a one-line note at its top pointing readers to the TL;DR for the decision-driven walkthrough.

- [ ] **Step 1: Locate the existing "Adding a new service" section.**

```bash
sed -n '/^## Adding a new service/,/^## /p' docs/CONTRIBUTING-services.md | head -3
```

- [ ] **Step 2: Insert a one-line pointer** immediately after the H2 heading, before the first numbered step. Edit using the heading + first step as `old_string`:

```markdown
## Adding a new service

> For a decision-driven walkthrough with worked example, see [TL;DR — the 60-second checklist](#tldr--the-60-second-checklist) and the six **Decision** sections that follow it. The 9-step list below is the terse "I know what I'm doing" path.

1. …(existing step content)
```

- [ ] **Step 3: Verify links.**

```bash
python scripts/check_doc_links.py
```

- [ ] **Step 4: Commit.**

```bash
git add docs/CONTRIBUTING-services.md
git commit -m "docs: cross-link existing 'Adding a new service' steps to the runbook TL;DR"
```

---

## Task 15: Add 1-line pointer above Schema cheatsheet

**Files:**
- Modify: `docs/CONTRIBUTING-services.md` — prepend a one-line note above the existing `## Schema cheatsheet` heading.
- Reference: spec §4 (the "kept, with 1-line pointer prepended" note).

- [ ] **Step 1: Insert the pointer** immediately under the H2:

```markdown
## Schema cheatsheet

> This section is a quick field reference. For guidance on which fields apply when (and why), see Decisions 1-6 above.

(existing schema cheatsheet content unchanged)
```

- [ ] **Step 2: Verify links.**

```bash
python scripts/check_doc_links.py
```

- [ ] **Step 3: Commit.**

```bash
git add docs/CONTRIBUTING-services.md
git commit -m "docs: cross-link Schema cheatsheet to the Decision sections"
```

---

## Task 16: Final pass — link check, anchor check, narrative read-through

**Files:**
- Verify: `docs/CONTRIBUTING-services.md` (full file)

- [ ] **Step 1: Run all audit gates that touch this doc.**

```bash
# 1. Internal markdown link validator
python scripts/check_doc_links.py
# Expected: exit 0

# 2. Doc-structure audit
python scripts/check-docs-drift.py
# Expected: PASS links / architecture_refs / source_matrix / required_files / placeholder_urls; exit 0

# 3. Full pytest (the doc work doesn't affect tests, but confirms no regression)
cd bootstrapper && uv run pytest -q --tb=no 2>&1 | tail -5
# Expected: 315 passed, 0 failed
```

- [ ] **Step 2: Anchor check.** All in-doc `[link](#anchor)` references must resolve. List them:

```bash
grep -oE '\[[^]]+\]\(#[^)]+\)' docs/CONTRIBUTING-services.md | sort -u
```

For each anchor, verify the matching `## ` or `### ` heading exists. GitHub's anchor algorithm: lowercase, spaces → `-`, drop punctuation. Spot-check 3-4 manually.

- [ ] **Step 3: End-to-end narrative read-through.** Read the doc top to bottom. Check for:
  - **Section order** matches spec §4 table.
  - **Each Decision section** has a "Worked example — Qdrant" callout.
  - **No "TBD" / "TODO" / placeholder content** anywhere.
  - **No broken cross-references** to spec/CHANGELOG/etc.
  - **Line count** is within spec's ~870-line estimate (±10%).

```bash
wc -l docs/CONTRIBUTING-services.md
# Expected: ~780-960 lines (target ~870)
```

- [ ] **Step 4: Schema-conformance spot-check.** The `services/qdrant/service.yml` snippet in the Mechanics section should validate against the schema. Test it manually:

```bash
# Extract the YAML snippet from the doc and validate it
# (manual: copy the snippet to /tmp/qdrant.yml, then:)
cd bootstrapper && uv run python -c "
import json, sys, yaml, jsonschema
schema = json.load(open('schemas/service.schema.json'))
doc = yaml.safe_load(open('/tmp/qdrant.yml'))
jsonschema.validate(doc, schema)
print('OK')
"
# Expected: OK
# If it fails: the worked example is broken; fix the YAML in the Mechanics section.
```

- [ ] **Step 5: Final commit (if any fixes were needed in this pass).**

```bash
git status docs/CONTRIBUTING-services.md
# If clean: skip the commit. If modified:
git add docs/CONTRIBUTING-services.md
git commit -m "docs: fix link anchors / narrative flow in service-addition runbook (final pass)"
```

- [ ] **Step 6: Final summary.** Print the deliverables and metrics:

```bash
echo "=== Deliverables ==="
wc -l docs/CONTRIBUTING-services.md
echo ""
echo "=== Sections ==="
grep -c "^## " docs/CONTRIBUTING-services.md
echo ""
echo "=== Commits made for this work ==="
git log --oneline --grep="service-addition runbook\|docs:.*service" $(git merge-base HEAD origin/main)..HEAD | wc -l
```

Expected:
- `wc -l`: ~870 lines (spec target).
- `grep -c "^## "`: 19-20 top-level sections.
- Commits: 14-16 commits total (one per task that touched the file).

---

## Self-Review Notes

Coverage matrix (spec sections → tasks):

| Spec section | Task |
|---|---|
| §6.1 TL;DR | Task 1 |
| §6.2 Six decisions overview | Task 1 |
| §6.3 Decision 1 — Folder flavor | Task 2 |
| §6.4 Decision 2 — Category | Task 3 |
| §6.5 Decision 3 — Source variants | Task 4 |
| §6.6 Decision 4 — Port allocation | Task 5 |
| §6.7 Decision 5 — Dependencies | Task 6 |
| §6.8 Decision 6 — Adaptive / hooks | Task 7 |
| §6.9 Mechanics | Task 8 |
| §6.10 Regen + lint commands | Task 9 |
| §6.11 Audit-script + CI implications | Task 10 |
| §6.12 Common gotchas | Task 11 |
| §6.13 Existing sections kept verbatim | Task 12 (reorder), Task 15 (Schema cheatsheet pointer) |
| §6.14 Modifications additional notes | Task 13 |
| §11 Implementation order step 8 (cross-link 9-step list) | Task 14 |
| §10 Acceptance criteria 1-7 | Task 16 (final verification) |

No spec section unaccounted for. No placeholder content in the plan. All YAML snippets are complete; all referenced files/paths/commands are concrete.
