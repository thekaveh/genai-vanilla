# Apache Airflow (DAG orchestrator)

Airflow runs as a 3-container family in the stack's `agents` band: `airflow-webserver` (Web UI + REST API), `airflow-scheduler` (DAG parser + LocalExecutor task runner), and `airflow-init` (one-shot bootstrap: DB migrate + admin user + Connection seeding).

## 1. Overview

Image: `apache/airflow:3.2.2` (Apache 2.0), wrapped by a local `services/airflow/build/Dockerfile` that adds the 10-provider bundle needed for the cross-stack integrations (apache-spark, amazon, postgres, redis, common-sql, weaviate, neo4j, openai, langchain, fab) plus `pyspark==4.1.2` (matches the Spark image — required by the Spark Connect smoke step in the sample DAG). LocalExecutor is the only supported executor in v1 — tasks run in the scheduler's process pool. Metadata DB lives in a new `airflow` database on Supabase Postgres, created by `airflow-init` on first start.

## 2. Access

| Surface | URL | Auth |
|---|---|---|
| Web UI (direct) | `http://localhost:${AIRFLOW_PORT}` | `admin` / `${AIRFLOW_ADMIN_PASSWORD}` |
| Web UI (Kong) | `http://airflow.localhost:${KONG_HTTP_PORT}` | Same |
| REST API | `http://airflow.localhost:${KONG_HTTP_PORT}/api/v2/` | HTTP basic (same admin creds) |

`AIRFLOW_ADMIN_PASSWORD` is auto-generated on first run and persisted to `.env`. Treat it like any other secret.

## 3. Configuration

```bash
AIRFLOW_SOURCE=disabled              # container | disabled
AIRFLOW_IMAGE=apache/airflow:3.2.2
AIRFLOW_PORT=                        # auto-assigned (agents band)
AIRFLOW_DB_USER=airflow              # role on Supabase Postgres
AIRFLOW_DB_PASSWORD=                 # auto-generated
AIRFLOW_FERNET_KEY=                  # auto-generated (Connection-password encryption)
AIRFLOW_SECRET_KEY=                  # auto-generated (AIRFLOW__API__SECRET_KEY — signs inter-process payloads in Airflow 3.x)
AIRFLOW_ADMIN_PASSWORD=              # auto-generated (admin login)
```

Auto-managed (resolved by the bootstrapper from `AIRFLOW_SOURCE`; do not hand-edit): `AIRFLOW_WEBSERVER_SCALE`, `AIRFLOW_SCHEDULER_SCALE`, `AIRFLOW_INIT_SCALE`.

## 4. Seeded Connections

`airflow-init` runs once at first start and seeds Airflow Connection objects for every enabled sibling service. Each is gated on the sibling's `_SOURCE` env var:

| Connection ID | Type | Target | Gated on |
|---|---|---|---|
| `postgres_supabase` | postgres | `supabase-db:5432/${SUPABASE_DB_NAME}` | always (required dep) |
| `litellm_default` | openai | `http://litellm:4000/v1` with `LITELLM_MASTER_KEY` (the `/v1` lives in conn.host because OpenAIHook ignores `api_base` extras) | always (LiteLLM is locked always-on) |
| `redis_default` | redis | `redis:6379` with `REDIS_PASSWORD` | always (Redis ships container-only always-on, auth-on by default) |
| `spark_default` | spark | `spark://spark-master:7077` | `SPARK_SOURCE=container` |
| `minio_default` | aws (S3-compat) | `http://minio:9000` with root creds, path-style addressing, region `us-east-1` | `MINIO_SOURCE=container` |
| `weaviate_default` | weaviate | host `weaviate`, port `8080`, gRPC `weaviate:50051` (via extra) | `WEAVIATE_SOURCE=container` (NOT `localhost` — the in-Compose DNS does not resolve in host-mode) |
| `neo4j_default` | neo4j | host `neo4j-graph-db`, port `7687`, login `${GRAPH_DB_USER}`, password `${GRAPH_DB_PASSWORD}` (Hook prepends `bolt://`) | `NEO4J_GRAPH_DB_SOURCE=container` (same caveat) |

Connection seeding is idempotent — `airflow-init` deletes-then-adds each Connection on every run, so changes to credentials propagate on the next `./start.sh`.

## 5. Sample DAG

`services/airflow/dags/example_etl_with_llm.py` ships pre-loaded. Three operators that smoke-test each Connection:

1. `PythonOperator` invoking Spark Connect at `sc://spark-connect:15002` — smoke-tests `spark_default` reachability without owning a JAR build. See the DAG docstring for why `SparkSubmitOperator` is deferred to user DAGs.
2. `OpenAIOperator` against `litellm_default` (sends a one-token prompt). Defaults to `ollama/qwen3.6:latest` (Ollama-mode); swap to `gpt-4o-mini` or similar if running with `--llm-provider-source none` + `CLOUD_OPENAI_SOURCE=enabled`.
3. `S3Hook.list_buckets()` against `minio_default`.

A commented `LangChainOperator` block at the bottom of the file shows the recommended pattern for chain-based LLM steps.

Use it as a template. Drop your own DAGs into `services/airflow/dags/` — they're bind-mounted into the container.

## 6. Hermes → Airflow integration

Hermes can trigger Airflow DAGs via the REST API:

```bash
curl -X POST \
  -u admin:${AIRFLOW_ADMIN_PASSWORD} \
  -H 'Content-Type: application/json' \
  -d '{"conf": {}}' \
  http://airflow.localhost:${KONG_HTTP_PORT}/api/v2/dags/example_etl_with_llm/dagRuns
```

This pattern — agent runtime → orchestrated workflow — pairs Hermes's reactive surface with Airflow's batch/scheduled surface.

## 7. Dependencies & Integrations

> Auto-generated section — the **Current** subsections are derived from `services/airflow/service.yml`'s `data_flow.calls` field (and inverse passes). Re-run `python -m bootstrapper.docs.regen airflow` after manifest changes.

### 7.1 Current — Upstream (this service calls)

| Service | Category |
|---|---|
| minio | data |
| neo4j | data |
| redis | data |
| spark | data |
| supabase | data |
| weaviate | data |
| litellm | llm |

### 7.2 Current — Downstream (services that call this)

| Service | Category |
|---|---|
| kong | infra |
| hermes | agents |

### 7.3 Architecture diagram

![airflow architecture](./architecture.svg)

[Open the interactive HTML diagram](./architecture.html) for a full-screen view.

### 7.4 Future — Missing pair integrations

_No high-confidence opportunities identified._

### 7.5 Future — Candidate new services

_No high-confidence opportunities identified._

### 7.6 Future — Unused features in this service

_No high-confidence opportunities identified._

## 8. Troubleshooting

- **`airflow-init` fails with "database does not exist"** — Supabase Postgres might not be running yet. `airflow-init` depends_on `supabase-db: service_healthy` so this shouldn't happen, but if it does, `docker logs ${PROJECT_NAME}-airflow-init` shows the psql error.
- **Web UI login rejected** — `AIRFLOW_ADMIN_PASSWORD` in `.env` may have rotated. Check the value; if rotated, `airflow-init` re-runs and re-syncs the admin user on next `./start.sh`.
- **DAG appears in UI but won't run** — Scheduler may be lagging. `docker logs ${PROJECT_NAME}-airflow-scheduler` for parse errors. The scheduler poll interval defaults to 30s.
- **`OpenAIOperator` errors with `auth required`** — `litellm_default` Connection has the wrong `LITELLM_MASTER_KEY`. Re-run `./start.sh` to re-sync the Connection; alternatively edit it in the Web UI under Admin → Connections.
- **Spark `spark_smoke` task can't reach `sc://spark-connect:15002` (or `spark://spark-master:7077` from user `SparkSubmitOperator` DAGs)** — Either (a) Spark isn't running (`SPARK_SOURCE=disabled` in `.env`; enable it via `--spark-source container` or remove the Spark-dependent steps from your DAG), or (b) it's the first DAG run after stack-up and spark-connect's JVM hasn't finished binding 15002 yet (20-60s cold-start lag). Airflow's `retries: 1` + `retry_delay: 2m` in default_args usually masks (b); if it doesn't, re-trigger the DAG once spark-connect is up.
- **`spark_smoke` raises `ModuleNotFoundError: No module named 'pyspark'`** — the airflow image hasn't been rebuilt since `pyspark` was added to `services/airflow/build/requirements.txt`. Run `docker compose build airflow-webserver` (or `./start.sh --rebuild airflow-webserver` if your wrapper supports it) and restart.
