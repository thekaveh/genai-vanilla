# Ray Cluster Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Ray distributed-compute cluster as `services/ray/` with CPU/GPU/external/disabled source variants, wizard prompts for worker count + external address, Kong basic-auth on `ray.localhost`, Backend REST API for job submission, and JupyterHub dep wiring.

**Architecture:** Two-container family (`ray-head` + `ray-worker`) in the `infra` category, with a `_generate_ray_config()` hook resolving `RAY_IMAGE`/`RAY_WORKER_SCALE`/`RAY_ADDRESS` from `RAY_SOURCE`+`RAY_WORKER_COUNT`. Backend gains a `/api/ray/*` REST surface that wraps Ray's `JobSubmissionClient`. JupyterHub gets `ray>=2.55.1` in its build image. Hermes manifest gets a `data_flow.calls` entry only (no code).

**Tech Stack:** Python (ray-client, FastAPI), YAML manifests, Docker Compose, Ray 2.55.1 (`rayproject/ray:2.55.1` + `:2.55.1-gpu`), Apache 2.0.

**Spec:** `docs/specs/2026-05-24-ray-cluster-design.md` (557 lines, approved). Tasks cite spec section numbers (§N) where authoritative content lives — engineers MUST read the cited section before implementing each task.

**Worktree:** All work happens in `.claude/worktrees/add-ray-cluster` (created in Task 0). Final integration is rebase-then-fast-forward into `main` per memory `project_branch_workflow.md`.

**Conventions for this plan:**
- Commits use the genai-vanilla style: terse third-person `<topic>:` prefix (e.g. `ray:`, `backend:`, `wizard:`, `docs:`), no Claude trailer (per memory `feedback_commits`).
- Each task ends with a verification command + commit.
- "Verify links" = `python scripts/check_doc_links.py` from repo root, expect exit 0.
- "Validate fragments" = `cd bootstrapper && uv run python -m tools.validate_fragments`, expect `OK — N manifest(s) validated.`
- "Run pytest" = `cd bootstrapper && uv run pytest -q --tb=short`, expect green.

---

## Task 0: Setup — create worktree, snapshot baseline

**Files:**
- Create: `.claude/worktrees/add-ray-cluster/` (worktree directory)

- [ ] **Step 1: Confirm main is clean + green**

```bash
cd /Users/kaveh/repos/genai-vanilla
git status -s
# Expected: clean (only docs/ROADMAP.md may show modified — user's WIP)

cd bootstrapper && uv run pytest -q --tb=no 2>&1 | tail -3
# Expected: 315 passed
```

- [ ] **Step 2: Create the worktree**

```bash
cd /Users/kaveh/repos/genai-vanilla
git worktree add -b add-ray-cluster .claude/worktrees/add-ray-cluster main
ls -la .claude/worktrees/add-ray-cluster/services
# Expected: branch created, worktree visible, services/ folder present
```

- [ ] **Step 3: Switch operating directory + verify baseline**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
git status
# Expected: On branch add-ray-cluster, nothing to commit

cd bootstrapper && uv run pytest -q --tb=no 2>&1 | tail -3
# Expected: 315 passed
```

- [ ] **Step 4: Read the spec end-to-end**

Read `docs/specs/2026-05-24-ray-cluster-design.md` (in the worktree — it was inherited from main). Take particular note of §5 (manifest shape), §8 (Backend REST), and §6 (wizard cascade). The spec is the substance; this plan only sequences and verifies.

- [ ] **Step 5: NO COMMIT yet.** Task 0 is setup only. Proceed to Task 1.

---

## Task 1: Write Ray manifest (`services/ray/service.yml`)

**Files:**
- Create: `services/ray/service.yml`
- Reference: spec §5 (Service manifest shape) — verbatim source for the manifest content.

- [ ] **Step 1: Create the services/ray directory + manifest**

```bash
mkdir -p services/ray
```

Then write `services/ray/service.yml` with the exact content from spec §5 (the `services/ray/service.yml` code block). Copy the full block verbatim — do NOT shorten or paraphrase. The content is:

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

- [ ] **Step 2: Run schema validation**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run python -c "
import json, yaml, jsonschema
schema = json.load(open('schemas/service.schema.json'))
doc = yaml.safe_load(open('../services/ray/service.yml'))
jsonschema.validate(doc, schema)
print('OK — ray manifest schema-valid')
"
```

Expected: `OK — ray manifest schema-valid`

- [ ] **Step 3: Run `validate_fragments` (may fail at this point — manifest is added but compose isn't yet)**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run python -m tools.validate_fragments 2>&1 | tail -5
```

Expected: may report missing `compose.yml` for ray — that's fixed in Task 2. Verify the error is specifically about the missing compose, not a manifest schema issue.

- [ ] **Step 4: Commit**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
git add services/ray/service.yml
git commit -m "ray: add service manifest for distributed-compute cluster"
```

---

## Task 2: Write Ray compose fragment + include in top-level

**Files:**
- Create: `services/ray/compose.yml`
- Modify: `docker-compose.yml` — add `- services/ray/compose.yml` to the `include:` block
- Reference: spec §5 (compose.yml content)

- [ ] **Step 1: Write the compose fragment**

Create `services/ray/compose.yml` with this content (verbatim from spec §5):

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

- [ ] **Step 2: Add the compose include line to top-level docker-compose.yml**

Open `docker-compose.yml`. Locate the `include:` block. Add `services/ray/compose.yml` after `services/kong/compose.yml` (the gateway-last note in the existing file still applies — but Ray is `infra` like Kong; place Ray AFTER the data-tier block and BEFORE the LLM-tier block, which matches its category position):

Find the existing line:
```yaml
  # LLM tier (cloud-providers + tts-provider are virtual; no compose fragment)
  - services/litellm/compose.yml
```

Insert BEFORE it:
```yaml
  # Compute substrate (infra)
  - services/ray/compose.yml
```

Use the Edit tool with the existing `  - services/litellm/compose.yml` line as a unique anchor.

- [ ] **Step 3: Run validate_fragments — should now pass**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run python -m tools.validate_fragments
```

Expected: `OK — 25 manifest(s) validated.` (was 24; ray adds one)

- [ ] **Step 4: Verify compose merge works**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
cp .env.example .env
docker compose -f docker-compose.yml config -q
echo "Exit: $?"
```

Expected: exit 0 (compose merges cleanly with default `RAY_SOURCE=disabled`). Note: the `RAY_DASHBOARD_PORT` etc. env vars are not yet in `.env.example` — compose will warn but config should still pass because `replicas: 0`.

If compose complains about unset env vars, that's expected at this point — Task 4 regenerates `.env.example` to add the new RAY_* vars.

- [ ] **Step 5: Commit**

```bash
git add services/ray/compose.yml docker-compose.yml
git commit -m "ray: add compose fragment + wire into top-level include"
```

---

## Task 3: Implement `_generate_ray_config()` hook + unit tests

**Files:**
- Modify: `bootstrapper/services/service_config.py` (add `_generate_ray_config()` method + call from `generate_service_environment()`)
- Create: `bootstrapper/tests/test_ray_config.py`
- Reference: spec §4 (Decision 6), §5 (env vars + auto_managed semantics)

- [ ] **Step 1: Open `bootstrapper/services/service_config.py` and study one existing hook**

Read the file. Locate `_generate_cloud_providers_config()` as a reference pattern. Note its inputs (`source_value`, `shared_env`), its outputs (a dict of env-var assignments), and how it's called from `generate_service_environment()`.

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
grep -n "_generate_cloud_providers_config\|_generate_stt_provider_config\|def generate_service_environment" bootstrapper/services/service_config.py
```

Expected: 3-5 line numbers showing the hook definitions + the dispatcher.

- [ ] **Step 2: Write the failing test FIRST (TDD)**

Create `bootstrapper/tests/test_ray_config.py`:

```python
"""Unit tests for _generate_ray_config() — derives RAY_IMAGE, RAY_WORKER_SCALE,
RAY_ADDRESS, RAY_HEAD_SCALE from RAY_SOURCE + RAY_WORKER_COUNT.

The hook is the only adaptive piece in the ray manifest — its correctness
is load-bearing for the entire compose substitution chain (image tag,
worker replicas, RAY_ADDRESS pushed into Backend / JupyterHub).
"""

from __future__ import annotations


def _service_config_instance():
    """Build a ServiceConfig instance with no real env file — we only
    test the pure hook function. Lazy-import to avoid module-load deps."""
    from services.service_config import ServiceConfig
    sc = ServiceConfig.__new__(ServiceConfig)
    # Minimal fields the hook reads; everything else stays uninitialized.
    sc.service_sources = {}
    return sc


def test_disabled_returns_empty_address_and_zero_scales():
    sc = _service_config_instance()
    out = sc._generate_ray_config(
        source_value="disabled",
        shared_env={"RAY_WORKER_COUNT": "2"},
    )
    assert out["RAY_HEAD_SCALE"] == "0"
    assert out["RAY_WORKER_SCALE"] == "0"
    assert out["RAY_ADDRESS"] == ""
    # Image is irrelevant when disabled but must be set to a valid default
    # (compose won't pull a missing image with replicas: 0, but tests for
    # env-example consistency need *some* value).
    assert out["RAY_IMAGE"].startswith("rayproject/ray:")


def test_container_cpu_returns_cpu_image_and_resolved_scales():
    sc = _service_config_instance()
    out = sc._generate_ray_config(
        source_value="ray-container-cpu",
        shared_env={"RAY_WORKER_COUNT": "3", "RAY_IMAGE": "rayproject/ray:2.55.1",
                    "RAY_GPU_IMAGE": "rayproject/ray:2.55.1-gpu"},
    )
    assert out["RAY_IMAGE"] == "rayproject/ray:2.55.1"
    assert out["RAY_HEAD_SCALE"] == "1"
    assert out["RAY_WORKER_SCALE"] == "3"
    assert out["RAY_ADDRESS"] == "ray://ray-head:10001"


def test_container_gpu_returns_gpu_image_and_resolved_scales():
    sc = _service_config_instance()
    out = sc._generate_ray_config(
        source_value="ray-container-gpu",
        shared_env={"RAY_WORKER_COUNT": "2", "RAY_IMAGE": "rayproject/ray:2.55.1",
                    "RAY_GPU_IMAGE": "rayproject/ray:2.55.1-gpu"},
    )
    assert out["RAY_IMAGE"] == "rayproject/ray:2.55.1-gpu"
    assert out["RAY_HEAD_SCALE"] == "1"
    assert out["RAY_WORKER_SCALE"] == "2"
    assert out["RAY_ADDRESS"] == "ray://ray-head:10001"


def test_external_uses_external_address_and_zero_scales():
    sc = _service_config_instance()
    out = sc._generate_ray_config(
        source_value="ray-external",
        shared_env={"RAY_EXTERNAL_ADDRESS": "ray://my-cluster.anyscale.com:10001",
                    "RAY_WORKER_COUNT": "5"},
    )
    assert out["RAY_HEAD_SCALE"] == "0"
    assert out["RAY_WORKER_SCALE"] == "0"
    assert out["RAY_ADDRESS"] == "ray://my-cluster.anyscale.com:10001"


def test_external_with_empty_address_falls_back_safely():
    """If user sets RAY_SOURCE=ray-external but forgets RAY_EXTERNAL_ADDRESS,
    we don't crash — emit an empty RAY_ADDRESS so consumers know Ray is
    unavailable. The source-validator should have caught this upstream
    via the `requires: [RAY_EXTERNAL_ADDRESS]` block, but the hook must
    still degrade gracefully."""
    sc = _service_config_instance()
    out = sc._generate_ray_config(
        source_value="ray-external",
        shared_env={"RAY_EXTERNAL_ADDRESS": "", "RAY_WORKER_COUNT": "0"},
    )
    assert out["RAY_ADDRESS"] == ""


def test_worker_count_zero_means_head_only():
    sc = _service_config_instance()
    out = sc._generate_ray_config(
        source_value="ray-container-cpu",
        shared_env={"RAY_WORKER_COUNT": "0", "RAY_IMAGE": "rayproject/ray:2.55.1",
                    "RAY_GPU_IMAGE": "rayproject/ray:2.55.1-gpu"},
    )
    assert out["RAY_HEAD_SCALE"] == "1"  # head still on
    assert out["RAY_WORKER_SCALE"] == "0"  # head-only single-node Ray


def test_invalid_worker_count_falls_back_to_default():
    """A malformed RAY_WORKER_COUNT (non-integer, negative) should fall
    back to the manifest's stated default `2` rather than crash."""
    sc = _service_config_instance()
    out = sc._generate_ray_config(
        source_value="ray-container-cpu",
        shared_env={"RAY_WORKER_COUNT": "not-a-number",
                    "RAY_IMAGE": "rayproject/ray:2.55.1",
                    "RAY_GPU_IMAGE": "rayproject/ray:2.55.1-gpu"},
    )
    assert out["RAY_WORKER_SCALE"] == "2"
```

- [ ] **Step 3: Run the new test — confirm it fails with "method not found"**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run pytest tests/test_ray_config.py -v 2>&1 | tail -15
```

Expected: failures with `AttributeError: 'ServiceConfig' object has no attribute '_generate_ray_config'` (or similar). All 7 tests should fail.

- [ ] **Step 4: Implement `_generate_ray_config()` in `bootstrapper/services/service_config.py`**

Add this method to the `ServiceConfig` class (placement: alphabetically near `_generate_cloud_providers_config`, or just before `generate_service_environment`):

```python
def _generate_ray_config(self, source_value: str, shared_env: dict) -> dict:
    """Resolve Ray's auto-managed env vars from RAY_SOURCE + RAY_WORKER_COUNT.

    Sets four env vars based on the active source:
      - RAY_IMAGE — CPU or GPU image tag (compose interpolates this)
      - RAY_HEAD_SCALE — 1 when container source, 0 otherwise
      - RAY_WORKER_SCALE — RAY_WORKER_COUNT when container source, 0 otherwise
      - RAY_ADDRESS — `ray://ray-head:10001` for container sources,
        `${RAY_EXTERNAL_ADDRESS}` value for ray-external, empty otherwise

    Args:
        source_value: Current RAY_SOURCE value (one of `ray-container-cpu`,
            `ray-container-gpu`, `ray-external`, `disabled`).
        shared_env: Env vars accumulated by earlier generators + manifest
            defaults. We read `RAY_WORKER_COUNT`, `RAY_IMAGE`,
            `RAY_GPU_IMAGE`, `RAY_EXTERNAL_ADDRESS` from here.

    Returns:
        Dict of resolved env-var assignments. The caller merges this into
        the .env-example output.
    """
    cpu_image = shared_env.get("RAY_IMAGE", "rayproject/ray:2.55.1") or "rayproject/ray:2.55.1"
    gpu_image = shared_env.get("RAY_GPU_IMAGE", "rayproject/ray:2.55.1-gpu") or "rayproject/ray:2.55.1-gpu"
    external_addr = (shared_env.get("RAY_EXTERNAL_ADDRESS", "") or "").strip()

    # Parse RAY_WORKER_COUNT with safe fallback to the manifest default (2).
    raw_count = shared_env.get("RAY_WORKER_COUNT", "2")
    try:
        worker_count = int(raw_count)
        if worker_count < 0:
            worker_count = 2
    except (ValueError, TypeError):
        worker_count = 2

    if source_value == "ray-container-cpu":
        return {
            "RAY_IMAGE": cpu_image,
            "RAY_HEAD_SCALE": "1",
            "RAY_WORKER_SCALE": str(worker_count),
            "RAY_ADDRESS": "ray://ray-head:10001",
        }
    if source_value == "ray-container-gpu":
        return {
            "RAY_IMAGE": gpu_image,
            "RAY_HEAD_SCALE": "1",
            "RAY_WORKER_SCALE": str(worker_count),
            "RAY_ADDRESS": "ray://ray-head:10001",
        }
    if source_value == "ray-external":
        return {
            "RAY_IMAGE": cpu_image,  # irrelevant (scale=0) but must be set
            "RAY_HEAD_SCALE": "0",
            "RAY_WORKER_SCALE": "0",
            "RAY_ADDRESS": external_addr,
        }
    # disabled (or any unknown source value): everything off, no address
    return {
        "RAY_IMAGE": cpu_image,
        "RAY_HEAD_SCALE": "0",
        "RAY_WORKER_SCALE": "0",
        "RAY_ADDRESS": "",
    }
```

- [ ] **Step 5: Wire the hook into `generate_service_environment()`**

Find `generate_service_environment()` in `bootstrapper/services/service_config.py`. Add a Ray section near the existing per-service config calls (e.g., after `_generate_stt_provider_config` and `_generate_tts_provider_config`):

```python
        # Generate Ray cluster configuration
        ray_source = self.service_sources.get("RAY_SOURCE", "disabled")
        ray_config = self._generate_ray_config(
            source_value=ray_source,
            shared_env=env_vars,
        )
        env_vars.update(ray_config)
```

Use the Edit tool with a unique surrounding-context anchor — `# Generate Document Processor configuration` (or whichever existing block sits near the end) followed by its body, then your insertion before the next existing block.

- [ ] **Step 6: Run the new test — confirm all 7 pass**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run pytest tests/test_ray_config.py -v 2>&1 | tail -15
```

Expected: 7 passed.

- [ ] **Step 7: Run the full pytest suite — confirm no regressions**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run pytest -q --tb=short 2>&1 | tail -5
```

Expected: 322 passed (315 baseline + 7 new). 0 failures.

- [ ] **Step 8: Commit**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
git add bootstrapper/services/service_config.py bootstrapper/tests/test_ray_config.py
git commit -m "ray: add _generate_ray_config() hook resolving RAY_IMAGE / scales / address from RAY_SOURCE + RAY_WORKER_COUNT"
```

---

## Task 4: Regenerate `.env.example` + README TOPOLOGY + architecture diagram

**Files:**
- Modify (auto-generated): `.env.example`, `README.md` TOPOLOGY block, `docs/diagrams/architecture.dot`, `docs/diagrams/architecture.svg`

- [ ] **Step 1: Regenerate `.env.example`**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run python -m services.env_assembler 2>&1 | tail -3
```

Expected: `Wrote /…/.env.example (NNN lines)` — line count grows by ~25-30 (Ray's env vars).

- [ ] **Step 2: Verify Ray's env vars landed in .env.example**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
grep -E "^RAY_|^# infra: Ray" .env.example | head -20
```

Expected: section header `# infra: Ray (distributed compute substrate)  (services/ray/service.yml)` + lines for `RAY_SOURCE`, `RAY_DASHBOARD_PORT`, `RAY_GCS_PORT`, `RAY_CLIENT_PORT`, `RAY_WORKER_COUNT`, `RAY_EXTERNAL_ADDRESS`, `RAY_IMAGE`, `RAY_GPU_IMAGE`, `RAY_HEAD_SCALE` (empty / auto-managed), `RAY_WORKER_SCALE` (empty / auto-managed), `RAY_ADDRESS` (empty / auto-managed).

Verify ports are in the infra block range (`6300X` where X is the next free slot after Kong: probably `63002`, `63003`, `63004`).

- [ ] **Step 3: Regenerate README TOPOLOGY block**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run python -m tools.generate_readme_topology 2>&1 | tail -3
```

Expected: `Updated README.md TOPOLOGY block`. The block now includes `| Infrastructure | Ray | 63002 | ray.localhost |` (or whatever port the slot allocator emitted).

- [ ] **Step 4: Verify the README addition**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
grep "Ray" README.md | head -5
```

Expected: A line like `| Infrastructure | Ray | 63002 | ray.localhost |`.

- [ ] **Step 5: Regenerate architecture.dot**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run python -m tools.generate_architecture_diagram 2>&1 | tail -3
```

Expected: `Wrote /…/docs/diagrams/architecture.dot`. The dot file now mentions the ray node.

- [ ] **Step 6: Render the SVG from the new .dot**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
dot -Tsvg docs/diagrams/architecture.dot > docs/diagrams/architecture.svg
diff <(dot -Tsvg docs/diagrams/architecture.dot) docs/diagrams/architecture.svg | head -3
echo "Exit: $?"
```

Expected: exit 0 (no diff).

- [ ] **Step 7: Run `validate_fragments` to confirm everything's still in sync**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run python -m tools.validate_fragments
```

Expected: `OK — 25 manifest(s) validated.`

- [ ] **Step 8: Commit**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
git add .env.example README.md docs/diagrams/architecture.dot docs/diagrams/architecture.svg
git commit -m "ray: regenerate .env.example, README topology, architecture diagram"
```

---

## Task 5: Generate per-service Ray README + diagram via `docs.regen`

**Files:**
- Modify: `services/ray/README.md` (regen will create the deps section; hand-author body after)
- Create (auto): `services/ray/architecture.svg`, `services/ray/architecture.html`

- [ ] **Step 1: Run regen for the ray service**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
PYTHONPATH=bootstrapper uv run --project bootstrapper python -m bootstrapper.docs.regen ray
ls services/ray/
```

Expected: `services/ray/` now contains `README.md`, `architecture.svg`, `architecture.html` (plus `service.yml` and `compose.yml` from earlier tasks).

- [ ] **Step 2: Hand-author the README body**

The auto-generated README contains a "Dependencies & Integrations" auto-block but the rest is empty/templated. Replace the README content (preserving the auto-generated `## N. Dependencies & Integrations` block — regen will keep it in sync) with a hand-authored body. Write `services/ray/README.md`:

```markdown
# Ray

Distributed-compute substrate for the stack. Ray runs as a head + worker cluster reachable from JupyterHub, Backend (via REST), and any host Python via `ray.init("ray://localhost:<RAY_CLIENT_PORT>")`.

## 1. Overview

Ray (`rayproject/ray:2.55.1`, Apache 2.0) is a generic parallel-compute framework. This stack ships it as a 2-container family (head + workers) wired so every tier can dispatch parallel work without rolling its own asyncio.gather glue. Use Ray when you have N independent units of work to fan out across CPUs (and eventually GPUs on multi-host Linux).

Active when `RAY_SOURCE ∈ {ray-container-cpu, ray-container-gpu}`. The `ray-external` source lets you point at a managed Anyscale or self-hosted external Ray cluster instead.

## 2. Access

| Surface | URL | Auth |
|---|---|---|
| Dashboard (UI + REST job-submission API) | `http://localhost:${RAY_DASHBOARD_PORT}` direct or `http://ray.localhost:${KONG_HTTP_PORT}` via Kong | Direct: unauthenticated. Kong: basic-auth with `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD`. |
| Client server (host Python) | `ray://localhost:${RAY_CLIENT_PORT}` | None |
| GCS (internal cluster controller) | `:${RAY_GCS_PORT}` host-side; `:6379` inside the network | None — internal only |
| Backend REST jobs API | `http://localhost:${BACKEND_PORT}/api/ray/jobs/submit` etc. | Backend's existing auth |

## 3. Configuration

| Env var | Default | When | Description |
|---|---|---|---|
| `RAY_SOURCE` | `disabled` | always | One of `ray-container-cpu`, `ray-container-gpu`, `ray-external`, `disabled`. |
| `RAY_WORKER_COUNT` | `2` | when source ∈ {cpu, gpu} | Number of `ray-worker` containers. Use `0` for head-only single-node mode. No hard upper bound — bounded by host RAM and CPUs. |
| `RAY_EXTERNAL_ADDRESS` | `""` | required when `RAY_SOURCE=ray-external` | `ray://…:10001` URL of the external cluster. |
| `RAY_DASHBOARD_PORT`, `RAY_GCS_PORT`, `RAY_CLIENT_PORT` | auto-assigned | always | Topology-allocated in the infra block. |
| `RAY_IMAGE`, `RAY_GPU_IMAGE`, `RAY_HEAD_SCALE`, `RAY_WORKER_SCALE`, `RAY_ADDRESS` | auto-managed | always | Resolved by `_generate_ray_config()` from RAY_SOURCE + RAY_WORKER_COUNT. Don't edit by hand. |

**Wizard behavior:** when the user selects `ray-container-cpu` or `ray-container-gpu`, the wizard then prompts for `RAY_WORKER_COUNT` (integer, default 2). When the user selects `ray-external`, the wizard prompts for `RAY_EXTERNAL_ADDRESS`.

## 4. Architecture & wiring

**Containers in the family:**
- `ray-head` — the cluster controller. Runs `ray start --head`. Exposes ports 8265 (dashboard + REST), 6379 (GCS — Ray's internal cluster controller, *distinct from the project's Redis cache* despite both using Redis wire protocol), 10001 (client server). Healthcheck on `:8265/api/version`.
- `ray-worker` — one or more replicas. Runs `ray start --address=ray-head:6379 --block`. No host ports.

**Why two `tmp` volumes:** Ray spills object-store state to `/tmp/ray` per node. Separate volumes for head and workers prevent collision.

**Critical shared memory:** Both containers set `shm_size: 4gb` — Docker's default 64MB causes immediate crash because Ray's Plasma object store needs shared memory. If you see startup failures with "Connection refused" on port 8265 within 60 seconds, check shm size.

**No external runtime dependencies.** Ray ships its own GCS (Redis-protocol cluster controller) and Plasma (shared-memory object store). The cluster is fully self-contained.

**Consumers in the stack:**
- **Backend** — exposes `/api/ray/jobs/{submit,status,stop,cluster-status}` for HTTP-driven job submission. Adapts via `RAY_ADDRESS` set by `_generate_ray_config()`.
- **JupyterHub** — notebooks can `import ray; ray.init()` directly (RAY_ADDRESS picked up from env). Sample notebook: `services/jupyterhub/notebooks/hello-ray.ipynb`.
- **Hermes** — agents can submit Ray jobs by calling Backend's `/api/ray/jobs/submit` (Hermes already calls Backend via `data_flow.calls`). No Hermes code change.

## 5. Dependencies & Integrations

(Auto-generated by `bootstrapper.docs.regen`. Re-run after editing `data_flow.calls`.)

## 6. Troubleshooting

- **Head container exits immediately with "Bus error" or "/dev/shm too small"** — Docker's default shared-memory size (64MB) is too small. Compose's `shm_size: 4gb` should handle this, but some installs (rootless Podman, older Docker) ignore it. Verify with `docker inspect ${PROJECT_NAME}-ray-head | grep ShmSize`.
- **Workers stuck "starting"** — they `depends_on: ray-head: service_healthy`. The head's `start_period: 60s` allows up to 60s before health checks count. If still stuck after 2 minutes, check the head's healthcheck output: `docker exec ${PROJECT_NAME}-ray-head curl -v http://localhost:8265/api/version`.
- **`ray.init("ray://localhost:PORT")` from host fails with version mismatch** — your host's `ray` Python package version must match the cluster's image version. Pin `ray>=2.55.1,<2.56` in your host venv to match the image's `rayproject/ray:2.55.1`.
- **Dashboard unreachable through Kong** — Kong's `ray.localhost` route requires `--setup-hosts` to have run AND basic-auth credentials match `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD` in `.env`. The direct port works without these.
- **`RAY_SOURCE=ray-external` ignored** — make sure `RAY_EXTERNAL_ADDRESS` is also set. The `requires: [RAY_EXTERNAL_ADDRESS]` source-option check will warn at wizard time but won't crash if the env var is set to an empty string.
```

- [ ] **Step 3: Re-run regen to populate the auto-deps section in the new README**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
PYTHONPATH=bootstrapper uv run --project bootstrapper python -m bootstrapper.docs.regen ray
PYTHONPATH=bootstrapper uv run --project bootstrapper python -m bootstrapper.docs.regen --all --check
echo "Exit: $?"
```

Expected: regen succeeds and the `--all --check` reports no drift.

- [ ] **Step 4: Verify hand-authored body survived regen (Future content + sections above the auto block must be preserved)**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
head -30 services/ray/README.md
```

Expected: the hand-authored Overview / Access / Configuration / Architecture & wiring sections are intact.

- [ ] **Step 5: Commit**

```bash
git add services/ray/README.md services/ray/architecture.svg services/ray/architecture.html
git commit -m "ray: hand-author README body + generate per-service architecture diagrams"
```

---

## Task 6: Add `ray.localhost` to hosts manager + Kong route + audit-script allowlist

**Files:**
- Modify: `bootstrapper/utils/hosts_manager.py` — add `ray.localhost` to `GENAI_HOSTS`
- Modify: `bootstrapper/utils/kong_config_generator.py` — add new route for `ray.localhost`
- Modify: `scripts/check-kong-routes.py` — add `ray.localhost` to `EXPECTED_HOST_ROUTES`

- [ ] **Step 1: Add `ray.localhost` to `bootstrapper/utils/hosts_manager.py::GENAI_HOSTS`**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
grep -n "GENAI_HOSTS\s*=" bootstrapper/utils/hosts_manager.py | head -3
```

Find the list. Add `"ray.localhost"` in alphabetical position (between `"openclaw.localhost"` and `"redis.localhost"` if present, or at the appropriate alphabetical spot).

- [ ] **Step 2: Add the Kong route in `bootstrapper/utils/kong_config_generator.py`**

Find an existing dashboard route with `preserve_host: True` + basic-auth — `litellm.localhost` or `minio.localhost` is the reference pattern. Read its route-generation code (search for `litellm.localhost` in `kong_config_generator.py`). The route should:
- Match host `ray.localhost`
- Forward to `http://ray-head:8265`
- Use `preserve_host: True`
- Apply `basic-auth` plugin with credentials sourced from `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD` (same secret as the existing dashboards)
- Be gated on `RAY_SOURCE` ∈ {ray-container-cpu, ray-container-gpu} — when ray-external or disabled, skip the route

```bash
grep -n "litellm.localhost\|minio.localhost\|preserve_host" bootstrapper/utils/kong_config_generator.py | head -10
```

Read those locations + replicate the pattern for ray. The implementation function probably has a helper like `_add_dashboard_route(host, upstream, ...)`. Use the same helper.

Pseudocode (adjust to match actual function names):

```python
# Inside the appropriate route-generation method (likely a `_generate_routes()`
# or `_add_dashboard_routes()` style function in kong_config_generator.py)
ray_source = env.get("RAY_SOURCE", "disabled")
if ray_source in ("ray-container-cpu", "ray-container-gpu"):
    self._add_dashboard_route(
        host="ray.localhost",
        upstream="http://ray-head:8265",
        preserve_host=True,
    )
```

- [ ] **Step 3: Add `ray.localhost` to `scripts/check-kong-routes.py::EXPECTED_HOST_ROUTES`**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
grep -n "EXPECTED_HOST_ROUTES" scripts/check-kong-routes.py
```

Find the dict. Note: the audit script runs against `.env.example` defaults where `RAY_SOURCE=disabled`. So the check won't fire by default. But for forward-compat (and when users override `--ray-source ray-container-cpu`), the entry is still worth pinning. Add:

```python
EXPECTED_HOST_ROUTES = {
    # …existing entries…
    "ray.localhost": "http://ray-head:8265",
}
```

If the audit script handles default-source gating differently (e.g., a separate "only check when source is on by default" dict), follow that pattern — read the script's logic carefully before adding.

- [ ] **Step 4: Test the Kong route generation with RAY_SOURCE enabled**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
# Temporarily set RAY_SOURCE=ray-container-cpu in a tmp .env and run the generator
cp .env.example /tmp/test.env
sed -i.bak 's/^RAY_SOURCE=.*/RAY_SOURCE=ray-container-cpu/' /tmp/test.env
cd bootstrapper && BOOTSTRAPPER_ENV_FILE=/tmp/test.env uv run python -c "
from utils.kong_config_generator import KongConfigGenerator
# … invoke the generator; print the generated kong.yml; grep for ray
" 2>&1 | head -30
```

If invoking the generator is non-trivial in isolation, skip this manual test and rely on the audit-script check (Step 6).

- [ ] **Step 5: Update hosts file + check_kong_routes test**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
python scripts/check-kong-routes.py 2>&1 | tail -5
```

Expected: `PASS default_host_routes` (the script runs with .env.example defaults where Ray is disabled — so ray.localhost route is not generated, but the EXPECTED_HOST_ROUTES entry is forward-looking).

- [ ] **Step 6: Run validate_fragments + full pytest**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run python -m tools.validate_fragments
uv run pytest -q --tb=short 2>&1 | tail -3
```

Expected: validator OK; tests still green.

- [ ] **Step 7: Commit**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
git add bootstrapper/utils/hosts_manager.py bootstrapper/utils/kong_config_generator.py scripts/check-kong-routes.py
git commit -m "ray: wire ray.localhost into Kong (basic-auth + preserve_host) + hosts manager + audit-script allowlist"
```

---

## Task 7: Wire wizard prompts (worker count + external address)

**Files:**
- Modify: `bootstrapper/wizard/llm_steps.py` OR `bootstrapper/ui/textual/integration.py` — wherever per-service follow-up prompts are wired in
- Reference: spec §6 (wizard integration)

- [ ] **Step 1: Survey the wizard prompt-cascade code**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
grep -rn "build_ollama_steps\|build_.*_steps\|PromptStep\|integer\|number\|BASE_PORT" bootstrapper/wizard/ bootstrapper/ui/textual/integration.py | head -20
```

Find the pattern for adding a follow-up prompt step. The Ollama LLM cascade (build_ollama_steps) is the closest analog — it splices steps in after a source selection. The base_port wizard step demonstrates an integer prompt.

- [ ] **Step 2: Decide whether to add an integer prompt step type or reuse an existing one**

Read `bootstrapper/ui/textual/widgets/prompt_panel.py` and look for an existing integer-input step. The base-port prompt is the canonical example. If the wizard already supports integer prompts, use it. If not, add a new `PromptStep.kind = "integer"` variant — but only if necessary.

```bash
grep -n "PromptStep\|kind=\"integer\"\|kind=\"number\"\|step_type" bootstrapper/ui/textual/widgets/prompt_panel.py | head -10
```

Expected: an existing integer step type exists for base-port. Use the same pattern.

- [ ] **Step 3: Build the Ray prompt cascade**

In the appropriate wizard module (`bootstrapper/wizard/` for prompt-building or `bootstrapper/ui/textual/integration.py` for the step assembly), add a Ray-specific step builder. Place it adjacent to the existing per-service step builders.

The cascade:

1. **Source-variant tile prompt for `RAY_SOURCE`** — already auto-generated from the manifest's `sources.options` block; nothing to add here.
2. **Integer prompt for `RAY_WORKER_COUNT`** — only when `RAY_SOURCE` ∈ {`ray-container-cpu`, `ray-container-gpu`}. Default `2`. Min `0`. No max.
3. **Text prompt for `RAY_EXTERNAL_ADDRESS`** — only when `RAY_SOURCE` == `ray-external`. Default empty. Hint: `ray://my-cluster.anyscale.com:10001`.

Concretely, add a function like:

```python
def build_ray_followup_steps(env_vars: dict, selections: dict, warn=None) -> list[PromptStep]:
    """Return follow-up wizard steps for Ray when its source is selected.

    Splice these in immediately after the RAY_SOURCE prompt.
    """
    source = selections.get("RAY_SOURCE", env_vars.get("RAY_SOURCE", "disabled"))
    steps = []
    if source in ("ray-container-cpu", "ray-container-gpu"):
        steps.append(PromptStep(
            kind="integer",  # use the same kind as base-port
            title="Ray worker count",
            description="Number of ray-worker containers. 0 = head-only single-node cluster.",
            env_var="RAY_WORKER_COUNT",
            default_value=int(env_vars.get("RAY_WORKER_COUNT", "2") or "2"),
            min_value=0,
        ))
    elif source == "ray-external":
        steps.append(PromptStep(
            kind="text",  # or "secret" if that's how the wizard handles non-tile text input
            title="Ray external cluster URL",
            description="The `ray://` URL of your external Ray cluster (Anyscale or self-hosted).",
            env_var="RAY_EXTERNAL_ADDRESS",
            default_value=env_vars.get("RAY_EXTERNAL_ADDRESS", ""),
            placeholder="ray://my-cluster.anyscale.com:10001",
        ))
    return steps
```

Splice the result into the main wizard-step list at the appropriate point (after the RAY_SOURCE tile prompt, before the next service's prompt). Follow how `build_ollama_steps` is spliced — read the call site in `bootstrapper/ui/textual/integration.py`.

- [ ] **Step 4: Add a unit test for the prompt cascade**

Create `bootstrapper/tests/test_wizard_ray_steps.py`:

```python
"""Wizard cascade for Ray: source-variant tile drives a follow-up integer
prompt for RAY_WORKER_COUNT (when container-*) or a text prompt for
RAY_EXTERNAL_ADDRESS (when ray-external)."""

from __future__ import annotations

import pytest


def _build(source: str, env_overrides: dict | None = None):
    """Call build_ray_followup_steps with a minimal env + selections shape."""
    from wizard.llm_steps import build_ray_followup_steps  # adjust import to actual module
    env = {"RAY_SOURCE": "disabled", "RAY_WORKER_COUNT": "2"}
    env.update(env_overrides or {})
    return build_ray_followup_steps(env_vars=env, selections={"RAY_SOURCE": source})


def test_container_cpu_emits_worker_count_step():
    steps = _build("ray-container-cpu")
    assert len(steps) == 1
    assert steps[0].env_var == "RAY_WORKER_COUNT"
    assert steps[0].default_value == 2


def test_container_gpu_emits_worker_count_step():
    steps = _build("ray-container-gpu")
    assert len(steps) == 1
    assert steps[0].env_var == "RAY_WORKER_COUNT"


def test_external_emits_address_step():
    steps = _build("ray-external")
    assert len(steps) == 1
    assert steps[0].env_var == "RAY_EXTERNAL_ADDRESS"


def test_disabled_emits_no_followup():
    steps = _build("disabled")
    assert steps == []


def test_worker_count_default_from_env():
    steps = _build("ray-container-cpu", env_overrides={"RAY_WORKER_COUNT": "5"})
    assert steps[0].default_value == 5
```

- [ ] **Step 5: Run the test — expect failures first**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run pytest tests/test_wizard_ray_steps.py -v 2>&1 | tail -15
```

Expected: import errors or attribute errors until your implementation from Step 3 lands.

- [ ] **Step 6: Iterate Step 3 + Step 5 until tests pass**

The test names define the contract. Adjust the function name, location, and parameter names to match what tests import. When all 5 tests pass, proceed.

- [ ] **Step 7: Run full pytest — confirm no regressions**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run pytest -q --tb=short 2>&1 | tail -3
```

Expected: 327 passed (322 + 5 new). 0 failures.

- [ ] **Step 8: Commit**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
git add bootstrapper/wizard/llm_steps.py bootstrapper/ui/textual/integration.py bootstrapper/tests/test_wizard_ray_steps.py
git commit -m "wizard: add Ray follow-up prompts (worker count integer + external address text)"
```

---

## Task 8: Add `ray` Python client dependency to Backend

**Files:**
- Modify: `services/backend/app/app/requirements.txt`

- [ ] **Step 1: Read the current requirements**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
cat services/backend/app/app/requirements.txt
```

Note where `ray` would fit alphabetically.

- [ ] **Step 2: Add the `ray` line**

Edit `services/backend/app/app/requirements.txt`. Add (in alphabetical position):

```
ray[client]>=2.55.1,<2.56
```

The `[client]` extra is the minimum subset needed for `JobSubmissionClient`. Pin to `<2.56` so client/server versions don't drift before we bump the image.

- [ ] **Step 3: Commit**

```bash
git add services/backend/app/app/requirements.txt
git commit -m "backend: add ray[client]>=2.55.1 dependency for Ray job submission"
```

---

## Task 9: Backend ray_client.py

**Files:**
- Create: `services/backend/app/app/ray_client.py`
- Reference: spec §8

- [ ] **Step 1: Create the file**

Write `services/backend/app/app/ray_client.py` with the content from spec §8 (the `ray_client.py` code block, verbatim — copy the full module body).

The module exposes:
- `class RayDisabledError(Exception)`
- `class RayClient` with `.get()` singleton, `.submit_job()`, `.get_job_status()`, `.get_job_logs()`, `.stop_job()`, `.cluster_status()`
- All methods raise `RayDisabledError` when `RAY_ADDRESS` is empty

- [ ] **Step 2: Verify Python imports cleanly**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/services/backend/app/app
python -c "import ray_client; print('ok')" 2>&1 | tail -3
```

Expected: `ok` (if ray Python package isn't installed locally, you'll see "No module named 'ray'" — that's fine; the imports inside RayClient._ensure_client are lazy). If you see a syntax error, fix it before proceeding.

- [ ] **Step 3: Commit**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
git add services/backend/app/app/ray_client.py
git commit -m "backend: add RayClient wrapper around ray.job_submission.JobSubmissionClient with RAY_ADDRESS-disabled handling"
```

---

## Task 10: Backend ray_routes.py + wire into main.py

**Files:**
- Create: `services/backend/app/app/ray_routes.py`
- Modify: `services/backend/app/app/main.py` (add `app.include_router(ray_router)`)

- [ ] **Step 1: Read main.py to understand the FastAPI app structure + existing router patterns**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
head -50 services/backend/app/app/main.py
grep -n "include_router\|APIRouter" services/backend/app/app/main.py
```

Expected: a few `include_router(...)` calls. Note the auth-dependency pattern (likely a `Depends(get_current_user)` or `Depends(verify_api_key)` shared across routers).

- [ ] **Step 2: Create `services/backend/app/app/ray_routes.py`**

Write the routes file. Use the same auth dependency that other backend routers use (read main.py for the exact pattern).

```python
"""FastAPI router for /api/ray/* — wraps the RayClient.

All endpoints require Backend's existing auth dependency. When Ray is
disabled (RAY_ADDRESS empty), every endpoint returns 503 with a clear
error message rather than 500.
"""

from __future__ import annotations

from typing import Any
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from .ray_client import RayClient, RayDisabledError

# Adjust the auth dependency import to match what main.py uses for
# other protected routers. Common patterns:
#   from .auth import get_current_user
#   from .auth import verify_api_key
# Read main.py + the existing auth module to pick the right one.
from .auth import verify_api_key  # placeholder — change to whatever exists

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ray", tags=["ray"], dependencies=[Depends(verify_api_key)])


class SubmitJobRequest(BaseModel):
    entrypoint: str = Field(..., description="Shell command to run on the Ray cluster.")
    runtime_env: dict[str, Any] | None = Field(
        default=None,
        description="Ray runtime_env dict (working_dir, pip, env_vars).",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Arbitrary metadata attached to the job.",
    )


class SubmitJobResponse(BaseModel):
    job_id: str


@router.post("/jobs/submit", response_model=SubmitJobResponse)
async def submit_job(payload: SubmitJobRequest) -> SubmitJobResponse:
    try:
        client = RayClient.get()
        job_id = client.submit_job(
            entrypoint=payload.entrypoint,
            runtime_env=payload.runtime_env,
            metadata=payload.metadata,
        )
        return SubmitJobResponse(job_id=job_id)
    except RayDisabledError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("ray submit_job failed")
        raise HTTPException(status_code=500, detail="Ray job submission failed")


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> dict:
    try:
        return RayClient.get().get_job_status(job_id)
    except RayDisabledError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("ray get_job_status failed")
        raise HTTPException(status_code=500, detail="Ray job status fetch failed")


@router.delete("/jobs/{job_id}")
async def stop_job(job_id: str) -> dict:
    try:
        stopped = RayClient.get().stop_job(job_id)
        return {"stopped": stopped}
    except RayDisabledError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("ray stop_job failed")
        raise HTTPException(status_code=500, detail="Ray job stop failed")


@router.get("/cluster/status")
async def cluster_status() -> dict:
    try:
        return RayClient.get().cluster_status()
    except RayDisabledError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        logger.exception("ray cluster_status failed")
        raise HTTPException(status_code=500, detail="Ray cluster status fetch failed")
```

If the auth-dependency import path differs from `.auth.verify_api_key`, find the right one by reading existing routers:

```bash
grep -n "Depends\(" services/backend/app/app/*.py | head -10
```

- [ ] **Step 3: Wire the router into main.py**

Find the existing `app.include_router(...)` calls in `main.py`. Add the Ray router using the same pattern:

```python
from .ray_routes import router as ray_router
# … existing routers …
app.include_router(ray_router)
```

- [ ] **Step 4: Verify the module imports without errors**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
python -c "
import sys
sys.path.insert(0, 'services/backend/app/app')
import ray_routes
print('routes module imports ok')
" 2>&1 | tail -3
```

Expected: `routes module imports ok` (with possible import warnings about ray not being installed locally — that's fine since RayClient defers ray imports).

- [ ] **Step 5: Commit**

```bash
git add services/backend/app/app/ray_routes.py services/backend/app/app/main.py
git commit -m "backend: add /api/ray/* router (submit/status/stop/cluster-status) with 503-on-disabled semantics"
```

---

## Task 11: Backend test scaffolding (conftest + __init__)

**Files:**
- Create: `services/backend/app/app/tests/__init__.py`
- Create: `services/backend/app/app/tests/conftest.py`

- [ ] **Step 1: Create the tests directory**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
mkdir -p services/backend/app/app/tests
touch services/backend/app/app/tests/__init__.py
```

- [ ] **Step 2: Create conftest.py with shared fixtures**

Write `services/backend/app/app/tests/conftest.py`:

```python
"""Shared pytest fixtures for the Backend app's tests.

The Backend has historically had no test files (P1 audit finding earlier
this branch). This is the bootstrap for that — Ray's job-submission
surface is the first real test suite. Follow the patterns established
here for future Backend test work.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def ray_disabled_env(monkeypatch):
    """Force RAY_ADDRESS empty → RayClient raises RayDisabledError on any call."""
    monkeypatch.setenv("RAY_ADDRESS", "")
    # Reset the singleton so the new env takes effect.
    from app import ray_client  # type: ignore
    ray_client.RayClient._instance = None
    yield
    ray_client.RayClient._instance = None


@pytest.fixture
def ray_enabled_env(monkeypatch):
    """Set RAY_ADDRESS to a fake URL → RayClient will attempt to use it."""
    monkeypatch.setenv("RAY_ADDRESS", "ray://ray-head:10001")
    monkeypatch.setenv("RAY_DASHBOARD_URL", "http://ray-head:8265")
    from app import ray_client  # type: ignore
    ray_client.RayClient._instance = None
    yield
    ray_client.RayClient._instance = None


@pytest.fixture
def mock_job_submission_client(monkeypatch):
    """Stand in for ray.job_submission.JobSubmissionClient. Configure
    methods per-test via `mock_job_submission_client.return_value.submit_job.return_value = "..."`."""
    mock_class = MagicMock()
    monkeypatch.setattr(
        "ray.job_submission.JobSubmissionClient",
        mock_class,
        raising=False,
    )
    return mock_class


@pytest.fixture
def fastapi_client(ray_enabled_env, mock_job_submission_client):
    """A TestClient bound to the Backend app, with Ray-enabled env + mocked
    JobSubmissionClient. Bypasses auth via dependency_overrides."""
    from fastapi.testclient import TestClient
    from app.main import app  # type: ignore
    # Bypass the auth dependency in tests.
    from app.auth import verify_api_key  # type: ignore — adjust to actual import
    app.dependency_overrides[verify_api_key] = lambda: {"sub": "test-user"}
    yield TestClient(app)
    app.dependency_overrides.clear()
```

If `verify_api_key` isn't the actual dependency name in Backend, adjust to whatever you found in Task 10 Step 2.

- [ ] **Step 3: Commit**

```bash
git add services/backend/app/app/tests/__init__.py services/backend/app/app/tests/conftest.py
git commit -m "backend: add pytest scaffolding (tests/__init__.py + conftest.py with Ray fixtures)"
```

---

## Task 12: Backend ray_client tests

**Files:**
- Create: `services/backend/app/app/tests/test_ray_client.py`

- [ ] **Step 1: Write the test file**

Create `services/backend/app/app/tests/test_ray_client.py`:

```python
"""Tests for RayClient (services/backend/app/app/ray_client.py).

Covers:
- Disabled-when-empty: RAY_ADDRESS="" makes every method raise RayDisabledError.
- Address-derivation: ray://ray-head:10001 → dashboard URL http://ray-head:8265.
- Override: RAY_DASHBOARD_URL takes precedence over derivation.
- submit_job calls through to the underlying JobSubmissionClient.
- get/stop/cluster also call through correctly.
"""

from __future__ import annotations

import pytest

from app.ray_client import RayClient, RayDisabledError, _ray_address  # type: ignore


def test_ray_address_empty_returns_none(monkeypatch):
    monkeypatch.setenv("RAY_ADDRESS", "")
    monkeypatch.delenv("RAY_DASHBOARD_URL", raising=False)
    assert _ray_address() is None


def test_ray_address_lan_form_returns_http(monkeypatch):
    monkeypatch.setenv("RAY_ADDRESS", "ray://ray-head:10001")
    monkeypatch.delenv("RAY_DASHBOARD_URL", raising=False)
    assert _ray_address() == "http://ray-head:8265"


def test_ray_address_external_returns_https(monkeypatch):
    monkeypatch.setenv("RAY_ADDRESS", "ray://my-cluster.anyscale.com:10001")
    monkeypatch.delenv("RAY_DASHBOARD_URL", raising=False)
    assert _ray_address() == "https://my-cluster.anyscale.com:8265"


def test_ray_dashboard_url_override(monkeypatch):
    """Explicit RAY_DASHBOARD_URL wins over derivation."""
    monkeypatch.setenv("RAY_ADDRESS", "ray://ray-head:10001")
    monkeypatch.setenv("RAY_DASHBOARD_URL", "https://custom-ray.example.com")
    assert _ray_address() == "https://custom-ray.example.com"


def test_submit_job_disabled(ray_disabled_env):
    client = RayClient.get()
    with pytest.raises(RayDisabledError):
        client.submit_job(entrypoint="echo hi")


def test_get_job_status_disabled(ray_disabled_env):
    with pytest.raises(RayDisabledError):
        RayClient.get().get_job_status("job_xyz")


def test_stop_job_disabled(ray_disabled_env):
    with pytest.raises(RayDisabledError):
        RayClient.get().stop_job("job_xyz")


def test_cluster_status_disabled(ray_disabled_env):
    with pytest.raises(RayDisabledError):
        RayClient.get().cluster_status()


def test_submit_job_succeeds_when_enabled(ray_enabled_env, mock_job_submission_client):
    mock_instance = mock_job_submission_client.return_value
    mock_instance.submit_job.return_value = "raysubmit_abc123"
    client = RayClient.get()
    job_id = client.submit_job(entrypoint="echo hi")
    assert job_id == "raysubmit_abc123"
    mock_instance.submit_job.assert_called_once()


def test_get_job_status_succeeds_when_enabled(ray_enabled_env, mock_job_submission_client):
    from types import SimpleNamespace
    mock_instance = mock_job_submission_client.return_value
    mock_status = SimpleNamespace(value="SUCCEEDED")
    mock_info = SimpleNamespace(__dict__={"status": "SUCCEEDED", "entrypoint": "echo hi"})
    mock_instance.get_job_status.return_value = mock_status
    mock_instance.get_job_info.return_value = mock_info
    result = RayClient.get().get_job_status("job_xyz")
    assert result["job_id"] == "job_xyz"
    assert result["status"] == "SUCCEEDED"
```

- [ ] **Step 2: Run the tests**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/services/backend/app/app
# Backend needs ray + fastapi + pytest in the test env. If running outside
# the backend container, install: pip install ray[client] fastapi pytest httpx
pytest tests/test_ray_client.py -v 2>&1 | tail -20
```

Expected: 10 passed. If `ray` isn't installed in the local Python, the tests using `mock_job_submission_client` may need additional setup — the `monkeypatch.setattr("ray.job_submission.JobSubmissionClient", ...)` requires the `ray` module to be importable. If unavailable locally, document this and move on; CI can run these tests in the Backend's container env.

- [ ] **Step 3: Commit**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
git add services/backend/app/app/tests/test_ray_client.py
git commit -m "backend: add RayClient unit tests covering disabled + enabled + address-derivation"
```

---

## Task 13: Backend ray_routes tests

**Files:**
- Create: `services/backend/app/app/tests/test_ray_routes.py`

- [ ] **Step 1: Write the routes test file**

Create `services/backend/app/app/tests/test_ray_routes.py`:

```python
"""Tests for /api/ray/* (services/backend/app/app/ray_routes.py).

Covers:
- 503 on disabled: when RAY_ADDRESS empty, every endpoint returns 503.
- 200 on enabled: submit returns job_id, status returns status payload, etc.
- 500 on unexpected errors (RayClient method raising a non-RayDisabledError).
"""

from __future__ import annotations

import pytest


def test_submit_returns_503_when_ray_disabled(ray_disabled_env, fastapi_client):
    # Note: ray_disabled_env conflicts with ray_enabled_env; this test uses
    # disabled, the fastapi_client fixture's ray_enabled_env runs after.
    # To handle this cleanly, override env manually here instead.
    import os
    os.environ["RAY_ADDRESS"] = ""
    from app import ray_client
    ray_client.RayClient._instance = None
    resp = fastapi_client.post(
        "/api/ray/jobs/submit",
        json={"entrypoint": "echo hi"},
    )
    assert resp.status_code == 503
    assert "not enabled" in resp.json()["detail"].lower() or "disabled" in resp.json()["detail"].lower()


def test_submit_returns_200_when_ray_enabled(fastapi_client, mock_job_submission_client):
    mock_instance = mock_job_submission_client.return_value
    mock_instance.submit_job.return_value = "raysubmit_abc"
    resp = fastapi_client.post(
        "/api/ray/jobs/submit",
        json={"entrypoint": "python -c 'print(1)'"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"job_id": "raysubmit_abc"}


def test_get_status_returns_200_when_enabled(fastapi_client, mock_job_submission_client):
    from types import SimpleNamespace
    mock_instance = mock_job_submission_client.return_value
    mock_instance.get_job_status.return_value = SimpleNamespace(value="RUNNING")
    mock_instance.get_job_info.return_value = SimpleNamespace(__dict__={"status": "RUNNING"})
    resp = fastapi_client.get("/api/ray/jobs/raysubmit_abc")
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == "raysubmit_abc"
    assert body["status"] == "RUNNING"


def test_stop_job_returns_200_when_enabled(fastapi_client, mock_job_submission_client):
    mock_instance = mock_job_submission_client.return_value
    mock_instance.stop_job.return_value = True
    resp = fastapi_client.delete("/api/ray/jobs/raysubmit_abc")
    assert resp.status_code == 200
    assert resp.json() == {"stopped": True}


def test_invalid_payload_returns_422(fastapi_client):
    """Missing the required `entrypoint` field → FastAPI returns 422 unproc."""
    resp = fastapi_client.post("/api/ray/jobs/submit", json={})
    assert resp.status_code == 422
```

- [ ] **Step 2: Run the tests**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/services/backend/app/app
pytest tests/test_ray_routes.py -v 2>&1 | tail -20
```

Expected: 5 passed. If errors about httpx or other test deps, install: `pip install httpx fastapi[testing] pytest`.

- [ ] **Step 3: Run ALL Backend tests + verify total count**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/services/backend/app/app
pytest tests/ -v 2>&1 | tail -5
```

Expected: 15 passed (10 ray_client + 5 ray_routes).

- [ ] **Step 4: Commit**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
git add services/backend/app/app/tests/test_ray_routes.py
git commit -m "backend: add Ray-routes integration tests (FastAPI TestClient + mocked JobSubmissionClient)"
```

---

## Task 14: Backend service.yml — add `runtime_adaptive.adapts_to: [ray]` + `data_flow.calls: [ray]`

**Files:**
- Modify: `services/backend/service.yml`

- [ ] **Step 1: Open and inspect the current backend manifest**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
grep -A20 "^runtime_adaptive:" services/backend/service.yml
grep -A5 "^data_flow:" services/backend/service.yml
```

Note the existing `adapts_to:` list and `environment_adaptation:` map.

- [ ] **Step 2: Add `ray` to runtime_adaptive.adapts_to + RAY_ADDRESS to environment_adaptation**

Use Edit on `services/backend/service.yml`:

`old_string`:
```yaml
runtime_adaptive:
  backend:
    adapts_to:
    - llm_provider
    - weaviate
    - stt_provider
    - tts_provider
    - doc_processor
    environment_adaptation:
      LITELLM_BASE_URL: http://litellm:4000
      LITELLM_API_KEY: ${LITELLM_MASTER_KEY}
      WEAVIATE_URL: http://weaviate:8080
      STT_ENDPOINT: ${STT_ENDPOINT}
      TTS_ENDPOINT: ${TTS_ENDPOINT}
      DOCLING_ENDPOINT: ${DOCLING_ENDPOINT}
    extra_hosts_adaptation: inherit from llm_provider
```

`new_string`:
```yaml
runtime_adaptive:
  backend:
    adapts_to:
    - llm_provider
    - weaviate
    - stt_provider
    - tts_provider
    - doc_processor
    - ray
    environment_adaptation:
      LITELLM_BASE_URL: http://litellm:4000
      LITELLM_API_KEY: ${LITELLM_MASTER_KEY}
      WEAVIATE_URL: http://weaviate:8080
      STT_ENDPOINT: ${STT_ENDPOINT}
      TTS_ENDPOINT: ${TTS_ENDPOINT}
      DOCLING_ENDPOINT: ${DOCLING_ENDPOINT}
      RAY_ADDRESS: ${RAY_ADDRESS}
    extra_hosts_adaptation: inherit from llm_provider
```

(If the actual content differs slightly, adapt — but the change is: add `- ray` to `adapts_to` and `RAY_ADDRESS: ${RAY_ADDRESS}` to `environment_adaptation`.)

- [ ] **Step 3: Add `ray` to `data_flow.calls`**

`old_string`:
```yaml
data_flow:
  calls:
    - supabase
    - redis
    - weaviate
    - neo4j
    - litellm
    - hermes
    - comfyui
    - stt-provider
    - tts-provider
    - doc-processor
    - n8n
```

`new_string`:
```yaml
data_flow:
  calls:
    - supabase
    - redis
    - weaviate
    - neo4j
    - litellm
    - hermes
    - comfyui
    - stt-provider
    - tts-provider
    - doc-processor
    - n8n
    - ray
```

- [ ] **Step 4: Re-validate the manifest**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run python -m tools.validate_fragments
uv run pytest -q --tb=short 2>&1 | tail -3
```

Expected: validator OK; full pytest still green (327 + 10 backend tests if those count = 337, but Backend tests run separately — pytest total likely stays at 327 from bootstrapper suite).

- [ ] **Step 5: Commit**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
git add services/backend/service.yml
git commit -m "backend: add runtime_adaptive ray + data_flow.calls ray entries"
```

---

## Task 15: JupyterHub — add `ray` dep + manifest update + seed notebook

**Files:**
- Modify: `services/jupyterhub/build/requirements.txt`
- Modify: `services/jupyterhub/service.yml`
- Create: `services/jupyterhub/notebooks/hello-ray.ipynb`

- [ ] **Step 1: Add `ray[client]` to JupyterHub's build requirements**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
cat services/jupyterhub/build/requirements.txt | head -20
```

Edit `services/jupyterhub/build/requirements.txt`. Add (in alphabetical position, likely near the bottom of the AI/ML section):

```
ray[client]>=2.55.1,<2.56
```

- [ ] **Step 2: Update JupyterHub manifest — add `ray` to runtime_adaptive + data_flow.calls**

Open `services/jupyterhub/service.yml`. Find its `runtime_adaptive` block (if present — JupyterHub may not have one yet; the bootstrapper supports adding new entries to existing manifests).

If JupyterHub already has a `runtime_adaptive.jupyterhub` block, add `- ray` to `adapts_to` and `RAY_ADDRESS: ${RAY_ADDRESS}` to `environment_adaptation`, same shape as Backend's Task 14 Step 2.

If JupyterHub has NO `runtime_adaptive` block, add one:

```yaml
runtime_adaptive:
  jupyterhub:
    adapts_to:
    - ray
    environment_adaptation:
      RAY_ADDRESS: ${RAY_ADDRESS}
```

Place it adjacent to wherever the manifest currently lives (typically after `rows:` / `exports:` / before `runtime_sc:`).

Also add `ray` to `data_flow.calls`:

```yaml
data_flow:
  calls:
    - supabase
    - redis
    - litellm
    # ... existing entries
    - ray  # NEW
```

- [ ] **Step 3: Create the seed notebook**

```bash
mkdir -p services/jupyterhub/notebooks
```

Create `services/jupyterhub/notebooks/hello-ray.ipynb` — a minimal Jupyter notebook in JSON form:

```json
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Hello Ray\n\nA minimal example showing how to connect to the in-stack Ray cluster from a JupyterHub notebook.\n\nThe `RAY_ADDRESS` environment variable is set automatically when Ray is enabled — `ray.init(address=\"auto\")` picks it up.\n\nIf Ray is disabled, this notebook errors out with a clear message."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import os\n",
    "import ray\n\n",
    "ray_address = os.environ.get(\"RAY_ADDRESS\", \"\").strip()\n",
    "if not ray_address:\n",
    "    raise RuntimeError(\n",
    "        \"RAY_ADDRESS is not set — Ray is disabled in this deployment. \"\n",
    "        \"Re-run ./start.sh --ray-source ray-container-cpu (or ray-container-gpu) to enable it.\"\n",
    "    )\n\n",
    "ray.init(address=\"auto\")\n",
    "print(\"cluster resources:\", ray.cluster_resources())"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "@ray.remote\n",
    "def double(x):\n",
    "    return x * 2\n\n",
    "results = ray.get([double.remote(i) for i in range(10)])\n",
    "print(results)"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Next steps\n\nSee `services/ray/README.md` for the full configuration reference. The dashboard is reachable at `http://ray.localhost:KONG_HTTP_PORT` (basic-auth: `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD`) or `http://localhost:RAY_DASHBOARD_PORT` directly."
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.x"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
```

- [ ] **Step 4: Verify the notebook is valid JSON**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
python -c "import json; json.load(open('services/jupyterhub/notebooks/hello-ray.ipynb')); print('ok')"
```

Expected: `ok`. Notebook validators are strict about JSON shape; any syntax errors will show up here.

- [ ] **Step 5: Wire the notebooks/ folder into JupyterHub's bind mounts**

The seed notebook needs to land in users' notebook directories. Look at how `services/jupyterhub/compose.yml` mounts user-content directories today:

```bash
grep -A3 "volumes:" services/jupyterhub/compose.yml | head -10
```

If there's already a bind mount for sample notebooks (e.g. `./notebooks:/home/jovyan/samples`), the new file lands there automatically. If not, add a new bind mount line. Document the decision in the README.

- [ ] **Step 6: Re-validate + run tests**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run python -m tools.validate_fragments
uv run pytest -q --tb=short 2>&1 | tail -3
```

Expected: validator OK; pytest still green.

- [ ] **Step 7: Commit**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
git add services/jupyterhub/
git commit -m "jupyterhub: add ray[client] dep + runtime_adaptive ray + seed hello-ray.ipynb notebook"
```

---

## Task 16: Hermes manifest update (data_flow.calls only — no code)

**Files:**
- Modify: `services/hermes/service.yml`

- [ ] **Step 1: Inspect current hermes data_flow.calls**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
grep -A20 "^data_flow:" services/hermes/service.yml | head -25
```

- [ ] **Step 2: Add `ray` to hermes's `data_flow.calls`**

Edit `services/hermes/service.yml`. Find the `data_flow.calls` list and append `- ray`.

If hermes's data_flow.calls doesn't already include `backend`, add that too (the spec assumes Hermes reaches Ray via Backend's REST API).

- [ ] **Step 3: Re-validate**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run python -m tools.validate_fragments
uv run pytest -q --tb=short 2>&1 | tail -3
```

Expected: validator OK; tests green.

- [ ] **Step 4: Commit**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
git add services/hermes/service.yml
git commit -m "hermes: add ray + backend to data_flow.calls (agents reach Ray via Backend REST)"
```

---

## Task 17: Regenerate all auto-artifacts after manifest changes

**Files:**
- Modify (auto): `.env.example`, `README.md` TOPOLOGY block, `docs/diagrams/architecture.{dot,svg}`, all `services/*/architecture.{svg,html}` and `services/*/README.md` Dependencies & Integrations blocks

- [ ] **Step 1: Run all four regen commands in order**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run python -m services.env_assembler 2>&1 | tail -2
uv run python -m tools.generate_readme_topology 2>&1 | tail -2
uv run python -m tools.generate_architecture_diagram 2>&1 | tail -2
dot -Tsvg ../docs/diagrams/architecture.dot > ../docs/diagrams/architecture.svg
PYTHONPATH=. uv run python -m docs.regen --all 2>&1 | tail -5
```

Expected: each command succeeds with no errors. The per-service `Dependencies & Integrations` blocks update across `services/backend/README.md`, `services/jupyterhub/README.md`, `services/hermes/README.md`, and `services/ray/README.md` to reflect the new `data_flow.calls` edges.

- [ ] **Step 2: Verify validate_fragments passes**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run python -m tools.validate_fragments
```

Expected: `OK — 25 manifest(s) validated.`

- [ ] **Step 3: Verify regen drift gate passes**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
PYTHONPATH=bootstrapper uv run --project bootstrapper python -m bootstrapper.docs.regen --all --check
echo "Exit: $?"
```

Expected: exit 0.

- [ ] **Step 4: Run check_doc_links**

```bash
python scripts/check_doc_links.py
```

Expected: exit 0.

- [ ] **Step 5: Commit all generated artifacts**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
git add -A
git status -s | head -30
# Review the diff list before committing — should be README updates, env.example, architecture.dot/svg, per-service deps blocks
git commit -m "ray: regenerate all auto-artifacts after manifest cross-edges (data_flow.calls additions)"
```

---

## Task 18: Regenerate compose-equivalence golden baseline

**Files:**
- Modify: `bootstrapper/tests/fixtures/rendered_config_baseline.yml`

- [ ] **Step 1: Inspect the byte-equivalence test and how the baseline is regenerated**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
grep -n "rendered_config_baseline\|_strip_volatile_defaults\|regenerate" bootstrapper/tests/test_fragment_equivalence.py | head -10
```

Memory note `project_compose_baseline_test` reminds: don't regenerate the baseline reflexively — extend `_strip_volatile_defaults` if the diff is just Compose-version churn. But for a new SERVICE addition, regenerating is the correct move.

- [ ] **Step 2: Run the byte-equivalence test and capture the diff**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run pytest tests/test_fragment_equivalence.py -v 2>&1 | tail -30
```

Expected: FAIL. The diff should show the new `ray-head` / `ray-worker` services + `ray-tmp` / `ray-tmp-worker` volumes appearing in the rendered output. Confirm the diff is exactly that — no surprises in other services.

- [ ] **Step 3: Regenerate the baseline**

Look at how the baseline is generated. Typically there's a helper:

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
cp .env.example .env  # materialize for compose
cd bootstrapper
uv run python -c "
import yaml, subprocess
from tests.test_fragment_equivalence import _strip_volatile_defaults
result = subprocess.run(
    ['docker', 'compose', '-f', '../docker-compose.yml', '--env-file', '../.env', 'config'],
    capture_output=True, text=True, check=True,
)
data = yaml.safe_load(result.stdout)
data = _strip_volatile_defaults(data)
with open('tests/fixtures/rendered_config_baseline.yml', 'w') as f:
    yaml.safe_dump(data, f, sort_keys=True)
print('Baseline regenerated')
"
```

If the test file has a `--regen` argparse flag or a helper script, use that instead — it's the canonical path.

- [ ] **Step 4: Re-run the byte-equivalence test**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run pytest tests/test_fragment_equivalence.py -v 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Run the source-permutation matrix test (slow — 10+ minutes)**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run pytest tests/test_source_permutations.py -v 2>&1 | tail -10
```

Expected: PASS for every Ray source variant (`ray-container-cpu`, `ray-container-gpu`, `ray-external`, `disabled`). If a permutation fails, the diff shows what's missing — typically a forgotten `runtime_sc.<source>` block.

- [ ] **Step 6: Commit the regenerated baseline**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
git add bootstrapper/tests/fixtures/rendered_config_baseline.yml
git commit -m "ray: regenerate compose-equivalence golden baseline to include ray-head + ray-worker"
```

---

## Task 19: Final verification + audit-gate sweep

**Files:**
- No new files. Verification + commits if any small fixes shake out.

- [ ] **Step 1: Run the full pytest suite from bootstrapper/**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run pytest -q --tb=short 2>&1 | tail -5
```

Expected: 327+ passed (315 baseline + 7 from Task 3 + 5 from Task 7). Backend's own test suite (Tasks 11–13) runs separately and isn't counted here unless CI is wired to include it.

- [ ] **Step 2: Run all five audit scripts + the docs-drift gate**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
python scripts/check_doc_links.py; echo "doc-links: $?"
python scripts/check-compose-source-deps.py 2>&1 | tail -3; echo "compose-source-deps: $?"
python scripts/check-docs-drift.py 2>&1 | tail -5; echo "docs-drift: $?"
python scripts/check-kong-routes.py 2>&1 | tail -3; echo "kong-routes: $?"
python scripts/validate_research_schema.py --all 2>&1 | tail -3; echo "research-schema: $?"
PYTHONPATH=bootstrapper uv run --project bootstrapper python -m bootstrapper.docs.regen --all --check; echo "regen-check: $?"
```

Expected: all six commands exit 0.

- [ ] **Step 3: Run validate_fragments + compose merge sanity**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run python -m tools.validate_fragments
cd ..
cp .env.example .env
docker compose -f docker-compose.yml config -q; echo "compose-config: $?"
```

Expected: validator OK; compose config exit 0.

- [ ] **Step 4: Manual smoke (optional but recommended) — actually start Ray and verify the dashboard works**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
./stop.sh 2>&1 | tail -3  # only if you have a previous run
./start.sh --ray-source ray-container-cpu --ray-worker-count 2 --no-tui 2>&1 | tail -20
```

Then:

```bash
# Dashboard direct
curl -sf "http://localhost:$(grep ^RAY_DASHBOARD_PORT .env | cut -d= -f2)/api/version" | head
# Expected: {"version": "2.55.1", ...}

# Client port reachable
python -c "import ray; ray.init(address='ray://localhost:$(grep ^RAY_CLIENT_PORT .env | cut -d= -f2)'); print(ray.cluster_resources()); ray.shutdown()"
# Expected: cluster resources dict with CPU + worker count

# Backend /api/ray/cluster/status (with valid auth)
# ... use the Backend's auth scheme — likely an X-API-Key header
```

If the manual smoke fails, the diff is small enough to bisect tasks. Fix and commit any small adjustments needed.

- [ ] **Step 5: Tear down the smoke test**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
./stop.sh 2>&1 | tail -3
```

(Per memory, never use `./stop.sh --cold` reflexively — only when explicitly needed.)

- [ ] **Step 6: Final commit (if any fixes shook out)**

```bash
git status -s
# If anything modified beyond Task 18's commit, stage + commit with a tight message
git add -A
git commit -m "ray: final verification fixes" --allow-empty-message
# Or skip if nothing to commit
```

---

## Task 20: Rebase + fast-forward into main

**Files:**
- Branch operations only

- [ ] **Step 1: Update main with any remote changes**

```bash
cd /Users/kaveh/repos/genai-vanilla
git fetch origin
git checkout main
git pull --ff-only origin main
```

Expected: clean fast-forward or "Already up to date".

- [ ] **Step 2: Rebase the worktree branch onto main**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster
git rebase main
```

Expected: clean rebase. If conflicts arise, resolve them carefully — the most likely conflict zones are `.env.example` and README TOPOLOGY block (both auto-generated; regenerate them post-rebase rather than hand-resolving).

- [ ] **Step 3: Run full audit gate one more time post-rebase**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/add-ray-cluster/bootstrapper
uv run pytest -q --tb=short 2>&1 | tail -3
uv run python -m tools.validate_fragments
```

Expected: all green.

- [ ] **Step 4: Fast-forward main**

```bash
cd /Users/kaveh/repos/genai-vanilla
git checkout main
git merge --ff-only add-ray-cluster
git log --oneline origin/main..HEAD | head -25
echo "---"
git log --oneline origin/main..HEAD | wc -l
```

Expected: 18-20 new commits on main (one per task), all `ray:` / `backend:` / `jupyterhub:` / `wizard:` / `hermes:` / `docs:` prefixed.

- [ ] **Step 5: Push to origin/main**

Per the user's prior pattern: explicit push to `main` is authorized (`/loop` / "push it" pattern from memory + recent session). Confirm one more time the working tree is clean + diff makes sense, then:

```bash
git push origin main 2>&1 | tail -5
```

Expected: clean push, no force, no rejects.

- [ ] **Step 6: Clean up the worktree**

```bash
cd /Users/kaveh/repos/genai-vanilla
git worktree remove .claude/worktrees/add-ray-cluster
git branch -d add-ray-cluster
```

Expected: worktree removed, local branch deleted (was merged into main).

- [ ] **Step 7: Verify CI is green on origin/main**

```bash
sleep 30  # wait for CI to start
gh run list --workflow=services-lint.yml --limit 1
```

Expected: latest run is queued or in_progress. After ~3-5 minutes:

```bash
gh run watch  # or
until gh run view --json status,conclusion -q '"\(.status)|\(.conclusion)"' 2>/dev/null | grep -q "completed"; do sleep 30; done
gh run view --json status,conclusion,jobs -q '{status, conclusion, jobs: [.jobs[] | {name, conclusion}]}'
```

Expected: all three CI jobs (`Manifest lint + unit tests`, `Compose merge + byte-equivalence + source-permutation matrix`, `Docs drift + audit scripts`) green.

If any job fails, that's the smoke test for whatever local check missed — investigate, fix, and re-push.

---

## Self-Review

### Spec coverage matrix (spec §X → plan Task N)

| Spec section | Task |
|---|---|
| §3 Pre-flight facts | T1 (manifest reflects facts) |
| §4 Decisions 1–5 | T1 (manifest fields), T2 (compose) |
| §4 Decision 6 (hook) | T3 (_generate_ray_config + tests) |
| §5 Manifest shape | T1 |
| §5 Compose shape | T2 |
| §6 Wizard integration | T7 |
| §7 Kong + hosts | T6 |
| §8 Backend REST | T8 (deps), T9 (client), T10 (routes), T11 (test scaffold), T12-13 (tests), T14 (manifest) |
| §9 JupyterHub wiring | T15 |
| §10 Hermes manifest | T16 |
| §11 Topology + ports | T4 (regen .env.example) |
| §12 Audit-script + CI | T6 (kong-routes script), T19 (full sweep) |
| §13 README TOPOLOGY | T4 |
| §14 Architecture diagram | T4, T17 |
| §15 Per-service docs | T5 |
| §17 Acceptance criteria 1–4 | T19 manual smoke (steps 4) |
| §17 Acceptance criteria 5–7 | T19 (audit gates), T18 (compose-equivalence) |
| §17 Acceptance criteria 8–13 | T17 (regen-check), T19 (gates) |
| §17 Acceptance criterion 14 | T20 (push) |
| §18 Implementation order | All tasks ordered per spec §18 |

No spec section unmapped to a task. No placeholders in the plan body. Method signatures are consistent across tasks (`_generate_ray_config(source_value, shared_env) -> dict`, `RayClient.get().submit_job(entrypoint, runtime_env, metadata) -> str`, etc.).

### Placeholder scan

Searched the plan for "TBD", "TODO", "implement later", "Add appropriate", "Similar to Task". Found one acceptable "TBD"-adjacent phrase: "use the same helper" in Task 6 Step 2 — this is a reasonable instruction (follow the existing pattern) since the helper name is locale-specific (e.g. `_add_dashboard_route` may differ in actual code). Engineer is told to read kong_config_generator.py first to identify the right helper, so this is not a placeholder.

### Type consistency

- `_generate_ray_config(self, source_value: str, shared_env: dict) -> dict` — Task 3 defines, Tasks 4 and 17 reference. Consistent.
- `RayClient.get().submit_job(entrypoint, runtime_env, metadata) -> str` — Task 9 defines, Tasks 12 and 13 reference. Consistent.
- `RAY_ADDRESS` semantics: `"ray://ray-head:10001"` (container), `${RAY_EXTERNAL_ADDRESS}` (external), `""` (disabled). Task 3 hook implements; Tasks 8, 9, 14, 15 reference. Consistent.
- Test fixture names (`ray_disabled_env`, `ray_enabled_env`, `mock_job_submission_client`, `fastapi_client`) defined in Task 11, used in Tasks 12 and 13. Consistent.
