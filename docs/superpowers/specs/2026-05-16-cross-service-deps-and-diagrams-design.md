# Cross-service dependencies, documentation standardization, and per-service architecture diagrams — Design

**Date:** 2026-05-16
**Status:** Approved (awaiting implementation plan)
**Owner:** Kaveh Razavi

## Problem

The stack has 21 services with wildly uneven documentation depth (placeholder
46-line docs alongside the 222-line Hermes gold standard), no canonical place
for "how this service relates to the others" in each doc, and no per-service
architecture diagrams at all. Manifests already encode a rich dependency graph
(`depends_on.required`, `runtime_adaptive.adapts_to`, `runtime_deps.optional`)
but readers can't see it. Cross-service integration opportunities exist
(Hermes ↔ Neo4j, Backend ↔ SearXNG, candidate new services like Obsidian/MCP)
but have never been systematically catalogued.

## Goals

1. Every service has a **standardized "Dependencies & Integrations" section**
   in its docs, with **Current** (manifest-derived) and **Future** (research-
   derived) subsections.
2. Every service has a **dedicated folder** under `docs/services/<name>/`
   containing `README.md`, `architecture.html`, and `architecture.svg`.
3. Every service has a **3-column tiered architecture diagram** (upstream /
   focus / downstream), regenerable on demand from manifests via a Python
   generator that applies the existing `architecture-diagram` skill's design
   system programmatically.
4. A **systematic pairwise integration research pass** (21 parallel subagents,
   hub-per-service) produces a master matrix of missing-pair integrations,
   candidate new services, and per-service feature gaps.
5. The seven placeholder docs (backend, comfyui, local-deep-researcher,
   multi2vec-clip, n8n, redis, searxng) are rewritten to Hermes-grade depth.

## Non-goals

- A top-level stack diagram showing all 21 services on one page (different
  layout problem; out of scope here).
- Auto-implementing any of the Future integrations. This project produces
  *documented opportunities*, not wired features.
- Linting/formatting tooling for the bootstrapper.
- A web viewer for the integration matrix.

## High-level architecture

Three phases under one umbrella spec. Phase A is a strict prerequisite for
B and C. B and C run in parallel once A is done.

```
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE A — Foundations                                               │
│   • Standardize per-service doc skeleton                            │
│   • Define "Dependencies & Integrations" subsection template        │
│   • Build manifest-driven diagram generator (Python module)         │
│   • Migrate docs/services/foo.md → docs/services/foo/README.md      │
│   • Update inbound links                                            │
│   • Generate v0 diagrams (current wiring only) for all 21 services  │
│   • CI drift gate                                                   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│ PHASE B — Research              │  │ PHASE C — Content authoring     │
│   21 parallel subagents,        │  │   Populate Future subsections   │
│   each produces a matrix row:   │  │   + bring 7 placeholder docs    │
│     1. Missing-pair integrations│  │   to Hermes-grade depth         │
│     2. Candidate new services   │  │                                 │
│     3. Per-service feature gaps │  │                                 │
└─────────────────────────────────┘  └─────────────────────────────────┘
                  │                               │
                  └───────────────┬───────────────┘
                                  ▼
                  ┌─────────────────────────────────┐
                  │ Regenerate all diagrams from    │
                  │ final state (implicit Phase D). │
                  └─────────────────────────────────┘
```

## Phase A — Foundations

### A.1 — Per-service doc folder layout

Migrate every `docs/services/<name>.md` to `docs/services/<name>/README.md`.
Both the diagram artifacts and the doc live in the same per-service folder:

```
docs/services/<name>/
├── README.md           # was docs/services/<name>.md
├── architecture.html   # generated, standalone (skill-compliant)
└── architecture.svg    # generated, embedded in README.md
```

Inbound references to the old `.md` paths must be rewritten in the same
migration commit. A validator script (`scripts/check_doc_links.py`) checks
every internal markdown link in `docs/**`, `README.md`, and `CHANGELOG.md`
resolves; CI runs this script.

### A.2 — Dependencies & Integrations section template

Every service README carries this canonical block, in this order, with the
exact subsection headings shown:

````markdown
## Dependencies & Integrations

> Auto-generated section — the **Current** subsections are derived from
> `services/<name>/service.yml`. Re-run
> `python -m bootstrapper.docs.regen <name>` after manifest changes.

### Current — Upstream (this service depends on)

| Service | Type | Mechanism | Failure mode |
|---|---|---|---|
| ... | required / adaptive / optional | <endpoint / protocol> | <what happens if disabled> |

### Current — Downstream (services that depend on this)

| Service | Type | Mechanism |
|---|---|---|
| ... | consumer | <how the consumer reaches this service> |

### Architecture diagram

![<Service> architecture](./architecture.svg)

[Open the interactive HTML diagram](./architecture.html) for a full-screen view.

### Future — Missing pair integrations

Pairs of existing stack services where wiring would add value but isn't in
place today. Source: `docs/research/rows/<name>.md`.

- **<Service> ↔ <Other>** — *Why:* ... *Mechanism sketch:* ... *Effort:* ... *Open questions:* ...

### Future — Candidate new services

External services not currently in the stack that would plug in cleanly here.
Each links to a full one-pager in `docs/research/candidates/<slug>.md`.

- **<Candidate>** ([details](../../../research/candidates/<slug>.md)) — *Headline:* ... *Wires into:* ...

### Future — Unused features in this service

Capabilities the upstream project exposes that we don't yet leverage.

- **<feature>** — *Why pursue:* ... *Effort:* ...
````

**Rules:**

1. Current vs Future is a hard split. Current is fact-based; Future is
   speculative. Readers should never have to guess which is which.
2. Both Upstream and Downstream tables are required even when empty. An
   explicit empty table beats a missing section.
3. The architecture diagram lives inside this section, not as a sibling.
4. The Failure mode column on the Upstream table surfaces adaptive
   degradation behavior already encoded in `runtime_adaptive`.
5. No "TBD" placeholders in Future bullets. If a sub-block has nothing
   notable, the entire sub-block emits the line
   `_No high-confidence opportunities identified._` and ends there.

### A.3 — Architecture diagram standard

**Layout:** three vertical lanes — upstream on the left (deps), focus in the
middle (single box, ~1.5–2× larger, category-colored stroke at full opacity),
downstream on the right (consumers).

**Visual style:** locked to the `architecture-diagram` skill's design system:

- Background: `#020617` (slate-950) with `40×40` grid pattern (`#1e293b`).
- Typography: JetBrains Mono everywhere; 12px component names, 9px sublabels,
  8px annotations, 7px tiny labels.
- Boxes: `rx="6"`, `stroke-width="1.5"`, `rgba(..., 0.4)` semi-transparent fill,
  category-color stroke pulled from `bootstrapper/services/topology.py::CATEGORY_COLORS`.
- Arrows: SVG `<marker id="arrowhead">`, painted before boxes so they render
  behind. Where masking matters (arrows passing under semi-transparent fills),
  emit an opaque `#0f172a` rect under the styled rect.

**Edge styles (three only):**

- `─────▶` Required dependency — solid slate (`#64748b`).
- `─ ─ ─▶` Optional / adaptive dependency — dashed amber (`#fbbf24`).
- `═════▶` Bidirectional loop (e.g. Hermes ↔ LiteLLM via model_list) —
  rendered as two parallel arrows with matching styles for the underlying
  dependency types.

**Layout rules:**

1. Sort within each lane by category, then alphabetically. Stable order
   across regenerations keeps diffs clean.
2. Empty lanes are drawn explicitly with a "no upstream deps" / "no
   downstream consumers" placeholder. Visual symmetry across all 21 diagrams.
3. Three summary cards below the diagram (following the skill's Info Card
   Pattern): required-dep count, optional-dep count, consumer count.
4. Footer line carries the generation timestamp (HTML comment only — not in
   SVG body, so SVG is byte-deterministic), manifest path, and the regen
   command.
5. Adaptive-degradation hover text on dashed edges via SVG `<title>` element.
6. viewBox height is computed from row count; no hand-tuning per service.
7. **Init containers are omitted from the focus diagram.** They are
   orchestration, not runtime dependencies. Their behavior is documented in
   the doc's text, not the diagram.

### A.4 — Python diagram generator

New module under `bootstrapper/docs/`:

```
bootstrapper/docs/
├── __init__.py
├── deps_resolver.py        # manifests → DepGraph
├── diagram_renderer.py     # DepGraph → HTML+SVG
├── deps_section_writer.py  # DepGraph → "Current — Upstream/Downstream" tables
├── merge_research.py       # 21 row files → docs/research/integration-matrix.md
├── templates/
│   ├── architecture.html.tmpl
│   ├── svg_box.tmpl
│   ├── svg_edge.tmpl
│   └── deps_section.md.tmpl
└── regen.py                # CLI entry: python -m bootstrapper.docs.regen
```

**Core data model:**

```python
@dataclass(frozen=True)
class DepEdge:
    other: str
    kind: Literal["required", "optional", "adaptive"]
    direction: Literal["upstream", "downstream"]
    mechanism: str
    failure_mode: str | None
    bidirectional: bool = False

@dataclass(frozen=True)
class DepGraph:
    focus: str
    category: str
    port: str | None
    source: str
    upstream: tuple[DepEdge, ...]
    downstream: tuple[DepEdge, ...]
    init_containers: tuple[str, ...]
```

**Resolution rules** (applied for each service against every other manifest):

1. `depends_on.required` → upstream `required` edge.
2. `runtime_adaptive.adapts_to` + `environment_adaptation` → upstream `adaptive`
   edge.
3. `runtime_deps.optional` → upstream `optional` edge.
4. Inverse pass: if service B lists A as required/adaptive/optional, A gets a
   downstream edge to B.
5. Loop detection: if A→B and B→A both exist, collapse into a bidirectional
   edge on both diagrams.
6. Mechanism text harvested from manifest env-var defaults (e.g.
   `LITELLM_LOCALHOST_URL`) and `runtime_adaptive.environment_adaptation`
   values. Fallback: container DNS from `services/<other>/compose.yml`.
7. Failure mode text comes from a new optional manifest field
   `runtime_adaptive.<container>.failure_mode`, falling back to
   `"Capability omitted from config.yaml; service continues without it."`

**CLI:**

```bash
python -m bootstrapper.docs.regen <name>              # one service
python -m bootstrapper.docs.regen --all               # all 21
python -m bootstrapper.docs.regen --all --dry-run     # preview
python -m bootstrapper.docs.regen <name> --section-only   # markdown only
python -m bootstrapper.docs.regen --all --check       # CI-friendly drift gate
```

Exit codes: `0` clean, `1` manifest error, `2` would-change in `--check`.

**Renderer guarantees:**

- Byte-identical output for the same manifest state.
- No timestamps in the SVG body (HTML footer only, as a comment).
- Category colors imported from `topology.CATEGORY_COLORS`.
- Lane x-positions, box dimensions, viewBox height computed from row counts.

**Golden snapshot test:** `bootstrapper/tests/fixtures/hermes.architecture.svg`.
Renders Hermes (most complex graph) and snapshot-compares. Manifest edits
require fixture regeneration — acceptable overhead.

### A.5 — Manifest schema additions

Two optional new fields in `services/<name>/service.yml`, validated by
`bootstrapper/schemas/service.schema.json`:

```yaml
runtime_adaptive:
  <container>:
    adapts_to: [...]
    failure_mode: "<sentence>"   # NEW, optional

docs:                            # NEW top-level key, optional
  diagram:
    extra_consumers: []          # escape hatch for wiring not expressible
                                 # in depends_on (e.g. Kong routing)
```

Both backwards-compatible. Default templates produce reasonable output
without them.

### A.6 — CI drift gate

`bootstrapper/tests/test_docs_drift.py` runs
`python -m bootstrapper.docs.regen --all --check` and fails if any committed
diagram or deps section disagrees with the current manifest state. Parallels
the existing `test_env_example_consistency` pattern.

### A.7 — Manifest-to-doc-folder mapping

Manifests (`services/<name>/service.yml`) and doc folders
(`docs/services/<name>/`) don't align 1:1. There are 24 manifests but 21
doc folders. Resolution:

**Meta-manifests excluded from diagram generation:**

- `services/globals/service.yml` — global env vars, no runtime container.
- `services/cloud-providers/service.yml` — cloud-LLM credentials grouping,
  no runtime container.

**Aggregate doc folders fold multiple manifests into one composite diagram:**

| Doc folder | Underlying manifests | Composite strategy |
|---|---|---|
| `docs/services/doc-processor/` | `docling` | 1:1 (single manifest, aggregate name only) |
| `docs/services/stt-provider/` | `parakeet`, `speaches` (Faster-Whisper role) | Focus tier shows a "STT Provider" boundary box containing one inner box per manifest; deps unioned across manifests |
| `docs/services/tts-provider/` | `speaches` (Kokoro/Piper role), `chatterbox`, `tts-provider` | Same composite focus pattern; dedup'd against stt-provider's `speaches` references |
| `docs/services/multi2vec-clip/` | (none — Weaviate sub-feature) | No diagram generated in A; the doc points at the Weaviate diagram instead |

**Resolver responsibilities:**

- `deps_resolver.build_doc_graph(doc_folder)` returns a `DepGraph` whose
  `focus` is the doc-folder name and whose `upstream`/`downstream` lists
  are the union of underlying manifests' edges, with intra-aggregate edges
  (e.g., chatterbox depending on tts-provider) suppressed.
- `diagram_renderer` renders aggregate focuses as a parent rectangle (rose
  stroke, `stroke-dasharray="4,4"`, matching the skill's "Security groups"
  pattern but used here for logical-grouping boundaries) wrapping inner
  manifest boxes.
- Total diagram output: **21 architecture.svg files**, one per doc folder.

### Phase A acceptance gates

1. `python -m bootstrapper.docs.regen --all` runs clean.
2. `bootstrapper/tests/test_docs_drift.py` passes.
3. Hermes golden-snapshot fixture matches.
4. Every `docs/services/<name>/` directory exists with `README.md`,
   `architecture.html`, `architecture.svg`.
5. Every inbound link previously pointing at `docs/services/<name>.md`
   resolves to `docs/services/<name>/README.md`; `scripts/check_doc_links.py`
   passes.
6. The `Dependencies & Integrations` section exists in every README.md.
7. Manifest schema additions validate against `service.schema.json`.

## Phase B — Pairwise integration research

### B.1 — Dispatch pattern

21 parallel subagents (`Explore` subagent_type), one per service. Each writes
to its own row file — no shared-file contention. Read-only mode for the
codebase; write-only to `docs/research/rows/<name>.md` and (conditionally)
`docs/research/candidates/<slug>.md`. WebFetch budget: **8 fetches per
subagent**.

### B.2 — Master matrix location

```
docs/research/
├── README.md                              # schema docs + how to update
├── integration-matrix.md                  # generated index — DO NOT EDIT
├── rows/
│   ├── hermes.md                          # one per service (21 files)
│   ├── litellm.md
│   ├── n8n.md
│   └── ...
└── candidates/
    ├── obsidian-mcp.md                    # one per candidate new service
    ├── langfuse.md
    └── ...
```

### B.3 — Row file schema (`rows/<service>.md`)

Frontmatter required. Three numbered sections required (each may declare
"No high-confidence opportunities identified" if empty).

```markdown
---
service: hermes
category: agents
generated: 2026-05-16
generator: phase-b-subagent
sources_consulted:
  - <URL or local path>
  - ...
---

# <Service> — Integration Research

## 1. Missing-pair integrations
- **<Service> ↔ <Other>**
  - Why valuable: ...
  - Mechanism sketch: ...
  - Effort: small | medium | large
  - Risks / open questions: ...
  - Confidence: high | medium | low

## 2. Candidate new services
- **<Candidate>** → `../candidates/<slug>.md`
  - Headline: ...
  - Other consumers in stack: ...

## 3. Per-service feature gaps
- **<feature>** — Why pursue: ... Effort: ...
```

**Hard caps:** 800 words per row file, 5 candidates per row file.

### B.4 — Candidate one-pager template

```markdown
---
slug: <kebab-case>
name: <Display Name>
type: external-service
category-fit: agents | data | media | ...
generated: 2026-05-16
upstream: <URL>
license: <SPDX>
referenced-by: [<service>, ...]
---

# <Name>

## Headline
One sentence.

## Problem it solves
2-3 sentences.

## Stack wiring sketch
- <service A> → <this candidate> via <protocol/endpoint>
- <this candidate> → <service B> via ...

## Effort
small | medium | large — one sentence on what dominates.

## Risks & open questions
Bulleted (may be empty).

## Why now (and why not sooner)
Optional, one paragraph.

## Upstream evidence
At least one URL.
```

**Enforced rules:**

1. Wiring sketch bullets must name services that exist in current topology.
2. Upstream evidence section is mandatory; at least one URL.
3. `referenced-by` list is maintained by the merge step, not by candidate
   author.

### B.5 — Subagent contract

Each subagent's prompt contains:

1. Target service name (the hub).
2. The other 20 services with category, port, current SOURCE, one-line
   description (pulled from `topology.py`).
3. The target's existing manifest, doc, and init scripts as read-only context.
4. Hard rules:
   - Must consult upstream project docs via WebFetch (budget: 8).
   - Must classify each candidate by Confidence.
   - Must NOT propose anything already wired (the subagent's prompt includes
     the service's current `runtime_adaptive.adapts_to` list as the "do not
     propose these" set).
   - Must write output to `docs/research/rows/<service>.md` in the strict
     schema.
   - Must check filesystem before creating a candidate one-pager — if it
     exists, append a `## Cross-references` link from the row file instead.
   - Max 5 candidates per row file.
5. Examples of good vs bad output, inline in the prompt.

### B.6 — Merge step

`python -m bootstrapper.docs.merge_research` reads the 21 row files and the
candidate one-pagers, then emits:

- `docs/research/integration-matrix.md` — a generated index with sections by
  service, by category, and a global "candidate new services" cross-reference
  table.
- Reconciles `referenced-by:` frontmatter on each candidate to list every row
  file that points to it.

Deterministic, re-runnable, idempotent.

### Phase B acceptance gates

1. 21 row files exist and parse against the schema (validator:
   `scripts/validate_research_schema.py`).
2. Candidate one-pagers parse against their template; every `Stack wiring
   sketch` bullet names a real service.
3. Merged `integration-matrix.md` builds without errors.
4. No row makes a Confidence claim without a `sources_consulted` entry.
5. Spot-check: 5 of 21 row files manually reviewed for quality before
   declaring B complete.

## Phase C — Content authoring

### C.1 — Three parallel streams

**Stream 1 — Current Integrations (no Phase B dep, mechanical):**
`python -m bootstrapper.docs.regen --all` writes the Current — Upstream and
Current — Downstream tables and regenerates diagrams. Idempotent.

**Stream 2 — Future Integrations (consumes Phase B row files):**
For each service, an author (a Claude session, or a subagent) reads
`docs/research/rows/<name>.md` + referenced candidate files and translates
research bullets into the README's Future subsections following the
template. Cross-links candidates to their one-pagers. Drops any candidate
lacking a viable wiring sketch.

**Stream 3 — Placeholder rewrites (the 7 thin docs):**
For backend, comfyui, local-deep-researcher, multi2vec-clip, n8n, redis,
searxng: rewrite to Hermes-grade depth. Author Overview, Access,
Configuration, Architecture & wiring, Troubleshooting sections (matching
Hermes's structure). Source material: service.yml, compose.yml, init
scripts, upstream docs. WebFetch budget: **6 per service**.

### C.2 — Parallelism

- All Stream-1 work batches into a single `regen --all` invocation.
- Stream-2 jobs are independent — dispatchable as 21 parallel subagents.
- Stream-3 rewrites are independent — dispatchable as 7 parallel subagents.
- For the 7 placeholder services, Stream-3 owns the whole README and absorbs
  its Stream-2 work internally.

### Phase C acceptance gates

1. Every README's Future subsections are populated (or explicitly state
   "No high-confidence opportunities identified" with no bullets).
2. The 7 placeholder docs reach a minimum of 150 lines and contain all five
   canonical sections (Overview, Access, Architecture & wiring,
   Configuration, Troubleshooting).
3. `regen --all --check` still passes.
4. All cross-links between READMEs and research files resolve.
5. CHANGELOG.md updated with one entry per major change.

## Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Inbound-link breakage after folder migration | high | `scripts/check_doc_links.py` runs in CI; A also rewrites all known references in the same commit |
| Subagent row-quality drift | medium | Strict schema + validator + 800-word cap; spot-check 5 of 21 |
| Candidate-one-pager bloat | medium | Hard cap of 5 candidates per row file; subagents must rank and trim |
| Diagram viewBox overflow (Kong has ~15 consumers) | medium | Renderer measures + grows viewBox dynamically; CI snapshot catches regressions |
| Unused manifest fields (`failure_mode`) | low | Optional from day one; default templates produce reasonable text |
| False-positive future integrations (already wired) | medium | Subagent prompt includes current `adapts_to` as do-not-propose set |
| Drift between manifests and committed diagrams | high without gate, low with gate | CI drift gate makes this impossible to merge |

## Cost sizing

- Phase B: 21 subagents × ~8 WebFetches = ~168 fetches.
- Phase C Stream-3: 7 subagents × ~6 WebFetches = ~42 fetches.
- Phase C Stream-2: 21 subagents, mostly local I/O, no WebFetch budget.
- Total: ~210 subagent WebFetches across the whole project.

## Out of scope (explicit)

- Top-level stack-wide architecture diagram (one page, all 21 services).
- Auto-implementing any Phase B future integrations.
- Linting/formatting tooling for the bootstrapper.
- A web viewer for the matrix.

## Open questions

None at design time. Manifest-to-doc-folder mapping (A.7) was surfaced in
spec self-review and resolved inline. Implementation plans for each phase
will surface tactical sub-questions as they arise.

## Implementation plan

This design has three phases. Each phase will get its own implementation
plan, written via the `writing-plans` skill, executed via
`executing-plans` (Phase A) or `subagent-driven-development` (Phases B and
C). The umbrella spec (this file) stays as the canonical reference;
individual plans cite it.

Phase ordering is strict: A must complete (all acceptance gates green)
before B or C dispatch. B and C run in parallel.
