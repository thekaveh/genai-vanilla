# Plan B — Production Hardening Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `prod` deployment profile to the bootstrapper that (1) confines all service host-port bindings to `127.0.0.1` (so only the public edge is reachable), (2) enforces memory/CPU limits on the heavy services, (3) turns Docker log rotation on, and (4) defaults Prometheus + Grafana on — all opt-in, with zero change to the default (dev) behaviour. The profile is selectable BOTH via `--profile prod` AND an equivalent **wizard step**, and in prod the wizard hides — and the CLI validator rejects — every `localhost` source variant (e.g. `ollama-localhost`, `parakeet-localhost`, ComfyUI/Neo4j/Weaviate `localhost`), which is meaningless on a remote host.

**Architecture:** A single global env var `HOST_BIND_IP` (default empty → `0.0.0.0`) is prefixed onto every published port in every fragment (`"${HOST_BIND_IP:-}${X_PORT}:CONTAINER"`). The resolved profile (from the wizard step OR `--profile prod`) writes `HOST_BIND_IP=127.0.0.1:` into `.env`, flips `PROMETHEUS_SOURCE`/`GRAFANA_SOURCE` to `container` (unless overridden), sets the `*_MEMORY_LIMIT`/`*_CPU_LIMIT` vars, and sets log-rotation vars consumed by per-fragment `logging:` blocks. This avoids Compose's port-merge limitation (you can't *remove* a published port via an override file) by changing emission at the env layer, which is the only clean mechanism. The wizard profile step mirrors the existing TRACK picker; prod source-filtering happens at the wizard option-builder and in the source validator. `container-gpu` is NOT auto-disabled in prod (that is a host-capability concern, not a profile one) — a separate optional guard, noted but out of scope here.

**Tech Stack:** Click CLI in `bootstrapper/start.py`; env writing via the existing source-override/env path; Compose interpolation; pytest + the fragment byte-equivalence baseline.

## Global Constraints

- `main` is protected — PR with 3 green checks; no direct push.
- Commits: terse third-person, no emoji, no Claude trailer.
- `.env.example` is generated; new vars are declared in a manifest (use the virtual `services/globals/` manifest for cross-cutting vars like `HOST_BIND_IP`) and emitted by `env_assembler`.
- Editing every fragment's `ports:` line changes rendered config → the byte-equivalence baseline (`bootstrapper/tests/fixtures/rendered_config_baseline.yml`) MUST be regenerated; with `HOST_BIND_IP` unset the rendered output must be **identical** to today (the `${HOST_BIND_IP:-}` prefix resolves to empty), so a correct change yields ZERO baseline diff in dev mode — verify that.
- Resource-limit pattern mirrors `services/hermes/compose.yml` (`deploy.resources.limits.memory/cpus` driven by `*_MEMORY_LIMIT`/`*_CPU_LIMIT` env vars).
- Kong's compose service id is `kong-api-gateway`.

---

### Task 1: `HOST_BIND_IP` global var + prefix all published ports

**Files:**
- Modify: `services/globals/service.yml` (declare `HOST_BIND_IP`)
- Modify: every `services/*/compose.yml` that publishes a host port (~24 fragments)
- Modify (generated): `.env.example`, `bootstrapper/tests/fixtures/rendered_config_baseline.yml`
- Test: `bootstrapper/tests/test_fragment_equivalence.py`, `tests/test_env_assembler.py`

**Interfaces:**
- Produces: env var `HOST_BIND_IP` (default `""`); every published port becomes `"${HOST_BIND_IP:-}${X_PORT}:CONTAINER"`.

- [ ] **Step 1: Declare `HOST_BIND_IP` in the globals manifest**

Add to `services/globals/service.yml` `env:`:
```yaml
  - name: HOST_BIND_IP
    default: ""
    description: |
      Host interface prefix for ALL published service ports. Empty (default)
      => Docker binds 0.0.0.0 (dev). `--profile prod` sets this to
      "127.0.0.1:" so service ports are reachable only from the host (the
      public edge — Cloudflare Tunnel or Caddy — reaches Kong locally).
      Must include the trailing colon when set, e.g. "127.0.0.1:".
```

- [ ] **Step 2: Prefix every published port**

For EACH fragment under `services/*/compose.yml`, change every published port from `"${X_PORT}:NNNN"` to `"${HOST_BIND_IP:-}${X_PORT}:NNNN"`. Example (`services/redis/compose.yml`):
```yaml
    ports:
      - "${HOST_BIND_IP:-}${REDIS_PORT}:6379"
```
And Kong (`services/kong/compose.yml`) — Kong ALSO gets the prefix, because in the tunnel model the edge reaches Kong on `127.0.0.1`:
```yaml
    ports:
      - "${HOST_BIND_IP:-}${KONG_HTTP_PORT}:8000/tcp"
      - "${HOST_BIND_IP:-}${KONG_HTTPS_PORT}:8443/tcp"
```
Do this mechanically for all `"${*_PORT}:` lines. A grep to find them all:
```bash
grep -rn '"\${[A-Z0-9_]*_PORT[^}]*}:' services/*/compose.yml
```

- [ ] **Step 3: Regenerate `.env.example` and verify ZERO dev-mode config drift**

```bash
cd bootstrapper && uv run python -m services.env_assembler
cd /Users/kaveh/repos/genai-vanilla && docker compose -f docker-compose.yml config > /tmp/after.yml
git stash && docker compose -f docker-compose.yml config > /tmp/before.yml && git stash pop
diff /tmp/before.yml /tmp/after.yml
```
Expected: **empty diff** (with `HOST_BIND_IP` unset, `${HOST_BIND_IP:-}` → empty, so rendered ports are byte-identical). If the diff is non-empty, a port line was rewritten incorrectly — fix before proceeding.

- [ ] **Step 4: Run env + fragment tests**

Run: `cd bootstrapper && uv run pytest tests/test_env_assembler.py tests/test_env_example_consistency.py tests/test_fragment_equivalence.py -q`
Expected: PASS. If the baseline test fails despite an empty dev-mode diff, regenerate it (`docker compose config > bootstrapper/tests/fixtures/rendered_config_baseline.yml`) — but a correct change should not require it.

- [ ] **Step 5: Add a prod-mode binding test**

Create `bootstrapper/tests/test_prod_bind_ip.py`:
```python
import subprocess, os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

def test_prod_bind_ip_localhost(tmp_path, monkeypatch):
    # Render compose with HOST_BIND_IP set; every published port must be 127.0.0.1-bound.
    env = os.environ.copy()
    env["HOST_BIND_IP"] = "127.0.0.1:"
    # provide minimal required vars by sourcing the committed .env.example
    out = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.yml", "--env-file", ".env.example", "config"],
        cwd=REPO, env=env, capture_output=True, text=True,
    )
    assert out.returncode == 0, out.stderr
    # No published port may bind 0.0.0.0 in prod mode.
    assert "0.0.0.0" not in out.stdout
```

- [ ] **Step 6: Run it**

Run: `cd bootstrapper && uv run pytest tests/test_prod_bind_ip.py -q`
Expected: PASS (requires Docker available; if CI lacks Docker for this test, mark it `@pytest.mark.skipif(shutil.which("docker") is None)`).

- [ ] **Step 7: Commit**

```bash
git add services/*/compose.yml services/globals/service.yml .env.example bootstrapper/tests/test_prod_bind_ip.py
git commit -m "Add HOST_BIND_IP prefix to all published ports (localhost binding in prod)"
```

---

### Task 2: `--profile prod` CLI flag + env wiring

**Files:**
- Modify: `bootstrapper/start.py` (Click option + handling)
- Test: `bootstrapper/tests/test_no_splash_flag.py` pattern → new `tests/test_profile_flag.py`

**Interfaces:**
- Produces: `--profile [default|prod]` (default `default`); when `prod`, sets `HOST_BIND_IP=127.0.0.1:`, defaults `PROMETHEUS_SOURCE`/`GRAFANA_SOURCE` to `container` when not explicitly overridden, and sets log-rotation vars (Task 4) + resource-limit vars (Task 3).

- [ ] **Step 1: Add the Click option** (mirror the existing `--no-port-migrate` option block in `start.py`)

```python
@click.option('--profile',
              type=click.Choice(['default', 'prod'], case_sensitive=False),
              default='default',
              help='Deployment profile. "prod": bind all service ports to '
                   '127.0.0.1 (public edge fronts Kong), enforce resource '
                   'limits, enable log rotation, default observability ON.')
```
Add `profile` to the `main(...)` signature alongside the other params, and store it on the starter: `starter.profile = profile` (next to `starter.no_splash = no_splash`).

- [ ] **Step 2: Apply prod env overrides before env generation**

Where the starter assembles/writes `.env` (the source-override application point used by the other `--*-source` flags), add:
```python
if getattr(self, "profile", "default") == "prod":
    overrides = {"HOST_BIND_IP": "127.0.0.1:"}
    # Default observability ON unless the user explicitly set the source flags.
    if prometheus_source is None:
        overrides["PROMETHEUS_SOURCE"] = "container"
    if grafana_source is None:
        overrides["GRAFANA_SOURCE"] = "container"
    # Log rotation (Task 5 consumes these).
    overrides["LOG_MAX_SIZE"] = "10m"
    overrides["LOG_MAX_FILE"] = "3"
    self._apply_env_overrides(overrides)  # use the existing override-writer
```
Use whatever the existing override-writer method is named (the same path `--prometheus-source` uses to persist into `.env`); do not invent a new mechanism.

- [ ] **Step 3: Test the flag is declared + threads through**

Create `bootstrapper/tests/test_profile_flag.py`:
```python
import inspect
import start

def test_cli_declares_profile():
    names = [p.name for p in start.main.params]
    assert "profile" in names

def test_profile_choices():
    opt = next(p for p in start.main.params if p.name == "profile")
    assert set(opt.type.choices) == {"default", "prod"}
```

- [ ] **Step 4: Run it**

Run: `cd bootstrapper && uv run pytest tests/test_profile_flag.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add bootstrapper/start.py bootstrapper/tests/test_profile_flag.py
git commit -m "Add --profile prod flag (localhost ports, observability on, log rotation)"
```

---

### Task 3: Deployment-profile wizard step + prod localhost-source filtering

**Files:**
- Modify: `bootstrapper/ui/textual/integration.py` (profile picker step + filter localhost options + thread `profile`)
- Modify: `bootstrapper/start.py` (pass `profile` into `run_setup_flow`/`run_launch_flow`; set `starter.profile` from the wizard selection)
- Modify: `bootstrapper/services/source_validator.py` (reject localhost sources in prod)
- Test: `bootstrapper/tests/test_profile_source_filter.py`

**Interfaces:**
- Consumes: `--profile` from Task 2; the TRACK picker pattern (`PICKER_STEP_TITLE`, `_make_track_skip`, `prefilled_selections`); `ServiceDiscovery.discover()` `svc.options`.
- Produces: a wizard step keyed `PROFILE_STEP_TITLE`; prod filtering of `localhost`-id options in the wizard; `SourceValidator.validate_no_localhost_in_prod(service_sources, profile)`; `profile` threaded through both flows; `starter.profile` set from the wizard pick so Task 2's env overrides run for wizard-driven runs too.

No new `profiles.yml` is needed — there are exactly two fixed profiles (`default`, `prod`), so the step is built inline (unlike tracks, which are data-driven).

- [ ] **Step 1: Thread `profile` through the flow signatures**

In `integration.py`, add `profile: str | None = None` to both `run_setup_flow(...)` and `run_launch_flow(...)` (mirror the existing `track` param). In `start.py`, pass `profile=profile` at both call sites (mirror `track=track`).

- [ ] **Step 2: Add the wizard profile step** (in `_build_steps_and_rows`, right after the track picker step is appended)

```python
PROFILE_STEP_TITLE = "Profile  ·  deployment hardening"
# ...
steps.append(PromptStep(
    title=PROFILE_STEP_TITLE,
    step_index=2, step_total=total,
    heading="Dev or production hardening?",
    subtitle=("prod: localhost-only ports, resource limits, log rotation, "
              "observability on — and localhost sources hidden."),
    options=[
        PromptOption(value="default", label="Default (dev)",
                     hint="0.0.0.0 ports; all sources available", badges=[]),
        PromptOption(value="prod", label="Production hardening",
                     hint="127.0.0.1 ports; localhost sources hidden", badges=[]),
    ],
    default_value=(profile or "default"),
    service_name="",
    skip_if_prev=((lambda sel, _p=profile: bool(_p)) if profile else None),
))
```
Prefill when `--profile` was passed: add `{PROFILE_STEP_TITLE: profile}` to `prefilled_selections` alongside the track prefill so downstream filters can read it even when the step auto-skips.

- [ ] **Step 3: Filter localhost options in the wizard when prod** (where `svc.options` becomes `PromptOption`s — the `opts = [...]` comprehension)

```python
_prod = (selections.get(PROFILE_STEP_TITLE) or profile) == "prod"
visible_opts = [o for o in svc.options if not (_prod and "localhost" in o)]
```
Build the `PromptOption` list from `visible_opts`. Edge case: if filtering removes the highlighted `current_value` (or empties the list), fall back the default highlight to the manifest default, else `disabled`, and add a one-line note. (Real localhost ids to filter, from the manifests: `ollama-localhost`, `parakeet-localhost`, `whisper-cpp-localhost`, `chatterbox-localhost`, `docling-localhost`, and bare `localhost` for comfyui/hermes/lightrag/neo4j/openclaw/tei-reranker/weaviate — substring `"localhost"` matches them all.)

- [ ] **Step 4: Reject localhost sources in the CLI validator under prod** (`source_validator.py`)

```python
def validate_no_localhost_in_prod(self, service_sources: dict, profile: str) -> bool:
    """Under --profile prod, localhost sources are unreachable on a remote
    host. Reject them with a clear, accumulated error."""
    if profile != "prod":
        return True
    ok = True
    for var, val in service_sources.items():
        if val and "localhost" in val:
            self.validation_errors.append(
                f"{var}='{val}' is not allowed with --profile prod "
                f"(localhost sources are unreachable on a remote host)."
            )
            ok = False
    return ok
```
Call it in `start.py`'s prod path before `validate_all_sources()` (pass the resolved profile), so a `--profile prod --ollama-source ollama-localhost` invocation fails fast with a readable message.

- [ ] **Step 5: Wire the wizard pick back to `starter.profile`**

In the wizard pipeline, after the prompts resolve, read `selections.get(PROFILE_STEP_TITLE)` and set `starter.profile = <that or "default">` BEFORE the env-override step from Task 2 runs — so a wizard-selected prod run gets `HOST_BIND_IP`, observability, limits, and log rotation exactly like the CLI `--profile prod` path.

- [ ] **Step 6: Tests** — create `bootstrapper/tests/test_profile_source_filter.py` (mirror `test_tracks_wizard_skip.py` + `test_source_validator_errors.py`):

```python
def test_validator_rejects_localhost_under_prod():
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from services.source_validator import SourceValidator
    v = SourceValidator()
    v.validation_errors = []
    ok = v.validate_no_localhost_in_prod({"OLLAMA_SOURCE": "ollama-localhost"}, "prod")
    assert ok is False and any("OLLAMA_SOURCE" in e for e in v.validation_errors)

def test_validator_allows_localhost_under_default():
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from services.source_validator import SourceValidator
    v = SourceValidator()
    v.validation_errors = []
    assert v.validate_no_localhost_in_prod({"OLLAMA_SOURCE": "ollama-localhost"}, "default") is True
```
Add a wizard-builder test asserting that, with `profile="prod"`, the built ComfyUI/Ollama step contains no option whose value contains `localhost` (mirror how `test_tracks_wizard_skip.py` drives the step builder).

- [ ] **Step 7: Run + commit**

Run: `cd bootstrapper && uv run pytest tests/test_profile_source_filter.py tests/test_profile_flag.py -q`
Expected: PASS.
```bash
git add bootstrapper/ui/textual/integration.py bootstrapper/start.py bootstrapper/services/source_validator.py bootstrapper/tests/test_profile_source_filter.py
git commit -m "Add deployment-profile wizard step + prod localhost-source filtering"
```

---

### Task 4: Resource limits on heavy services

**Files:**
- Modify: heavy `services/*/compose.yml` + their `service.yml` (declare `*_MEMORY_LIMIT`/`*_CPU_LIMIT` with prod-safe defaults)
- Test: `tests/test_fragment_equivalence.py`

**Interfaces:**
- Consumes: existing `deploy:` blocks. Produces: `deploy.resources.limits` on Spark, Airflow, Zeppelin, Neo4j, Weaviate, ComfyUI, Ray (the RAM-heavy set), mirroring Hermes/LightRAG.

- [ ] **Step 1: For each heavy service, add the limit env vars to its manifest** (example, `services/neo4j/service.yml`):
```yaml
  - name: NEO4J_MEMORY_LIMIT
    default: 2g
    description: "Container memory limit (deploy.resources.limits.memory)."
  - name: NEO4J_CPU_LIMIT
    default: "1.5"
    description: "Container CPU limit (deploy.resources.limits.cpus)."
```

- [ ] **Step 2: Add the limits to each fragment's `deploy:` block** (example, `services/neo4j/compose.yml`):
```yaml
    deploy:
      replicas: ${NEO4J_SCALE:-1}
      resources:
        limits:
          memory: ${NEO4J_MEMORY_LIMIT:-2g}
          cpus: "${NEO4J_CPU_LIMIT:-1.5}"
```
Repeat for spark, airflow, zeppelin, weaviate, comfyui, ray with sized defaults appropriate to a 32 GB host (document the chosen numbers in each manifest description).

- [ ] **Step 3: Regenerate `.env.example` + baseline; test**

```bash
cd bootstrapper && uv run python -m services.env_assembler
cd /Users/kaveh/repos/genai-vanilla && docker compose -f docker-compose.yml config > bootstrapper/tests/fixtures/rendered_config_baseline.yml
cd bootstrapper && uv run pytest tests/test_fragment_equivalence.py tests/test_env_assembler.py -q
```
Expected: PASS. (Limits with `:-default` change rendered config because the `deploy.resources` block is now present — the baseline regen is expected here. Keep the diff scoped to the touched services.)

- [ ] **Step 4: Commit**

```bash
git add services/*/service.yml services/*/compose.yml .env.example bootstrapper/tests/fixtures/rendered_config_baseline.yml
git commit -m "Add resource limits to heavy services"
```

---

### Task 5: Log rotation

**Files:**
- Modify: each `services/*/compose.yml` (add a `logging:` block) OR document a daemon-level default
- Modify: `services/globals/service.yml` (`LOG_MAX_SIZE`, `LOG_MAX_FILE`)

- [ ] **Step 1: Declare the vars in globals** (`services/globals/service.yml`):
```yaml
  - name: LOG_MAX_SIZE
    default: "10m"
    description: "Per-container json-file log max size (Docker logging option)."
  - name: LOG_MAX_FILE
    default: "3"
    description: "Per-container json-file log file count (Docker logging option)."
```

- [ ] **Step 2: Add a `logging:` block to each long-running service fragment**:
```yaml
    logging:
      driver: json-file
      options:
        max-size: "${LOG_MAX_SIZE:-10m}"
        max-file: "${LOG_MAX_FILE:-3}"
```
(Defaults bound the size even in dev. Alternative: set these in the host's `/etc/docker/daemon.json` — note that in the runbook as the simpler global option, but the per-fragment block is version-controlled and explicit.)

- [ ] **Step 3: Regenerate `.env.example` + baseline; test**

```bash
cd bootstrapper && uv run python -m services.env_assembler
cd /Users/kaveh/repos/genai-vanilla && docker compose -f docker-compose.yml config > bootstrapper/tests/fixtures/rendered_config_baseline.yml
cd bootstrapper && uv run pytest -q
```
Expected: full suite PASS.

- [ ] **Step 4: Commit**

```bash
git add services/*/compose.yml services/globals/service.yml .env.example bootstrapper/tests/fixtures/rendered_config_baseline.yml
git commit -m "Add json-file log rotation to long-running services"
```

---

### Task 6: Document the profile

**Files:**
- Modify: `README.md` (add `--profile prod` to the options list), `docs/CHANGELOG.md`

- [ ] **Step 1: Add to README's option list** (near the `--no-port-migrate` line):
```bash
./start.sh --profile prod      # Production hardening: localhost-only ports, resource limits, log rotation, observability on
```

- [ ] **Step 2: CHANGELOG "Added" entry** describing `--profile prod` + `HOST_BIND_IP`.

- [ ] **Step 3: Run audits + commit**

```bash
cd /Users/kaveh/repos/genai-vanilla && python scripts/check_doc_links.py && PYTHONPATH=bootstrapper python -m bootstrapper.docs.regen --all --check
git add README.md docs/CHANGELOG.md
git commit -m "docs: document --profile prod hardening"
```

---

## Self-Review

- **Spec coverage:** Implements P0-3 (lock network exposure via `HOST_BIND_IP`) and P0-7 (resource limits + log rotation + observability-on `compose.prod` semantics via the prod profile). Adds the reviewer-requested **wizard profile step** (Task 3) and **prod `localhost`-source filtering** in both the wizard and the CLI validator.
- **Placeholders:** none — exact env names, fragment edits, module/function names, and commands given. Per-service limit numbers are left to the implementer to size, with explicit guidance (32 GB host) — that is a sizing decision, not a placeholder.
- **Type consistency:** `HOST_BIND_IP`, `LOG_MAX_SIZE`, `LOG_MAX_FILE`, `*_MEMORY_LIMIT`/`*_CPU_LIMIT`, `PROFILE_STEP_TITLE`, `validate_no_localhost_in_prod`, and `starter.profile` used identically across the globals manifest, fragments, the `--profile prod` override map, the wizard builder, and the validator. The wizard pick and the CLI flag both resolve to the same `profile` value that drives every prod behaviour.
- **Key correctness note:** the `${HOST_BIND_IP:-}` prefix yields a byte-identical dev render (empty prefix), so Task 1 must produce a zero diff in dev — this is the test that proves the mechanism is non-breaking. Resource-limit/logging tasks DO change the baseline (expected) and regenerate it.
- **Risk:** the baseline regen is sensitive to local vs CI Docker Compose version (documented repo gotcha); if local regen yields unrelated drift, defer the baseline commit to the CI-artifact path.
