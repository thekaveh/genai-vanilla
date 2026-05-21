# Data Engineering track — stack-fit analysis — Design

**Date:** 2026-05-21
**Status:** Draft (awaiting review)
**Owner:** Kaveh Razavi

## Problem

The stack has grown a roadmap that explicitly identifies three vertical
tracks (3D / game-generation, financial / trading-AI, RAG
specializations). A fourth track has been requested: a **Data
Engineering** lane — lakehouse + ingestion + BI + (optional) MLOps —
with explicit interest in **Scala / JVM** tooling alongside the stack's
existing Python-dominant surface. The user sketched a concrete starter
set: **Apache Spark**, **Apache Airflow**, **MinIO** (already shipped),
**JupyterHub with Scala** (already-shipped JupyterHub plus a Scala
kernel), and **Apache Zeppelin**.

This document does a deep stack-fit analysis for that fourth track,
surfaces the gaps, flags where the 2026 OSS landscape diverges from the
user's starter set, and proposes a minimal additive ROADMAP.md edit
plan.

This is a **research spec**, not an application design. Designing any
concrete data-engineering application (ELT pipelines, ML models, BI
dashboards) is a separate exercise once the platform pieces are in.

## Goals

1. Validated lakehouse-shape walk-through end-to-end, identifying which
   stack services do which job.
2. A **phased** list of service additions: Phase 1 (lakehouse core +
   BI), Phase 2 (ingestion + quality + CDC + catalog), Phase 3
   (optional MLOps slice).
3. Honest **divergence callouts** where 2026 OSS reality conflicts with
   the user's initial sketch — Zeppelin, Airflow primacy, and the
   Scala/JVM client-side requirement.
4. **Cross-cutting reuse** of services already in the stack or already
   in Tier 2 cross-cutting infrastructure (Ray, E2B), so the Data
   Engineering track does not duplicate what already exists.
5. A **minimal additive ROADMAP.md edit plan** — adds a new
   `#### Data engineering track` sub-section to Tier 3 (parallel to
   3D + Financial), extends the Long-term-vision block with a fourth
   bullet, appends to the skip list.
6. A clean **skip list** with reasons so future contributors don't
   re-propose evaluated-and-declined candidates.

## Non-goals

- Designing the data warehouse / data marts themselves (schemas, models,
  business KPIs). That belongs to deployment-specific projects on top
  of this platform.
- SaaS-data-warehouse migration patterns (Snowflake → self-host,
  BigQuery → self-host). Out of scope.
- Regulatory / governance frameworks (GDPR data-subject-rights
  pipelines, HIPAA boundaries). Belongs to a separate compliance-
  design exercise.
- Kubernetes-native services (Airbyte v2026, Spark Operator). The
  stack is Docker-Compose-first; K8s migration is a future macro
  decision.
- Choosing between Trino and StarRocks at runtime. Trino is the
  recommended default; StarRocks is documented but not in the initial
  scope.
- Real-time analytical engines (Apache Druid, ClickHouse-as-OLAP) as
  primary path. Time-series is covered by TimescaleDB; OLAP at
  lakehouse latency is covered by Trino + Iceberg.

## Scope decisions captured in this spec

- **Comprehensive scope, phased like Dreamscapes / Trading.** Phase 1
  is core lakehouse + BI; Phase 2 is ingestion + quality + CDC +
  catalog; Phase 3 is optional MLOps. Each phase is separable.
- **JVM / Scala lane explicit.** The Data Engineering track is the
  JVM-friendly lane in an otherwise Python-dominant stack. The spec
  argues the lane is *opt-in*, not required everywhere — Spark Connect
  is the key technical reason.
- **Source-variant pattern for the orchestrator.** Dagster recommended
  as the primary asset-centric orchestrator; Apache Airflow remains a
  first-class alternative via an `ORCHESTRATOR_SOURCE` source variant.

## The three divergences from the user's starter list

### Divergence 1 — Apache Zeppelin → Almond on existing JupyterHub

The user proposed Zeppelin. The spec recommends **skipping Zeppelin**
and using the **Almond Scala kernel** on the already-shipped JupyterHub
instead.

Reasons:
- Zeppelin's release cadence has slowed materially since 2024
  (most-recent meaningful release is the 0.11.x series; activity is
  thin compared to JupyterHub / Almond).
- The Polynote alternative (Netflix) is **abandoned** (last release
  2022).
- Almond delivers full Scala / Spark notebook support inside the
  notebook server we already operate, removing the need to run two
  notebook surfaces with overlapping UX.

If a future deployment explicitly needs Zeppelin's paragraph
interpreter model, it can be added then — but the default
recommendation is to stop here.

### Divergence 2 — Airflow primacy → Dagster primary, Airflow alternative

The user proposed Airflow. Airflow is already in the roadmap (Tier 3
General-purpose) and remains a credible choice. But for an
Iceberg / dbt / Spark / lakehouse-centric workflow, **Dagster** is the
2026 consensus pick:

- Software-defined Assets model fits Iceberg-as-asset thinking exactly.
- First-class dbt / Spark / Iceberg integration.
- Better UI lineage and asset-graph visualisation.
- Task-centric Airflow is still the right tool when the work is
  fundamentally task-shaped (cron-like jobs, external API calls); but
  it is the wrong primary for lakehouse pipelines.

**Recommendation:** roadmap **both** via an `ORCHESTRATOR_SOURCE`
source variant. Dagster is the default for lakehouse / asset-centric
workloads; Airflow is a permitted alternative for task-centric workloads
and for teams with existing Airflow muscle memory. This mirrors the
existing `STT_PROVIDER_SOURCE` / `TTS_PROVIDER_SOURCE` pattern.

### Divergence 3 — Scala-Spark cluster → Spark Connect makes Scala optional for clients

The user framed the Spark engine as the place where Scala lives. **Spark
Connect** (GA since Spark 3.4, recommended client surface in Spark 4.x)
changes this:

- The Spark cluster runs JVM (master + workers + Connect server).
- Clients speak **gRPC** to the Connect server: Python (PySpark
  Connect), Scala, Go, Rust, and Node have first-class clients.
- This means the **FastAPI backend, JupyterHub Python kernels, Dagster /
  Airflow workers, and Hermes / Ollama-orchestrated jobs** can use Spark
  transparently without a JVM in their container.

Scala remains useful for:
- The Almond kernel (Scala notebooks are real and valuable).
- Spark UDFs that must run inside the cluster's JVM (rare but real).
- Performance-sensitive ETL where the JVM API is meaningfully faster
  than the gRPC client.

**This makes the JVM lane opt-in, not pervasive.** Surface this
explicitly in the spec to defuse "do we need Scala everywhere?"
pressure.

## Pipeline walk-throughs

### 1. Batch / lakehouse-analytics pipeline

```
[sources]
   Supabase Postgres tables           Existing-stack service logs
       ↓                                       ↓
   [CDC, Phase 2]                          [batch ingest, Phase 2]
   Debezium Server → Redpanda            dlt (Python lib) inside Dagster worker
       ↓                                       ↓
                ────────────┬─────────────────
                            ↓
                  [object storage]
                  MinIO buckets (raw / curated)
                            ↓
                  [lakehouse table format]
                  Apache Iceberg tables
                  registered in Lakekeeper REST catalog
                            ↓
        ┌──────────────────┴──────────────────┐
        ↓                                     ↓
   [transformations]                      [federation]
   dbt-core inside Dagster                Trino: ad-hoc + dashboard queries
   (or SQLMesh)                           DuckDB: in-process for backend / nb
        ↓                                     ↓
   [quality]                              [BI / dashboards]
   Soda Core + dbt tests + Elementary     Apache Superset
                            ↓
                  [catalog / lineage]
                  OpenMetadata (Postgres + OpenSearch)
                            ↓
                  [exposed to consumers]
                  - Backend (FastAPI) — application queries
                  - JupyterHub (Python + Almond Scala kernel)
                  - Hermes — MCP-exposed table tools
                  - LiteLLM consumers — table-grounded LLM responses
```

### 2. Streaming / CDC pipeline

```
[change source]
   Supabase Postgres write-ahead log
        ↓
   Debezium Server (compose service, Apache-2.0)
        ↓
   [event bus]
   Redpanda topics (Tier 3 financial track — re-used here)
        ↓
   [stream consumers]
   - Dagster sensors → trigger Iceberg compaction / refresh
   - Backend (FastAPI) — real-time application updates
   - n8n / Windmill — event-driven workflows
   - Hermes / Open WebUI — real-time agent triggers
   - OpenMetadata — lineage events
```

### 3. ML training pipeline (Phase 3)

```
[features]
   Trino over Iceberg → offline feature view
   Redis-backed Feast online store
        ↓
   [training]
   JupyterHub notebook OR Dagster asset
   - Python: PySpark Connect → cluster
   - Scala: Almond kernel → cluster
        ↓
   [tracking]
   MLflow (Postgres registry + MinIO artifacts)
        ↓
   [data versioning]
   lakeFS (Git-like branches over MinIO)
   DVC (Git-side, library-in-image)
        ↓
   [serving, future]
   LiteLLM upstream (for LLM-shaped models)
   Bespoke FastAPI route (for non-LLM models)
        ↓
   [observability]
   Langfuse (for any LLM-augmented training calls)
   Prometheus + Grafana (training-job metrics)
```

## Phased additions

### Phase 1 — lakehouse core + BI

| Service | Add as | License | Role |
|---|---|---|---|
| **Apache Spark** (standalone + Spark Connect) | new compose service: one image, three roles (master / worker / connect-server) | Apache-2.0 | Distributed compute + cross-language client surface |
| **Lakekeeper** (Iceberg REST catalog) | new compose service | Apache-2.0 | Lighter than Apache Polaris; Postgres-backed; single Rust binary |
| **Trino** | new compose service | Apache-2.0 | Federated SQL across Iceberg, Postgres, Mongo, Redpanda, … |
| **DuckDB** | library-in-image (backend + JupyterHub) | MIT | Ad-hoc Iceberg reads without cluster spin-up |
| **dbt-core** | library-in-image (orchestrator workers) | Apache-2.0 | SQL transformations |
| **Apache Superset** | new compose service | Apache-2.0 | Primary BI / dashboard surface |
| **Almond Scala kernel** | image flavor on existing JupyterHub | BSD-3 | The Scala lane, opt-in |
| **Dagster** | new compose service (primary orchestrator) | Apache-2.0 | Asset-centric orchestration over Iceberg / dbt / Spark |

**Note:** Apache Airflow's existing Tier 3 General-purpose roadmap entry
is retained as a permitted alternative orchestrator via the
`ORCHESTRATOR_SOURCE` source-variant pattern. SQLMesh (Apache-2.0) is
documented as a permitted alternative to dbt-core.

### Phase 2 — ingestion + quality + CDC + catalog

| Service | Add as | License | Role |
|---|---|---|---|
| **dlt** (data load tool) | library-in-image (orchestrator workers + backend) | Apache-2.0 | Python-first ingestion; 2.8–6× faster than Airbyte / Sling on SQL replication |
| **Soda Core** + **Elementary** | libraries-in-image | Apache-2.0 | Data quality + dbt-native observability + anomaly detection |
| **Debezium Server** | new compose service | Apache-2.0 | CDC over Redpanda; no Kafka Connect required |
| **OpenMetadata** | new compose service | Apache-2.0 | Data catalog with column-level lineage; reuses Postgres + OpenSearch |

**Skip Airbyte** — Docker Compose support deprecated in 2025;
production now requires Kubernetes + Postgres + Redis + Temporal; ELv2
license is also incompatible with the stack's permissive-boilerplate
posture. **Meltano** (MIT) is documented as the fallback if Singer
connectors are specifically needed.

### Phase 3 — optional MLOps slice

| Service | Add as | License | Role |
|---|---|---|---|
| **MLflow** | new compose service | Apache-2.0 | Experiment + model tracking; Postgres-backed registry + MinIO artifacts |
| **lakeFS** | new compose service | Apache-2.0 | Git-like branches over MinIO; petabyte-scale, no copying |
| **DVC** | library-in-image | Apache-2.0 | Git-side ML asset versioning |
| **Feast** | new compose service | Apache-2.0 | Feature store; Redis online + Iceberg-via-Trino offline |

## Coverage from existing + roadmapped services

| Role | Service | Status |
|---|---|---|
| Object storage / data lake | MinIO | shipped |
| Catalog metadata, MLflow registry | Supabase (Postgres) | shipped |
| Feast online store, Dagster sensor state | Redis | shipped |
| Catalog search, lineage events | OpenSearch | roadmap Tier 3 (general) |
| CDC sink, event bus | Redpanda | roadmap Tier 3 (financial track) |
| Time-series storage | TimescaleDB extension | roadmap Tier 3 (financial track) |
| Python + Scala notebooks | JupyterHub + Almond | shipped + new image flavor |
| Edge gateway | Kong | shipped |
| LLM routing | LiteLLM | shipped |
| Agent runtime, MCP tool surface | Hermes, MCP gateway | shipped + Tier 1 |
| LLM observability | Langfuse | roadmap Tier 1 |
| Infra observability | Prometheus + Grafana | roadmap Tier 1 |
| Secrets | Infisical (ops) + OpenBao (cryptographic) | roadmap Tier 1 |
| Code-first workflows | Windmill | roadmap Tier 3 (general) |
| Parallel compute | Ray | Tier 2 cross-cutting |
| Untrusted-code sandbox | E2B (self-hosted) | Tier 2 cross-cutting |

The lakehouse foundation is unusually well-covered by reused services:
**MinIO** is the data lake, **Postgres** carries every catalog's
metadata, **Redis** is the Feast online store, **OpenSearch** is
OpenMetadata's search backend, **Redpanda** is Debezium's sink, and
**Ray** + **E2B** (cross-cutting) handle parallel and sandboxed work
respectively.

## Skip list (with reasons)

- **Apache Zeppelin** — superseded by Almond-on-JupyterHub; activity has
  slowed since 2024.
- **Polynote** (Netflix) — abandoned, last release 2022.
- **Airbyte** — Docker Compose support deprecated; ELv2 license; K8s-
  only production deployment.
- **DataHub** as the catalog — heavyweight (GMS + Kafka consumers +
  Elasticsearch + Neo4j); OpenMetadata has the right footprint for
  compose.
- **Apache Atlas** — legacy Hadoop-era; out of scope.
- **Apache Hive** — legacy; Trino + Iceberg replaces it.
- **Apache Hudi** — declining mindshare; Iceberg owns the table-format
  space in 2026.
- **Apache Polaris** as the catalog — defensible (Apache governance,
  Snowflake-donated, supports Iceberg + Delta + Hudi), but operationally
  heavier than Lakekeeper for this stack's footprint. Documented as a
  permitted alternative.
- **Pachyderm** — HPE discontinued OSS releases in 2024.
- **Featureform** — smaller community than Feast.
- **W&B Local** — requires commercial license.
- **StarRocks** as primary OLAP — defer; revisit only if Trino dashboard
  latency becomes a pain point. Documented as a permitted accelerator.
- **ClearML** as MLOps primary — richer than MLflow but operationally
  heavier; deferred until MLflow's tracking-only feature surface is
  insufficient.

## Cross-cutting findings

### Spark Connect changes the JVM story

Surfaced as one of the three divergences above. The implication for the
roadmap is significant: **the JVM lane is opt-in**, used only for the
notebook layer (Almond) and rare UDF work. Most consumers (Dagster
workers, FastAPI backend, JupyterHub Python kernels, Hermes-orchestrated
jobs) talk to Spark via gRPC and stay Python.

### Reuse of the Tier 2 cross-cutting infrastructure

Both cross-cutting services land here naturally:
- **Ray** — parallel ETL fan-out, embedding-generation jobs over
  Iceberg, ML hyperparameter search, training acceleration for Phase 3
  MLOps work.
- **E2B (self-hosted)** — sandboxed execution of notebook code from
  untrusted sources, sandboxed dbt-pipeline plugins, agent-generated
  ETL scripts.

This is the second strong validation of the Tier 2 cross-cutting
sub-section (after the original Trading-track surfacing).

### JVM lane container patterns

Standard 2026 pattern: **one `spark-base` image** (Eclipse Temurin
JDK 17 + Spark 4.x + Iceberg runtime + AWS S3A connector + spark-connect
jars) used by **master**, **worker**, and **connect-server** containers
— three roles, one image, different entrypoints. This avoids JDK drift
between cluster components.

**JupyterHub** stays on its existing Python base image and pulls Almond
via coursier at first-run (no JVM in the base image). **Trino**,
**OpenMetadata**, and **Dagster** each ship with their own runtime
choices and should not share the spark-base image.

### `ORCHESTRATOR_SOURCE` source-variant pattern

Mirrors the existing `STT_PROVIDER_SOURCE` and `TTS_PROVIDER_SOURCE`
patterns. Allowed values: `dagster-container`, `airflow-container`,
`dagster-localhost`, `airflow-localhost`, `external`, `disabled`. The
bootstrapper enforces exactly one orchestrator is active when
`ORCHESTRATOR_SOURCE != disabled`.

### No in-house custom services

Unlike the Trading-fleet spec (which identified wallet / risk-control /
audit-sealer as custom in-house components), Data Engineering needs
**zero in-house custom services**. Every gap fills with an established
OSS service. The boilerplate's value here is the *wiring*, not new
code.

## Roadmap-addendum plan

Minimal additive edits to `docs/ROADMAP.md`.

### Tier 3 — new sub-section `#### Data engineering track`

Place after `#### Financial / trading-AI track`, before
`#### Real-time / collaboration`. New entries:

- **Apache Spark (standalone + Spark Connect)** — distributed compute
- **Lakekeeper** — Iceberg REST catalog
- **Trino** — federated SQL
- **Apache Superset** — BI dashboards
- **Dagster** — primary asset-centric orchestrator
- **dlt + Meltano + Debezium Server + OpenMetadata** — Phase 2 ingestion
  + CDC + catalog
- **MLflow + lakeFS + Feast** — Phase 3 MLOps slice
- **Almond Scala kernel for JupyterHub** — image-flavor note
- **Note on dbt-core / SQLMesh / DuckDB / Soda Core / Elementary / DVC**
  as library-in-image additions (not compose services)
- **`ORCHESTRATOR_SOURCE` source-variant pattern note** referencing
  the existing `STT_PROVIDER_SOURCE` precedent

### Existing entries to update in place

- **Apache Airflow integration** (currently Tier 3 General-purpose) —
  add a one-line note that it now lives under the Data engineering
  track as the alternative orchestrator under `ORCHESTRATOR_SOURCE`.
  Keep the entry where it is (cross-track relevance) but cross-
  reference the new sub-section.

### Long-term vision — extend the existing 4th block

Append a fourth bullet to the "Foundation for vertical AI applications"
block:

> **Data Engineering — lakehouse + ML platform** — host a complete
> data-engineering pipeline: **MinIO** lake → **Apache Iceberg** tables
> in **Lakekeeper** catalog → **Trino** + **DuckDB** for federated SQL
> → **dbt-core** transformations → **Apache Superset** for BI;
> orchestrated by **Dagster** (or **Apache Airflow** under
> `ORCHESTRATOR_SOURCE`); ingested via **dlt** + **Debezium Server** →
> Redpanda; quality enforced by **Soda Core** + **Elementary**; cataloged
> in **OpenMetadata**; MLOps via **MLflow** + **lakeFS** + **Feast**;
> Scala notebooks via **Almond** on existing **JupyterHub**, with
> **Spark Connect** keeping the rest of the stack Python-native.

### Considered and rejected — append a new block under the existing skip list

```
**From the data-engineering stack-fit research (2026-05-21 — see
`docs/superpowers/specs/2026-05-21-data-engineering-stack-fit.md`):**

- Apache Zeppelin — superseded by Almond-on-JupyterHub …
- Polynote (Netflix) — abandoned, last release 2022 …
- Airbyte — Docker Compose deprecated; ELv2 license …
- DataHub as the catalog — too heavy for compose …
- Apache Atlas / Hive / Hudi — legacy or declining …
- Pachyderm — HPE discontinued OSS …
- Featureform — smaller community than Feast …
- W&B Local — commercial-license requirement …
- StarRocks as primary OLAP — defer until Trino latency …
- ClearML as MLOps primary — defer until MLflow insufficient …
```

## Validation

This spec is research-only; it does not change runtime behaviour.
Validation is exclusively documentation review:

1. The current `docs/ROADMAP.md` Tier 1/2/3 listings remain accurate
   after edits; no entry conflicts.
2. Each new service is justified by at least one specific integration
   with an existing or roadmapped service in the pipeline walk-throughs.
3. Each phase is **separable** — Phase 2 must not require Phase 3 of
   the same scenario.
4. Each skip-list entry has a **concrete reason** (license,
   maintenance, redundancy with an existing pick).
5. The three divergences (Zeppelin, Airflow primacy, Scala-via-Connect)
   are surfaced explicitly so future readers don't re-propose them.

## Open questions / future sessions

- **Concrete data-platform-on-top-of-stack project** — when ready,
  design a specific data product (a particular data warehouse, a
  particular set of dbt models, a specific BI dashboard) using these
  platform pieces.
- **Kubernetes migration** — at some point the stack may outgrow
  Docker Compose; when that happens, Airbyte and Spark Operator
  become reasonable additions.
- **StarRocks vs Trino performance** — only worth a future evaluation
  if dashboard latency on the Trino path becomes a real pain.
- **OpenMetadata vs DataHub re-evaluation** — only worth revisiting if
  OpenMetadata coverage proves insufficient (column-level lineage,
  custom-source connectors).
- **Lakekeeper vs Polaris re-evaluation** — only worth revisiting if
  Lakekeeper's operational footprint becomes a constraint.
- **MLOps depth** — Phase 3 here is intentionally minimal (MLflow +
  lakeFS + DVC + Feast). A deeper MLOps slice (KServe, Seldon, BentoML
  for serving; W&B Local replacement) is a separate future track.

## Follow-up

After this spec is approved:

1. Apply the **Roadmap-addendum plan** edits to `docs/ROADMAP.md`:
   - Tier 3: new `#### Data engineering track` sub-section with the
     listed entries
   - In-place update to the existing **Apache Airflow integration**
     entry cross-referencing the new sub-section
   - Long-term vision: append the 4th bullet
   - Skip list: append the data-engineering block
2. Schedule a future concrete-platform-design brainstorm once a
   specific data product is in scope.
