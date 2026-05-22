# Architecture diagram refresh — Design

**Date:** 2026-05-22
**Status:** Approved (awaiting implementation plan)
**Owner:** Kaveh Razavi
**Predecessor:** `docs/superpowers/specs/2026-05-16-cross-service-deps-and-diagrams-design.md` (umbrella spec — Phase A foundations, sections A.3 + A.4)

## Problem

Phase A's `bootstrapper/docs/diagram_renderer.py` generates per-service architecture diagrams from manifests at `docs/services/<name>/architecture.svg`. Two systemic problems surfaced once the user reviewed the output:

1. **Accuracy.** The resolver reads `depends_on.required`, `runtime_adaptive.adapts_to`, and `runtime_deps.optional`. These encode **bootstrap-dependency direction** (which services need which others to be present at init time). They do NOT encode **data-flow direction** (which services CALL which others at runtime).

   Example: Ollama's manifest declares `depends_on.required: [litellm]` so the bootstrapper waits for LiteLLM before starting Ollama (so Ollama's init script can register its models with LiteLLM). The diagram places Ollama in LiteLLM's *downstream* lane. But the user (correctly) thinks of LiteLLM as a gateway that *calls* Ollama — Ollama is upstream in the request path. The same flip applies to weaviate (calls litellm for vectorization), comfyui (calls litellm), and several others.

2. **Aesthetics.** Diagrams sprawl badly. Kong is 2020px tall (20 boxes stacked in one column). LiteLLM is 1520px. Other diagrams (neo4j, minio) come out 220px and look skimpy. Five-times size variance, no clustering, fan-out clutter, repetitive `required` sublabels everywhere, no legend, no visual hierarchy beyond "focus box slightly bigger".

## Goals

1. Diagrams reflect **runtime data flow** — "A calls B" relationships, not bootstrap order.
2. High-fanout diagrams (kong, litellm, supabase, backend with 15+ consumers) render compactly with visible structure.
3. Low-fanout diagrams (neo4j, minio with 2-3 consumers) don't look anemic.
4. Visual style is more polished (focus dominance, less repetition, clear legend).
5. Existing Phase A tooling (`bootstrapper/docs/`, `regen` CLI, drift gate) keeps working — same entry points, same byte-determinism guarantees.

## Non-goals

- Replacing the entire diagram pipeline. The renderer, resolver, regen CLI, and drift gate stay; we change their *content*.
- A top-level stack-wide diagram (still out of scope).
- Animating diagrams or making them interactive beyond static HTML.
- Removing the bootstrap-dependency fields from manifests — they're still needed for actual docker-compose orchestration. They just stop being read by the diagram resolver.

## Data model change

### New optional manifest field: `data_flow.calls`

Each `services/<name>/service.yml` may declare:

```yaml
data_flow:
  calls:
    - <service-name>           # one of the 21 doc-folder names
    - <service-name>
    - ...
```

Semantics: "At runtime, this service calls/depends-on those services in the request path." Direction is data flow.

Rules:
- Optional. Missing field = empty list.
- Strings must be valid doc-folder names (validated by manifest_validator).
- Order in the list is not significant (resolver sorts).
- A service may declare itself as calling another even when no `depends_on.required` exists — the two fields are independent. (E.g., LiteLLM's manifest doesn't `depends_on` ollama, but `data_flow.calls: [ollama, cloud-providers, supabase, redis]` is the truth.)

### Schema update

`bootstrapper/schemas/service.schema.json` gains:

```json
"data_flow": {
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "calls": {
      "type": "array",
      "items": { "type": "string", "pattern": "^[a-z][a-z0-9-]*$" },
      "uniqueItems": true,
      "description": "Services this one calls at runtime. Drives the diagram resolver. Independent of depends_on (bootstrap order)."
    }
  }
}
```

### Resolver rewrite (`bootstrapper/docs/deps_resolver.py`)

The current resolver reads three dep fields and computes upstream + downstream via direct + inverse passes. After this change:

- **Drop:** all reads of `depends_on.required`, `runtime_adaptive.adapts_to`, `runtime_deps.optional`, `doc_extras.diagram.extra_consumers`. These continue to live in manifests for other consumers (compose, bootstrapper) but are invisible to the diagram resolver.
- **Add:** read `data_flow.calls` from every manifest.
- **Upstream (of focus F):** F's own `data_flow.calls` list.
- **Downstream (of focus F):** every other manifest whose `data_flow.calls` contains F.
- **Bidirectional collapse:** if A calls B AND B calls A, mark both edges bidirectional (rare in data-flow but possible — Hermes↔LiteLLM via model registration + tool calls).
- **Edge kind:** there's only ONE kind now (`calls`). Drop the `required / adaptive / optional` distinction from `DepEdge.kind`. Replace with a single `kind: "calls"` or remove the field entirely.
- **Aggregate folders** (stt-provider, tts-provider, doc-processor, multi2vec-clip) still resolve via `build_doc_graph` per spec A.7 — unchanged logic, but the underlying edges come from `data_flow.calls` instead.

`DepEdge` shape (simplified):

```python
@dataclass(frozen=True, order=True)
class DepEdge:
    other: str
    direction: Literal["upstream", "downstream"]
    bidirectional: bool = False
    other_category: str = "external"
```

The `mechanism`, `failure_mode`, `kind` fields go away (no longer needed for the simpler model).

### Deps section impact

`bootstrapper/docs/deps_section_writer.py` rendered tables with columns:
- Upstream: `Service | Type | Mechanism | Failure mode`
- Downstream: `Service | Type | Mechanism`

After this change:
- Upstream table: `Service | Category` — drop Type (always "calls"), drop Mechanism (no longer derivable), add Category (the called service's category).
- Downstream table: `Service | Category` — same simplification.

This means **every service's README needs to regenerate** with the new section shape. The drift gate will catch this immediately.

## Visual design

### Layout: cluster-by-category in the downstream lane

The downstream lane shows services grouped into one cluster per category (infra, data, llm, media, agents, apps). Each cluster is a small bordered box with:

- A header bar showing the category name (left) + count badge (right), both in the category color.
- A 2-column packed grid of small pills inside, one per service.
- A dashed 1px border in the category color at 40% opacity (subtle, doesn't compete with edges).

Categories with zero services in the lane are not drawn. Cluster ordering follows `topology.CATEGORY_ORDER` (infra, data, llm, media, agents, apps).

The **upstream lane uses the same clustering** (when the focus calls services in multiple categories — e.g., Hermes upstream has 1 llm + 4 media). This gives visual parallelism between the two lanes.

### Focus box

- Larger than tier boxes (~170×60 vs 110×30 for pills).
- Background: vertical gradient `#1e293b → #0f172a`.
- Border: 1.5px stroke + a 24px soft glow, both in the focus's category color (from `CATEGORY_COLORS`).
- Two-line label: SERVICE NAME (15px, bold) + sublabel (10px, slate) showing `<category> · <source-or-role>`.
- Vertically centered against the longest lane.

### Edges

- One edge per **cluster** (not per service). Endpoint is the cluster header, not the individual pill. This collapses kong's 20 edges into 5.
- Single edge style: solid slate (`#64748b`), 1.5px stroke, arrowhead marker.
- Bidirectional pairs get a `↔ bidirectional` annotation inside the relevant cluster header, not a second arrow.
- Edges drawn before clusters (so they render behind, per Phase A's z-order pattern).

### Pills (downstream/upstream service boxes)

- ~110×24px (smaller than current 200×60).
- Single line: service name only. **No "required" sublabel.**
- 1px border in service's category color.
- Background: `rgba(15, 23, 42, 0.7)`.
- Pills are reachable as boxes but the diagram-level edges target the cluster header, not the pill.

### Empty lanes

- If the upstream lane has 0 entries (e.g., Kong calls nothing), the lane shrinks to ~half width and shows a centered italic `— none —` placeholder inside a thin dashed border. The focus shifts proportionally toward the empty side.
- Same rule for empty downstream (rare; the focus would be a leaf service no one calls).

### Legend bar

Centered below the diagram, above the summary cards. One line: category-colored dots (`infra`, `data`, `llm`, `media`, `agents`, `apps`) + a `calls (data-flow)` arrow legend.

### Summary cards

Three cards below the legend:
- **Calls** — count of upstream edges (services this focus calls).
- **Consumers** — count of downstream edges (services that call this focus).
- **Categories served** — count of distinct downstream categories (a "spread" measure for high-fanout services).

For low-fanout cases, the "Categories served" card just shows a small number; no special handling.

### Color palette

Unchanged. Pulls from `topology.CATEGORY_COLORS`:
- `infra`: `#f7768e` (Tokyo Night red)
- `data`: `#7dcfff` (cyan)
- `llm`: `#e0af68` (yellow)
- `media`: `#7aa2f7` (blue)
- `agents`: `#9ece6a` (green)
- `apps`: `#bb9af7` (purple)

### Typography

Unchanged from the architecture-diagram skill's design system: JetBrains Mono everywhere; 15px focus title, 11px lane headers, 10px pill labels, 9px cluster headers + summary labels.

### Background

Unchanged: `#020617` slate-950 with the 40×40 grid pattern.

## Authoring data_flow.calls

This is **content work, not code work** — populating each manifest's `data_flow.calls` field. Source material:

- Each service's manifest, init scripts, and compose env block (what URLs it actually hits).
- Phase B research rows under `docs/research/rows/<name>.md` — many already enumerate the data-flow edges.
- The user's mental model (validated through brainstorming).

The implementation plan will include a table of starting values for each of the 21+ services. Rough sketch of the high-confidence calls:

| Service | calls |
|---|---|
| backend | supabase, redis, weaviate, neo4j, litellm, hermes, comfyui, stt-provider, tts-provider, doc-processor, n8n |
| comfyui | litellm, minio |
| doc-processor | (none — it's called by others, doesn't call out) |
| hermes | litellm, stt-provider, tts-provider, comfyui, searxng |
| jupyterhub | litellm, hermes, weaviate, neo4j, minio, supabase |
| kong | (none — Kong is a reverse proxy; all flows go *through* Kong, but Kong doesn't initiate calls) |
| litellm | supabase, redis, ollama, cloud-providers |
| local-deep-researcher | litellm, searxng |
| minio | (none — leaf storage service) |
| multi2vec-clip | (none — called by weaviate; doesn't call out) |
| n8n | supabase, weaviate, comfyui, doc-processor, hermes, litellm, stt-provider, tts-provider, searxng, minio (when configured) |
| neo4j | supabase (auth via Caddy) |
| ollama | supabase, litellm |
| open-webui | litellm, hermes, doc-processor, searxng (when configured) |
| openclaw | litellm, hermes, n8n |
| redis | (none — leaf cache) |
| searxng | (none — issues outbound to external search engines, none of which are in-stack) |
| stt-provider | (none — called by others) |
| supabase | (none — leaf data service) |
| tts-provider | (none — called by others) |
| weaviate | litellm, multi2vec-clip |

The plan will turn this table into 21+ manifest edits, each adding a `data_flow.calls` block.

**Kong note (resolved).** Kong is a reverse proxy: it ROUTES inbound traffic to backends but doesn't INITIATE outbound calls in the request path. Strict data-flow rendering would leave Kong with empty upstream AND empty downstream — visually correct but uninformative (users mentally model Kong as "the front door for everything").

**Decision:** List Kong-fronted services in Kong's own `data_flow.calls` block with a header comment in `services/kong/service.yml` explicitly noting "fronts (proxy direction, not outbound initiation)". This is a documented convention, not a separate field — keeps the schema small. The diagram renders Kong as upstream of every fronted service, which matches the "Kong is the front door" mental model.

## Migration & regeneration

1. Add `data_flow.calls` field to schema and `Manifest` dataclass.
2. Author the 21+ manifest edits (one per service) per the table above.
3. Rewrite `deps_resolver.py` per the new model.
4. Rewrite `diagram_renderer.py` per the visual design.
5. Update `deps_section_writer.py` table shape.
6. Update Hermes golden snapshot fixture (`bootstrapper/tests/fixtures/hermes.architecture.svg` + `hermes.deps_section.md`).
7. Regenerate all 21 diagrams + deps sections via `regen --all`.
8. Drift gate `test_docs_drift.py` passes again.
9. CHANGELOG entry.

## Tests

- **Schema tests** (`test_manifests.py`) — extend to cover `data_flow.calls` round-trip + rejection of invalid service names.
- **Resolver tests** (`test_deps_resolver.py`) — rewrite. Old tests around `required`/`adaptive`/`optional` go away. New tests:
  - Upstream = focus's `data_flow.calls`.
  - Downstream = inverse pass over all manifests.
  - Empty `data_flow.calls` → empty upstream.
  - Bidirectional collapse when both directions declare each other.
  - Aggregate doc folders still work.
- **Renderer tests** (`test_diagram_renderer.py`) — rewrite. Old tests around edge kinds (required vs adaptive) go away. New tests:
  - Cluster headers rendered.
  - Pills don't carry "required" sublabel.
  - Empty lane shows `— none —` placeholder.
  - Focus glow stroke present.
  - One edge per cluster (count edges vs pill count).
  - SVG remains byte-deterministic.
  - Hermes golden snapshot matches the regenerated fixture.
- **Drift gate** unchanged; should pass after regeneration.

## Acceptance gates

1. `python -m bootstrapper.docs.regen --all` runs clean.
2. `bootstrapper/tests/test_docs_drift.py` passes.
3. Hermes golden snapshot matches.
4. Every `docs/services/<name>/architecture.svg` parses as well-formed XML (existing test from Phase A's `b751440` fix carries forward).
5. Schema additions validate against `service.schema.json`.
6. Spot-check 5 diagrams in browser — Kong, LiteLLM, Hermes, MinIO, Neo4j — visually approved by user.
7. No service has a `data_flow.calls` entry pointing at a non-existent doc folder.

## Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| `data_flow.calls` author error (service typo) | medium | Schema validator + manifest_validator cross-check service names against topology |
| Disagreement on the "Kong fronts everything" representation | medium | Decision deferred to plan-writing; both approaches sketched in spec |
| Phase B research rows referenced manifest-derived diagrams; will those references go stale? | low | Phase B's content doesn't link to specific diagram shapes — it lists relationships in prose |
| Bidirectional loop edge cases | low | Detect during resolver, single test covers it |
| Large changes to deps section tables break links | low | Tables stay in the same section heading; only column shape changes; cross-doc links unaffected |
| Authoring 21 manifest entries by hand introduces inconsistencies | medium | Plan includes a Python script that *suggests* values by reading code/compose + cross-checking against Phase B rows; human approves each |

## Out of scope

- A second visualization mode showing bootstrap dependencies (if needed later, separate spec).
- Animating diagrams.
- An interactive HTML version where clicking a service navigates to its diagram (Phase C-style follow-up).
- Stack-wide single-page diagram.

## Decided conventions

1. **Kong representation:** services Kong fronts go into Kong's own `data_flow.calls` with a header comment in `services/kong/service.yml` noting the proxy-direction convention. No `data_flow.fronts` field.
2. **Authoring approach:** hand-edit the 21+ manifests directly per the starter table above. No author script.
3. **Init-time calls:** do NOT count as data flow. `ollama-init` calling LiteLLM to register models is bootstrap; it doesn't appear in `data_flow.calls`. Only request-path runtime calls qualify. The schema description for `data_flow.calls` states this explicitly.
4. **Hermes ↔ LiteLLM bidirectional:** real and rendered. LiteLLM proxies the `hermes-agent` model to Hermes at runtime (LiteLLM calls Hermes); Hermes uses LiteLLM as its LLM gateway (Hermes calls LiteLLM). Both manifests declare each other in `data_flow.calls`. Renderer collapses to a bidirectional annotation.
