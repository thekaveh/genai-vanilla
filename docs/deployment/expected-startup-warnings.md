# Expected Startup Warnings

The first ~60 seconds after `./start.sh` produce a handful of warnings and one-shot ERROR lines that look alarming but are either (a) library-internal noise we can't suppress without forking, (b) intentional secure defaults, or (c) startup races that don't recur and don't affect functionality. This page enumerates the ones we've investigated and decided to live with, so future operators don't chase them.

If you see a warning *not* on this list, that's a real signal — start there.

## Inventory

### Library-internal / image-baked deprecations (no action from us)

| Service | Message | Why we live with it |
|---|---|---|
| `genai-supabase-auth` | `DEPRECATION NOTICE: GOTRUE_JWT_ADMIN_GROUP_NAME not supported by Supabase's GoTrue, will be removed soon` | We do not set this env var anywhere (`grep -r GOTRUE_JWT_ADMIN_GROUP_NAME` is empty). GoTrue's own startup banner announces the upcoming removal regardless of whether the var is set. |
| `genai-kong-api-gateway` | `[warn] rate-limiting: config.redis_port / redis_ssl / redis_ssl_verify / redis_timeout / redis_database is deprecated, please use config.redis.<key> instead (deprecated after 4.0)` × ~20 (once per worker) | Fired by Kong's bundled `rate-limiting` plugin schema. We never set any `redis_*` keys — the only `rate-limiting` plugin instance is on the `searxng-api` route with `policy: local` (no Redis at all). Kong's plugin warns about its own schema defaults. Will need attention when Kong 4.0 ships. |
| `genai-supabase-realtime` | `[warning] Replica region not found, defaulting to Realtime.Repo` × 2 | Single-node mode. Realtime is multi-region aware; on a single-node setup it defaults to the primary Repo, which is what we want. |
| `genai-open-web-ui` | `WARNING: Running pip as the 'root' user can result in broken permissions ...` × 5 | Emitted by the Open WebUI runtime tool installation. The image runs as root by design. |
| `genai-jupyterhub` | `WARNING: Use start-notebook.py instead` / `WARNING: container must be started as root to grant sudo permissions!` | Both come from the jupyter/docker-stacks base. We need root for sudo grants to the spawned user notebooks. |
| `genai-minio` | `WARNING: Host local has more than 0 drives of set. A host failure will result in data becoming unavailable.` | Single-host dev mode. Production multi-node MinIO would silence this. |

### Intentional secure defaults

| Service | Message | Why |
|---|---|---|
| `genai-hermes` | `WARNING gateway.run: No user allowlists configured. All unauthorized users will be denied. Set GATEWAY_ALLOW_ALL_USERS=true ... or configure platform allowlists ...` | Hermes is secure-by-default — operator must explicitly opt in (per-platform allowlists or `GATEWAY_ALLOW_ALL_USERS=true`). |
| `genai-open-web-ui` | `WARNING: CORS_ALLOW_ORIGIN IS SET TO '*' - NOT RECOMMENDED FOR PRODUCTION DEPLOYMENTS.` | Dev default; production stacks should set an explicit origin list. |

### Unavoidable startup races

| Service | Message | Cause / mitigation |
|---|---|---|
| `genai-supabase-db` | `ERROR: relation "LiteLLM_VerificationTokenView" does not exist` × 8, `ERROR: type "LiteLLM_VerificationTokenView" already exists` × 1 (and similar for `MonthlyGlobalSpend`, `Last30dKeysBySpend`, …) | LiteLLM's `/v1/proxy` starts 4 worker processes in parallel. After the parent runs `prisma migrate deploy` (once, cleanly), each worker calls `create_missing_views()` which uses a SELECT-then-CREATE pattern. Two of the eight views (`LiteLLM_VerificationTokenView`, `Last30dTopEndUsersSpend`) use plain `CREATE VIEW` instead of `CREATE OR REPLACE VIEW`, so the 4 workers race — one wins, the rest see "already exists". This is a LiteLLM upstream source-code race; mitigating it would require either monkey-patching `litellm/proxy/db/create_views.py` inside the container, running LiteLLM with `--num_workers 1` (kills throughput), or waiting for an upstream patch. |
| `genai-weaviate` | `level":"warning","msg":"heartbeat timeout reached, starting election` (1 line) | Single-node Raft REQUIRES a leader election to make the only node the leader. Election takes ~100 ms. The `failed to join cluster` warning that previously preceded this is silenced by `RAFT_BOOTSTRAP_EXPECT=1` + `RAFT_JOIN=weaviate` in `services/weaviate/compose.yml`. The remaining heartbeat-timeout is intrinsic to Raft. |
| `genai-lightrag` | `ERROR: PostgreSQL database, error:relation "lightrag_*" does not exist` × 8 at first boot, each immediately followed by `Creation success` + `Creating HNSW index ...` | LightRAG's PGVectorStorage uses a SELECT-then-CREATE pattern (probe-then-init) for its 8 backing tables. On a fresh DB the SELECT errors (no rows exist), the error is caught, CREATE TABLE runs, success line follows. Self-resolving; only fires on the very first boot against a clean Supabase volume. Same shape as the LiteLLM view-create race above. |
| `genai-kong-api-gateway` | `[warn] the "user" directive makes sense only if the master process runs with super-user privileges, ignored` × 2 | Kong's bundled nginx config sets a `user` directive but the container runs as a non-root user (matches Kong's own security recommendation). nginx ignores the directive; no functional impact. Kong upstream chose not to silence this. |

### macOS Docker Desktop — container expects Linux host paths

The following warnings appear because containers built for Linux look for Linux-specific paths (`/etc/machine-id`, `/run/udev/data`, container-runtime sockets) that don't exist on macOS Docker Desktop's VM. All non-fatal; the affected services run normally.

| Service | Message | Why |
|---|---|---|
| `genai-cadvisor` | `Failed to get system UUID: open /etc/machine-id: no such file or directory` + Podman / containerd / crio / mesos `factory` registration failures | cAdvisor tries to discover container runtimes at startup. Docker Desktop on macOS only provides the Docker socket; the rest fail registration. cAdvisor still collects Docker metrics. |
| `genai-node-exporter` | `Failed to open directory, disabling udev device properties` (path `/run/udev/data`) | node-exporter's diskstats collector wants udev metadata. macOS doesn't have udev; the collector falls back to bare diskstats without device labels. |
| `genai-postgres-exporter` | `Error opening config file "postgres_exporter.yml": no such file or directory` | The exporter looks for an optional config file we don't mount. Without it, it uses sensible defaults and queries the database directly. Harmless. |

### Bind-mount permission quirks (macOS Docker Desktop)

| Service | Message | Why |
|---|---|---|
| `genai-searxng` | `WARNING: "/etc/searxng" directory is not owned by "searxng:searxng"` + same for `settings.yml` | Bind-mount of `services/searxng/config/` into `/etc/searxng`. macOS files are owned by the host user (uid 501); inside the container they appear as `root:root` through Docker Desktop's UID translation. `chown` inside the container can't persist for host-side bind mounts. Searxng's own message says "MAY cause issues" — and in practice it doesn't (healthcheck + searches both succeed). |

### Capability gaps (documented, not silenced)

| Service | Message | Note |
|---|---|---|
| `genai-n8n-worker` | `Failed to start Python task runner in internal mode. because Python 3 is missing from this system.` | The n8n image is Alpine + Node, no Python. We don't bundle the Python task runner. If you need Python nodes in n8n workflows, either (a) build a custom n8n image with `apk add python3 py3-pip`, or (b) deploy the runner in external mode per [n8n's docs](https://docs.n8n.io/hosting/configuration/task-runners/#setting-up-external-mode). |

### Acceptable info messages

| Service | Message | Why |
|---|---|---|
| `genai-weaviate` | `Multiple vector spaces are present, GraphQL Explore and REST API list objects endpoint module include params has been disabled as a result.` | We register multiple vectorizers (`text2vec-openai`, `text2vec-ollama`, `multi2vec-clip`, `generative-openai`, `generative-ollama`) so different classes can pick the right one. The trade-off is that the GraphQL `Explore` endpoint is disabled. We don't use `Explore` in any consumer (backend uses class-specific GraphQL `Get` queries instead). |

### Silenced — fixed at the source (do not re-add)

These previously appeared in logs and have been actively silenced by config edits:

| Service | Was | How silenced |
|---|---|---|
| `genai-n8n` | `DEPRECATION: N8N_RUNNERS_ENABLED → Remove this environment variable; it is no longer needed.` | Removed `N8N_RUNNERS_ENABLED: true` from `services/n8n/compose.yml` (was set on both `n8n` and `n8n-worker`; default is now `true`). |
| `genai-backend` | `UserWarning: Storage endpoint URL should have a trailing slash. The URL has been automatically corrected.` | Added trailing `/` in `services/backend/app/app/main.py:62` (`storage_url = f"{KONG_URL}/storage/v1/"`). |
| `genai-open-web-ui` | `WARNING langchain_community.utils.user_agent: USER_AGENT environment variable not set` | Set `USER_AGENT: GenAI-Vanilla/Open-WebUI` in `services/open-webui/compose.yml`. |
| `genai-weaviate` | `failed to join cluster from [<self>:8300]` + extra `heartbeat timeout` / `starting election` lines | Set `RAFT_BOOTSTRAP_EXPECT=1` + `RAFT_JOIN=weaviate` in `services/weaviate/compose.yml`. Single-node mode now starts with explicit voter config; the join-attempt warning is gone (the remaining heartbeat-timeout is intrinsic to Raft single-node election). |
| `genai-searxng` | `ERROR:searx.botdetection: X-Forwarded-For nor X-Real-IP header is set!` (one-shot at boot) | Added `--header=X-Forwarded-For: 127.0.0.1` to the healthcheck in `services/searxng/compose.yml`. The trusted-proxies module's `log_error_only_once` would otherwise fire on the first XFF-less healthcheck after startup. |

## When to update this page

Add an entry here when:

1. You investigate a warning, confirm it's library-internal / one-shot / intentional, and want future operators to skip the same investigation.
2. You silence a warning via a code/config change — keep the entry but note the date + commit so the entry can eventually be retired if the upstream library stops emitting.

Remove an entry when:

1. The upstream library stops emitting the message in a version we've adopted.
2. We've fixed the root cause and the warning no longer appears in a fresh `./start.sh`.

If you encounter a startup warning **not** on this list, that's a real signal worth investigating before adding it here.
