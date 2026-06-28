# Apache Zeppelin (Spark-first notebook)

Zeppelin runs as a single container in the stack's `apps` band. The Spark interpreter is pre-configured against the in-stack Spark cluster (master RPC + Spark Connect gRPC + MinIO S3A). The JDBC interpreter ships with credentials in env vars but Zeppelin does not auto-load them — first-time users create a `postgres` interpreter (group `jdbc`) via the UI — `default.url` = `${ZEPPELIN_JDBC_POSTGRES_URL}`; see §4 for the one-time setup. Notebooks live in `services/zeppelin/notebooks/`, bind-mounted into the container.

## 1. Overview

Image: `apache/zeppelin:0.12.1` (Apache 2.0). All interpreters run in-process (no Kubernetes interpreter isolation). The Spark interpreter is the headline. The image does NOT bundle a full Spark distribution — `/opt/zeppelin/interpreter/spark/` contains only the interpreter shim, so `%spark` cells must run against an external Spark driver via **Spark Connect** (configured once in the UI — see §1.2).

**Hard requirement:** Zeppelin is gated on `SPARK_SOURCE != disabled`. Picking `ZEPPELIN_SOURCE=container` without Spark surfaces an actionable error from the bootstrapper; the spec considers a Spark-less Zeppelin broken on purpose.

**Design deviation from spec §3.2.7:** the spec envisioned a `zeppelin-init` sidecar to materialize starter notebooks and seed interpreter config files. We ship `notebooks/` bind-mounted directly and rely on env-driven interpreter config — same outcome, simpler topology, and users can edit notebooks without restarting the container.

### 1.1 What Spark Connect is (and why Zeppelin uses it)

[Spark Connect](https://spark.apache.org/docs/latest/spark-connect-overview.html) is a client-server protocol introduced in Spark 3.4: a thin client sends DataFrame / SQL operations over **gRPC** to a remote Spark driver, instead of running the driver in the same JVM as the client. The client carries no cluster — it only needs the matching Spark-Connect client library and a `sc://host:port` URL.

In Atlas this is the supported way to run Spark from a notebook:

- Zeppelin's image ships **no Spark distribution**, so there is no local driver to run.
- The stack runs a dedicated **`spark-connect` sidecar** (`services/spark/compose.yml`) — a `start-connect-server.sh` process bound to gRPC `0.0.0.0:15002`, wired to the standalone cluster (`--master spark://spark-master:7077`) and pre-loaded with the `hadoop-aws` + AWS SDK v2 bundle (via `services/spark/build/Dockerfile`), MinIO s3a credentials, and `spark.eventLog` to `s3a://spark-history/`.
- Zeppelin's `%spark` interpreter, set to `spark.remote = sc://spark-connect:15002`, becomes that thin client. The **driver runs on the sidecar**, executors on `spark-worker`, and the notebook just streams results back.

This is the same protocol that managed offerings (Databricks Connect, Google Cloud Serverless for Apache Spark, Amazon EMR Serverless) expose — so the in-stack pattern transfers to a remote/cloud Spark backend with only a URL + auth change (see §1.5).

### 1.2 Configure the Spark interpreter (one-time, step-by-step)

The interpreter config is **not** seeded automatically (the image ships interpreter defaults; we don't bind-mount `conf/interpreter.json` yet). Do this once per fresh container:

1. Confirm the Spark side is up: `docker ps --filter name=spark-connect` shows `${PROJECT_NAME}-spark-connect` (i.e. `SPARK_SOURCE != disabled`). On a cold start its JVM lags `spark-master` by 20-60s (loading the Connect plugin + binding 15002) — wait for it before step 6.
2. Open Zeppelin (`http://localhost:${ZEPPELIN_PORT}` or `http://zeppelin.localhost:${KONG_HTTP_PORT}`).
3. Top-right user menu → **Interpreter**.
4. Find the **`spark`** interpreter group → click **edit**.
5. Under **Properties**, add (or set) a property:
   - name: `spark.remote`
   - value: `sc://spark-connect:15002`

   Leave the existing `SPARK_HOME` / `master` properties as-is — when `spark.remote` is present the interpreter uses Connect mode and ignores them.
6. Click **Save**, then confirm the "restart interpreter" prompt (or use the interpreter's **restart** button).

That single property is the whole setup. `SPARK_MASTER` / `SPARK_SUBMIT_OPTIONS` in the compose env are inert in this mode — they only matter on a user-mounted `spark-submit` path (a `SPARK_HOME` you bind-mount yourself), which is not the supported in-stack flow.

### 1.3 Verify it works

In a new notebook, run a `%spark` (Scala) cell:

```scala
%spark
println(spark.version)                 // prints the cluster's Spark version (4.1.x)
spark.range(5).selectExpr("id * id as sq").show()
```

…and a `%spark.pyspark` (Python) cell:

```python
%spark.pyspark
spark.sql("SELECT 1 + 1 AS result").show()
```

If both return values, the notebook is talking to the `spark-connect` driver. (The starter notebook `notebooks/spark_basics.zpln` in §5 does the same checks plus an s3a round-trip.)

### 1.4 How MinIO (s3a) and Spark History work through Connect

You do **not** configure storage credentials in the notebook. Because the driver runs on the `spark-connect` sidecar, every Connect session inherits the **server's** conf:

- `s3a://` reads/writes use the sidecar's `spark.hadoop.fs.s3a.*` (MinIO endpoint `http://minio:9000`, root creds, path-style). So `spark.read.parquet("s3a://<bucket>/…")` from a `%spark` cell just works once the bucket exists.
- `spark.eventLog.enabled=true` + `spark.eventLog.dir=s3a://spark-history/` are set on the server, so every Connect session's events land in the History Server automatically — no per-notebook config. Browse them at the Spark History UI (`SPARK_HISTORY_PORT`).

### 1.5 Reaching Spark Connect from outside the stack (host IDEs, remote/cloud)

The `spark-connect` sidecar is **backend-only by design** — it publishes no host port, so `sc://spark-connect:15002` resolves only from inside the Docker `backend-network` (Zeppelin, Airflow DAGs). Two ways to go further, both tracked as roadmap items:

- **Host-side IDE / local Jupyter:** would require publishing the 15002 gRPC port to the host (then `sc://localhost:<port>`). Not enabled in the in-stack-only baseline.
- **Remote/managed Spark (cloud burst):** the same `spark.remote` client can point at a managed Spark Connect endpoint instead. Amazon EMR Serverless, for example, exposes interactive Spark Connect sessions at `sc://<endpoint>:443/;use_ssl=true;x-aws-proxy-auth=<token>` — the token is fetched per-session via the `emr-serverless` API and expires hourly, and the client's Spark version must match the EMR release's Spark version. That is a fundamentally different, ephemeral-session + IAM model than the static in-network sidecar — useful for scale-out, not a drop-in replacement.

### 1.6 Driving Zeppelin from VS Code

Zeppelin speaks its own REST + websocket protocol, **not** the Jupyter kernel protocol — so VS Code's built-in Jupyter extension cannot connect to it. Use the community **"Zeppelin Notebook"** extension ([`AllenLi1231.zeppelin-vscode`](https://marketplace.visualstudio.com/items?itemName=AllenLi1231.zeppelin-vscode)) instead. It renders `.zpln` notebooks in VS Code and runs every paragraph **server-side** on the Zeppelin server:

1. Install `AllenLi1231.zeppelin-vscode` from the Marketplace (requires Zeppelin >= 0.8.0; this image is 0.12.0).
2. Open or create a `.zpln` file. On the first cell run, the extension prompts for the **server URL** — enter `http://localhost:${ZEPPELIN_PORT}` (no credentials; the stack ships no auth — see §2).
3. Complete the one-time `spark.remote` interpreter setup from §1.2 if you haven't. It lives server-side, so it applies to the web UI and VS Code alike.

Because execution happens on the server, `%spark` (Scala) and `%spark.pyspark` cells run through the same Spark Connect sidecar as the web UI — VS Code never needs a Scala kernel or a Spark client of its own, and S3A/MinIO + the History Server behave identically.

**Remote host:** the extension only needs the HTTP UI, so SSH-tunnel it and point at localhost — `ssh -N -L ${ZEPPELIN_PORT}:localhost:${ZEPPELIN_PORT} user@host`. You do **not** expose the backend-only gRPC port (15002); the Zeppelin server reaches Spark Connect on the Docker network for you (§1.5).

**Caveats** (third-party extension): no notebook permissions / version-control / cron; don't edit a cell mid-run (close and reopen the notebook to resync); the VS Code language mode is cosmetic syntax highlighting only. The browser UI (§2) is the dependable fallback.

## 2. Access

| Surface | URL | Auth |
|---|---|---|
| Direct | `http://localhost:${ZEPPELIN_PORT}` | None |
| Kong | `http://zeppelin.localhost:${KONG_HTTP_PORT}` | None |

No authentication ships pre-configured. For real use, enable Shiro auth via `conf/shiro.ini` (see [Zeppelin upstream docs](https://zeppelin.apache.org/docs/0.12.0/setup/security/shiro_authentication.html)).

## 3. Configuration

```bash
ZEPPELIN_SOURCE=disabled           # container | disabled
ZEPPELIN_IMAGE=apache/zeppelin:0.12.1
ZEPPELIN_PORT=                     # auto-assigned (apps band)
```

## 4. Integration with the stack

- **Spark** (required) — `%spark` cells need the one-time Spark Connect setup from §1 (`spark.remote = sc://spark-connect:15002` in the Interpreter UI). The image ships no Spark distribution, so the `SPARK_MASTER` / `SPARK_SUBMIT_OPTIONS` env vars in compose only take effect on a spark-submit launch path that requires a user-mounted `SPARK_HOME` — out of the box they are inert.
- **MinIO** — in Spark Connect mode, `s3a://` credentials come from the **spark-connect server's** own conf (see `services/spark/compose.yml`), so MinIO reads/writes work from `%spark` cells once Connect is configured. (`SPARK_SUBMIT_OPTIONS` would only matter on the user-mounted spark-submit path above.)
- **Supabase Postgres** — JDBC connection details exposed as env vars (`ZEPPELIN_JDBC_POSTGRES_URL` / `_USER` / `_PASSWORD`). Zeppelin does not auto-bind these to the JDBC interpreter — one-time setup: open Zeppelin → Interpreter → `+ Create`, name it `postgres` with interpreter group `jdbc`, and set `default.driver=org.postgresql.Driver`, `default.url=jdbc:postgresql://supabase-db:5432/${SUPABASE_DB_NAME}` (copy the exact value from the container's `ZEPPELIN_JDBC_POSTGRES_URL` env — `${SUPABASE_DB_NAME}` defaults to `postgres` but is configurable), `default.user`/`default.password` from the corresponding env vars. Then `%postgres SELECT version()` works — note the old `%jdbc(postgres)` prefix syntax was removed in Zeppelin 0.12 (the interpreter warns "not supported anymore" and falls back to `default.*`). Tracked as a future improvement (bind-mount `conf/interpreter.json` so this is zero-touch).
- **LiteLLM** (optional) — Python interpreter can call the LiteLLM gateway via `openai.OpenAI(base_url="http://litellm:4000/v1", api_key=...)`. No pre-configuration ships; users wire it themselves.

## 5. Starter notebook

`services/zeppelin/notebooks/spark_basics.zpln` ships pre-loaded. 4 cells:
1. Spark version check (`sc.version`)
2. Markdown intro
3. MinIO round-trip via S3A (`s3a://spark-history/...`)
4. Postgres JDBC `SELECT version()` against supabase-db (requires the one-time `postgres` interpreter setup in §4; the cell will error with "Interpreter not properly configured" until you complete it)

Use it as a template for your own notebooks.

## 6. Dependencies & Integrations

> Auto-generated section — the **Current** subsections are derived from `services/zeppelin/service.yml`'s `data_flow.calls` field (and inverse passes). Re-run `python -m bootstrapper.docs.regen zeppelin` after manifest changes.

### 6.1 Current — Upstream (this service calls)

| Service | Category |
|---|---|
| minio | data |
| spark | data |
| supabase | data |

### 6.2 Current — Downstream (services that call this)

| Service | Category |
|---|---|
| kong | infra |

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
- **First `%spark` cell after stack-up errors with "connection refused"** — Zeppelin's `depends_on` gates on `spark-master: service_healthy` and `spark-init: service_completed_successfully`, but NOT on the `spark-connect` sidecar, whose JVM startup lags spark-master by 20-60s on cold start (loading the Spark Connect plugin + binding 15002). Just re-run the cell once spark-connect is up. We don't ship a Connect-side readiness probe because `start-connect-server.sh` doesn't expose `/health`.
- **S3A: "Access Denied" on s3a://...** — MinIO root credentials drift between `.env` and what the container received. `docker exec ${PROJECT_NAME}-zeppelin env | grep -E 'MINIO|SPARK_SUBMIT_OPTIONS'` to confirm. Re-run `./start.sh` to refresh.
- **JDBC interpreter "Interpreter not properly configured"** — Zeppelin does not auto-bind the `ZEPPELIN_JDBC_POSTGRES_*` env vars to a JDBC interpreter profile. Walk through §4's one-time UI setup, then restart it (Interpreter → postgres → Restart). Supabase Postgres also must be running (it's a required dep of the stack).
- **"Notebook won't save"** — `/notebook` is bind-mounted from `services/zeppelin/notebooks/`. Confirm `services/zeppelin/notebooks/` exists and is writable by the host user. Zeppelin writes new .zpln files there.
