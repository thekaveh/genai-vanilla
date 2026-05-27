# Localhost Port Override — Design

**Status:** Implemented 2026-05-26 — PR #10 merged.
**Author:** Kaveh Razavi (via Claude brainstorming).
**Spec lineage:** Extends the inline `SecondaryNumberInput` widget pattern shipped on
2026-05-25 for Ray worker count (commit `4f79394`).

---

## 1. Goal

A user running a localhost-mode stack service on a non-default port (e.g.,
Ollama on `:11500` instead of `:11434`, ComfyUI on `:9000` instead of `:8000`)
edits that port **inline on the wizard's source-selection step** using the same
`OptionRowWithInput` widget shipped for Ray. The override must propagate
symmetrically through every downstream consumer — Kong gateway routes,
in-container clients (Backend, n8n, Open WebUI, …), and the wizard's own
service-table port column — with no asymmetric drift between them.

## 2. Background

### 2.1 Today's localhost-source plumbing

Today the stack stores localhost-mode endpoints as **monolithic URLs** in env
vars like:

```
COMFYUI_LOCALHOST_URL=http://host.docker.internal:8000
```

That single URL is consumed in three places, all of which read from the same
env var so they stay aligned by construction:

1. **Kong gateway** (`bootstrapper/utils/kong_config_generator.py`) — localhost
   routes target `host.docker.internal:<port>`.
2. **In-container clients** — services read `${<SVC>_ENDPOINT}`, which
   `runtime_sc.<localhost-source>.environment` resolves to the URL var.
3. **Wizard service-table** (`bootstrapper/ui/state_builder.py::resolve_port`)
   — regex-extracts `:<port>` from the URL for the display column.

The display column is **read-only** today; the wizard has no affordance to
edit the port.

### 2.2 Services currently in scope

Survey of `services/*/service.yml` (2026-05-25):

| Service | `<SVC>_LOCALHOST_URL` env var today | Default port |
|---|---|---|
| Comfyui | ✅ `COMFYUI_LOCALHOST_URL` | 8000 |
| Docling | ✅ `DOCLING_LOCALHOST_URL` | 63021 |
| Hermes | ✅ `HERMES_LOCALHOST_URL` | 63028 |
| Openclaw | ✅ `OPENCLAW_LOCALHOST_URL` | 63024 |
| Parakeet (STT) | ✅ `PARAKEET_LOCALHOST_URL` | 63022 |
| Whisper-cpp (STT) | ✅ `WHISPER_CPP_LOCALHOST_URL` | 63025 |
| Chatterbox (TTS) | ✅ `CHATTERBOX_LOCALHOST_URL` | 63027 |
| Ollama | ❌ hardcoded `http://host.docker.internal:11434` in `runtime_sc` | 11434 |
| Neo4j | ❌ hardcoded in Kong + `runtime_sc` | 7474 (HTTP) + 7687 (Bolt) |
| Weaviate | ❌ hardcoded in Kong + `runtime_sc` | 8080 |

All 10 services are in scope. The bottom 3 need new env var plumbing
introduced as part of this feature; Neo4j needs **two** ports (HTTP + Bolt).

### 2.3 Widget the feature builds on

`bootstrapper/ui/textual/widgets/option_row.py::OptionRowWithInput` and
`bootstrapper/ui/textual/widgets/prompt_panel.py::SecondaryNumberInput`,
shipped on 2026-05-25 (commit `4f79394`). The widget renders an inline integer
textbox between an option row's label and its badges, with a unit-suffix
label (currently `workers`), keeping the textbox + suffix + badges columns
column-aligned across eligible and ineligible rows. The slot width
(`SECONDARY_INPUT_SLOT_WIDTH = 12` cells) accommodates a 5-digit port.

## 3. Non-goals

The following are explicitly **out of scope** for this spec and noted here so
they don't accumulate as silent assumptions:

- **Custom hostnames.** The URL is always `http://host.docker.internal:<port>`.
  Users with non-default hostnames lose them on wizard run (with a warning —
  see §6.2). A "custom hostname override" feature is additive on top of this
  design and is left for a future spec.
- **Live probing of the localhost service.** The bootstrapper does not check
  whether the user's typed port actually has a listener. The
  `check_localhost_service` TODO in `kong_config_generator.py` remains
  unwired. Same failure mode as today: connection refused at first request,
  not at startup.
- **Cloud / external sources.** Only `localhost`-source variants get the
  widget. Container-mode ports continue to flow through
  `services/topology.py::PORT_DEFAULTS` and the existing `--base-port`
  mechanism.

## 4. Architecture

### 4.1 Single source of truth = port

`.env` stores `<SVC>_LOCALHOST_PORT=<n>`. The URL is **derived** at compose-
render time and Kong-config-generation time as
`http://host.docker.internal:${<SVC>_LOCALHOST_PORT:-<manifest-default>}`.
The old `<SVC>_LOCALHOST_URL` env vars are migrated away (see §6).

This eliminates the asymmetric-override class of bug from memory
`feedback_localhost_url_override_symmetry.md` — there is no longer a "URL var
that some consumers read and others don't." Every consumer reads the same
PORT var.

### 4.2 Widget API generalization

`secondary_number` moves from `PromptStep` onto `PromptOption`. Each row
carries its own `SecondaryNumberInput` config (or `None`), writing to its own
`env_var`. The `show_when` field is removed — eligibility is "this option
has a config attached or not."

```python
# BEFORE (Ray-only, single env_var per step):
@dataclass
class PromptStep:
    secondary_number: SecondaryNumberInput | None = None
@dataclass
class SecondaryNumberInput:
    env_var: str
    show_when: tuple[str, ...] = ()        # filter, removed
    ...

# AFTER (per-option, any env_var per row):
@dataclass
class PromptOption:
    secondary_number: SecondaryNumberInput | None = None    # new
@dataclass
class SecondaryNumberInput:
    env_var: str
    # show_when removed
    ...
```

The Ray case migrates retroactively: instead of one `SecondaryNumberInput`
on the step with `show_when=("ray-container-cpu","ray-container-gpu")`, each
of those two `PromptOption`s carries its own (identical) config writing to
`RAY_WORKER_COUNT`. The STT/TTS case works naturally — `parakeet-localhost`
and `whisper-cpp-localhost` rows each carry their own config writing to
different env vars (`PARAKEET_LOCALHOST_PORT` vs.
`WHISPER_CPP_LOCALHOST_PORT`).

### 4.3 Sibling-sync semantics

Sibling input sync (the existing "typing in one row mirrors to others"
behavior shipped for Ray) is **keyed by `env_var`**. Two rows whose configs
share an `env_var` sync keystrokes; two rows with different `env_var`s
don't.

- Ray case: both eligible rows share `env_var="RAY_WORKER_COUNT"` → they
  sync. Unchanged behavior.
- STT case: rows have different `env_var`s → they're independent. Correct —
  they represent different ports for different services.

Implementation note: `PromptPanel._sync_secondary_inputs` already iterates
`self._secondary_inputs`. The change is to filter by env_var association
before mirroring. The Input widget gains an associated env_var attribute set
at mount time.

### 4.4 Data flow per wizard confirm

```
                  wizard prompt step "ComfyUI · source"
                  │  comfyui-container                            (no inline textbox)
                  ▼  comfyui-localhost [8000] port  ← user types 9000

   PromptOption.secondary_number =
       SecondaryNumberInput(
         env_var="COMFYUI_LOCALHOST_PORT",
         default_value=8000,
         number_min=1024, number_max=65535,
         unit_suffix="port")
                                                     ▼
   selections["__secondary__:COMFYUI_LOCALHOST_PORT"] = "9000"
                                                     ▼
   _selections_to_args → ollama_user_models["COMFYUI_LOCALHOST_PORT"] = "9000"
                                                     ▼
   start.py::apply_user_model_selections → update_env_file(.env)
                                                     ▼
                              .env: COMFYUI_LOCALHOST_PORT=9000
                                                     │
   ┌─────────────────────┬───────────────────┬───────┴──────────────┐
   ▼                     ▼                   ▼                      ▼
 docker compose       Kong config        wizard service-table     in-container
 substitutes into     generator builds   resolver reads           consumer reads
 runtime_sc:          http://host.docker COMFYUI_LOCALHOST_PORT   COMFYUI_ENDPOINT
 COMFYUI_ENDPOINT     .internal:9000     directly → ":9000"       → http://host.docker
 = http://host.docker as route target                              .internal:9000
 .internal:9000
```

## 5. Components & file-touch surface

| Layer | Files | Change |
|---|---|---|
| **Manifest (existing URL vars)** | `services/{comfyui,docling,hermes,openclaw,parakeet,whisper-cpp,chatterbox}/service.yml` | Replace URL env var with PORT; rewrite `runtime_sc.<src>.environment` to `${<SVC>_LOCALHOST_PORT:-<def>}`. (7 services) |
| **Manifest (new vars)** | `services/{ollama,neo4j,weaviate}/service.yml` | Add new `<SVC>_LOCALHOST_PORT` env vars (neo4j gets 2: HTTP + Bolt); update `runtime_sc.<src>.environment` to consume them. (3 services, 4 new env vars) |
| **Kong generator** | `bootstrapper/utils/kong_config_generator.py` | Each localhost-route target switches from `get_env_value('<SVC>_LOCALHOST_URL', fallback)` to `f"http://host.docker.internal:{get_env_value('<SVC>_LOCALHOST_PORT', '<def>')}"`. Centralize in one helper to keep the pattern uniform. |
| **Service-table resolver** | `bootstrapper/ui/state_builder.py::resolve_port` | When `"localhost" in source`, read PORT var directly (no regex from URL). Topology row gains a `localhost_port_var` field. |
| **Widget API** | `bootstrapper/ui/textual/widgets/prompt_panel.py` (`PromptStep.secondary_number` removed; `PromptOption.secondary_number` added; `SecondaryNumberInput.show_when` removed; `secondary_value()` → `secondary_values()` returning list), `widgets/option_row.py` (mounting branch keys off `opt.secondary_number`), sibling sync (keyed by `env_var`) | The Approach A refactor from §4.2. |
| **Wizard wiring** | `bootstrapper/ui/textual/integration.py` | For each localhost-capable service, attach `secondary_number` to the corresponding `<svc>-localhost` option(s). Ray's existing wiring migrates to per-option too. |
| **Selections pipeline** | `bootstrapper/ui/textual/screens/wizard_screen.py::_action_confirm`, `integration.py::_selections_to_args` | `secondary_value()` → `secondary_values()` (list of `(env_var, value)`). Each tuple becomes `selections["__secondary__:<env>"]`. The drain loop in `_selections_to_args` is already generic. |
| **Migration** | `bootstrapper/services/migrations/migration_v2.py` (new) | One-shot rewrite of `<SVC>_LOCALHOST_URL` → `<SVC>_LOCALHOST_PORT` in `.env`. Sentinel `BOOTSTRAPPER_PORT_LAYOUT_VERSION` bumped from `1` to `2`. |
| **Topology** | `bootstrapper/services/topology.py` | Add `localhost_port_var` field on `TopologyRow`. Populate for the 10 services. |
| **`.env.example` regen** | (regenerated by `bootstrapper/services/env_assembler.py`) | New defaults appear automatically once the manifests above are updated. Test `test_env_example_consistency` enforces. |

## 6. Migration & backwards compat

### 6.1 `migration_v2.py`

Pattern mirrors the existing `migration_v1.py` (port-layout v0 → v1 rewrite,
per CLAUDE.md). Gated by the same `BOOTSTRAPPER_PORT_LAYOUT_VERSION`
sentinel, bumped from `1` to `2`.

Sequence on next `./start.sh`:

1. Bootstrapper reads `BOOTSTRAPPER_PORT_LAYOUT_VERSION` from `.env`.
2. If sentinel is `1` (or absent) → run `migration_v2`. If sentinel is `2`
   → no-op (idempotent re-run is safe).
3. `migration_v2` scans `.env` for every line matching
   `^<SVC>_LOCALHOST_URL=(http://[^:]+:(\d+).*)?$` across the 7 services that
   previously had this var.
4. For each match:
   - Extract the port via the capture group.
   - Append `<SVC>_LOCALHOST_PORT=<extracted>` if not already present.
   - **Comment out** (not delete) the old URL line with a migration trailer:
     `# COMFYUI_LOCALHOST_URL=…  # migrated to COMFYUI_LOCALHOST_PORT by migration_v2 (2026-05-25)`.
5. Append `BOOTSTRAPPER_PORT_LAYOUT_VERSION=2` to update the sentinel.

Commenting (not deleting) preserves an audit trail for users who hand-
customized — if migration extracts the port wrong (e.g., user had a non-
standard URL the regex didn't match), they see the old line in `.env` and
can recover.

### 6.2 Edge cases

| Edge case | Migration behavior |
|---|---|
| `COMFYUI_LOCALHOST_URL` not in `.env` at all | Skip — new manifest default surfaces via `.env.example` regen. |
| `COMFYUI_LOCALHOST_URL=` (empty) | Comment out, no PORT line emitted; service falls back to manifest default at compose time. |
| Non-default hostname: `COMFYUI_LOCALHOST_URL=http://192.168.1.10:9000` | Extract port `9000`, write `COMFYUI_LOCALHOST_PORT=9000`. **Custom hostname is dropped.** Bootstrapper emits a `[migration]` warning so the user sees it. |
| URL has no port: `COMFYUI_LOCALHOST_URL=http://host.docker.internal` (malformed) | Skip the line, comment it out, emit warning. New default applies. |
| Sentinel already at `2` | Migration is a no-op (re-running is safe). |
| User runs new bootstrapper, then downgrades | New PORT vars are unrecognized by old runtime_sc; commented-out URL vars are still present in `.env` for hand-recovery. Not a supported path, but the comment-out-don't-delete policy makes it recoverable. |

### 6.3 The 3 newly-overridable services (ollama / neo4j / weaviate)

Never had a `<SVC>_LOCALHOST_URL` env var — URLs were hardcoded. Nothing to
migrate. The new `<SVC>_LOCALHOST_PORT` vars are added to `.env.example` via
`env_assembler` regen; existing users get them appended to their `.env` on
next start via the existing `backfill_missing_env_vars` pipeline (per memory
`project_env_write_semantics`, "appends new vars to bottom").

### 6.4 Note on the sentinel name

`BOOTSTRAPPER_PORT_LAYOUT_VERSION` was originally for "port slot allocator
layout" semantics (v0 → v1). This migration is about env-var schema, not
port slots. Strictly speaking a separate sentinel
(e.g., `BOOTSTRAPPER_LOCALHOST_OVERRIDE_VERSION`) would be more semantically
correct.

**Decision:** Reuse the existing sentinel and bump to `2`. The cost of
introducing a second sentinel is more confusion than the cost of broadening
one sentinel's meaning. The migration file is named `migration_v2.py`
mechanically consistent with `migration_v1.py`.

## 7. Error handling

### 7.1 Input validation (widget level)

| Bound | Value | Rationale |
|---|---|---|
| `number_min` | **1024** | Privileged-port range below 1024 requires root on Linux/macOS; user services almost never bind there. Cleaner UX than letting them type 80 and have the service fail to start. |
| `number_max` | **65535** | IANA-valid max. |
| Default | per-service from manifest | Read from the same manifest declaration that seeds `.env.example`. |

Out-of-bounds values are **clamped silently** by the existing widget logic
(verified by `test_clamps_value_above_max` / `test_clamps_value_below_min`).
No error dialog. Matches the Ray widget UX.

### 7.2 Non-numeric input

Existing fall-back: `int()` raises → reset to default. Locked in by
`test_falls_back_to_default_on_garbage_input`. Same behavior as Ray.

### 7.3 Port collision with stack-reserved ports

A user might type `64000` — the Kong gateway port if `BASE_PORT=64000`. The
collision is on the **host** side, between the user's external localhost
service and a stack container-mode service.

**Behavior:** detect-and-warn, don't block. After the user confirms a
localhost-port that matches another row's host port, the pre-launch summary
table flags it with a yellow `⚠ port 64000 also used by kong` line. Launch
proceeds; the user can ack and continue, or go back and change the port.

**Rationale:** the user *might* be deliberately picking a port they're also
flipping the colliding service away from in the same wizard run. Walls of
validation rules backfire; the warning preserves agency.

### 7.4 "User picks localhost but the service isn't actually running"

Today's behavior: failure at first request (connection refused). This
feature changes nothing about that. Out of scope per §3.

### 7.5 Wizard navigation: switching source mid-wizard

User selects `comfyui-localhost`, types `9000`, then switches to
`comfyui-container`. On confirm, `selections["__secondary__:COMFYUI_LOCALHOST_PORT"]`
is **not** captured — the currently-selected option has no `secondary_number`
config, so the eligibility check filters it out. `.env` is not written with
the port for the abandoned row. Correct: localhost-port is conceptually a
child of the localhost source choice.

### 7.6 Re-running the wizard with a previously-set custom port

User ran the wizard last week and set `COMFYUI_LOCALHOST_PORT=9000`. Today
they re-run. The wizard reads `.env`, the textbox default for the
`comfyui-localhost` row resolves to **9000** (prior choice), not the
manifest default `8000`. Same pattern as the existing Ray case:
```python
raw_default = (env_vars.get("RAY_WORKER_COUNT") or "2").strip()
```

### 7.7 `runtime_sc` env-var interpolation

The compose pattern `http://host.docker.internal:${COMFYUI_LOCALHOST_PORT:-8000}`
requires Compose v2.20+'s nested-variable handling. The repo's CLAUDE.md
already requires v2.26+ — safe. Other `runtime_sc` patterns already use
`${VAR:-default}`.

### 7.8 Disabled / external / container sources

Carry no `secondary_number` config — they reserve layout space (empty
placeholder) so the badges column stays column-aligned. Exactly the Ray
pattern shipped 2026-05-25.

## 8. Testing strategy

| Behavior | Test file | Locks in |
|---|---|---|
| Per-option `secondary_number` API | `tests/test_prompt_panel_secondary_input.py` (update) | `secondary_values()` returns one tuple per visible eligible row; different env_vars yield distinct tuples; no-config rows yield no tuple. |
| Sibling sync keyed by `env_var` | same file, new test | Two rows with `env_var="A"` mirror; a third with `env_var="B"` is independent. |
| Ray migrated to per-option | `tests/test_wizard_ray_steps.py` (update) | Both eligible options carry the config writing `RAY_WORKER_COUNT`; selecting either produces `__secondary__:RAY_WORKER_COUNT`. Regression guard. |
| Localhost wiring per service | `tests/test_localhost_port_override.py` (new) | Parametrized over the 10 services: source step's `<svc>-localhost` option carries the correct `SecondaryNumberInput` (env_var, default, min, max, unit_suffix). |
| Selections → .env routing | same file | End-to-end: pick `comfyui-localhost` with `9000` → `.env` gets `COMFYUI_LOCALHOST_PORT=9000`. |
| `migration_v2` schema rewrite | `tests/test_migration_v2.py` (new) | All 6 edge cases from §6.2. |
| Sentinel gating | same file | Runs on sentinel=1; no-op on sentinel=2. |
| Kong reads PORT vars | `tests/test_kong_alias_routes.py` (update) | Parametrized over 10 services: route `url` equals `f"http://host.docker.internal:{env['<SVC>_LOCALHOST_PORT']}"`. |
| Wizard port column | `tests/test_state_builder.py` (new or existing) | `resolve_port(name, "<svc>-localhost", …)` returns `:{PORT_var_value}`. |
| `.env.example` byte-equivalence | `tests/test_env_example_consistency.py` (existing) | Post-regen: PORT vars present for all 10 services; URL vars absent for the migrated 7. |
| Compose fragment equivalence | `tests/test_fragment_equivalence.py` (existing) → baseline update | Rendered compose references `${<SVC>_LOCALHOST_PORT:-<def>}` not URL vars. |
| Manifest schema validation | `tests/test_manifests.py` (existing) | Ollama / Neo4j / Weaviate new env entries pass schema (`bootstrapper/schemas/service.schema.json`). Neo4j has 2 port vars. |
| Port-collision warning | `tests/test_pre_launch_summary.py` (likely new) | Summary flags collision, doesn't block launch. |

### Audit gates affected

| Gate | What changes |
|---|---|
| `python -m bootstrapper.docs.regen --all --check` | Service READMEs auto-regenerate. May mention new env vars in `## Configuration`. Drift gate enforces. |
| `python scripts/check_doc_links.py` | Should remain green. |
| `python scripts/check-compose-source-deps.py` | Should remain green. |
| `python scripts/check-kong-routes.py` | **Load-bearing.** Update audit fixture so every localhost-mode route's `url` reflects the env-var-derived port. Without this update, the gate trips for all 10 services. |

### CI impact

All 3 `services-lint.yml` jobs are touched:
- `Manifest lint + unit tests` — runs new test files.
- `Compose merge + byte-equivalence + source-permutation matrix` — baseline updated; source-permutation matrix automatically exercises new env-var pattern.
- `Docs drift + audit scripts` — runs `regen --check` and the audit scripts.

## 9. Implementation order

A logical ordering that lets the test suite stay green at every commit:

1. **Widget refactor** — per-option `secondary_number`, migrate Ray to the new API. Tests: existing Ray tests + new env_var-keyed sync tests.
2. **Manifest changes for the 7 existing-URL services** — replace URL with PORT. Tests: `env_example_consistency` + `fragment_equivalence` baseline.
3. **Manifest additions for the 3 new services** — ollama, neo4j, weaviate. Same tests.
4. **Kong generator update.** Tests: `kong_alias_routes` + `check-kong-routes` audit fixture.
5. **State_builder resolver update.** Tests: `state_builder`.
6. **Wizard wiring** — attach `secondary_number` to each localhost option. Tests: `localhost_port_override` parametrized.
7. **`migration_v2` + sentinel bump.** Tests: `migration_v2`.
8. **Port-collision warning in pre-launch summary.** Tests: `pre_launch_summary`.

Each step is independently testable and shippable.

## 10. References

- Memory `feedback_localhost_url_override_symmetry.md` — the constraint that
  shaped §4.1's "single source of truth = port" decision.
- Memory `project_env_write_semantics.md` — `update_env_file` appending
  semantics referenced in §6.3.
- Commit `4f79394` (2026-05-25) — the `OptionRowWithInput` widget this spec
  extends.
- `bootstrapper/services/migrations/migration_v1.py` — pattern `migration_v2`
  mirrors.
- `bootstrapper/schemas/service.schema.json` — manifest schema the new env
  entries must satisfy.
