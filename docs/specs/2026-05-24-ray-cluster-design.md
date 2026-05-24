# Design — Add Ray distributed-compute cluster to the stack

**Status:** awaiting user review (brainstorm phase complete)
**Author:** Kaveh + Claude (brainstorm session 2026-05-24)
**Scope:** add `services/ray/` as a new container family + minimum-viable client integration in Backend and JupyterHub. Defers Ray Serve LLM, Hermes tool catalog entry, and multi-host Ray clusters.

---

## 1. Problem

The roadmap's "vertical-scenario tracks" all need the same primitive: take N independent units of work and execute them in parallel across CPUs/GPUs. Trading needs parameter sweeps for backtests, 3D needs batch mesh-candidate generation and rendering, RAG needs embedding pipelines across large corpora, data-engineering needs batch ML training. Today there is no shared compute substrate in the stack — each track would roll its own parallelism, leading to inconsistent patterns and wasted effort. Without Ray, every "I have N jobs, run them" workflow either runs serially or builds bespoke `asyncio.gather` glue per service.

Ray fills this gap as a generic distributed-compute substrate. On a single-GPU Mac dev box where Docker has no GPU passthrough, Ray's raw throughput win is modest, but it still earns its keep via orchestration polish (pipeline chaining, retries, result aggregation, checkpointing) and ensures batch pipelines don't need rewriting when scaled onto multi-GPU Linux hosts.

## 2. Non-goals

- **Not** integrating Ray Serve LLM (OpenAI-compatible inference on Ray) — separate spec when GPU host is available.
- **Not** adding a Ray-submit-job tool to Hermes's catalog — Hermes-driven agents reach Ray via the Backend REST API documented here; the tool-catalog entry is a Hermes-side concern.
- **Not** multi-host Ray clusters — single Docker host only. Multi-host requires manual cluster config and is out of scope.
- **Not** Ray Tune / Ray Train hyperparameter frontends — those are pure Python library work that doesn't require new infrastructure.
- **Not** ARM64 image variants — Ray's amd64 image is the canonical published artifact as of May 2026; arm64 is nightly-only.
- **Not** dynamic worker autoscaling — autoscaling is a Kubernetes-only feature (KubeRay). Compose users get a fixed `RAY_WORKER_COUNT`.

## 3. Pre-flight facts (verified from upstream)

| Question | Answer | Source |
|---|---|---|
| Image | `rayproject/ray:2.55.1` (CPU) + `rayproject/ray:2.55.1-gpu` (GPU) | hub.docker.com/r/rayproject/ray |
| License | Apache 2.0 ✓ | github.com/ray-project/ray |
| In-container ports | 8265 (dashboard + REST job-submission API), 6379 (GCS — Ray's internal cluster controller, distinct from our Redis cache container), 10001 (Ray client server) | docs.ray.io |
| External runtime deps | None. Ray ships its own GCS / Plasma object store. Stateless. | docs.ray.io |
| Healthcheck endpoint | Not officially documented. Use `curl -f http://localhost:8265/api/version` (200 once GCS is up). | docs.ray.io |
| Compose gotcha | `shm_size: 4gb` REQUIRED — Docker default 64MB causes immediate startup crash | oneuptime.com docker compose guide |
| Multi-arch | amd64 primary; arm64 is nightly-only as of May 2026 | github.com/ray-project/ray issues |
| Cluster topology | Head + N workers; workers find head via `--address=ray-head:6379` | docs.ray.io |
| Anyscale (managed cloud) | Exists; `external` source pointing at `ray://<anyscale-host>:10001` is sensible | anyscale.com |
| Worker scaling | Compose: fixed at compose time. Autoscaling is K8s-only. | docs.ray.io |
| Default dashboard auth | Unauthenticated. Front via Kong basic-auth (existing pattern). | docs.ray.io |
| Python client | `pip install ray` (current 2.55.1) | pypi.org/project/ray |

## 4. The six decisions (per runbook)

| # | Decision | Answer |
|---|---|---|
| 1 | Folder flavor | container — multi-container family (`ray-head` + `ray-worker`) |
| 2 | Category | `infra` — Ray is substrate plumbing for every tier (parallel to Kong's role as gateway substrate), not a workflow tool. |
| 3 | Source variants | `ray-container-cpu`, `ray-container-gpu`, `ray-external`, `disabled`. Default `disabled`. |
| 4 | Port allocation | Three contiguous slots in `infra` block (currently 2/10 used → 5/10 after Ray). Auto-assigned: `RAY_DASHBOARD_PORT`, `RAY_GCS_PORT`, `RAY_CLIENT_PORT`. |
| 5 | Dependencies | `required: []`, `optional: []`. Ray is genuinely standalone. |
| 6 | Adaptive / hooks | **Minimal hook required** — `_generate_ray_config()` in `bootstrapper/services/service_config.py` resolves three derived env vars from `RAY_SOURCE` + `RAY_WORKER_COUNT`: `RAY_IMAGE` (CPU vs GPU image), `RAY_WORKER_SCALE` (= `RAY_WORKER_COUNT` for container sources, `0` otherwise), and `RAY_ADDRESS` (= `ray://ray-head:10001` for container, `${RAY_EXTERNAL_ADDRESS}` for external, empty for disabled). Backend + JupyterHub get `runtime_adaptive.adapts_to: [ray]` on their manifests so `RAY_ADDRESS` flows into them. |

## 5. Service manifest shape

### `services/ray/service.yml`

```yaml
name: ray
label: "Ray (distributed compute substrate)"
category: infra
docs: services/ray/README.md

containers:
  - ray-head
  - ray-worker

images:
  - var: RAY_IMAGE
    default: "rayproject/ray:2.55.1"
    container: ray-head
    notes: "CPU build. Same image used for both head and CPU workers."
  - var: RAY_GPU_IMAGE
    default: "rayproject/ray:2.55.1-gpu"
    container: ray-head
    notes: "GPU build with CUDA runtime. Selected by ray-container-gpu source."

sources:
  var: RAY_SOURCE
  default: disabled
  options:
    - id: ray-container-cpu
      label: "Container (CPU)"
    - id: ray-container-gpu
      label: "Container (GPU, NVIDIA)"
    - id: ray-external
      label: "External (Anyscale or custom cluster URL)"
      requires: [RAY_EXTERNAL_ADDRESS]
    - id: disabled
      label: "Disabled"

env:
  - name: RAY_SOURCE
    default: disabled
  - name: RAY_DASHBOARD_PORT
    # default removed — computed by services/topology.py slot allocator
    description: "Host port for the Ray dashboard + REST job-submission API (in-container 8265)."
  - name: RAY_GCS_PORT
    # default removed — computed by services/topology.py slot allocator
    description: "Host port for the Ray GCS (in-container 6379). Distinct from the project's Redis cache container; Ray bundles its own GCS process."
  - name: RAY_CLIENT_PORT
    # default removed — computed by services/topology.py slot allocator
    description: "Host port for the Ray client server (in-container 10001). Used by host Python: `ray.init('ray://localhost:<port>')`."
  - name: RAY_WORKER_COUNT
    default: 2
    description: "Number of ray-worker replicas. The wizard prompts for this with default 2. Valid values: 0 (head-only mode) and up. No hard upper bound — bounded by host resources."
  - name: RAY_EXTERNAL_ADDRESS
    default: ""
    description: "Required when RAY_SOURCE=ray-external. Format: `ray://hostname:10001` (Anyscale or custom Ray cluster URL)."
  - name: RAY_HEAD_SCALE
    auto_managed: true
  - name: RAY_WORKER_SCALE
    auto_managed: true
    description: "Resolved by the bootstrapper from RAY_WORKER_COUNT when source is ray-container-{cpu,gpu}; 0 otherwise."
  - name: RAY_ADDRESS
    auto_managed: true
    description: "Resolved per source: `ray://ray-head:10001` for container sources, `${RAY_EXTERNAL_ADDRESS}` for external, empty for disabled. Consumed by Backend / JupyterHub via runtime_adaptive."

depends_on:
  required: []
  optional: []

exports: []

rows:
  - display_name: "Ray"
    source_var: RAY_SOURCE
    port_var: RAY_DASHBOARD_PORT
    scale_var: RAY_HEAD_SCALE
    alias: ray.localhost
    description: "Distributed-compute substrate (cluster controller + workers)."

runtime_sc:
  # Note: scale values here are bootstrapper-display defaults. Actual
  # compose replicas are driven by ${RAY_HEAD_SCALE} / ${RAY_WORKER_SCALE}
  # in compose.yml, which the _generate_ray_config() hook writes to .env
  # based on RAY_SOURCE + RAY_WORKER_COUNT. Same pattern for the image:
  # compose.yml says `image: ${RAY_IMAGE}` and the hook sets RAY_IMAGE
  # to the CPU or GPU image tag based on source.
  ray-head:
    ray-container-cpu:
      scale: 1
      environment: {}
      deploy: {}
      extra_hosts: []
    ray-container-gpu:
      scale: 1
      environment:
        NVIDIA_VISIBLE_DEVICES: ${NVIDIA_VISIBLE_DEVICES:-all}
      deploy:
        resources:
          reservations:
            devices:
              - driver: nvidia
                count: 1
                capabilities: [gpu]
      extra_hosts: []
    ray-external:
      scale: 0
      environment: {}
      deploy: {}
      extra_hosts: []
    disabled:
      scale: 0
      environment: {}
      deploy: {}
      extra_hosts: []
  ray-worker:
    ray-container-cpu:
      scale: 1
      environment: {}
      deploy: {}
      extra_hosts: []
    ray-container-gpu:
      scale: 1
      environment:
        NVIDIA_VISIBLE_DEVICES: ${NVIDIA_VISIBLE_DEVICES:-all}
      deploy:
        resources:
          reservations:
            devices:
              - driver: nvidia
                count: 1
                capabilities: [gpu]
      extra_hosts: []
    ray-external:
      scale: 0
      environment: {}
      deploy: {}
      extra_hosts: []
    disabled:
      scale: 0
      environment: {}
      deploy: {}
      extra_hosts: []

data_flow:
  calls: []
```

### `services/ray/compose.yml`

```yaml
# services/ray/compose.yml — Ray distributed-compute cluster (head + workers)
services:
  ray-head:
    image: ${RAY_IMAGE:-rayproject/ray:2.55.1}
    container_name: ${PROJECT_NAME}-ray-head
    hostname: ray-head
    restart: unless-stopped
    deploy:
      replicas: ${RAY_HEAD_SCALE:-0}
    shm_size: 4gb
    command:
      - bash
      - -c
      - |
        ray start --head \
          --dashboard-host 0.0.0.0 \
          --port 6379 \
          --ray-client-server-port 10001 \
          --dashboard-port 8265 \
          --block
    ports:
      - "${RAY_DASHBOARD_PORT}:8265"
      - "${RAY_GCS_PORT}:6379"
      - "${RAY_CLIENT_PORT}:10001"
    volumes:
      - ray-tmp:/tmp/ray
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8265/api/version || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    networks:
      - backend-network

  ray-worker:
    image: ${RAY_IMAGE:-rayproject/ray:2.55.1}
    restart: unless-stopped
    deploy:
      replicas: ${RAY_WORKER_SCALE:-0}
    shm_size: 4gb
    command:
      - bash
      - -c
      - |
        ray start --address=ray-head:6379 --block
    depends_on:
      ray-head:
        condition: service_healthy
    volumes:
      - ray-tmp-worker:/tmp/ray
    networks:
      - backend-network

volumes:
  ray-tmp:
    name: ${PROJECT_NAME}-ray-tmp
    driver: local
  ray-tmp-worker:
    name: ${PROJECT_NAME}-ray-tmp-worker
    driver: local
```

**Note on the GPU image variant:** The compose `image: ${RAY_IMAGE}` is resolved at compose-merge time from `.env`. The new `_generate_ray_config()` hook in `bootstrapper/services/service_config.py` (Decision 6) writes the correct value to `.env` per source:

- `RAY_SOURCE=ray-container-cpu` → `RAY_IMAGE=rayproject/ray:2.55.1` (CPU image, from `RAY_IMAGE`'s manifest default)
- `RAY_SOURCE=ray-container-gpu` → `RAY_IMAGE=rayproject/ray:2.55.1-gpu` (GPU image, from `RAY_GPU_IMAGE`'s manifest default)
- `RAY_SOURCE=ray-external` / `disabled` → `RAY_IMAGE` left at CPU default (containers are scale=0, image value is irrelevant)

The same hook also resolves `RAY_WORKER_SCALE` (= `RAY_WORKER_COUNT` when source is container-*, else `0`) and `RAY_ADDRESS` (= `ray://ray-head:10001` for container, `${RAY_EXTERNAL_ADDRESS}` for external, empty for disabled).

## 6. Wizard integration

When the user is prompted for `RAY_SOURCE`:

- Standard tile prompt: `ray-container-cpu`, `ray-container-gpu`, `ray-external`, `disabled` (default `disabled`).
- Per-tile badges: `CPU` / `GPU` / `external` / `disabled` — automatically derived from option-name patterns by the existing `_badges_for_option()` helper.

When the user picks `ray-container-cpu` or `ray-container-gpu`, the wizard then prompts:

- **Integer prompt for `RAY_WORKER_COUNT`** (default `2`, min `0`, no max).
- Hint text: "Number of Ray worker containers. 0 = head-only single-node cluster. Defaults to 2."

When the user picks `ray-external`:

- Wizard prompts for `RAY_EXTERNAL_ADDRESS` (secret-input style — though it's not a secret, it's free-form text). Sample placeholder: `ray://my-cluster.anyscale.com:10001`.

The existing integer-prompt step type (`BASE_PORT` already uses it) is reused. No new widget needed.

## 7. Kong route + hosts entry

- Add to `bootstrapper/utils/hosts_manager.py::GENAI_HOSTS`: `ray.localhost`.
- Add to `bootstrapper/utils/kong_config_generator.py`: a new route for `ray.localhost` → `http://ray-head:8265/` with:
  - `preserve_host: True` (browser SPA — Ray dashboard emits HTML)
  - `basic-auth` plugin using existing `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD` (same credentials as LiteLLM + Hermes + MinIO console)
- Add to `scripts/check-kong-routes.py::EXPECTED_HOST_ROUTES`: `"ray.localhost": "http://ray-head:8265"` — only checked when Ray is enabled-by-default (it isn't, default is `disabled`), but adding the entry is forward-compatible.

## 8. Backend REST surface

### `services/backend/app/app/ray_client.py`

A lazy singleton that wraps Ray's `JobSubmissionClient`. Connects via `RAY_ADDRESS` env var. Safely no-ops when Ray is disabled (returns a `RayDisabledError` from any method).

```python
"""Lazy Ray-cluster client for the Backend.

The Backend reaches the Ray cluster via Ray's REST job-submission API
(NOT via ray.init() — that would pin the FastAPI worker process to the
Ray cluster lifecycle, which causes issues on reloads). Job submission
+ status polling go through a REST client that's cheap to create.

When Ray is disabled (RAY_ADDRESS is empty), every method raises
RayDisabledError. The router translates that into a 503 with a clear
message rather than a 500.
"""

import os
from typing import Optional

from fastapi import HTTPException


class RayDisabledError(Exception):
    """Raised by RayClient methods when Ray is not configured."""


def _ray_address() -> Optional[str]:
    """Return the cluster dashboard URL the JobSubmissionClient needs.

    RAY_ADDRESS is the env var the manifest sets — it's the `ray://` URL
    for direct client connection. For the JobSubmissionClient we need
    the HTTP dashboard URL — derive it from the cluster head hostname.
    """
    ray_addr = os.environ.get("RAY_ADDRESS", "").strip()
    if not ray_addr:
        return None
    # ray://ray-head:10001 → http://ray-head:8265
    # ray://anyscale.example.com:10001 → https://anyscale.example.com:8265
    # (external HTTPS-by-default for Anyscale; configurable via RAY_DASHBOARD_URL override)
    explicit_dashboard = os.environ.get("RAY_DASHBOARD_URL", "").strip()
    if explicit_dashboard:
        return explicit_dashboard
    if ray_addr.startswith("ray://"):
        host = ray_addr[len("ray://"):].rsplit(":", 1)[0]
        scheme = "https" if "." in host else "http"  # heuristic: bare hostname = LAN
        return f"{scheme}://{host}:8265"
    return None


class RayClient:
    _instance: Optional["RayClient"] = None

    @classmethod
    def get(cls) -> "RayClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._addr = _ray_address()
        self._client = None

    def _ensure_client(self):
        if self._addr is None:
            raise RayDisabledError("RAY_ADDRESS not set — Ray cluster is disabled")
        if self._client is None:
            from ray.job_submission import JobSubmissionClient
            self._client = JobSubmissionClient(self._addr)
        return self._client

    def submit_job(self, entrypoint: str, runtime_env: dict | None = None, metadata: dict | None = None) -> str:
        return self._ensure_client().submit_job(
            entrypoint=entrypoint, runtime_env=runtime_env or {}, metadata=metadata or {}
        )

    def get_job_status(self, job_id: str) -> dict:
        client = self._ensure_client()
        return {
            "job_id": job_id,
            "status": client.get_job_status(job_id).value,
            "info": client.get_job_info(job_id).__dict__,
        }

    def get_job_logs(self, job_id: str) -> str:
        return self._ensure_client().get_job_logs(job_id)

    def stop_job(self, job_id: str) -> bool:
        return self._ensure_client().stop_job(job_id)

    def cluster_status(self) -> dict:
        # Hits the dashboard's /api/cluster_status (no auth required from inside
        # backend-network — Kong basic-auth only protects host-facing access).
        import urllib.request, json
        addr = self._ensure_client() and self._addr
        with urllib.request.urlopen(f"{addr}/api/cluster_status", timeout=5) as resp:
            return json.loads(resp.read())
```

### `services/backend/app/app/ray_routes.py`

A FastAPI router mounted at `/api/ray/` from `main.py`. Four endpoints:

- `POST /api/ray/jobs/submit` — accepts `{"entrypoint": str, "runtime_env"?: dict, "metadata"?: dict}`; returns `{"job_id": str}`. Uses Backend's existing auth.
- `GET /api/ray/jobs/{job_id}` — status + info + logs.
- `DELETE /api/ray/jobs/{job_id}` — stops the job.
- `GET /api/ray/cluster/status` — cluster status.

All endpoints handle `RayDisabledError` → HTTP 503 with `{"error": "Ray is not enabled in this deployment"}`.

### Tests under `services/backend/app/app/tests/`

This is Backend's first real test directory (audit P1 — Backend has no test files today). Adding:

- `tests/__init__.py`
- `tests/conftest.py` — common fixtures including a `ray_disabled_env` fixture and a `ray_mock_client` fixture using monkeypatch.
- `tests/test_ray_client.py` — RayClient with `RAY_ADDRESS=""` raises `RayDisabledError`; RayClient with mock JobSubmissionClient submits jobs.
- `tests/test_ray_routes.py` — endpoint smoke tests with mocked client (no real Ray cluster needed): submit returns job_id, status returns 503 when disabled, etc.

Adding pytest to Backend's requirements (it's already there from the audit findings — confirm and use). Tests run via `cd services/backend/app/app && python -m pytest tests/`.

CI: extend `.github/workflows/services-lint.yml`'s lint job to also run Backend's tests (or document as a follow-up if too invasive — Backend doesn't have a venv setup in CI today).

### `services/backend/app/app/requirements.txt`

Add: `ray>=2.55.1` (matches the image's Ray version — Ray client/server versions must match).

### `services/backend/service.yml`

Add to `runtime_adaptive.backend`:
- `adapts_to:` extend the existing list with `- ray`
- `environment_adaptation:` extend with `RAY_ADDRESS: ${RAY_ADDRESS}`

Update `data_flow.calls:` to add `- ray`.

## 9. JupyterHub wiring

### `services/jupyterhub/build/requirements.txt`

Add `ray>=2.55.1`.

### `services/jupyterhub/service.yml`

Add to `runtime_adaptive.jupyterhub`:
- `adapts_to:` extend with `- ray`
- `environment_adaptation:` extend with `RAY_ADDRESS: ${RAY_ADDRESS}`

Update `data_flow.calls:` to add `- ray`.

### Seed notebook

Add `services/jupyterhub/notebooks/hello-ray.ipynb` — a minimal sample:

```python
import ray
ray.init(address="auto")  # uses RAY_ADDRESS automatically
print(ray.cluster_resources())

@ray.remote
def double(x):
    return x * 2

result = ray.get([double.remote(i) for i in range(10)])
print(result)
```

Documented in `services/jupyterhub/README.md` as the canonical "Ray-from-Jupyter" recipe.

## 10. Hermes manifest update (no code)

`services/hermes/service.yml`:
- `data_flow.calls:` add `- ray` and `- backend`

That's it. Hermes-agent-side tool-catalog entry to actually call Backend's `/api/ray/jobs/submit` is documented as a follow-up in the Hermes README, but not implemented this round (it's a Hermes-side task, not Ray-side).

## 11. Topology + port allocation

`bootstrapper/services/topology.py::CATEGORY_SLOTS` requires NO change — Ray fits in the existing `infra` block (0, 10).

Resulting port assignments after `env_assembler` runs:
- Existing infra: `KONG_HTTP_PORT=63000`, `KONG_HTTPS_PORT=63001`, plus globals (none in infra block beyond Kong).
- New: `RAY_DASHBOARD_PORT=63002`, `RAY_GCS_PORT=63003`, `RAY_CLIENT_PORT=63004` (or whatever the slot allocator emits — exact numbers determined at regen time).

## 12. Audit-script + CI implications

- `scripts/check-compose-source-deps.py`: no additions (Ray has no compose-level `depends_on` edges to validate beyond `ray-worker → ray-head`).
- `scripts/check-kong-routes.py`: add `ray.localhost` entry to `EXPECTED_HOST_ROUTES` (when source is enabled-by-default — Ray defaults to disabled, so this entry is conditional; the right pattern is to add the entry but skip it via the source-defaults check the script already does).
- `.github/dependabot.yml`: no new `directories:` entries — Backend's existing `services/backend/app/app` and JupyterHub's existing `services/jupyterhub/build` entries cover the new `ray>=2.55.1` dependency.

## 13. README.md TOPOLOGY block

Regenerated by `bootstrapper/tools/generate_readme_topology.py`. Will auto-include:

```
| Infrastructure | Ray | 63002 | ray.localhost |
```

## 14. Architecture diagram

`docs/diagrams/architecture.dot` regenerated to include the Ray cluster as a new `infra`-cluster node. No edges from Ray to other services (it's standalone); edges INTO Ray from Backend, JupyterHub, Hermes via their `data_flow.calls` entries.

## 15. Per-service docs

`services/ray/{README.md, architecture.svg, architecture.html}` auto-generated by `bootstrapper.docs.regen ray`. The README is largely templated; we hand-author the body (Overview, Access, Configuration, Architecture & wiring, Dependencies & Integrations [auto], Troubleshooting) with Ray-specific content:

- Overview: "Ray cluster as the stack's distributed-compute substrate. Use it from JupyterHub for batch compute or from Backend's REST API for job submission from other services."
- Access: dashboard at `ray.localhost` (basic-auth), client at `:RAY_CLIENT_PORT`, REST submission at Backend `/api/ray/`.
- Configuration: source-variant table, `RAY_WORKER_COUNT` description, GPU mode prereqs.
- Architecture & wiring: head + N workers, GCS port distinct from project Redis, no external deps.
- Dependencies & Integrations: auto-generated.
- Troubleshooting: top hits — `shm_size` insufficient → crash on startup, dashboard timeout → wait 60s (start_period), `ray.init()` from host using `ray://localhost:PORT` formatting, version-mismatch errors between client and server.

## 16. Risks + mitigations

| Risk | Mitigation |
|------|------------|
| `shm_size: 4gb` may not be honored on some Docker installs | Document in service README + startup healthcheck catches a crashed container |
| Ray dashboard unauthenticated by default → Kong basic-auth is the gate | Document direct-port access bypasses auth; recommend not exposing host ports in production |
| `RAY_WORKER_COUNT=0` head-only mode breaks worker-required code paths | Document head-only mode is supported; tests cover it |
| Resource contention on dev Macs (Docker often allocated 8GB) | README "minimum requirements" note: 12GB Docker memory recommended with Ray enabled at default worker count |
| Ray Python client version drift between Backend/JupyterHub and the cluster image | Pin both to `ray>=2.55.1,<2.56` in requirements; image pinned to `2.55.1` |
| Compose-equivalence golden baseline will fail on first run after Ray added | Acceptable — regenerate baseline once after adding Ray (memory note `project_compose_baseline_test`) |
| Backend's first test files run in CI | Lint workflow must learn how to run Backend tests; if too invasive, document as Phase-2 follow-up |
| Ray's GCS uses Redis wire protocol on port 6379 — confusion with the project's Redis container | Manifest comments + README explicitly call out the distinction. `RAY_GCS_PORT` env var name avoids "REDIS" naming. |
| `ray-worker` `depends_on: ray-head: service_healthy` adds a 60s start_period | Acceptable — workers can wait; users see "starting" log lines |

## 17. Acceptance criteria

1. `./start.sh --ray-source ray-container-cpu --ray-worker-count 3` brings up `ray-head` (healthy in <90s) + 3 `ray-worker` replicas.
2. Dashboard at `http://localhost:<RAY_DASHBOARD_PORT>` reachable directly (and via `http://ray.localhost:<KONG_HTTP_PORT>` with basic-auth using `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD`).
3. From host Python: `ray.init("ray://localhost:<RAY_CLIENT_PORT>")` connects and `ray.cluster_resources()` returns CPU + worker count.
4. From JupyterHub notebook: opening `hello-ray.ipynb` and running all cells succeeds end-to-end.
5. `curl -X POST http://localhost:<BACKEND_PORT>/api/ray/jobs/submit -H "Authorization: ..." -H "Content-Type: application/json" -d '{"entrypoint": "python -c \"import ray; print(ray.cluster_resources())\""}'` returns `{"job_id": "..."}`.
6. `GET /api/ray/jobs/{job_id}` reports `SUCCEEDED` with logs.
7. `./start.sh --ray-source disabled` — Backend's `/api/ray/*` returns 503 cleanly; no errors at startup.
8. All audit gates pass: `validate_fragments`, `regen --all --check`, `check_doc_links`, `check-compose-source-deps`, `check-docs-drift`, `check-kong-routes`, `validate_research_schema --all`.
9. Pytest suite green; count grows by the new Backend tests (from 315 → ~320).
10. `services/ray/{README.md, architecture.svg, architecture.html}` auto-generated and schema-valid.
11. `services/ray/service.yml` validates against `bootstrapper/schemas/service.schema.json`.
12. `.env.example` regenerated with new `RAY_*` env vars in alphabetical position.
13. `docs/diagrams/architecture.dot` + `.svg` regenerated showing the Ray cluster.
14. Branch lands on `main` via fast-forward merge; CI green; final user-visible test: `./stop.sh --cold && ./start.sh --ray-source ray-container-cpu --ray-worker-count 2` and the dashboard loads.

## 18. Implementation order (preview — writing-plans will detail)

1. **Worktree** — create `.claude/worktrees/add-ray-cluster` from `main`.
2. **Manifest + compose** — write `services/ray/service.yml` + `services/ray/compose.yml`, add include to top-level `docker-compose.yml`. Run `validate_fragments`. Commit.
3. **Topology side-effects** — regen `.env.example` + README topology + architecture diagram. Verify all four port slots assigned. Commit.
4. **Auto-generated docs** — run `docs.regen ray` to create per-service README + SVG + HTML; hand-author README body. Commit.
5. **Kong route + hosts** — update `hosts_manager.py` + `kong_config_generator.py` + `check-kong-routes.py`. Commit.
6. **Backend REST surface** — `ray_client.py` + `ray_routes.py` + tests + `requirements.txt` + manifest `runtime_adaptive` update. Commit.
7. **JupyterHub wiring** — `requirements.txt` + manifest `runtime_adaptive` update + seed notebook. Commit.
8. **Hermes manifest update** — `data_flow.calls` additions. Commit.
9. **Compose-equivalence baseline regen** — accept the new baseline reflecting Ray's compose contribution. Commit.
10. **Audit-script updates** — `check-kong-routes.py` allowlist. Commit.
11. **Full verification pass** — every audit script + pytest + manual smoke (`./start.sh` with Ray enabled). Commit fixes if any.
12. **Land** — rebase + fast-forward into `main`, push.
