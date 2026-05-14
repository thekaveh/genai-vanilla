# MinIO service — design

**Date:** 2026-05-12
**Status:** approved design, ready for implementation planning
**Branch / worktree:** `add-minio-service`
**Roadmap entry:** `docs/ROADMAP.md` — Tier 2 → moved to Completed on land

---

> **Historical-context note (May 13, 2026):** This spec was written before the
> per-service modularization refactor landed. The refactor is now complete
> (commit `a6abd34`). MinIO ships in the modular layout as
> `services/minio/{service.yml, compose.yml}` with its init scripts under
> `services/minio/init/scripts/`. The variable names and bucket-name
> contract described below are stable and unchanged by that migration —
> only the on-disk locations differ from what's described in section
> "Monolithic-shape integration" below.

## Context

The GenAI Vanilla stack today has exactly one storage surface: Supabase Storage with a filesystem backend (`STORAGE_BACKEND=file`, `/var/lib/storage` on a named volume). That surface is well-suited to app-tier files — row-level-security uploads, signed URLs, ~50 MB ceiling per file via `STORAGE_FILE_SIZE_LIMIT=52428800`. It is the wrong surface for high-throughput, large-blob artifact workloads: ComfyUI generated images at scale, document-processor binaries, model checkpoints, dataset versioning, n8n / Backend artifact handoff.

`docs/ROADMAP.md` (Tier 2, lines 165–181) makes the architectural intent explicit:

> Complements Supabase Storage rather than replacing it: Supabase Storage stays the app-tier file surface (row-level-security uploads, signed URLs); MinIO becomes the artifact-tier surface for high-throughput, large-blob workloads.

This spec lands MinIO as that artifact-tier surface — a self-contained, S3-compatible storage service with a published consumer contract (bucket names + scoped service-account credentials in `.env`) but **no consumer code changes in this PR**. Per-consumer integrations (ComfyUI, Backend, n8n, JupyterHub, Doc Processor) each ship in their own follow-up PR; the foundation laid here makes each of those a small env-only adoption.

Two project-level decisions narrowed scope before this design was written:

1. **Monolithic-shape integration.** The per-service modularization refactor (approved separately, plan at `/Users/kaveh/.claude/plans/please-do-a-comprehensive-lovely-pelican.md`) is not yet landed. MinIO is integrated in the current monolithic shape — single `docker-compose.yml`, single `.env.example`, single `bootstrapper/service-configs.yml` — and will migrate into `services/minio/` along with its siblings when the refactor lands. The variable names and bucket-name contract chosen here are stable across that migration.
2. **Leaf-plus-contract scope.** This PR ships MinIO as a leaf service with an opinionated bucket and credential layout. It does **not** wire any of the five planned consumers. The credentials and bucket names are in `.env` from day one so each consumer adoption is a small, focused PR.

---

## Architecture

### Position in the stack

MinIO is a leaf storage service. It depends on nothing inside the stack. It attaches to the existing `backend-network`. Internal service-discovery hostname is `minio`:

- S3 API: `http://minio:9000` (intra-stack)
- Admin console: `http://minio:9001` (intra-stack)

Host-exposed:

- S3 API: `http://localhost:${MINIO_PORT}` (default `63026`)
- Admin console: `http://localhost:${MINIO_CONSOLE_PORT}` (default `63027`)

No Kong route. MinIO is internal infrastructure for the artifact tier; consumers talk to it directly over the Compose network. The host-exposed S3 API enables external tooling (aws-cli, `mc`, host-side notebooks) without traversing the API gateway. The host-exposed console enables browser-based bucket inspection and service-account verification.

### Image pin

- `MINIO_IMAGE` — `minio/minio:RELEASE.2025-10-15T17-29-55Z`. This release is also a CVE fix for **service-account privilege escalation via session-policy bypass** — directly relevant since this spec is built around service accounts. Treat it as the floor; do not downgrade.
- `MINIO_INIT_IMAGE` — `minio/mc:RELEASE.2025-08-13T08-35-41Z` (most recent stable `mc` at planning time; MinIO server / `mc` client are cross-version compatible within a reasonable window).

Re-verify both tags against `github.com/minio/minio/releases` and `github.com/minio/mc/releases` at implementation time and bump to whatever is then most recent stable (the server pin must remain ≥ `RELEASE.2025-10-15T17-29-55Z` for the CVE).

`:latest` is rejected: every other data service in the stack pins a specific version (`supabase/storage-api:v1.22.7`, `kong:3.9.0`, etc.). Pinning protects users from `RELEASE.<date>` server / client incompatibilities and surprise auth changes.

### Ports

| Variable | Offset | Default (with `BASE_PORT=63000`) | Container port | Purpose |
|---|---|---|---|---|
| `MINIO_PORT` | `+26` | `63026` | `9000` | S3 API |
| `MINIO_CONSOLE_PORT` | `+27` | `63027` | `9001` | Admin console (web UI) |

Offsets 26 and 27 are the next contiguous unused slots in the existing allocation (verified against `bootstrapper/core/port_manager.py:18-46`: current dict covers offsets 0–25 plus 48).

**Source-of-truth registration — required.** Both ports must be registered in `PortManager.PORT_MAPPING` in `bootstrapper/core/port_manager.py`:

```python
PORT_MAPPING = {
    # ... existing entries unchanged ...
    'OPENCLAW_BRIDGE_PORT': 25,
    'MINIO_PORT': 26,            # MinIO S3 API
    'MINIO_CONSOLE_PORT': 27,    # MinIO admin console
    'JUPYTERHUB_PORT': 48,
}
```

This is non-negotiable for `--base-port` to behave correctly. The bootstrapper's port-rewriting pipeline reads this dict from exactly two places:

- `PortManager.update_env_ports()` (`port_manager.py:129-179`) — runs on every `./start.sh` invocation; rewrites `MINIO_PORT=<base+26>` and `MINIO_CONSOLE_PORT=<base+27>` into `.env` so that `--base-port 64000` produces `MINIO_PORT=64026`, `MINIO_CONSOLE_PORT=64027`.
- The TUI wizard's `_recompute_ports` callback in `bootstrapper/ui/textual/integration.py:467` and `:571` — both read `port_offsets = PortManager.PORT_MAPPING` directly, so any entry added to the dict flows into the live wizard preview.

Both paths pick up new entries automatically; **no changes are required to `update_env_ports` or `_recompute_ports`** beyond adding the two dict entries. Verified by reading both call sites.

Also: `validate_base_port()` (`port_manager.py:63-73`) computes the upper bound from `max(self.PORT_MAPPING.values())`, currently `48` (JupyterHub). Adding offsets 26 and 27 does not change the upper bound, so the existing validator remains correct.

The literal defaults `63026` / `63027` shown in `.env.example` are just what the shipped file looks like at `BASE_PORT=63000`; the bootstrapper recomputes both on every run from the offset registration above.

### Healthcheck

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

`/minio/health/live` is MinIO's documented liveness endpoint. Implementation note: if `curl` is not present in the official `minio/minio` image, fall back to `mc ready local` (the `mc` binary ships in some MinIO images) or rewrite as a stdlib-Python probe in the LiteLLM style. Confirm `curl` presence during implementation and adjust if needed.

### Persistence

One named volume:

```yaml
volumes:
  minio-data:
    name: ${PROJECT_NAME}-minio-data
    driver: local
```

Mounted into the container at `/data`. Naming follows the stack convention. `./stop.sh --cold` removes it (consistent with all other named volumes).

### Restart policy & container naming

- `restart: unless-stopped`
- `container_name: ${PROJECT_NAME}-minio`
- No `deploy.resources` block. `deploy.replicas: ${MINIO_SCALE:-1}` follows the auto-managed scale pattern.

### Source variants

In `bootstrapper/service-configs.yml`:

```yaml
source_configurable:
  minio:
    container:
      scale: 1
      environment:
        MINIO_ENDPOINT: http://minio:9000
        MINIO_PUBLIC_ENDPOINT: http://localhost:${MINIO_PORT}
      deploy: {}
      extra_hosts: []
    disabled:
      scale: 0
      environment:
        MINIO_ENDPOINT: ""
        MINIO_PUBLIC_ENDPOINT: ""
      deploy: {}
      extra_hosts: []
```

Plus a `service_dependencies` entry: `minio: { requires: [], optional: [] }`.

`localhost` and `external` variants are deferred. No existing localhost-MinIO use case in the stack to validate against, and the ROADMAP frames MinIO as a leaf service with no upstream dependencies. The schema accepts new variants additively; future PRs can add them without churn.

---

## Bucket layout & service accounts — the public contract

Five pre-provisioned buckets, one per planned consumer. Five scoped service accounts, one per bucket. **Root credentials are never surfaced to consumers** — they exist for admin operations only.

| Bucket | Consumer | Service-account env prefix |
|---|---|---|
| `comfyui` | ComfyUI generated outputs | `MINIO_COMFYUI_*` |
| `backend` | Backend (FastAPI) large blobs / embeddings / checkpoints | `MINIO_BACKEND_*` |
| `n8n` | n8n workflow file I/O | `MINIO_N8N_*` |
| `jupyter` | JupyterHub datasets and model artifacts | `MINIO_JUPYTER_*` |
| `docling` | Doc Processor parsed-document persistence | `MINIO_DOCLING_*` |

Bucket names are the bare service identifier (no `-artifacts` / `-blobs` / `-files` / `-datasets` / `-output` suffix) — short, matches the service name 1:1, and reads cleanly in S3 URIs (`s3://backend/<key>` vs. `s3://backend-blobs/<key>`). Hand-edits to the `MINIO_BUCKET_*` vars in `.env` stick.

### Per-bucket IAM policy

Each service account is bound to an inline policy scoped to its bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": ["arn:aws:s3:::<bucket>/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": ["arn:aws:s3:::<bucket>"]
    }
  ]
}
```

A cross-bucket access attempt with a consumer credential returns 403. Verified explicitly in the verification plan.

---

## Init container — `minio-init`

A one-shot provisioning container using `minio/mc` as image.

```yaml
minio-init:
  image: ${MINIO_INIT_IMAGE}
  container_name: ${PROJECT_NAME}-minio-init
  restart: "no"
  depends_on:
    minio:
      condition: service_healthy
  environment:
    MINIO_ROOT_USER: ${MINIO_ROOT_USER}
    MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    MINIO_BUCKET_COMFYUI: ${MINIO_BUCKET_COMFYUI}
    MINIO_COMFYUI_ACCESS_KEY: ${MINIO_COMFYUI_ACCESS_KEY}
    MINIO_COMFYUI_SECRET_KEY: ${MINIO_COMFYUI_SECRET_KEY}
    # ... same pattern for BACKEND, N8N, JUPYTER, DOCLING
  volumes:
    - ./minio-init/scripts:/scripts:ro
  entrypoint: ["/bin/sh", "/scripts/init-minio.sh"]
  networks:
    - backend-network
```

### Provisioning script — `minio-init/scripts/init-minio.sh`

Idempotent on re-runs (every `./start.sh` re-runs it):

1. `mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"`
2. For each `<bucket>` in the contract: `mc mb --ignore-existing local/<bucket>` (no-op if exists).
3. For each consumer:
   - Render the inline policy JSON to a temp file with the bucket name substituted.
   - `mc admin policy create local <consumer>-policy /tmp/<consumer>-policy.json` — handle "already exists" gracefully (parse stderr; `mc admin policy update` if present, otherwise continue).
   - `mc admin user svcacct add local "$MINIO_ROOT_USER" --access-key="$ACCESS" --secret-key="$SECRET" --policy=/tmp/<consumer>-policy.json` — `mc admin user svcacct add` returns a recognizable error when the access key already exists; the script swallows that case.
4. `set -euo pipefail` at top; explicit per-step exit-code handling for the idempotent cases.

Logs go to stdout — visible via `docker logs ${PROJECT_NAME}-minio-init` and in the bootstrapper's streaming launch log.

---

## Key generation — bootstrapper integration

Extend `bootstrapper/utils/key_generator.py` (the same module that generates `LITELLM_MASTER_KEY` and Supabase JWT secrets). On every `./start.sh`:

| Variable | Generation rule | When |
|---|---|---|
| `MINIO_ROOT_USER` | not generated — defaults to `minioadmin` in `.env.example` | never |
| `MINIO_ROOT_PASSWORD` | 32-char URL-safe random (`secrets.token_urlsafe(24)`) | only if blank |
| `MINIO_<NAME>_ACCESS_KEY` (×5) | 20-char alphanumeric uppercase (matches MinIO's expected format) | only if blank |
| `MINIO_<NAME>_SECRET_KEY` (×5) | 40-char URL-safe random | only if blank |

The "only if blank" guard means hand-edits stick (consistent with how every existing key is handled). Persist by rewriting the relevant `.env` lines in-place — same mechanism `key_generator.py` already uses.

---

## `.env.example` block

Appended to the end of the data-services region:

```
# =============================================================================
# MinIO (S3-compatible object storage — artifact-tier complement to Supabase Storage)
# =============================================================================
MINIO_SOURCE=container                            # Options: container, disabled
MINIO_IMAGE=minio/minio:RELEASE.2025-10-15T17-29-55Z
MINIO_INIT_IMAGE=minio/mc:RELEASE.2025-08-13T08-35-41Z
MINIO_PORT=63026                                  # S3 API
MINIO_CONSOLE_PORT=63027                          # Admin console UI
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=                              # Auto-generated on first start
MINIO_REGION=us-east-1
MINIO_ENDPOINT=                                   # AUTO-MANAGED (internal, e.g. http://minio:9000)
MINIO_PUBLIC_ENDPOINT=                            # AUTO-MANAGED (host, e.g. http://localhost:63026)
MINIO_SCALE=1                                     # AUTO-MANAGED (0 when MINIO_SOURCE=disabled)

# Per-consumer bucket names + service-account credentials
MINIO_BUCKET_COMFYUI=comfyui
MINIO_COMFYUI_ACCESS_KEY=                         # Auto-generated on first start
MINIO_COMFYUI_SECRET_KEY=                         # Auto-generated on first start

MINIO_BUCKET_BACKEND=backend
MINIO_BACKEND_ACCESS_KEY=
MINIO_BACKEND_SECRET_KEY=

MINIO_BUCKET_N8N=n8n
MINIO_N8N_ACCESS_KEY=
MINIO_N8N_SECRET_KEY=

MINIO_BUCKET_JUPYTER=jupyter
MINIO_JUPYTER_ACCESS_KEY=
MINIO_JUPYTER_SECRET_KEY=

MINIO_BUCKET_DOCLING=docling
MINIO_DOCLING_ACCESS_KEY=
MINIO_DOCLING_SECRET_KEY=
```

---

## Bootstrapper changes

### `bootstrapper/service-configs.yml`

Add the `source_configurable.minio` block (shown in Architecture → Source variants above) and the `service_dependencies.minio` entry.

### `bootstrapper/services/service_config.py`

The generic engine over the `source_configurable.<service>.<variant>.environment` map already handles new entries. Confirm `MINIO_ENDPOINT`, `MINIO_PUBLIC_ENDPOINT`, and `MINIO_SCALE` are emitted from the new `environment` block; no special-case logic required.

### `bootstrapper/utils/key_generator.py`

Add the 11 MinIO-related key generations described in Key generation above.

### `bootstrapper/start.py`

Add Click flag:

```
--minio-source [container|disabled]
```

Default `container`. Wire through `SourceOverrideManager` identically to `--weaviate-source`. Add the corresponding entry to the help epilogue / flag-listing.

### `bootstrapper/ui/textual/screens/minio.py` (new)

Mirrors `weaviate.py` / `searxng.py`. Single-select between **container** and **disabled** with a description panel:

> **MinIO — artifact-tier object storage.** Provides S3-compatible storage for ComfyUI outputs, Backend blobs, n8n files, JupyterHub datasets, and Doc Processor output. Buckets and scoped service-account credentials are provisioned automatically. Consumer code is unchanged in this release — Supabase Storage remains the app-tier file surface; each consumer's artifact path is wired through MinIO in its own follow-up.

Insert in the screen sequence after `weaviate.py` and before `n8n.py` (data layer, not UI/workflow). Live-status panel shows S3 API endpoint and console URL.

### `bootstrapper/ui/state.py` + `state_builder.py`

Add `minio_source: str` to `AppState`. Plumb through CLI flag and TUI screen.

### `bootstrapper/ui/textual/screens/summary.py`

Add a MinIO row to the pre-launch summary table: endpoint, console URL, status.

---

## `docker-compose.yml` changes

Two new service blocks (`minio`, `minio-init`) appended to the data-services region. One new named volume `minio-data` in the top-level `volumes:` map. No changes to existing services.

```yaml
volumes:
  # ... existing entries ...
  minio-data:
    name: ${PROJECT_NAME}-minio-data
    driver: local

services:
  # ... existing entries ...

  minio:
    image: ${MINIO_IMAGE}
    container_name: ${PROJECT_NAME}-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
      MINIO_REGION: ${MINIO_REGION}
      MINIO_BROWSER_REDIRECT_URL: ${MINIO_PUBLIC_ENDPOINT}
    ports:
      - "${MINIO_PORT}:9000"
      - "${MINIO_CONSOLE_PORT}:9001"
    volumes:
      - minio-data:/data
    deploy:
      replicas: ${MINIO_SCALE:-1}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - backend-network

  minio-init:
    image: ${MINIO_INIT_IMAGE}
    container_name: ${PROJECT_NAME}-minio-init
    restart: "no"
    depends_on:
      minio:
        condition: service_healthy
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
      MINIO_BUCKET_COMFYUI: ${MINIO_BUCKET_COMFYUI}
      MINIO_COMFYUI_ACCESS_KEY: ${MINIO_COMFYUI_ACCESS_KEY}
      MINIO_COMFYUI_SECRET_KEY: ${MINIO_COMFYUI_SECRET_KEY}
      MINIO_BUCKET_BACKEND: ${MINIO_BUCKET_BACKEND}
      MINIO_BACKEND_ACCESS_KEY: ${MINIO_BACKEND_ACCESS_KEY}
      MINIO_BACKEND_SECRET_KEY: ${MINIO_BACKEND_SECRET_KEY}
      MINIO_BUCKET_N8N: ${MINIO_BUCKET_N8N}
      MINIO_N8N_ACCESS_KEY: ${MINIO_N8N_ACCESS_KEY}
      MINIO_N8N_SECRET_KEY: ${MINIO_N8N_SECRET_KEY}
      MINIO_BUCKET_JUPYTER: ${MINIO_BUCKET_JUPYTER}
      MINIO_JUPYTER_ACCESS_KEY: ${MINIO_JUPYTER_ACCESS_KEY}
      MINIO_JUPYTER_SECRET_KEY: ${MINIO_JUPYTER_SECRET_KEY}
      MINIO_BUCKET_DOCLING: ${MINIO_BUCKET_DOCLING}
      MINIO_DOCLING_ACCESS_KEY: ${MINIO_DOCLING_ACCESS_KEY}
      MINIO_DOCLING_SECRET_KEY: ${MINIO_DOCLING_SECRET_KEY}
    volumes:
      - ./minio-init/scripts:/scripts:ro
    entrypoint: ["/bin/sh", "/scripts/init-minio.sh"]
    networks:
      - backend-network
```

`MINIO_BROWSER_REDIRECT_URL` is set to the host-side public endpoint so console redirects (auth, signed-URL flows) point to a host URL the browser can resolve.

---

## New repo directory

```
minio-init/
└── scripts/
    └── init-minio.sh
```

Mirrors `comfyui-init/scripts/`, `n8n-init/scripts/`, `ollama-pull/scripts/`. Bind-mounted read-only into `minio-init`.

---

## Documentation surface

### New page — `docs/services/minio.md`

Follows the `docs/services/<name>.md` pattern (verified against `docs/services/supabase.md`). Sections:

1. **Overview** — what MinIO is, artifact-tier framing, explicit "complements Supabase Storage, does not replace it" boundary.
2. **Endpoints** — host (`http://localhost:63026` API, `http://localhost:63027` console) and internal (`http://minio:9000`).
3. **Default credentials** — `MINIO_ROOT_USER=minioadmin`; root password auto-generated to `.env` on first start; instructions to retrieve it and log into the console.
4. **Bucket layout** — table of the five pre-provisioned buckets and their intended consumers.
5. **Service accounts** — one per consumer, scoped via inline policy, env vars they are surfaced as.
6. **Consumer integration recipe** — a generic ~8-line Python snippet using `boto3` showing how a future consumer would construct an S3 client from the env vars (`endpoint_url=MINIO_ENDPOINT`, `aws_access_key_id=MINIO_<NAME>_ACCESS_KEY`, `aws_secret_access_key=MINIO_<NAME>_SECRET_KEY`, `config=Config(s3={"addressing_style": "path"})`, `region_name=MINIO_REGION`). Plus a parallel `mc` snippet for shell.
7. **Source variants** — `container`, `disabled`; rationale for not shipping `localhost` / `external` yet.
8. **Data persistence** — `minio-data` named volume; `./stop.sh --cold` wipes it.
9. **Operations** — how to add a bucket manually (`mc mb local/<name>`), how to rotate a service-account key (`mc admin user svcacct rm` + re-run `minio-init`), where logs go.
10. **Troubleshooting** — common pitfalls (path-style addressing required for MinIO; CORS for browser clients; clock skew between client and server; service-account access denied → check policy scope; restart loop → check `MINIO_ROOT_PASSWORD` not empty).

### `README.md` updates

The root README has multiple service tables. Audit during implementation and add MinIO consistently to:

- The services-list section (one-line description + the artifact-tier positioning).
- Any port-allocation table that lists the `630xx` sequence (add `63026` and `63027`).
- The "what's included" / architecture overview section if present.

### `docs/ROADMAP.md` update

Move the MinIO entry from **Tier 2: planned candidates** (lines 165–181) to **Completed**, restructured to match the format of the existing Completed entries (LiteLLM gateway, LangMem, JupyterHub). Preserve the consumer list as "intended consumers; per-consumer wiring to follow in dedicated PRs."

### `docs/CHANGELOG.md` entry

Add a new bullet under `[Unreleased] → Added`:

> **MinIO object storage**: S3-compatible artifact-tier storage service with five pre-provisioned buckets (ComfyUI / Backend / n8n / JupyterHub / Doc Processor) and scoped service-account credentials. Admin console at `http://localhost:63027`. Consumer code is unchanged in this release; each consumer integration ships in a dedicated follow-up.

Remove the corresponding "ROADMAP additions" Unreleased bullet (line 9) for MinIO since it is no longer a future plan; replace with the Added entry above.

---

## Files touched

**New:**
- `docs/superpowers/specs/2026-05-12-minio-service-design.md` (this file)
- `docs/services/minio.md`
- `minio-init/scripts/init-minio.sh`
- `bootstrapper/ui/textual/screens/minio.py`

**Modified:**
- `docker-compose.yml` (append `minio` and `minio-init` services + `minio-data` volume)
- `.env.example` (append MinIO block)
- `bootstrapper/service-configs.yml` (add `source_configurable.minio` + `service_dependencies.minio`)
- `bootstrapper/core/port_manager.py` (register `MINIO_PORT=26` and `MINIO_CONSOLE_PORT=27` in `PortManager.PORT_MAPPING` — required for `--base-port` recomputation)
- `bootstrapper/utils/key_generator.py` (generate `MINIO_ROOT_PASSWORD` + 10 per-consumer keys)
- `bootstrapper/start.py` (add `--minio-source` Click flag)
- `bootstrapper/ui/state.py` (add `minio_source` field)
- `bootstrapper/ui/state_builder.py` (plumb the new field)
- `bootstrapper/ui/textual/integration.py` (register new screen in sequence)
- `bootstrapper/ui/textual/screens/summary.py` (add MinIO row to launch summary)
- `README.md` (service list + port table + overview)
- `docs/ROADMAP.md` (move MinIO entry from Tier 2 to Completed)
- `docs/CHANGELOG.md` (replace Unreleased roadmap-addition bullet with Added entry)

**Reused — do not duplicate:**
- `bootstrapper/utils/key_generator.py` — existing key-generation framework (matches `LITELLM_MASTER_KEY` pattern).
- `bootstrapper/services/service_config.py` — generic engine over the `source_configurable.<service>.<variant>.environment` map already handles the new entry.
- `bootstrapper/core/port_manager.py` — `update_env_ports()` and `calculate_port_assignments()` automatically pick up new `PORT_MAPPING` entries; the TUI wizard's `_recompute_ports` (`integration.py:467, 571`) reads the same dict. No call-site changes needed.
- `bootstrapper/utils/source_override_manager.py` — already handles arbitrary SOURCE flags from CLI.
- Init-container pattern from `comfyui-init/`, `n8n-init/`, `ollama-pull/`.

---

## Extensibility — what this design enables

The design closes with explicit hooks for downstream work, none of which is in scope for this PR:

- **Per-consumer wiring.** Each of the five consumers can adopt MinIO via env-only changes in its own follow-up; credentials and bucket names are already in `.env` from the moment this PR lands.
- **Weaviate S3 backup.** Weaviate's `backup-s3` module reads `BACKUP_S3_BUCKET`, `BACKUP_S3_ENDPOINT`, `BACKUP_S3_ACCESS_KEY_ID`, `BACKUP_S3_SECRET_ACCESS_KEY`. Adding it is one new bucket in `minio-init` (`weaviate-backups`), one new service account, and an env update on the Weaviate service.
- **Supabase Storage S3 backend (out of scope, possible).** The ROADMAP positions MinIO as a complement, not a replacement. The technical path remains reachable: flip `STORAGE_BACKEND=s3`, add `AWS_S3_ENDPOINT`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `GLOBAL_S3_BUCKET`, `AWS_S3_FORCE_PATH_STYLE=true` to `supabase-storage`'s env, and add a dedicated bucket + service account. Documented here so the path is known; not recommended without an explicit redesign discussion.
- **Postgres dumps to S3**, **Ollama model cache to S3**, **JupyterHub dataset persistence**, **n8n S3 trigger nodes** — each is a single bucket + single service account + a small consumer-side env change.
- **Modularization migration.** When the per-service refactor lands, MinIO carves out cleanly into `services/minio/{service.yml,compose.yml}`. The public env contract (`MINIO_BUCKET_*`, `MINIO_<NAME>_ACCESS_KEY`, `MINIO_<NAME>_SECRET_KEY`, `MINIO_ENDPOINT`) stays identical, so any consumers adopted before the migration are unaffected.

---

## Verification

Run from the repo root after implementation:

1. **Fresh start, default selections.**
   ```sh
   ./stop.sh --cold
   ./start.sh --minio-source container
   ```
   Expected: `genai-minio` and `genai-minio-init` appear in `docker ps`; `minio-init` exits with code 0; `.env` now contains a non-empty `MINIO_ROOT_PASSWORD` and ten non-empty per-consumer keys.

2. **Console reachability.** Browse `http://localhost:63027`, log in with `minioadmin` / the `.env` `MINIO_ROOT_PASSWORD`. Confirm five buckets visible. Under Identity → Service Accounts confirm five accounts, each with the expected scoped policy attached.

3. **S3 API smoke test from host.**
   ```sh
   mc alias set local http://localhost:63026 minioadmin "$MINIO_ROOT_PASSWORD"
   mc ls local/
   ```
   Expected: five buckets listed (`comfyui`, `backend`, `n8n`, `jupyter`, `docling`).

4. **Per-consumer credential & IAM scoping smoke test.** With `MINIO_BACKEND_ACCESS_KEY` / `MINIO_BACKEND_SECRET_KEY`:
   ```sh
   mc alias set backend-test http://localhost:63026 "$MINIO_BACKEND_ACCESS_KEY" "$MINIO_BACKEND_SECRET_KEY"
   echo hello | mc pipe backend-test/backend/test.txt    # succeeds
   echo hello | mc pipe backend-test/comfyui/test.txt    # FAILS with 403 AccessDenied
   ```
   Confirms IAM scoping works end-to-end.

5. **Source-variant flip.**
   ```sh
   ./start.sh --minio-source disabled
   ```
   Expected: `minio` container exits and is not scheduled (`replicas: 0`); `minio-init` is skipped (depends on healthy minio). Other services unaffected (no consumers in this PR).

6. **Idempotence on re-run.** Re-run `./start.sh --minio-source container` against an existing `minio-data` volume. `minio-init` re-runs and exits 0 — no errors from `mc mb --ignore-existing`, no duplicate-svcacct errors.

7. **Bootstrapper-level checks.**
   - `./start.sh --help` lists `--minio-source` with the two choices.
   - Running `./start.sh` with no flags renders the MinIO wizard screen between Weaviate and n8n.
   - The launch-summary screen shows MinIO endpoints and selected source.

8. **Cold-start data wipe.**
   ```sh
   ./stop.sh --cold
   docker volume ls | grep minio    # empty
   ./start.sh --minio-source container
   ```
   Expected: `genai-minio-data` is recreated; all five buckets re-provision; new credentials are emitted to `.env` only if the variables were blanked.

9. **Cross-runtime check.** Repeat verification 1 with Podman. Confirm healthcheck passes and the host-exposed ports are reachable under the runtime-specific `HOST_GATEWAY_IP` handling.

10. **Hand-edit stickiness.** Manually edit `MINIO_BUCKET_BACKEND=my-custom-bucket` in `.env`, re-run `./start.sh`. Expected: `my-custom-bucket` is created (not `backend`); `key_generator.py` does not overwrite the hand edit.

11. **Base-port recomputation.** Run:
    ```sh
    ./stop.sh --cold
    ./start.sh --base-port 64000 --minio-source container
    grep -E '^MINIO_(CONSOLE_)?PORT=' .env
    ```
    Expected: `MINIO_PORT=64026` and `MINIO_CONSOLE_PORT=64027` in `.env`; the `minio` container's host port maps are `64026:9000` and `64027:9001`; the TUI wizard's live preview (when run interactively with `--base-port 64000`) shows the same recomputed values. Confirms the offsets registered in `PortManager.PORT_MAPPING` are picked up by both the `.env`-rewrite path and the TUI preview path.

---

## Out of scope

Explicitly not in this PR; called out so reviewers don't expect them:

- Any consumer code change (ComfyUI, Backend, n8n, JupyterHub, Doc Processor stay on their current storage paths).
- Weaviate backup wiring.
- Supabase Storage S3-backend mode.
- MinIO `localhost` and `external` source variants.
- Kong route for MinIO.
- TLS / HTTPS for MinIO (the stack runs internally on HTTP; TLS is a stack-wide concern).
- Multi-node / distributed MinIO deployments.
- Per-service-modularization refactor of MinIO into `services/minio/` (deferred until the broader refactor lands).
