# Apache Zeppelin (Spark-first notebook)

Zeppelin runs as a single container in the stack's `apps` band. Pre-configured Spark + JDBC interpreters point at the in-stack Spark cluster + Supabase Postgres. Notebooks live in `services/zeppelin/notebooks/`, bind-mounted into the container.

## 1. Overview

Image: `apache/zeppelin:0.12.0` (Apache 2.0). All interpreters run in-process (no Kubernetes interpreter isolation). The Spark interpreter is the headline — `SPARK_MASTER` + `SPARK_CONNECT_URL` point at the in-stack cluster, and `SPARK_SUBMIT_OPTIONS` pre-configures S3A against MinIO.

**Hard requirement:** Zeppelin is gated on `SPARK_SOURCE != disabled`. Picking `ZEPPELIN_SOURCE=container` without Spark surfaces an actionable error from the bootstrapper; the spec considers a Spark-less Zeppelin broken on purpose.

## 2. Access

| Surface | URL | Auth |
|---|---|---|
| Direct | `http://localhost:${ZEPPELIN_PORT}` | None |
| Kong | `http://zeppelin.localhost:${KONG_HTTP_PORT}` | None |

No authentication ships pre-configured. For real use, enable Shiro auth via `conf/shiro.ini` (see [Zeppelin upstream docs](https://zeppelin.apache.org/docs/0.12.0/setup/security/shiro_authentication.html)).

## 3. Configuration

```bash
ZEPPELIN_SOURCE=disabled           # container | disabled
ZEPPELIN_IMAGE=apache/zeppelin:0.12.0
ZEPPELIN_PORT=                     # auto-assigned (apps band)
```

## 4. Integration with the stack

- **Spark** (required) — `SPARK_MASTER=spark://spark-master:7077` and `SPARK_CONNECT_URL=sc://spark-master:15002` baked into the env. Notebooks use `%spark` cells with no extra config.
- **MinIO** — Spark interpreter pre-configured with `s3a://` via `SPARK_SUBMIT_OPTIONS` — read/write to MinIO buckets directly from Spark cells.
- **Supabase Postgres** — JDBC interpreter pre-configured at `jdbc:postgresql://supabase-db:5432/${SUPABASE_DB_NAME}`. SQL cells `%jdbc(postgres)` work without per-notebook setup.
- **LiteLLM** (optional) — Python interpreter can call the LiteLLM gateway via `openai.OpenAI(base_url="http://litellm:4000/v1", api_key=...)`. No pre-configuration ships; users wire it themselves.

## 5. Starter notebook

`services/zeppelin/notebooks/spark_basics.zpln` ships pre-loaded. 4 cells:
1. Spark version check (`sc.version`)
2. Markdown intro
3. MinIO round-trip via S3A (`s3a://spark-history/...`)
4. Postgres JDBC `SELECT version()` against supabase-db

Use it as a template for your own notebooks.

## 6. Dependencies & Integrations

> Auto-generated section — the **Current** subsections are derived from `services/zeppelin/service.yml`'s `data_flow.calls` field (and inverse passes). Re-run `python -m bootstrapper.docs.regen zeppelin` after manifest changes.

### 6.1 Current — Upstream (this service calls)

| Service | Category |
|---|---|
| kong | infra |
| minio | data |
| spark | data |
| supabase | data |
| litellm | llm |

### 6.2 Current — Downstream (services that call this)

_No downstream consumers._

### 6.3 Architecture diagram

![zeppelin architecture](./architecture.svg)

[Open the interactive HTML diagram](./architecture.html) for a full-screen view.

### 6.4 Future — Missing pair integrations

_No high-confidence opportunities identified._

### 6.5 Future — Candidate new services

_No high-confidence opportunities identified._

### 6.6 Future — Unused features in this service

_No high-confidence opportunities identified._

## 7. Troubleshooting

- **Spark interpreter says "no master URL"** — `SPARK_MASTER` env var is missing from the container. Check the compose env block; the manifest's runtime_sc + compose.yml dual-write should ensure it. Restart the container after fixing.
- **S3A: "Access Denied" on s3a://...** — MinIO root credentials drift between `.env` and what the container received. `docker exec genai-zeppelin env | grep -E 'MINIO|SPARK_SUBMIT_OPTIONS'` to confirm. Re-run `./start.sh` to refresh.
- **JDBC interpreter can't connect** — Supabase Postgres might be disabled. Zeppelin's gating only checks Spark, not Supabase. Set `SUPABASE_SOURCE=container` for the JDBC interpreter to work.
- **"Notebook won't save"** — `/notebook` is bind-mounted from `services/zeppelin/notebooks/`. Confirm `services/zeppelin/notebooks/` exists and is writable by the host user. Zeppelin writes new .zpln files there.
