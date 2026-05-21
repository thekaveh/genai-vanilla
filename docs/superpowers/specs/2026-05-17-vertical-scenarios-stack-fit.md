# Vertical-scenario stack-fit: Dreamscapes and Trading-fleet — Design

**Date:** 2026-05-17
**Status:** Draft (awaiting review)
**Owner:** Kaveh Razavi

## Problem

The stack just gained a 30-candidate roadmap with three strategic tracks
(3D / game-generation, financial / trading-AI, RAG specializations). Two
concrete future scenarios — **Dreamscapes** (sketch → 3D mini-world that
the user can fly or walk through) and a **Trading-bot fleet** (paper-first
with promotion to live, orchestrated, monitored, scaled) — have been
described, but it is not obvious which parts of the existing+roadmapped
stack already serve them, and which additional services would be
*immediately beneficial*. Without that mapping, the roadmap risks two
failure modes: over-investing in services neither scenario needs, or
under-investing in services both need.

This document does a deep stack-fit analysis of both scenarios against
the current state of the stack (25 service families shipped, ~30 roadmap
candidates spread across Tier 1/2/3 plus three labelled tracks), surfaces
the gaps, and proposes a minimal additive set of ROADMAP.md edits.

This is a **research spec**, not an application design. Designing either
Dreamscapes or the trading-fleet app is a separate future brainstorm.

## Goals

1. Validated walk-through of each scenario against the existing+roadmapped
   stack, identifying which services do which job.
2. A **phased** list of service additions for each scenario (Phase 1 =
   immediate / browser-first MVP for Dreamscapes, paper-trading fleet
   for Trading; Phase 2 = next-tier capabilities; Phase 3 = advanced
   features).
3. **Cross-cutting findings** — services beneficial to both scenarios,
   shared infrastructure patterns, reused gateways.
4. A **minimal additive ROADMAP.md edit plan** — net new Tier 1/2/3
   entries and updates to the long-term-vision block, with no removals
   or restructuring beyond what's strictly necessary.
5. A clean **skip list** with reasons, so future contributors don't
   re-propose candidates that were already evaluated and declined.

## Non-goals

- Designing either application (UI flows, data models, API surfaces).
  Each app gets its own brainstorm session.
- Recommending native-desktop or cloud-rendered Dreamscapes paths
  beyond a forward-looking mention; browser/WebGL is the initial scope.
- Legal / regulatory / compliance advice for live trading.
- Concrete implementation of the ROADMAP edits — this spec defines
  *what* will change in ROADMAP.md, the actual edits are a follow-up
  task.
- Choosing between Three.js and Babylon.js at the frontend level; both
  are acceptable, the spec lists Three.js as the primary recommendation
  but does not block on it.

## Scope decisions captured in this spec

These were explicitly confirmed during brainstorming and propagate into
every section below.

- **Trading execution mode:** paper-trading and live-trading, with
  paper-first promotion to live. This drags in the full surface
  (custody, kill-switches, audit, promotion gate).
- **Dreamscapes delivery target:** browser / WebGL first; native-desktop
  and cloud-rendered streaming are forward-looking. Phase 1 designs
  must work in a stock browser without plugins.
- **World representations for Dreamscapes evolve** from free-form
  ("snowdome") → voxel grids → larger tile/GIS-style maps. Phase 1
  covers free-form; phases 2–3 add voxel and tile/GIS.
- **Deliverable shape:** single unified spec (this document) plus a
  minimal additive ROADMAP.md edit pass. No new top-level docs.

## Dreamscapes — stack-fit analysis

### Pipeline walk-through

The end-to-end Dreamscapes flow:

```
user text + sketch input
        ↓
[LLM] LiteLLM-routed model (e.g. Ollama / Hermes persona)
        ↓
[image gen] ComfyUI (with ControlNet for sketch conditioning)
        ↓
[image-to-3D] InstantMesh (fast draft) or Hunyuan3D-2 / TRELLIS (high quality)
        ↓
[refinement / assembly] Blender headless (mesh cleanup, scene composition)
        ↓
[real-scene capture, optional] NerfStudio (when user uploads photos/video)
        ↓
[asset optimization] glTF-Transform worker → KTX2 + Draco + meshopt
[splat path, alternative] DreamGaussian → SuperSplat conversion
        ↓
[storage] MinIO buckets (per-user, per-scene)
        ↓
[indexing] Weaviate (asset embeddings) + LightRAG (scene/entity graph)
        ↓
[serving] Kong route + Backend (FastAPI) signed-URL handler
        ↓
[viewer] browser-side Three.js + react-three-fiber app
        ↓
[multiplayer, phase 3] Colyseus authoritative server
[audio, parallel] AudioCraft / MusicGen for procedural background music
```

### Coverage from existing + roadmapped services

| Role | Service | Status |
|---|---|---|
| LLM routing | LiteLLM | shipped |
| Reasoning agent | Hermes | shipped |
| Image generation | ComfyUI | shipped |
| Image-to-3D mesh | Hunyuan3D-2 / TRELLIS | roadmap Tier 3 (3D track) |
| Scene assembly / render | Blender headless | roadmap Tier 3 (3D track) |
| Real-scene reconstruction | NerfStudio | roadmap Tier 3 (3D track) |
| Asset storage | MinIO | shipped |
| Asset embeddings | Weaviate | shipped |
| Scene / asset graph | LightRAG | roadmap Tier 2 |
| Procedural audio | AudioCraft / MusicGen | roadmap Tier 3 (general) |
| Edge gateway | Kong | shipped |
| Backend orchestration | Backend (FastAPI) | shipped |

The *generation* side is covered. The gaps are in **browser viewer,
asset pipeline, world representation, multiplayer, and sketch input**.

### Phase 1 additions — browser-first MVP

| Service | Add as | License | Role |
|---|---|---|---|
| **Three.js + react-three-fiber** | frontend dependency (no container) | MIT | Browser-side viewer; widest 2026 ecosystem for glTF / KTX2 / Gaussian Splat loaders |
| **glTF-Transform worker** | small FastAPI container wrapping the `gltf-transform` CLI | MIT | Single-binary asset pipeline: KTX2 + Draco + meshopt in one pass |
| **SuperSplat worker** | small headless container | MIT (PlayCanvas-org) | `.ply → .splat / .ksplat` conversion for the splat branch |
| **InstantMesh** | new compose service (GPU) | Apache-2.0 | Fast image-to-3D (≈10 s/mesh); fast-path complement to Hunyuan3D-2 |
| **DreamGaussian** | new compose service (GPU) | MIT | Gaussian-splat output for snowdome interiors (skips meshing entirely) |
| **excalidraw-room** | tiny WebSocket container | MIT | Collaborative-canvas backend for sketch input (Excalidraw frontend speaks to it) |

**Note:** Babylon.js (Apache-2.0) is a reasonable secondary choice if a
physics + native WebXR surface becomes important before Phase 3; either
works.

### Phase 2 additions — voxel and tile/GIS worlds

| Service | Add as | License | Role |
|---|---|---|---|
| **Vengi voxconvert worker** | small headless container | MIT | The only currently-maintained permissive `.vox` ↔ `.obj/.ply/.gltf` converter (npm `vox-to-gltf` is abandoned) |
| **PostGIS extension** | enable on existing Supabase Postgres | PostgreSQL License | Spatial data storage for tile / GIS-style worlds; zero new container |
| **Tegola** | new compose service | MIT | Vector-tile server (PostGIS → MVT), single Go binary; perfect for dynamically-generated chunked worlds |
| **MapLibre GL JS** | frontend dependency (no container) | BSD-3 | Client-side vector-tile renderer |
| **WaveFunctionCollapse worker** | small Python container | MIT | Procedural tile generation; the canonical PCG primitive in 2026 |

### Phase 3 additions — collaborative + advanced

| Service | Add as | License | Role |
|---|---|---|---|
| **Colyseus** | new compose service (Node) | MIT | Authoritative multiplayer server for shared "fly inside" sessions; better than Yjs for tick-rate position sync |
| **Cloud-render pool + WebRTC SFU** | future; LiveKit (already Tier 3) can serve as the SFU half | Apache-2.0 (LiveKit) | Server-side rendered scenes streamed to thin browser clients when scene complexity exceeds the WebGL budget |

### Dreamscapes skip list (with reasons)

- **Needle Engine** — proprietary EULA, license-server required for CI;
  fails permissive-boilerplate posture.
- **PlayCanvas Engine** — engine is MIT but the value is its proprietary
  cloud editor, which is not self-hostable. Three.js dominates without
  the lock-in.
- **Stable Fast 3D (SF3D)** — Stability AI Community License is
  source-available but commercial-restricted; functionally overlaps
  Hunyuan3D-2 anyway.
- **Wonder3D / Wonder3D++** — CC-BY-NC (non-commercial only).
- **Rodin (Hyper3D)** — closed-source SaaS; no self-host path.
- **tldraw** — commercial use requires watermark or paid license;
  Excalidraw covers the same ground under MIT.
- **Drawpile** — GPL-3.0 viral copyleft.
- **Goxel** — GPL-3.0; Vengi covers voxel conversion permissively.
- **Liveblocks self-hosted** — Apache-2.0 core but the practical
  production stack is SaaS-only.
- **OpenVDB** — useful but only when voxel grids exceed ~256³ or
  volumetric effects are needed; defer until Phase 3+.
- **TileServer-GL** — for pre-baked MBTiles; Dreamscapes generates
  worlds dynamically, so Tegola is the better fit.
- **Yjs + Hocuspocus** — CRDT shape suits *co-editing the scene graph*,
  not 60Hz position sync; revisit if co-edit features land in Phase 3+.
- **PlayCanvas / Needle / Verge3D as primary engine** — all proprietary
  or proprietary-editor-dependent.

## Trading-fleet — stack-fit analysis

### Pipeline walk-through

```
[market data sources] OpenBB Platform (multi-provider aggregator)
        ↓                                  ↓
   [historical]                        [streaming]
   TimescaleDB (Postgres extension)    Redpanda topics
        ↓                                  ↓
[strategy authoring]
   - human-authored:        JupyterHub research notebooks
   - LLM-generated:         LiteLLM + Hermes → E2B sandbox (Phase 3)
        ↓
[paper-mode fleet]
   Hummingbot API (orchestrator) — Hummingbot Dashboard (UI)
        ↓
   N bot processes (Hummingbot strategy runners OR NautilusTrader workers)
   each reading market data + writing to:
        ↓
[paper ledger]
   Internal wallet/ledger service (custom; Supabase Postgres tables)
        ↓
[performance evaluation]
   Ray cluster (parallel backtest sweeps) → metrics in TimescaleDB
        ↓
[promotion gate]
   Windmill flow: checks Sharpe / max-DD / walk-forward / slippage
   → signs promotion record → flips bot from paper-mode to live-mode
        ↓
[live trading custody]
   OpenBao (Transit engine; signs orders, keys never leave the vault)
        ↓
[exchange / brokerage adapters]
   - crypto: CCXT (library inside backend)
   - equities: alpaca-py / ib_insync (libraries; thin internal wallet adapter)
        ↓
[risk control]
   Custom risk-control service (subscribes to Redpanda order events;
   publishes `halt` topic on global limit breach)
        ↓
[observability]
   - Langfuse (LLM-decision traces for strategy-tuning calls)
   - Prometheus + Grafana (infra metrics; bot latency, fill rates)
   - Hummingbot Dashboard (per-bot PnL, position grid, strategy config)
        ↓
[compliance / audit trail]
   Order events → OpenSearch (forensic queries) + MinIO Object Lock
   (Merkle-anchored WORM archive via audit-sealer worker)
```

### Coverage from existing + roadmapped services

| Role | Service | Status |
|---|---|---|
| LLM routing | LiteLLM | shipped |
| Agent runtime | Hermes | shipped |
| MCP tool surface | MCP gateway (mcpo + MetaMCP) | roadmap Tier 1 |
| Financial data aggregator | OpenBB Platform | roadmap Tier 3 (financial track) |
| Time-series store | TimescaleDB extension | roadmap Tier 3 (financial track) |
| Streaming broker | Redpanda | roadmap Tier 3 (financial track) |
| Algorithmic engine (library) | NautilusTrader | roadmap Tier 3 (financial track) |
| LLM observability | Langfuse | roadmap Tier 1 |
| Infra observability | Prometheus + Grafana | roadmap Tier 1 |
| Ops secrets | Infisical | roadmap Tier 1 |
| Code-first workflow | Windmill | roadmap Tier 3 (general) |
| Notebook research | JupyterHub | shipped |
| Edge gateway | Kong | shipped |
| Object storage | MinIO | shipped |
| Forensic search | OpenSearch | roadmap Tier 3 (general) |

The *data* and *engine* sides are covered. The gaps are in **fleet
orchestration, wallet abstraction, trading-key custody, promotion gate,
fleet-scale backtest, risk-control, and compliance audit trail**.

### Phase 1 additions — paper-trading fleet

| Service | Add as | License | Role |
|---|---|---|---|
| **Hummingbot API** | new compose service | Apache-2.0 | The only OSS *fleet manager* in 2026: multi-instance server (April 2026); creates / backtests / deploys / monitors N bots with one-click paper-or-live toggle |
| **Hummingbot Dashboard** | new compose service | Apache-2.0 | Streamlit / React UI for the fleet manager; per-bot PnL, position grid, strategy configuration |
| **CCXT** | library inside Backend | MIT | Unified API for 100+ crypto exchanges; certified-tier coverage on Binance / Coinbase / Kraken; the de-facto crypto wallet adapter |
| **Internal wallet / ledger service** | new in-house FastAPI service | (in-house) | Synthetic paper ledger (Phase 1) and live adapter (Phase 2); single API regardless of mode; backed by Supabase Postgres tables |

### Phase 2 additions — live-trading + promotion gate

| Service | Add as | License | Role |
|---|---|---|---|
| **OpenBao** | new compose service | MPL-2.0 (Linux Foundation; Vault fork) | Trading-key custody via Transit engine: keys never leave the vault, signing happens inside; complements Infisical (different threat model) |
| **Promotion-gate Windmill flows** | new Windmill workspace (no new compose service) | (uses existing Windmill) | DAGs that run Sharpe / max-DD / walk-forward / slippage checks against a candidate strategy and sign a promotion record into Supabase |
| **Risk-control service** | new in-house FastAPI service | (in-house) | Subscribes to Redpanda order topics; enforces per-strategy notional cap, per-account drawdown, market circuit-breakers; publishes a `halt` topic every bot subscribes to |
| **Audit-sealer worker** | new in-house Python worker | (in-house) | Batches order events, computes Merkle root, writes WORM-locked archive to MinIO via S3 Object Lock; stores the anchor in Postgres |
| **Equities adapter libraries** | `alpaca-py` and `ib_insync` inside Backend | MIT / BSD | Adapters wrapped behind the internal wallet/ledger service; no standalone "wallet-abstraction-as-a-service" exists in OSS, so the abstraction is in-house |

### Phase 3 additions — fleet-scale + LLM-generated strategies

| Service | Add as | License | Role |
|---|---|---|---|
| **Ray cluster** | new compose service (head + workers) | Apache-2.0 | Ray Tune is the de-facto 2026 parallel-backtest substrate; Nautilus runs inside each Ray task for fleet-scale parameter sweeps |
| **E2B (self-hosted)** | new compose service | Apache-2.0 | Firecracker microVM sandbox for executing LLM-generated strategy code safely; the 2026 reference for "untrusted code from agents" |
| **FinRL + FinGPT** | image flavors (JupyterHub kernel + E2B template) | MIT | AI-assisted strategy generation libraries; ride inside JupyterHub notebooks and E2B sandboxes — no standalone compose service needed |

### Custody trade-off (Infisical vs OpenBao)

**Both, different use-cases:**

- **Infisical** (Tier 1 in roadmap) — ops secrets: `.env` rotation,
  third-party-API keys for non-trading services, per-environment
  scoping. Use as planned.
- **OpenBao** (this spec, Phase 2) — trading-key custody: Transit
  engine signs orders without exposing private keys; key generation
  inside vault; per-exchange policy-scoped tokens; pair with hardware
  root (YubiHSM or cloud KMS) for the unseal key.

**Do not** repurpose Infisical for trading keys. Different threat model
(ops-team operational mistake vs adversary exfiltrating signing keys).
Do not drop Infisical in favor of OpenBao — Infisical's UX is better
for the ops-secrets use-case.

### Trading-fleet skip list (with reasons)

- **Freqtrade** as fleet manager — GPL-3.0 viral copyleft; FreqUI is
  single-user grade; not fleet-shaped.
- **NautilusTrader as the orchestrator** — LGPL library is fine for use
  as an engine, but Nautilus docs explicitly state distributed
  orchestration is out of scope. Run it as a *worker engine* under
  Hummingbot, not as the fleet plane.
- **OctoBot** — GPL-3.0.
- **Jesse** — MIT but single-bot framework without fleet primitives.
- **Lean / QuantConnect** — Apache-2.0 but C#-centric, heavy, and the
  brokerage-abstraction value is realised better via direct CCXT +
  per-broker libraries inside the in-house wallet service.
- **Silent Shard / Web3Auth MPC wallets** — over-engineered for a
  single-operator fleet; OpenBao Transit + per-exchange API-key
  scoping covers the threat model. Revisit if threshold signing
  across multiple machines becomes a real requirement.
- **Daytona** as the LLM-strategy sandbox — Docker rootless gives only
  kernel-shared isolation; E2B's Firecracker microVMs are the safer
  pick for untrusted code.
- **Specialized blockchain-anchored audit-trail products** —
  proprietary, expensive, and over-engineered at boutique scale;
  OpenSearch + MinIO Object Lock + Merkle anchors in Postgres is
  sufficient.

## Cross-cutting findings

### Services beneficial to both scenarios

- **MCP gateway (`mcpo` + MetaMCP, Tier 1)** — exposes OpenBB / Hummingbot
  endpoints (trading) AND Blender / Hunyuan3D / ComfyUI / Tegola
  endpoints (Dreamscapes) to every LLM consumer behind a single,
  namespaced tool surface. The single highest-leverage Tier 1 addition
  for *both* scenarios.
- **Langfuse (Tier 1)** — traces LLM calls for both
  strategy-tuning (trading) and sketch-prompt-tuning (Dreamscapes).
- **Infisical (Tier 1)** — ops secrets in both scenarios (exchange
  read-only keys, signed model-download URLs, OpenBB provider keys).
- **Redpanda (Tier 3 financial track)** — already needed for trading
  market-data fan-out; equally useful as the event bus for Dreamscapes
  asset-pipeline events (`asset.generated`, `asset.optimized`,
  `scene.indexed`) feeding n8n / Windmill workflows.
- **LightRAG (Tier 2)** — graph-shaped data lives in both: trading
  has a strategy-attribution graph (which signal influenced which
  trade); Dreamscapes has the asset / scene-component graph. Same
  retrieval primitive, two domains.

### Shared infrastructure patterns

- **Ray as the parallel-work substrate** — primarily a trading-fleet
  addition (parallel backtest sweeps), but Ray would also serve
  parallel Dreamscapes pipelines (batch-rendering 100 angles of a
  scene, batch-meshing 50 candidate dreamscapes for A/B comparison).
- **MinIO buckets per scenario** — the existing MinIO already has
  per-consumer service-account credentials; add `dreamscapes` and
  `trading` buckets the same way.
- **Custom in-house services dominate the financial track** (wallet,
  risk, audit-sealer) — pattern: thin FastAPI services that wrap
  existing primitives (Redpanda, Supabase, MinIO Object Lock,
  OpenBao). This is intentional: the OSS landscape for these
  specific roles is thin in 2026, and writing 200–500 lines of
  Python is cheaper than evaluating an unmaintained third-party.

### Two patterns to call out explicitly

- **Hummingbot is a fleet plane, NautilusTrader is the worker engine.**
  Do not try to make one do the other's job. Two-tier execution is
  the 2026 standard.
- **For Dreamscapes, image-to-3D has two complementary fast paths.**
  InstantMesh (≈10 s) for drafts and previews; Hunyuan3D-2 / TRELLIS
  for finals. DreamGaussian is a *different shape* (splat output) and
  is the right pick when the user wants a snowdome interior that
  doesn't need a polygonal mesh at all.

## Roadmap-addendum plan

Minimal, additive edits to `docs/ROADMAP.md`. No section removals,
no restructuring beyond what's listed.

### Tier 1 — append one entry

- **OpenBao — production-grade key custody** (sibling of Infisical;
  emphasises trading-key-custody role; Phase 2 of trading track).

### Tier 2 — append three entries

- **Three.js + react-three-fiber + glTF-Transform — browser 3D
  pipeline foundation** (frontend dep + asset pipeline worker;
  Phase 1 of 3D track).
- **Hummingbot API + Hummingbot Dashboard — trading-bot fleet
  manager** (Phase 1 of trading track).
- **CCXT — unified crypto exchange adapter** (library inside Backend;
  Phase 1 of trading track).

### Tier 3 — extensions to existing sub-sections

**Inside the existing `#### 3D / game-generation track` sub-section:**

- **InstantMesh** — fast image-to-3D draft path
- **DreamGaussian** — splat-output alternative for snowdome interiors
- **SuperSplat** — Gaussian Splat asset conversion worker
- **Vengi voxconvert** — voxel format converter (`.vox` ↔ glTF)
- **PostGIS + Tegola + MapLibre GL JS** — vector-tile stack for the
  RTS-tile evolution
- **WaveFunctionCollapse worker** — procedural tile generation
- **Colyseus** — authoritative multiplayer server for collaborative
  dreamscapes
- **Excalidraw + excalidraw-room** — sketch input surface

**Inside the existing `#### Financial / trading-AI track` sub-section:**

- **Ray cluster** — parallel-backtest substrate
- **E2B (self-hosted)** — Firecracker sandbox for LLM-generated
  strategies
- **FinRL / FinGPT image flavors** — JupyterHub + E2B kernel images
  for AI-assisted strategy authoring (library packaging, not a new
  compose service)
- **Internal wallet / ledger service, risk-control service, and
  audit-sealer worker** — in-house Phase-2 components; documented for
  scope visibility, marked explicitly as not third-party

### Long-term vision — extend the existing 4th block

The current "Foundation for vertical AI applications" block in the
Long-term vision section already names 3D and Trading as tracks. Add
two sentences:

> The 3D track composes a browser-first pipeline (Three.js + r3f →
> glTF-Transform → asset CDN via MinIO + Kong) with image-to-3D
> fast-path (InstantMesh) and fidelity-path (Hunyuan3D-2 / TRELLIS),
> evolving from snowdome-style free-form scenes to voxel
> (Vengi-converted) and RTS-tile (PostGIS + Tegola + MapLibre) world
> representations, with Colyseus enabling shared sessions.
>
> The financial-trading track composes a paper-first fleet
> (Hummingbot API + Dashboard orchestrating NautilusTrader workers
> over CCXT and equities adapters), promoted to live via signed
> Windmill flows, executed against OpenBao-custodied keys, monitored
> with Langfuse + Grafana + Hummingbot Dashboard, and audited via
> OpenSearch + MinIO Object Lock with Merkle anchors.

### Considered and rejected (append to existing skip block in ROADMAP.md)

- **Needle Engine, PlayCanvas, Stable Fast 3D, Wonder3D, Rodin,
  tldraw, Drawpile, Goxel** — Dreamscapes skip list above.
- **Freqtrade, OctoBot, Jesse, Lean as fleet manager; Silent Shard /
  Web3Auth MPC; Daytona for LLM-strategy sandbox** — Trading skip
  list above.

## Open questions / future sessions

- **Dreamscapes-the-app brainstorm** — when ready, design the
  application that sits on top of these services (UX flows, world
  schema, scene-versioning model, persistence, sharing, monetisation).
- **Trading-fleet-the-app brainstorm** — when ready, design the
  application (strategy schema, promotion checklist, dashboard
  layout, role-based-access, regulatory adapters).
- **Native-desktop Dreamscapes** — Godot or Unreal headless build
  farm; not in initial scope but explicitly mentioned by the user as
  a future direction.
- **Cloud-render Dreamscapes** — GPU pool + WebRTC SFU (LiveKit) for
  scenes that exceed the WebGL budget; not in initial scope.
- **MPC custody upgrade path** — only if multi-party signing becomes
  a real requirement; OpenBao + per-exchange API-key scoping is
  sufficient at single-operator scale.
- **Regulatory adapters for live trading** — KYC/AML, broker
  onboarding, jurisdiction-specific reporting — explicitly out of
  scope for this technical research and belongs in a separate
  compliance-design exercise before any real-money live trading.

## Validation

This spec is research-only; it does not change runtime behaviour.
Validation is exclusively documentation review:

1. The current `docs/ROADMAP.md` Tier 1/2/3 listings remain accurate;
   no entry conflicts with what this spec proposes.
2. Each new service is justified by **at least one** specific
   integration with an existing or roadmapped service in the
   pipeline walk-throughs.
3. Each phase is **separable** — Phase 2 must not require Phase 3 of
   the same scenario.
4. Each skip-list entry has a **concrete reason** (license,
   maintenance, redundancy with an existing pick).

## Follow-up

After this spec is approved:

1. Apply the **Roadmap-addendum plan** edits to `docs/ROADMAP.md`
   (Tier 1: 1 new entry; Tier 2: 3 new entries; Tier 3 sub-sections:
   ~12 new entries; Long-term-vision: extend the existing block by
   two sentences; skip list: append two short blocks).
2. Schedule the Dreamscapes-the-app brainstorm and the
   Trading-fleet-the-app brainstorm as separate sessions.
