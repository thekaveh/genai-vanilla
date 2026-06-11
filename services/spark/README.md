# Apache Spark (standalone cluster)

Spark runs as a 5-container family in the stack's `data` band: `spark-master`, `spark-worker` (replicas via `SPARK_WORKER_COUNT`), `spark-history`, `spark-connect` (dedicated Spark Connect gRPC sidecar), and `spark-init` (an idempotent minio/mc init that creates the spark-history bucket).

## 1. Overview

Image: locally built `${PROJECT_NAME}-spark:local` — `FROM apache/spark:4.1.2` plus hadoop-aws + AWS SDK v2 jars baked in by `services/spark/build/Dockerfile` (the upstream image ships no S3A support). Standalone mode — no YARN, no Kubernetes. Each role (master, worker, history, connect) is launched with an explicit `/opt/spark/bin/spark-class` or `start-connect-server.sh` command in `services/spark/compose.yml` since `apache/spark` doesn't carry the `SPARK_MODE=master|worker|history` env-driven entrypoint that Bitnami used to ship. **Spark Connect (gRPC) runs on the dedicated `spark-connect` sidecar at `sc://spark-connect:15002`** — earlier drafts attempted to host Connect inside the master JVM via `SPARK_DAEMON_JAVA_OPTS`, but `spark-class Master` doesn't honour `--conf` or `spark.plugins`, so the listener never bound. The sidecar runs `start-connect-server.sh --master spark://spark-master:7077`, which is the upstream-supported pattern.

> **Note on image choice:** earlier drafts of this service pinned `bitnami/spark:4.1.2`. Bitnami's image library moved behind the Broadcom paywall in 2025; no public 4.x tag exists today. `apache/spark` is the upstream-maintained alternative.

## 2. Access

| Surface | URL | Auth |
|---|---|---|
| Master UI (direct) | `http://localhost:${SPARK_MASTER_UI_PORT}` | None |
| Master UI (Kong) | `http://spark.localhost:${KONG_HTTP_PORT}` | None |
| History UI (direct) | `http://localhost:${SPARK_HISTORY_PORT}` | None |
| History UI (Kong) | `http://spark-history.localhost:${KONG_HTTP_PORT}` | None |
| Spark Connect | `sc://spark-connect:15002` | None — backend-network only |
| Master RPC | `spark://spark-master:7077` | None — backend-network only |

## 3. Configuration

```bash
SPARK_SOURCE=disabled              # container | disabled
SPARK_IMAGE=apache/spark:4.1.2
SPARK_MASTER_UI_PORT=              # auto-assigned by topology (data band)
SPARK_HISTORY_PORT=                # auto-assigned
SPARK_WORKER_COUNT=2               # 1-8 (wizard prompts via SecondaryNumberInput)
```

## 4. Integration with the stack

- **MinIO** — `spark-history` reads `s3a://spark-history/` for event logs. The `spark-init` container creates the bucket on first start (idempotent).
- **Supabase Postgres** — Spark JDBC connector available; users add `--jars postgresql.jar` and point at `jdbc:postgresql://supabase-db:5432/${SUPABASE_DB_NAME}`. No pre-wired connection.
- **Zeppelin** — Zeppelin's Spark interpreter points at `spark://spark-master:7077` (RPC) and `sc://spark-connect:15002` (gRPC Connect). See `services/zeppelin/README.md`.
- **Airflow** — Airflow's `spark_default` Connection is seeded by `airflow-init` when `SPARK_SOURCE=container`. The provided `example_etl_with_llm.py` DAG uses `PythonOperator` + Spark Connect (`sc://spark-connect:15002`) for smoke; `SparkSubmitOperator` is available via the bundled `apache-airflow-providers-apache-spark` for user DAGs. See `services/airflow/README.md`.
- **Prometheus + Grafana** — deferred. Spec §5.1 marks Spark × Prometheus + Grafana as CRITICAL-opt-in (JMX exporter sidecar + scrape job + `spark.json` dashboard), but the implementation is not yet wired. Tracking as a follow-up; for now use cAdvisor's container-level metrics in the existing Grafana dashboards.

## 5. Dependencies & Integrations

> Auto-generated section — the **Current** subsections are derived from `services/spark/service.yml`'s `data_flow.calls` field (and inverse passes). Re-run `python -m bootstrapper.docs.regen spark` after manifest changes.

### 5.1 Current — Upstream (this service calls)

| Service | Category |
|---|---|
| minio | data |
| supabase | data |

### 5.2 Current — Downstream (services that call this)

| Service | Category |
|---|---|
| kong | infra |
| airflow | agents |
| zeppelin | apps |

### 5.3 Architecture diagram

![spark architecture](./architecture.svg)

[Open the interactive HTML diagram](./architecture.html) for a full-screen view.

### 5.4 Future — Missing pair integrations

_No high-confidence opportunities identified._

### 5.5 Future — Candidate new services

_No high-confidence opportunities identified._

### 5.6 Future — Unused features in this service

_No high-confidence opportunities identified._

## 6. Troubleshooting

- **History UI shows no jobs** — first check producer config: a driver must set `spark.eventLog.enabled=true` + `spark.eventLog.dir=s3a://spark-history/`. The `spark-connect` sidecar and Zeppelin's `SPARK_SUBMIT_OPTIONS` already set these globally, so any sc://spark-connect:15002 client + Zeppelin `%spark` cell emits events automatically. User-driven `spark-submit` jobs need to pass the same `--conf` pair. Secondary check: confirm the spark-history bucket exists in MinIO (`mc ls minio/spark-history`); the `spark-init` container creates it on first start.
- **Workers don't appear in the master UI** — Compose's `depends_on: spark-master: condition: service_healthy` should serialize this. If a worker stays "lost", check `docker logs ${PROJECT_NAME}-spark-worker-1`.
- **OOM in a worker** — Spark workers are unbounded by default. Set `SPARK_WORKER_MEMORY=4G` in the container env block for production use.
- **Spark Connect refused** — the gRPC server runs on the `spark-connect` sidecar (NOT spark-master); clients must use `sc://spark-connect:15002`. The port is backend-network-only — don't expose 15002 to the host.
