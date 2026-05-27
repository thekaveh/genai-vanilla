> **Status:** COMPLETED 2026-05-26 (PR #10). All tasks below shipped — checkboxes are not retroactively flipped; consult `git log` for actual deliverables. Retained as a historical record of the plan-as-executed.

# Localhost Port Override Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users override the default port number on every localhost-source variant inline via the wizard's `OptionRowWithInput` widget, with the override propagating symmetrically through `.env`, compose runtime_sc, Kong gateway routes, in-container clients, and the wizard's service-table.

**Architecture:** Port is the single source of truth in `.env` (`<SVC>_LOCALHOST_PORT=<n>`); the URL is derived at compose-render time and Kong-config-generation time as `http://host.docker.internal:${<SVC>_LOCALHOST_PORT:-<default>}`. The widget API is generalized: `secondary_number` moves from `PromptStep` onto `PromptOption`, eligibility becomes "config attached vs. not," and sibling-sync is keyed by `env_var` so unrelated rows don't mirror each other.

**Tech Stack:** Python 3.12, Textual TUI framework, Docker Compose, Kong (DB-less declarative config), pytest. Plan reuses existing test fixtures (`bootstrapper/tests/fixtures/rendered_config_baseline.yml`), the existing migration pattern (`bootstrapper/services/migrations/migration_v1.py`), and the existing audit gates (`scripts/check-kong-routes.py`).

**Spec:** `docs/specs/2026-05-25-localhost-port-override-design.md`

---

## Pre-flight

### Working environment

- **Branch protection.** `main` rejects direct pushes. Per memory `project-main-branch-protection`, every commit must land via a PR with the 3 services-lint CI checks green.
- **Worktree workflow.** Use `.claude/worktrees/<feature-name>/` per memory `project_branch_workflow`. The feature name for this plan is `localhost-port-override`.
- **Commit style.** Terse third-person verb, lowercase `<area>:` prefix (e.g. `wizard:`, `kong:`, `services:`), no Claude trailer. Match recent commits like `4f79394 wizard: add inline secondary number input on options-step rows`.
- **Test runner.** `cd bootstrapper && uv run pytest -q` for the full suite (~25 sec, currently 342 passing). Run from `bootstrapper/` directory.
- **Audit gates** (run at the end of each phase):
  - `cd /Users/kaveh/repos/genai-vanilla && PYTHONPATH=bootstrapper python -m bootstrapper.docs.regen --all --check`
  - `python scripts/check_doc_links.py`
  - `python scripts/check-compose-source-deps.py`
  - `python scripts/check-kong-routes.py`

### Existing tests this plan extends (not replaces)

- `bootstrapper/tests/test_prompt_panel_secondary_input.py` — widget contract tests for the existing per-step API. Will be rewritten when the API becomes per-option.
- `bootstrapper/tests/test_wizard_ray_steps.py` — Ray cascade tests; the worker-count case must continue to pass after the Ray wiring is migrated to the new API.
- `bootstrapper/tests/test_env_example_consistency.py` — asserts `.env.example` matches the manifest declarations byte-for-byte.
- `bootstrapper/tests/test_fragment_equivalence.py` — asserts the rendered compose matches the golden baseline. Updated each time a `runtime_sc.environment` block changes.
- `bootstrapper/tests/test_manifests.py` — manifest schema validation.

### Files this plan creates

- `bootstrapper/services/migrations/migration_v2.py` (Task 11)
- `bootstrapper/tests/test_migration_v2.py` (Task 11)
- `bootstrapper/tests/test_localhost_port_override.py` (Task 10)
- `bootstrapper/tests/test_port_collision_warning.py` (Task 13)

### Files this plan modifies

| Layer | Path | Tasks |
|---|---|---|
| Widget | `bootstrapper/ui/textual/widgets/prompt_panel.py` | 1, 3 |
| Widget | `bootstrapper/ui/textual/widgets/option_row.py` | 2 |
| Wizard | `bootstrapper/ui/textual/screens/wizard_screen.py` | 4 |
| Wizard | `bootstrapper/ui/textual/integration.py` | 4, 10 |
| Topology | `bootstrapper/services/topology.py` | 5 |
| Manifest dataclass | `bootstrapper/services/manifests.py` | 5 |
| Schema | `bootstrapper/schemas/service.schema.json` | 5 |
| Service manifests (refactor 7) | `services/{comfyui,docling,hermes,openclaw,parakeet,chatterbox}/service.yml` | 6 |
| Service manifests (add 3) | `services/{ollama,neo4j,weaviate}/service.yml` | 7 |
| Kong | `bootstrapper/utils/kong_config_generator.py` | 8 |
| State builder | `bootstrapper/ui/state_builder.py` | 9 |
| Migration | `bootstrapper/start.py` | 12 |
| Baseline fixture | `bootstrapper/tests/fixtures/rendered_config_baseline.yml` | 6, 7, 8 (regenerated) |
| Pre-launch UX | `bootstrapper/ui/state.py` (or similar — find at task time) | 13 |

---

## Task 0: Set up the feature worktree

**Files:**
- Modify: `.claude/worktrees/localhost-port-override/` (creates new worktree)

- [ ] **Step 1: Confirm primary repo is clean**

```bash
cd /Users/kaveh/repos/genai-vanilla && git status --short
```
Expected: empty output. If anything is uncommitted, stop and ask the user to stash/commit first — see memory `project_branch_workflow`'s "never `update-ref` while main is checked out elsewhere" warning.

- [ ] **Step 2: Create the worktree**

```bash
cd /Users/kaveh/repos/genai-vanilla \
  && git worktree add .claude/worktrees/localhost-port-override -b worktree-localhost-port-override main
```
Expected: `Preparing worktree (new branch 'worktree-localhost-port-override')` and `HEAD is now at <sha> <msg>`.

- [ ] **Step 3: Move into the worktree and verify**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/localhost-port-override \
  && git branch --show-current \
  && cd bootstrapper && uv run pytest -q 2>&1 | tail -3
```
Expected: branch `worktree-localhost-port-override`; tests `342 passed, 3 skipped`.

- [ ] **Step 4: No commit yet** — task 0 is setup only.

---

## Phase 1 — Widget API refactor: per-option `secondary_number`

This phase generalizes the inline-textbox widget so each option can carry its own integer-input config (with its own `env_var`). The Ray case migrates retroactively at the end of the phase.

### Task 1: `PromptOption.secondary_number` + drop `show_when`

**Files:**
- Modify: `bootstrapper/ui/textual/widgets/prompt_panel.py:196-227` (SecondaryNumberInput) and `:230-251` (PromptOption) and `:254-309` (PromptStep)
- Modify: `bootstrapper/tests/test_prompt_panel_secondary_input.py` (rewrite for new API)

- [ ] **Step 1: Write failing tests** (`bootstrapper/tests/test_prompt_panel_secondary_input.py` — REPLACE the file's contents)

```python
"""Unit tests for the per-option ``SecondaryNumberInput`` widget contract.

Eligibility is now per-option: a ``PromptOption`` either carries a
``SecondaryNumberInput`` config (eligible — renders an inline textbox)
or doesn't (no textbox slot rendered on that row). Different options
on the same step can carry configs writing to DIFFERENT env vars; the
widget mirrors keystrokes only between siblings sharing an env_var.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest

from ui.textual.widgets.prompt_panel import (
    PromptOption,
    PromptPanel,
    PromptStep,
    SecondaryNumberInput,
)


@dataclass
class _InputStub:
    """Stand-in for textual.widgets.Input — exposes value + env_var."""
    value: str = ""
    # Each Input is associated with the env_var it writes; set by
    # PromptPanel when mounting. _sync_secondary_inputs filters siblings
    # by this attribute.
    associated_env_var: str = ""


class _PanelStub:
    """Stand-in for PromptPanel that exposes only what secondary_values
    and _sync_secondary_inputs need."""

    secondary_values = PromptPanel.secondary_values
    _sync_secondary_inputs = PromptPanel._sync_secondary_inputs
    selected_option = PromptPanel.selected_option

    def __init__(self, step: PromptStep, *, selected_index: int = 0):
        self._step = step
        self._selected_index = selected_index
        self._secondary_inputs: list[_InputStub] = []


def _opt(value: str, *, secondary: SecondaryNumberInput | None = None) -> PromptOption:
    return PromptOption(value=value, label=value, secondary_number=secondary)


def _step(options: list[PromptOption]) -> PromptStep:
    return PromptStep(
        title="test step",
        step_index=1,
        step_total=1,
        heading="",
        options=options,
        kind="options",
    )


# ─── secondary_values: returns ALL eligible rows' values ──────────────

def test_secondary_values_empty_when_no_options_have_config():
    """A vanilla step with no option carrying a config yields no values."""
    panel = _PanelStub(_step([_opt("a"), _opt("b")]))
    assert panel.secondary_values() == []


def test_secondary_values_returns_one_tuple_per_eligible_option():
    """Two eligible options writing the SAME env_var still produce two
    tuples (the caller deduplicates if it cares — for our pipeline they
    share a key in the selections dict so the second write wins, which
    is fine because the sync logic keeps siblings equal)."""
    cfg = SecondaryNumberInput(env_var="X", default_value=5, number_min=0, number_max=100)
    panel = _PanelStub(_step([_opt("a", secondary=cfg), _opt("b", secondary=cfg), _opt("c")]))
    panel._secondary_inputs = [
        _InputStub(value="5", associated_env_var="X"),
        _InputStub(value="5", associated_env_var="X"),
    ]
    tuples = panel.secondary_values()
    assert tuples == [("X", "5"), ("X", "5")]


def test_secondary_values_distinct_env_vars_yield_distinct_tuples():
    """STT case: parakeet-localhost writes PARAKEET_LOCALHOST_PORT,
    whisper-cpp-localhost writes WHISPER_CPP_LOCALHOST_PORT. Both
    visible inputs produce distinct tuples."""
    cfg_a = SecondaryNumberInput(env_var="PARAKEET", default_value=63022,
                                 number_min=1024, number_max=65535)
    cfg_b = SecondaryNumberInput(env_var="WHISPER", default_value=63025,
                                 number_min=1024, number_max=65535)
    panel = _PanelStub(_step([_opt("p", secondary=cfg_a), _opt("w", secondary=cfg_b)]))
    panel._secondary_inputs = [
        _InputStub(value="63022", associated_env_var="PARAKEET"),
        _InputStub(value="63025", associated_env_var="WHISPER"),
    ]
    assert panel.secondary_values() == [("PARAKEET", "63022"), ("WHISPER", "63025")]


def test_secondary_values_clamps_each_independently():
    """Each input's value is clamped to its own config's min/max."""
    cfg_a = SecondaryNumberInput(env_var="A", default_value=8000, number_min=1024, number_max=65535)
    cfg_b = SecondaryNumberInput(env_var="B", default_value=11434, number_min=1024, number_max=65535)
    panel = _PanelStub(_step([_opt("a", secondary=cfg_a), _opt("b", secondary=cfg_b)]))
    panel._secondary_inputs = [
        _InputStub(value="99999", associated_env_var="A"),  # clamps to 65535
        _InputStub(value="50",    associated_env_var="B"),  # clamps to 1024
    ]
    assert panel.secondary_values() == [("A", "65535"), ("B", "1024")]


def test_secondary_values_falls_back_to_default_on_garbage_input():
    cfg = SecondaryNumberInput(env_var="X", default_value=8000, number_min=1024, number_max=65535)
    panel = _PanelStub(_step([_opt("a", secondary=cfg)]))
    panel._secondary_inputs = [_InputStub(value="not-a-number", associated_env_var="X")]
    assert panel.secondary_values() == [("X", "8000")]


def test_secondary_values_empty_input_uses_default():
    cfg = SecondaryNumberInput(env_var="X", default_value=8000, number_min=1024, number_max=65535)
    panel = _PanelStub(_step([_opt("a", secondary=cfg)]))
    panel._secondary_inputs = [_InputStub(value="", associated_env_var="X")]
    assert panel.secondary_values() == [("X", "8000")]


# ─── _sync_secondary_inputs: keyed by env_var ─────────────────────────

def test_sync_mirrors_value_across_siblings_sharing_env_var():
    """Two inputs writing the same env_var sync; a third writing a
    different env_var stays independent."""
    panel = _PanelStub(_step([]))
    a = _InputStub(value="2", associated_env_var="X")
    b = _InputStub(value="2", associated_env_var="X")
    c = _InputStub(value="9000", associated_env_var="Y")
    panel._secondary_inputs = [a, b, c]
    a.value = "7"
    panel._sync_secondary_inputs(a)
    assert b.value == "7", "Same-env_var sibling not synced"
    assert c.value == "9000", "Different-env_var sibling should be independent"


def test_sync_is_idempotent_when_values_already_match():
    panel = _PanelStub(_step([]))
    a = _InputStub(value="5", associated_env_var="X")
    b = _InputStub(value="5", associated_env_var="X")
    panel._secondary_inputs = [a, b]
    panel._sync_secondary_inputs(a)
    assert a.value == "5" and b.value == "5"


# ─── dataclass shape ──────────────────────────────────────────────────

def test_secondary_number_input_dropped_show_when_field():
    """show_when removed — eligibility is now per-option config attached."""
    fields = {f for f in SecondaryNumberInput.__dataclass_fields__}
    assert "show_when" not in fields, (
        f"SecondaryNumberInput should no longer have show_when. Fields: {fields}"
    )


def test_prompt_option_has_secondary_number_field():
    """The new per-option config lives on PromptOption."""
    fields = PromptOption.__dataclass_fields__
    assert "secondary_number" in fields, (
        f"PromptOption should carry secondary_number. Fields: {set(fields)}"
    )
    assert fields["secondary_number"].default is None


def test_prompt_step_no_longer_has_secondary_number_field():
    """The step-level secondary_number is gone — eligibility is per-option now."""
    fields = {f for f in PromptStep.__dataclass_fields__}
    assert "secondary_number" not in fields, (
        f"PromptStep should no longer carry secondary_number. Fields: {fields}"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd bootstrapper && uv run pytest tests/test_prompt_panel_secondary_input.py -v 2>&1 | tail -20
```
Expected: ALL 11 tests FAIL with errors like `AttributeError: ... has no attribute 'secondary_values'` and `AssertionError: PromptOption should carry secondary_number`.

- [ ] **Step 3: Update `SecondaryNumberInput` and `PromptOption` dataclasses**

In `bootstrapper/ui/textual/widgets/prompt_panel.py`, replace the `SecondaryNumberInput` class (currently at lines 196-227) with:

```python
@dataclass
class SecondaryNumberInput:
    """An inline integer textbox attached to a ``PromptOption``. The
    option renders the input directly between its label and its badges
    (see ``OptionRowWithInput``).

    On confirm, the integer value is captured alongside the tile
    selection and written to ``env_var`` via the wizard's selection
    pipeline.

    Eligibility for the inline input is now per-option: a
    ``PromptOption`` either carries one of these (eligible — input
    rendered) or doesn't (no input on that row). The earlier
    ``show_when`` filter on this dataclass is gone — equivalent
    behaviour comes from attaching the config to the matching options.

    ``unit_suffix`` is the short label rendered immediately to the
    right of the textbox on eligible rows ("workers", "port", "MB", …)
    so the user reads the row as ``ollama-localhost [ 11434 ] port
    [rec.]``. Empty string hides the suffix entirely.

    Sibling-sync semantics (when two rows on the same step both carry
    a config): inputs writing the SAME ``env_var`` mirror keystrokes
    so the user only types once; inputs writing DIFFERENT ``env_var``s
    are independent (e.g. STT step's parakeet vs whisper-cpp ports).
    """
    env_var: str
    description: str = ""
    default_value: int = 0
    number_min: int = 0
    number_max: int = 1_000_000
    unit_suffix: str = ""
```

In the same file, update the `PromptOption` dataclass (currently at lines 230-251) by adding the new field at the end (preserve existing fields):

```python
@dataclass
class PromptOption:
    value: str
    label: str
    hint: str = ""
    badges: list[str] = field(default_factory=list)
    pulls: int = 0
    sizes: tuple[str, ...] = ()
    pulled_variants: frozenset[str] = field(default_factory=frozenset)
    # Inline secondary integer input attached to THIS row. When set, the
    # row renders via OptionRowWithInput with an editable textbox between
    # the label and the badges. When None (the default), the row renders
    # via the plain OptionRow. See SecondaryNumberInput for semantics.
    secondary_number: "SecondaryNumberInput | None" = None
```

In the same file, remove the `secondary_number` field from `PromptStep` (currently at lines 304-309). After removal, the relevant tail of `PromptStep` reads:

```python
    filter_tags: tuple[str, ...] = ()
    # secondary_number REMOVED 2026-05-25 — config now lives on each
    # PromptOption (see PromptOption.secondary_number). Eligibility is
    # "option carries a config" instead of "step-level show_when filter."
```

- [ ] **Step 4: Run dataclass-shape tests to verify they pass**

```bash
cd bootstrapper && uv run pytest tests/test_prompt_panel_secondary_input.py::test_secondary_number_input_dropped_show_when_field tests/test_prompt_panel_secondary_input.py::test_prompt_option_has_secondary_number_field tests/test_prompt_panel_secondary_input.py::test_prompt_step_no_longer_has_secondary_number_field -v 2>&1 | tail -10
```
Expected: 3 passes. Other tests still fail (they depend on `secondary_values` which doesn't exist yet — implemented in Task 3).

- [ ] **Step 5: Commit**

```bash
git add bootstrapper/ui/textual/widgets/prompt_panel.py bootstrapper/tests/test_prompt_panel_secondary_input.py
git commit -m "$(cat <<'EOF'
wizard: move SecondaryNumberInput config from PromptStep onto PromptOption

Eligibility for the inline textbox is now per-option: a PromptOption
carrying secondary_number is eligible; otherwise the row renders
without an input. Replaces the previous step-level show_when filter
(which couldn't express "different env vars per row" — needed for the
upcoming localhost-port-per-service feature).

Dataclass shape only in this commit. The mounting branch in
OptionRowWithInput + sibling sync + secondary_value capture are
updated in following commits (kept separate so each step is
independently bisectable).
EOF
)"
```

### Task 2: `OptionRowWithInput` mount logic — per-option config

**Files:**
- Modify: `bootstrapper/ui/textual/widgets/prompt_panel.py:725-779` (the options-mount branch in `load_step`)
- Test: same test file from Task 1 (tests already written)

- [ ] **Step 1: Read the current options-mount branch**

The current branch (lines 725-779) keys off `step.secondary_number` (singular). After the refactor it keys off `opt.secondary_number` (per-option).

- [ ] **Step 2: Replace the options-mount branch with per-option logic**

In `bootstrapper/ui/textual/widgets/prompt_panel.py`, replace the block that starts with `# Options-list mounting.` (line ~725) through the end of the `for i, opt in enumerate(step.options):` loop with:

```python
        # Options-list mounting.
        #
        # When ANY option on the step carries a ``secondary_number``
        # config, EVERY row uses the ``OptionRowWithInput`` composite
        # so the textbox column and the badges column align across the
        # screen — eligible rows mount a real ``Input`` tagged with the
        # env_var it writes, ineligible rows mount a spacer Static of
        # the same width.
        #
        # When NO option on the step has a secondary_number, every row
        # falls back to the plain ``OptionRow`` — the existing baseline.
        self._secondary_inputs = []
        any_secondary = any(opt.secondary_number is not None for opt in step.options)

        # Fixed label column width for the composite layout (cells):
        # cursor + dot indicator (3) + inter-column gap (4) + the
        # longest option label in this step. Every row uses the same
        # value so the textbox column lands at the same x on every row.
        label_col_width = 0
        if any_secondary and step.options:
            label_col_width = SECONDARY_LABEL_PREFIX_WIDTH + max(
                len(opt.label) for opt in step.options
            )

        # Compute the longest unit_suffix in the step so every row's
        # suffix cell reserves the same width (eligible rows render the
        # text, ineligible rows render a space-padded equivalent).
        unit_suffix_for_row = ""
        if any_secondary:
            unit_suffix_for_row = max(
                (opt.secondary_number.unit_suffix
                 for opt in step.options if opt.secondary_number is not None),
                key=len,
                default="",
            )

        self._option_list.remove_children()
        for i, opt in enumerate(step.options):
            if not any_secondary:
                self._option_list.mount(OptionRow(
                    opt.label,
                    hint=opt.hint,
                    badges=opt.badges,
                    selected=(i == self._selected_index),
                ))
                continue
            cfg = opt.secondary_number
            inp: "Input | None" = None
            if cfg is not None:
                inp = Input(
                    value=str(cfg.default_value),
                    placeholder=str(cfg.default_value),
                )
                # Tag the input with its env_var so _sync_secondary_inputs
                # can mirror only between siblings sharing one.
                inp.associated_env_var = cfg.env_var  # type: ignore[attr-defined]
                self._secondary_inputs.append(inp)
            self._option_list.mount(OptionRowWithInput(
                opt.label,
                hint=opt.hint,
                badges=opt.badges,
                selected=(i == self._selected_index),
                input_widget=inp,
                label_width=label_col_width,
                unit_suffix=unit_suffix_for_row,
            ))
```

- [ ] **Step 3: Smoke-import to catch syntax errors**

```bash
cd bootstrapper && PYTHONPATH=. python -c "
from ui.textual.widgets.prompt_panel import PromptPanel, PromptOption, PromptStep, SecondaryNumberInput
print('imports OK')
print('PromptOption fields:', list(PromptOption.__dataclass_fields__))
"
```
Expected: `imports OK` + the fields list ending in `secondary_number`.

- [ ] **Step 4: Run the full suite — expect Ray tests to fail (Ray wiring still uses old API; fixed in Task 4)**

```bash
cd bootstrapper && uv run pytest -q 2>&1 | tail -8
```
Expected: many failures in tests that exercise the Ray wizard step. The exact count isn't load-bearing; the goal is "the dataclass refactor + new mount logic compiles and the widget-only tests pass."

- [ ] **Step 5: Commit**

```bash
git add bootstrapper/ui/textual/widgets/prompt_panel.py
git commit -m "$(cat <<'EOF'
wizard: per-option secondary_number drives OptionRowWithInput mount

When ANY option on the step carries a SecondaryNumberInput config,
every row uses the OptionRowWithInput composite — eligible rows mount
a real Input tagged with its env_var, ineligible rows mount the
existing spacer Static. Tag-on-Input is consumed by the next commit's
sibling-sync refactor.

Ray wiring still uses the old step-level API and fails at runtime
until Task 4 migrates it. Tests for the new mount logic land in
Task 3.
EOF
)"
```

### Task 3: `secondary_values()` + env-var-keyed sibling sync

**Files:**
- Modify: `bootstrapper/ui/textual/widgets/prompt_panel.py:781-796` (`_sync_secondary_inputs`)
- Modify: `bootstrapper/ui/textual/widgets/prompt_panel.py:1326-1355` (`secondary_value` → `secondary_values`)

- [ ] **Step 1: Read the current implementations**

```bash
grep -n "_sync_secondary_inputs\|def secondary_value" bootstrapper/ui/textual/widgets/prompt_panel.py | head
```

- [ ] **Step 2: Replace `_sync_secondary_inputs` with env-var-keyed sync**

In `bootstrapper/ui/textual/widgets/prompt_panel.py`, replace the existing `_sync_secondary_inputs` method (currently lines 781-796) with:

```python
    def _sync_secondary_inputs(self, source: "Input") -> None:
        """Mirror ``source.value`` across every sibling secondary input
        that writes the SAME ``env_var``.

        Called from ``on_input_changed`` whenever any eligible-row Input
        emits a Changed event. Inputs writing the same env_var share
        one logical value (e.g. Ray's two container-source rows both
        write RAY_WORKER_COUNT and stay synced); inputs writing
        different env_vars are independent (e.g. STT step's parakeet
        vs. whisper-cpp ports).

        The associated env_var was stamped on each Input as
        ``associated_env_var`` when it was mounted (see ``load_step``).
        """
        source_env_var = getattr(source, "associated_env_var", "")
        new_value = source.value or ""
        for other in self._secondary_inputs:
            if other is source:
                continue
            if getattr(other, "associated_env_var", "") != source_env_var:
                continue  # different env_var — independent
            if other.value == new_value:
                continue
            other.value = new_value
```

- [ ] **Step 3: Replace `secondary_value()` with `secondary_values()` (plural, returns list)**

In `bootstrapper/ui/textual/widgets/prompt_panel.py`, replace the entire `secondary_value` method (currently lines 1326-1355) with:

```python
    def secondary_values(self) -> list[tuple[str, str]]:
        """Return one ``(env_var, value)`` tuple per visible eligible
        input on the active step, or ``[]`` when the step has no
        secondary inputs.

        Different rows can write different env_vars (e.g. STT step's
        parakeet-localhost vs whisper-cpp-localhost). The caller routes
        each tuple through ``selections["__secondary__:<env_var>"]``.

        Per-input clamping into the configured ``[number_min, number_max]``
        range; non-numeric input falls back to ``default_value``.

        Eligibility is now per-option: this method iterates the
        active step's options, finds those carrying a
        ``secondary_number`` config, and pairs each with the matching
        Input from ``self._secondary_inputs`` (in mount order).
        """
        if self._step is None or self._step.kind != "options":
            return []
        # Walk options in display order; each eligible option's index
        # in the input list mirrors its mount order in the option list.
        results: list[tuple[str, str]] = []
        input_iter = iter(self._secondary_inputs)
        for opt in self._step.options:
            cfg = opt.secondary_number
            if cfg is None:
                continue
            try:
                inp = next(input_iter)
            except StopIteration:
                break
            raw = (inp.value or "").strip()
            try:
                value = int(raw) if raw else int(cfg.default_value)
            except ValueError:
                value = int(cfg.default_value)
            value = max(cfg.number_min, min(cfg.number_max, value))
            results.append((cfg.env_var, str(value)))
        return results
```

- [ ] **Step 4: Run the widget tests — they should all pass now**

```bash
cd bootstrapper && uv run pytest tests/test_prompt_panel_secondary_input.py -v 2>&1 | tail -15
```
Expected: ALL 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add bootstrapper/ui/textual/widgets/prompt_panel.py
git commit -m "$(cat <<'EOF'
wizard: secondary_values() returns per-eligible-row tuples; sync keyed by env_var

secondary_value() (singular) → secondary_values() (list of (env_var,
value) tuples). One tuple per visible eligible row; different rows
can write to different env_vars (STT step's parakeet vs whisper-cpp
ports — both inputs are visible, both produce tuples).

_sync_secondary_inputs now filters siblings by associated_env_var so
two inputs writing the same env_var mirror keystrokes (Ray's
container-cpu + container-gpu rows) while two writing different
env_vars stay independent (STT's per-engine ports).
EOF
)"
```

### Task 4: `wizard_screen` drain + Ray wiring migration

**Files:**
- Modify: `bootstrapper/ui/textual/screens/wizard_screen.py:605-619` (confirm-handler secondary drain)
- Modify: `bootstrapper/ui/textual/integration.py:245-277` (Ray wiring to attach config per-option)
- Test: `bootstrapper/tests/test_wizard_ray_steps.py` (existing tests must continue to pass)

- [ ] **Step 1: Replace the secondary drain in the confirm handler**

In `bootstrapper/ui/textual/screens/wizard_screen.py`, replace lines 610-619 (the `Inline secondary integer input ...` block) with:

```python
        # Inline secondary integer inputs (kind="options" + per-option
        # secondary_number): capture each visible eligible input's value
        # under a synthetic ``__secondary__:<ENV_VAR>`` key so
        # _selections_to_args can route them to the env-write bag.
        # Empty list when the step has no eligible rows.
        for env_var, value in self._prompt.secondary_values():
            self._selections[f"__secondary__:{env_var}"] = value
```

- [ ] **Step 2: Migrate the Ray wiring to attach `secondary_number` per-option**

In `bootstrapper/ui/textual/integration.py`, replace the block starting at line 245 (the `Inline secondary integer input: Ray's source prompt ...` comment) through line 277 (the `secondary_number=secondary,` line in the `steps.append(...)` call) with:

```python
        # Per-option secondary_number: attach the inline integer input to
        # the specific option rows where it makes sense.
        # • Ray: worker count on the container-cpu / container-gpu rows.
        # • Localhost-port overrides: attached per-localhost-row in
        #   Task 10. None of the localhost-attachments live here today.
        ray_secondary: SecondaryNumberInput | None = None
        if svc.key in ("ray", "ray-head") or svc.display_name == "Ray":
            raw_default = (env_vars.get("RAY_WORKER_COUNT") or "2").strip()
            try:
                worker_default = max(0, min(64, int(raw_default)))
            except ValueError:
                worker_default = 2
            ray_secondary = SecondaryNumberInput(
                env_var="RAY_WORKER_COUNT",
                description=(
                    "Ray worker replicas alongside the head node "
                    "(0 = head-only single-node cluster). 0-64."
                ),
                default_value=worker_default,
                number_min=0,
                number_max=64,
                unit_suffix="workers",
            )
        opts = [
            PromptOption(
                value=opt,
                label=opt,
                hint=_option_hint(opt),
                badges=_badges_for_option(opt, recommended=(opt == svc.current_value)),
                # Attach Ray's worker-count config to the container-cpu
                # and container-gpu options (the eligible source variants).
                secondary_number=(
                    ray_secondary
                    if ray_secondary is not None
                       and opt in ("ray-container-cpu", "ray-container-gpu")
                    else None
                ),
            )
            for opt in svc.options
        ]
        default = svc.current_value if svc.current_value in svc.options else (
            svc.options[0] if svc.options else None
        )
        steps.append(PromptStep(
            title=f"{svc.display_name}  ·  source",
            step_index=i + 2, step_total=total,
            heading=f"How should {svc.display_name} run?",
            subtitle=svc.description or "",
            options=opts, default_value=default, service_name=svc.display_name,
            service_key=svc.key,
            # secondary_number REMOVED from PromptStep — config is now
            # on individual PromptOption entries above.
        ))
```

Note: the `opts = [PromptOption(...)]` list comprehension was earlier in the file; the change is to MOVE the Ray secondary computation BEFORE the comprehension and inline the per-option attachment INTO the comprehension. The `secondary_number=` kwarg on `PromptStep` is removed.

- [ ] **Step 3: Run the existing Ray tests to verify the migration preserves behavior**

```bash
cd bootstrapper && uv run pytest tests/test_wizard_ray_steps.py -v 2>&1 | tail -10
```
Expected: 4 tests pass (cpu / gpu emit no cascade; external emits address; disabled emits nothing).

- [ ] **Step 4: Run the full suite**

```bash
cd bootstrapper && uv run pytest -q 2>&1 | tail -5
```
Expected: `342 passed` (or similar — same baseline as before this plan started).

- [ ] **Step 5: Commit**

```bash
git add bootstrapper/ui/textual/screens/wizard_screen.py bootstrapper/ui/textual/integration.py
git commit -m "$(cat <<'EOF'
wizard: confirm drains secondary_values() list; Ray migrated to per-option API

The single-tuple secondary_value() drain becomes a loop over
secondary_values() so a step with multiple eligible rows writing
different env_vars persists all of them (groundwork for STT step's
per-engine port inputs).

Ray wiring moves the worker-count SecondaryNumberInput onto the
ray-container-cpu / ray-container-gpu PromptOption entries explicitly
instead of the step-level config + show_when filter. Behaviour is
identical end-to-end; the test suite still goes green.
EOF
)"
```

---

## Phase 2 — Topology + manifest baseline

### Task 5: `localhost_port_var` on `Row` + manifest schema

**Files:**
- Modify: `bootstrapper/services/manifests.py:97-106` (`ManifestRow` dataclass)
- Modify: `bootstrapper/services/manifests.py:331-337` (`ManifestRow` construction from YAML)
- Modify: `bootstrapper/services/topology.py:101-114` (`Row` dataclass)
- Modify: `bootstrapper/services/topology.py:310-322` (`Row` construction from `ManifestRow`)
- Modify: `bootstrapper/schemas/service.schema.json` (add `localhost_port_var` to row schema)
- Test: `bootstrapper/tests/test_manifests.py` (add a case validating the new field)

- [ ] **Step 1: Find the schema row definition**

```bash
grep -n "localhost_endpoint_var\|properties.*rows" bootstrapper/schemas/service.schema.json | head -10
```

- [ ] **Step 2: Write a failing test that the new field round-trips through manifest → topology**

Append this test to `bootstrapper/tests/test_manifests.py`:

```python
def test_row_carries_localhost_port_var_through_topology(tmp_path):
    """Newly-added field on ManifestRow → Row in topology, surfaced
    intact so state_builder.resolve_port can read it without going
    back through the YAML."""
    from services.manifests import _load_one_manifest
    from services.topology import build_topology

    # Synthetic minimal manifest with the new field.
    manifest_yml = tmp_path / "minimal" / "service.yml"
    manifest_yml.parent.mkdir(parents=True)
    manifest_yml.write_text("""
name: minimal
label: Minimal
category: apps
docs: services/minimal/README.md
containers: [minimal]
sources:
  var: MINIMAL_SOURCE
  default: container
  options:
    - id: container
      label: "Container"
    - id: localhost
      label: "Localhost"
env: []
rows:
  - display_name: "Minimal"
    source_var: MINIMAL_SOURCE
    port_var: MINIMAL_PORT
    localhost_endpoint_var: MINIMAL_ENDPOINT
    localhost_port_var: MINIMAL_LOCALHOST_PORT
""")
    topology = build_topology(tmp_path)
    matching = [r for r in topology.rows if r.display_name == "Minimal"]
    assert len(matching) == 1
    row = matching[0]
    assert row.localhost_port_var == "MINIMAL_LOCALHOST_PORT", (
        f"localhost_port_var did not survive manifest→Row round-trip; "
        f"got {row.localhost_port_var!r}"
    )
```

- [ ] **Step 3: Run the test to verify it fails**

```bash
cd bootstrapper && uv run pytest tests/test_manifests.py::test_row_carries_localhost_port_var_through_topology -v 2>&1 | tail -10
```
Expected: `AttributeError: 'Row' object has no attribute 'localhost_port_var'` or similar.

- [ ] **Step 4: Add the field to `ManifestRow`**

In `bootstrapper/services/manifests.py`, update the `ManifestRow` dataclass (lines 97-106) to add the new field at the end:

```python
@dataclass(frozen=True)
class ManifestRow:
    """Single row entry in a manifest's rows: list."""
    display_name: str
    source_var: str
    port_var: str = ""
    scale_var: str = ""
    alias: str = ""
    description: str = ""
    localhost_endpoint_var: str = ""
    # Env var holding the user-overridable host port for the localhost
    # source variant. Read by ui.state_builder.resolve_port to show the
    # port column on localhost rows; written by the wizard via the
    # inline SecondaryNumberInput widget. Empty string means the
    # service has no overridable localhost port (mostly: services with
    # no localhost source variant, OR legacy services not yet migrated
    # to the LOCALHOST_PORT pattern).
    localhost_port_var: str = ""
```

Also update the `ManifestRow` construction site (around line 337):

```python
            ManifestRow(
                display_name=r["display_name"],
                source_var=r["source_var"],
                port_var=r.get("port_var", ""),
                scale_var=r.get("scale_var", ""),
                alias=r.get("alias", ""),
                description=r.get("description", ""),
                localhost_endpoint_var=r.get("localhost_endpoint_var", ""),
                localhost_port_var=r.get("localhost_port_var", ""),
            )
```

- [ ] **Step 5: Add the field to `Row` and propagate through `build_topology`**

In `bootstrapper/services/topology.py`, update the `Row` dataclass (lines 101-114):

```python
@dataclass(frozen=True)
class Row:
    """A single box row. Resolved from a manifest's rows[] entry plus category metadata."""

    manifest: str
    display_name: str
    source_var: str
    port_var: str | None
    scale_var: str | None
    alias: str | None
    description: str
    localhost_endpoint_var: str | None
    # The env var holding the overridable host port for this row's
    # localhost source variant. None when the manifest doesn't declare
    # one (service has no localhost source, OR legacy service not yet
    # migrated to the LOCALHOST_PORT pattern).
    localhost_port_var: str | None
    category: str
    locked: bool
```

Update the construction site (around line 311):

```python
        for r in m.rows:
            rows.append(Row(
                manifest=m.name,
                display_name=r.display_name,
                source_var=r.source_var,
                port_var=r.port_var or None,
                scale_var=r.scale_var or None,
                alias=r.alias or None,
                description=r.description,
                localhost_endpoint_var=r.localhost_endpoint_var or None,
                localhost_port_var=r.localhost_port_var or None,
                category=m.category,
                locked=locked_by_name[m.name],
            ))
```

- [ ] **Step 6: Add the schema entry**

In `bootstrapper/schemas/service.schema.json`, find the `rows` array's item schema (search for `localhost_endpoint_var`) and add a sibling property next to it. Example, given the existing pattern:

```json
"localhost_endpoint_var": {
  "type": "string",
  "description": "..."
},
"localhost_port_var": {
  "type": "string",
  "description": "Env var holding the user-overridable host port for the localhost source variant. Empty for services without an overridable localhost port."
}
```

- [ ] **Step 7: Run the test to verify it passes**

```bash
cd bootstrapper && uv run pytest tests/test_manifests.py::test_row_carries_localhost_port_var_through_topology -v 2>&1 | tail -5
```
Expected: PASS.

- [ ] **Step 8: Run full suite — expect zero regressions (field defaults to empty)**

```bash
cd bootstrapper && uv run pytest -q 2>&1 | tail -5
```
Expected: all pass (+1 vs baseline).

- [ ] **Step 9: Commit**

```bash
git add bootstrapper/services/manifests.py bootstrapper/services/topology.py bootstrapper/schemas/service.schema.json bootstrapper/tests/test_manifests.py
git commit -m "$(cat <<'EOF'
services: row.localhost_port_var carries the user-overridable host port var

New optional manifest field that names the env var holding a localhost
source's host port (e.g. COMFYUI_LOCALHOST_PORT). Defaults to empty
when absent — services not yet migrated to the LOCALHOST_PORT pattern
continue to behave exactly as before. Schema + dataclass + topology
round-trip; consumers (state_builder, Kong generator, wizard) follow
in later commits.
EOF
)"
```

### Task 6: Refactor 7 services' manifests — URL → PORT

**Files (all in same task — same pattern across services):**
- Modify: `services/comfyui/service.yml`
- Modify: `services/docling/service.yml`
- Modify: `services/hermes/service.yml`
- Modify: `services/openclaw/service.yml`
- Modify: `services/parakeet/service.yml`
- Modify: `services/chatterbox/service.yml`
- Modify: `bootstrapper/tests/fixtures/rendered_config_baseline.yml` (regenerate)

Default ports for reference (extracted from current `.env.example`):

| Service | Old URL var | New PORT var | Default |
|---|---|---|---|
| Comfyui | `COMFYUI_LOCALHOST_URL` | `COMFYUI_LOCALHOST_PORT` | 8000 |
| Docling | `DOCLING_LOCALHOST_URL` | `DOCLING_LOCALHOST_PORT` | 63021 |
| Hermes | `HERMES_LOCALHOST_URL` | `HERMES_LOCALHOST_PORT` | 63028 |
| Openclaw | `OPENCLAW_LOCALHOST_URL` | `OPENCLAW_LOCALHOST_PORT` | 63024 |
| Parakeet | `PARAKEET_LOCALHOST_URL` | `PARAKEET_LOCALHOST_PORT` | 63022 |
| Whisper-cpp | `WHISPER_CPP_LOCALHOST_URL` | `WHISPER_CPP_LOCALHOST_PORT` | 63025 |
| Chatterbox | `CHATTERBOX_LOCALHOST_URL` | `CHATTERBOX_LOCALHOST_PORT` | 63027 |

- [ ] **Step 1: For each of the 7 manifests, apply the pattern**

Per service, perform these exact edits in `services/<svc>/service.yml`:

**(a)** In the `env:` list, replace the URL-var entry:
```yaml
  - name: <SVC>_LOCALHOST_URL
    default: "http://host.docker.internal:<PORT>"
```
with:
```yaml
  - name: <SVC>_LOCALHOST_PORT
    default: "<PORT>"
    description: "Host port for the localhost source variant. URL is derived at compose-render time as http://host.docker.internal:<PORT>."
```

**(b)** In the `rows:` entry for the service, add the new field next to `localhost_endpoint_var`:
```yaml
    localhost_endpoint_var: <SVC>_ENDPOINT
    localhost_port_var: <SVC>_LOCALHOST_PORT
```

**(c)** In `runtime_sc.<svc>.<localhost-source-id>.environment`, replace:
```yaml
        <SVC>_ENDPOINT: ${<SVC>_LOCALHOST_URL:-http://host.docker.internal:<PORT>}
```
with:
```yaml
        <SVC>_ENDPOINT: http://host.docker.internal:${<SVC>_LOCALHOST_PORT:-<PORT>}
```

Worked example for `services/comfyui/service.yml`:
```yaml
# env: section
  - name: COMFYUI_LOCALHOST_PORT
    default: "8000"
    description: "Host port for the localhost source variant. URL is derived at compose-render time as http://host.docker.internal:8000."

# rows: section
  - display_name: "ComfyUI"
    source_var: COMFYUI_SOURCE
    port_var: COMFYUI_PORT
    scale_var: COMFYUI_SCALE
    alias: comfyui.localhost
    description: "AI image generation & workflows."
    localhost_endpoint_var: COMFYUI_ENDPOINT
    localhost_port_var: COMFYUI_LOCALHOST_PORT

# runtime_sc: section (the comfyui.localhost source)
    localhost:
      scale: 0
      environment:
        COMFYUI_ENDPOINT: http://host.docker.internal:${COMFYUI_LOCALHOST_PORT:-8000}
        IS_LOCAL_COMFYUI: 'true'
        COMFYUI_LOCAL_MODELS_PATH: ${COMFYUI_LOCAL_MODELS_PATH:-~/Documents/ComfyUI/models}
      deploy: {}
      extra_hosts:
      - host.docker.internal:host-gateway
```

Note for STT (parakeet manifest): there are TWO localhost-source variants (`parakeet-localhost` and `whisper-cpp-localhost`), each with its OWN env var. Both go through this same pattern; replace both URL refs with PORT refs in `runtime_sc.stt-provider.<src>.environment`.

- [ ] **Step 2: Regenerate `.env.example` and the compose baseline**

```bash
cd bootstrapper && PYTHONPATH=. python -m services.env_assembler 2>&1 | tail -5
```
Expected: `.env.example` updated; the URL entries are gone, PORT entries are present.

For the compose baseline, run pytest first to see the drift:
```bash
cd bootstrapper && uv run pytest tests/test_fragment_equivalence.py -v 2>&1 | tail -10
```
Expected: failure with a diff showing 7 services' `<SVC>_ENDPOINT` lines changed from `${<SVC>_LOCALHOST_URL:-...}` to `http://host.docker.internal:${<SVC>_LOCALHOST_PORT:-...}`.

Per memory `project_compose_baseline_test`, the right move when the change is intentional + you've eyeballed the diff is to surgically edit the baseline. Update `bootstrapper/tests/fixtures/rendered_config_baseline.yml` to match the new compose-rendered shape: search for each of the 7 affected lines and replace.

For Docling, look for the existing line:
```yaml
      DOCLING_ENDPOINT: ${DOCLING_LOCALHOST_URL:-http://host.docker.internal:63021}
```
and change to:
```yaml
      DOCLING_ENDPOINT: http://host.docker.internal:${DOCLING_LOCALHOST_PORT:-63021}
```
(Substring search will find one instance per affected service.)

- [ ] **Step 3: Run the affected tests to verify they now pass**

```bash
cd bootstrapper && uv run pytest tests/test_fragment_equivalence.py tests/test_env_example_consistency.py -v 2>&1 | tail -10
```
Expected: PASS.

- [ ] **Step 4: Run full suite — expect green**

```bash
cd bootstrapper && uv run pytest -q 2>&1 | tail -5
```
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add services/{comfyui,docling,hermes,openclaw,parakeet,chatterbox}/service.yml .env.example bootstrapper/tests/fixtures/rendered_config_baseline.yml
git commit -m "$(cat <<'EOF'
services: refactor 7 manifests from LOCALHOST_URL to LOCALHOST_PORT

Comfyui, Docling, Hermes, Openclaw, Parakeet, Whisper-cpp, Chatterbox
each switch from a monolithic <SVC>_LOCALHOST_URL env var to a
<SVC>_LOCALHOST_PORT integer var. runtime_sc.<src>.environment derives
the URL via shell interpolation:
http://host.docker.internal:${<SVC>_LOCALHOST_PORT:-<default>}.

Kong gateway + wizard service-table consumers follow in later commits.
.env migration (URL → PORT in existing user .env files) is Task 11.
EOF
)"
```

### Task 7: Add LOCALHOST_PORT env vars for Ollama, Neo4j, Weaviate

**Files:**
- Modify: `services/ollama/service.yml`
- Modify: `services/neo4j/service.yml`
- Modify: `services/weaviate/service.yml`
- Modify: `.env.example` (regenerated)
- Modify: `bootstrapper/tests/fixtures/rendered_config_baseline.yml` (regenerated)

New env vars + defaults:

| Service | New var | Default | Existing runtime_sc reference |
|---|---|---|---|
| Ollama | `OLLAMA_LOCALHOST_PORT` | 11434 | `OLLAMA_ENDPOINT: http://host.docker.internal:11434` |
| Neo4j | `NEO4J_LOCALHOST_HTTP_PORT` | 7474 | (Kong route only — runtime_sc doesn't use HTTP) |
| Neo4j | `NEO4J_LOCALHOST_BOLT_PORT` | 7687 | `NEO4J_URI: bolt://host.docker.internal:7687` |
| Weaviate | `WEAVIATE_LOCALHOST_PORT` | 8080 | `WEAVIATE_URL: http://host.docker.internal:8080` |

- [ ] **Step 1: `services/ollama/service.yml` — add env entry + rewire runtime_sc**

Add to the `env:` list (alphabetical or grouped with related vars — find a spot near other OLLAMA_* declarations):

```yaml
  - name: OLLAMA_LOCALHOST_PORT
    default: "11434"
    description: "Host port for the ollama-localhost source variant. URL is derived at compose-render time as http://host.docker.internal:11434."
```

Add to the `rows:` entry for Ollama:

```yaml
    localhost_endpoint_var: LITELLM_OLLAMA_UPSTREAM
    localhost_port_var: OLLAMA_LOCALHOST_PORT
```

Replace the existing `runtime_sc.ollama.ollama-localhost.environment` block (around lines 118-124):

```yaml
    ollama-localhost:
      scale: 0
      environment:
        OLLAMA_ENDPOINT: http://host.docker.internal:${OLLAMA_LOCALHOST_PORT:-11434}
      deploy: {}
      extra_hosts:
      - host.docker.internal:host-gateway
```

- [ ] **Step 2: `services/neo4j/service.yml` — add TWO env entries + rewire runtime_sc**

Add to the `env:` list:

```yaml
  - name: NEO4J_LOCALHOST_HTTP_PORT
    default: "7474"
    description: "Host HTTP port for the neo4j-localhost source variant (browser UI + REST). Kong route target is derived as http://host.docker.internal:7474."
  - name: NEO4J_LOCALHOST_BOLT_PORT
    default: "7687"
    description: "Host Bolt port for the neo4j-localhost source variant (driver protocol). NEO4J_URI is derived as bolt://host.docker.internal:7687."
```

Add to the `rows:` entry. Neo4j has two ports so the `localhost_port_var` field can only hold one — by convention, use the BOLT port (the one in NEO4J_URI, the in-container client path):

```yaml
    alias: graph.localhost
    localhost_port_var: NEO4J_LOCALHOST_BOLT_PORT
```

> **Wizard caveat for Neo4j:** the inline-textbox UI is single-input-per-row. For Neo4j the wizard will edit ONLY the Bolt port (the canonical one — backend, JupyterHub, etc. all use Bolt). The HTTP port is auto-derived as `bolt − 13` (7687 − 13 = 7674? no — the convention is independent: HTTP=7474, Bolt=7687). Override the HTTP port via .env hand-edit; this matches the existing Neo4j pattern where the manifest exposes one knob.

Actually correct that — re-read: there's no "auto-derive" rule. The two ports are independent. The wizard inline edits ONLY the Bolt port; HTTP is left at its default and the user edits `.env` manually if they need a non-default HTTP port. Document this in the `description:` strings above so the runbook is clear.

Replace the `runtime_sc.neo4j-graph-db.localhost.environment` block:

```yaml
    localhost:
      scale: 0
      environment:
        NEO4J_URI: bolt://host.docker.internal:${NEO4J_LOCALHOST_BOLT_PORT:-7687}
      deploy: {}
      extra_hosts:
      - host.docker.internal:host-gateway
```

- [ ] **Step 3: `services/weaviate/service.yml` — add env entry + rewire runtime_sc**

Add to the `env:` list:

```yaml
  - name: WEAVIATE_LOCALHOST_PORT
    default: "8080"
    description: "Host port for the weaviate-localhost source variant. URL is derived at compose-render time as http://host.docker.internal:8080."
```

Add to the `rows:` entry:

```yaml
    alias: weaviate.localhost
    localhost_endpoint_var: WEAVIATE_URL
    localhost_port_var: WEAVIATE_LOCALHOST_PORT
```

Replace the `runtime_sc.weaviate.localhost.environment` block:

```yaml
    localhost:
      scale: 0
      environment:
        WEAVIATE_URL: http://host.docker.internal:${WEAVIATE_LOCALHOST_PORT:-8080}
      deploy: {}
      extra_hosts:
      - host.docker.internal:host-gateway
```

- [ ] **Step 4: Regenerate `.env.example`**

```bash
cd bootstrapper && PYTHONPATH=. python -m services.env_assembler 2>&1 | tail -5
```
Expected: 4 new lines appear in `.env.example` (`OLLAMA_LOCALHOST_PORT=11434`, `NEO4J_LOCALHOST_HTTP_PORT=7474`, `NEO4J_LOCALHOST_BOLT_PORT=7687`, `WEAVIATE_LOCALHOST_PORT=8080`).

- [ ] **Step 5: Update the compose baseline**

```bash
cd bootstrapper && uv run pytest tests/test_fragment_equivalence.py -v 2>&1 | tail -15
```
Expected: failure showing the changed `OLLAMA_ENDPOINT`, `NEO4J_URI`, `WEAVIATE_URL` lines in the localhost sources.

Edit `bootstrapper/tests/fixtures/rendered_config_baseline.yml` to match:
- Find `OLLAMA_ENDPOINT: http://host.docker.internal:11434` (in the ollama-localhost block) → change to `OLLAMA_ENDPOINT: http://host.docker.internal:${OLLAMA_LOCALHOST_PORT:-11434}`
- Find `NEO4J_URI: bolt://host.docker.internal:7687` → change to `NEO4J_URI: bolt://host.docker.internal:${NEO4J_LOCALHOST_BOLT_PORT:-7687}`
- Find `WEAVIATE_URL: http://host.docker.internal:8080` (in the weaviate-localhost block — DON'T touch the container-mode `weaviate:8080`) → change to `WEAVIATE_URL: http://host.docker.internal:${WEAVIATE_LOCALHOST_PORT:-8080}`

- [ ] **Step 6: Run affected tests**

```bash
cd bootstrapper && uv run pytest tests/test_fragment_equivalence.py tests/test_env_example_consistency.py tests/test_manifests.py -v 2>&1 | tail -10
```
Expected: PASS.

- [ ] **Step 7: Full suite green**

```bash
cd bootstrapper && uv run pytest -q 2>&1 | tail -5
```

- [ ] **Step 8: Commit**

```bash
git add services/{ollama,neo4j,weaviate}/service.yml .env.example bootstrapper/tests/fixtures/rendered_config_baseline.yml
git commit -m "$(cat <<'EOF'
services: add LOCALHOST_PORT env vars for ollama / neo4j / weaviate

Ollama, Neo4j, Weaviate were the three localhost-capable services that
previously hardcoded host.docker.internal:<port> in their runtime_sc
environment blocks. They now declare LOCALHOST_PORT env vars that
runtime_sc consumes via shell interpolation. Neo4j has two ports
(HTTP browser + Bolt protocol); the wizard's inline-textbox edits the
Bolt port (NEO4J_URI), with HTTP overridable via .env hand-edit.

Kong gateway routes for these services still hardcode the port — that
switches to env-derived in Task 8.
EOF
)"
```

---

## Phase 3 — Consumers: Kong + service-table

### Task 8: Kong localhost-route generator reads PORT vars

**Files:**
- Modify: `bootstrapper/utils/kong_config_generator.py:200-260` (the localhost-route rows table)
- Modify: `bootstrapper/utils/kong_config_generator.py:307-340` (`_stt_localhost_url`, `_tts_localhost_url`)
- Modify: `bootstrapper/utils/kong_config_generator.py:536-540` (comfyui localhost URL ref)
- Modify: `bootstrapper/tests/test_kong_alias_routes.py` (extend or write new)
- Modify: any audit fixture used by `scripts/check-kong-routes.py` (find at task time)

- [ ] **Step 1: Survey what the existing localhost-route helpers do**

```bash
grep -nE "host\.docker\.internal|LOCALHOST_URL|LOCALHOST_PORT" bootstrapper/utils/kong_config_generator.py | head -30
```

- [ ] **Step 2: Write a failing test that Kong's localhost route reads the PORT var**

Append to `bootstrapper/tests/test_kong_alias_routes.py`:

```python
import pytest

@pytest.mark.parametrize("env_var,svc_source_var,svc_source_value,expected_port", [
    ("COMFYUI_LOCALHOST_PORT", "COMFYUI_SOURCE", "localhost", "9999"),
    ("DOCLING_LOCALHOST_PORT", "DOC_PROCESSOR_SOURCE", "docling-localhost", "9999"),
    ("HERMES_LOCALHOST_PORT", "HERMES_SOURCE", "localhost", "9999"),
    ("OPENCLAW_LOCALHOST_PORT", "OPENCLAW_SOURCE", "localhost", "9999"),
    ("PARAKEET_LOCALHOST_PORT", "STT_PROVIDER_SOURCE", "parakeet-localhost", "9999"),
    ("WHISPER_CPP_LOCALHOST_PORT", "STT_PROVIDER_SOURCE", "whisper-cpp-localhost", "9999"),
    ("CHATTERBOX_LOCALHOST_PORT", "TTS_PROVIDER_SOURCE", "chatterbox-localhost", "9999"),
    ("OLLAMA_LOCALHOST_PORT", "LLM_PROVIDER_SOURCE", "ollama-localhost", "9999"),
    ("NEO4J_LOCALHOST_HTTP_PORT", "NEO4J_GRAPH_DB_SOURCE", "localhost", "9999"),
    ("WEAVIATE_LOCALHOST_PORT", "WEAVIATE_SOURCE", "localhost", "9999"),
])
def test_kong_localhost_route_reads_port_var(
    env_var, svc_source_var, svc_source_value, expected_port, tmp_path
):
    """Each localhost-mode route's `url` is derived from the matching
    LOCALHOST_PORT env var — never hardcoded, never from the legacy URL
    var. Sets a non-default port and asserts the generated route URL
    reflects it."""
    from utils.kong_config_generator import KongConfigGenerator
    from core.config_parser import ConfigParser

    env_path = tmp_path / ".env"
    env_path.write_text(
        f"{svc_source_var}={svc_source_value}\n"
        f"{env_var}={expected_port}\n"
        "DASHBOARD_USERNAME=u\nDASHBOARD_PASSWORD=p\n",
        encoding="utf-8",
    )
    cp = ConfigParser(str(tmp_path))
    cp.env_file_path = env_path
    cp.parse_env_file()
    gen = KongConfigGenerator(cp)
    gen.load_environment_variables()
    cfg = gen.generate_kong_config()
    # Pull every service block, find the one whose route matches this
    # service-source variant, assert the url contains the typed port.
    found = []
    for svc in cfg["services"]:
        url = svc.get("url", "") or ""
        if f":{expected_port}" in url and "host.docker.internal" in url:
            found.append((svc["name"], url))
    assert found, (
        f"Expected at least one Kong service route to target "
        f"host.docker.internal:{expected_port} (matching {env_var}). "
        f"Got services: {[(s['name'], s.get('url')) for s in cfg['services']]}"
    )
```

- [ ] **Step 3: Run the test — expect FAIL for the 10 cases**

```bash
cd bootstrapper && uv run pytest tests/test_kong_alias_routes.py::test_kong_localhost_route_reads_port_var -v 2>&1 | tail -15
```
Expected: all 10 parametrized cases FAIL (route URLs still use the default port from the hardcoded fallback, or the legacy URL var).

- [ ] **Step 4: Introduce a centralized helper for "localhost URL from PORT var"**

In `bootstrapper/utils/kong_config_generator.py`, add this method to `KongConfigGenerator` near the top of the class (after `get_env_value`):

```python
    def _localhost_url(self, port_var: str, default_port: str | int) -> str:
        """Build a localhost-source upstream URL from a PORT env var.

        Returns ``http://host.docker.internal:<port>/`` where <port> is
        the value of ``port_var`` in .env if set, else ``default_port``.
        Centralized helper so the 10 localhost routes all share one
        substitution path — drift between them is the bug class memory
        ``feedback_localhost_url_override_symmetry`` warns against.
        """
        port = self.get_env_value(port_var) or str(default_port)
        return f"http://host.docker.internal:{port}/"
```

- [ ] **Step 5: Replace the hardcoded localhost lambdas in the rows table**

In `bootstrapper/utils/kong_config_generator.py`, find the `rows: List[tuple]` definition (around line 202) and replace each localhost-factory lambda with a `_localhost_url` call. Worked example for Neo4j and Weaviate:

```python
        rows: List[tuple] = [
            (
                "graph.localhost", "neo4j-browser",
                "NEO4J_GRAPH_DB_SOURCE",
                lambda _src: "http://neo4j-graph-db:7474/",
                lambda _src: self._localhost_url("NEO4J_LOCALHOST_HTTP_PORT", "7474"),
            ),
            (
                "weaviate.localhost", "weaviate-api",
                "WEAVIATE_SOURCE",
                lambda _src: "http://weaviate:8080/",
                lambda _src: self._localhost_url("WEAVIATE_LOCALHOST_PORT", "8080"),
            ),
            (
                "ollama.localhost", "ollama-api",
                "LLM_PROVIDER_SOURCE",
                lambda src: (
                    "http://ollama:11434/"
                    if src and src.startswith("ollama-container")
                    else None
                ),
                lambda src: (
                    self._localhost_url("OLLAMA_LOCALHOST_PORT", "11434")
                    if src == "ollama-localhost" else None
                ),
            ),
            (
                "docling.localhost", "docling-api",
                "DOC_PROCESSOR_SOURCE",
                lambda _src: "http://docling-gpu:8000/",
                lambda _src: self._localhost_url("DOCLING_LOCALHOST_PORT", "63021"),
            ),
            # ... preserve the research.localhost row exactly as today
            (
                "research.localhost", "research-api",
                "LOCAL_DEEP_RESEARCHER_SOURCE",
                lambda _src: "http://local-deep-researcher:2024/",
                lambda _src: None,
            ),
            (
                "stt.localhost", "stt-api",
                "STT_PROVIDER_SOURCE",
                self._stt_container_url,
                self._stt_localhost_url,
            ),
            # ... preserve tts row, append the rest as today
        ]
```

- [ ] **Step 6: Update `_stt_localhost_url` and `_tts_localhost_url`**

Replace `_stt_localhost_url` (lines 307-319):

```python
    def _stt_localhost_url(self, source: str) -> Optional[str]:
        """STT host-install URL — engine-specific PORT env var."""
        if source == "parakeet-localhost":
            return self._localhost_url("PARAKEET_LOCALHOST_PORT", "63022")
        if source == "whisper-cpp-localhost":
            return self._localhost_url("WHISPER_CPP_LOCALHOST_PORT", "63025")
        return None
```

Replace `_tts_localhost_url` (lines 333-340):

```python
    def _tts_localhost_url(self, source: str) -> Optional[str]:
        """TTS host-install URL — engine-specific PORT env var."""
        if source == "chatterbox-localhost":
            return self._localhost_url("CHATTERBOX_LOCALHOST_PORT", "63027")
        return None
```

- [ ] **Step 7: Replace the Hermes localhost ref (separate route)**

Find the Hermes / openclaw / comfyui localhost route blocks elsewhere in `kong_config_generator.py` (search for the remaining `_LOCALHOST_URL`) and replace each with a `_localhost_url(<PORT_var>, <default>)` call. Example for the comfyui block (around line 536):

Search:
```python
            self.get_env_value('COMFYUI_LOCALHOST_URL')
```
Replace with:
```python
            self._localhost_url("COMFYUI_LOCALHOST_PORT", "8000")
```
(Plus whatever surrounding rstrip / `+ "/"` logic the call site has — preserve it if the call had any; the `_localhost_url` helper already returns a trailing `/`.)

Do the same for `HERMES_LOCALHOST_URL` and `OPENCLAW_LOCALHOST_URL` references.

- [ ] **Step 8: Run the parameterized test — expect all 10 to pass**

```bash
cd bootstrapper && uv run pytest tests/test_kong_alias_routes.py -v 2>&1 | tail -15
```
Expected: all 10 PASS.

- [ ] **Step 9: Update the audit-script fixture if `scripts/check-kong-routes.py` uses one**

```bash
python scripts/check-kong-routes.py 2>&1 | tail -5
```
If it FAILS with a diff against a fixture, find the fixture file referenced and update it to match the new env-derived URLs. (If it has no fixture, this step is no-op.)

- [ ] **Step 10: Full suite green + audit gates**

```bash
cd bootstrapper && uv run pytest -q 2>&1 | tail -5
cd /Users/kaveh/repos/genai-vanilla && python scripts/check-kong-routes.py 2>&1 | tail -3
```

- [ ] **Step 11: Commit**

```bash
git add bootstrapper/utils/kong_config_generator.py bootstrapper/tests/test_kong_alias_routes.py scripts/check-kong-routes.py
git commit -m "$(cat <<'EOF'
kong: localhost routes derive URL from LOCALHOST_PORT env vars

Centralizes the 10 localhost-mode upstream URLs through a single
_localhost_url(port_var, default) helper. Each route now reads the
matching <SVC>_LOCALHOST_PORT env var directly, eliminating the
hardcoded-port fallbacks and the legacy <SVC>_LOCALHOST_URL reads
across services that had them.

Locks in the symmetry rule from feedback_localhost_url_override_symmetry
in memory — Kong and the in-container client now look at the same
PORT var, so a wizard-changed value reaches both consumers atomically.
EOF
)"
```

### Task 9: `state_builder.resolve_port` reads PORT var directly

**Files:**
- Modify: `bootstrapper/ui/state_builder.py:66-86` (`resolve_port` function)
- Test: add a test to `bootstrapper/tests/test_state_builder.py` (or create if absent)

- [ ] **Step 1: Check if a test file already exists**

```bash
ls bootstrapper/tests/test_state_builder*.py 2>&1
```
If absent, create `bootstrapper/tests/test_state_builder.py`.

- [ ] **Step 2: Write a failing test**

In `bootstrapper/tests/test_state_builder.py` (create the file if it doesn't exist):

```python
"""Unit tests for ui.state_builder.resolve_port — focuses on the
localhost path which now reads PORT vars directly instead of regex-
extracting from a URL var (the URL vars are gone)."""

from __future__ import annotations

import pytest

from ui.state_builder import resolve_port


@pytest.mark.parametrize("display_name,source,port_env_var,port_value", [
    ("ComfyUI", "localhost", "COMFYUI_LOCALHOST_PORT", "9000"),
    ("Docling", "docling-localhost", "DOCLING_LOCALHOST_PORT", "63099"),
    ("LLM Engine", "ollama-localhost", "OLLAMA_LOCALHOST_PORT", "11500"),
])
def test_resolve_port_for_localhost_reads_port_var(
    display_name, source, port_env_var, port_value
):
    """For a localhost-source row, the displayed port is the value of
    the row's localhost_port_var in env (formatted as ``:<port>``)."""
    env = {port_env_var: port_value}
    result = resolve_port(display_name, source=source, port_var=None, env=env)
    assert result == f":{port_value}", (
        f"resolve_port should return :{port_value}; got {result!r}"
    )


def test_resolve_port_for_localhost_returns_none_when_var_unset():
    """An empty PORT var falls back to the manifest default at compose-
    render time, but for the wizard's port display we just show
    nothing — the run isn't started yet."""
    result = resolve_port("ComfyUI", source="localhost", port_var=None, env={})
    assert result is None


def test_resolve_port_for_disabled_returns_none():
    """Disabled rows show no port (existing baseline)."""
    assert resolve_port("ComfyUI", "disabled", None, {}) is None
```

- [ ] **Step 3: Run the test — expect FAIL**

```bash
cd bootstrapper && uv run pytest tests/test_state_builder.py -v 2>&1 | tail -10
```
Expected: the first 3 parameterized cases fail (regex from URL still wired; PORT var isn't read).

- [ ] **Step 4: Update `resolve_port` to read PORT var when available**

Replace `resolve_port` in `bootstrapper/ui/state_builder.py` (lines 66-86):

```python
def resolve_port(name: str, source: str, port_var: Optional[str], env: dict) -> Optional[str]:
    """Compute the displayed port for a service given its current SOURCE, its
    port env var, and the parsed .env.

    For localhost sources, the port is the value of the row's
    ``localhost_port_var`` in env (the new override pattern). Returns
    None when the var is unset or empty — the wizard's pending row
    state then surfaces the manifest default via .env.example backfill
    before the next read.
    """
    if source == "disabled":
        return None
    if "localhost" in source:
        for r in _get_topology().rows:
            if r.display_name == name and r.localhost_port_var:
                port = env.get(r.localhost_port_var, "").strip()
                return f":{port}" if port else None
        return None
    if port_var:
        port = env.get(port_var, "")
        return f":{port}" if port else None
    return None
```

(The earlier code path used `localhost_endpoint_var` and a regex; that path is replaced entirely because the URL vars are gone for the migrated services and the new `localhost_port_var` field is the canonical source.)

- [ ] **Step 5: Run the test — expect PASS**

```bash
cd bootstrapper && uv run pytest tests/test_state_builder.py -v 2>&1 | tail -10
```
Expected: 5 PASS.

- [ ] **Step 6: Full suite green**

```bash
cd bootstrapper && uv run pytest -q 2>&1 | tail -5
```

- [ ] **Step 7: Commit**

```bash
git add bootstrapper/ui/state_builder.py bootstrapper/tests/test_state_builder.py
git commit -m "$(cat <<'EOF'
wizard: state_builder.resolve_port reads localhost_port_var directly

Drops the regex-extract-from-URL path for localhost sources (the URL
vars are gone after Tasks 6+7). The wizard's service-table port column
now reads the row's localhost_port_var in env directly. Matches the
new single-source-of-truth model where the PORT var is canonical and
the URL is derived at compose-render time.
EOF
)"
```

---

## Phase 4 — Wizard wiring

### Task 10: Attach per-option `secondary_number` to each localhost row

**Files:**
- Modify: `bootstrapper/ui/textual/integration.py` (the per-svc PromptOption list-comprehension)
- Create: `bootstrapper/tests/test_localhost_port_override.py`

This task adds the wiring that actually shows the inline textbox on each localhost source row. The widget API + manifest fields + Kong consumer + state_builder are all in place from earlier tasks; this is the user-visible "feature lands" step.

- [ ] **Step 1: Write a failing test parameterized over the 10 localhost-capable services**

Create `bootstrapper/tests/test_localhost_port_override.py`:

```python
"""End-to-end tests for the localhost-port-override wizard wiring.

For each of the 10 localhost-capable services, the source step has
the matching localhost option(s) carrying a SecondaryNumberInput with
the correct env_var, default, min/max, unit_suffix='port'."""

from __future__ import annotations

from typing import Iterable

import pytest


# (service display name, expected localhost option value, expected env var, expected default port)
LOCALHOST_WIRING = [
    ("ComfyUI",       "localhost",           "COMFYUI_LOCALHOST_PORT",         "8000"),
    ("Docling",       "docling-localhost",   "DOCLING_LOCALHOST_PORT",         "63021"),
    ("Hermes",        "localhost",           "HERMES_LOCALHOST_PORT",          "63028"),
    ("OpenClaw",      "localhost",           "OPENCLAW_LOCALHOST_PORT",        "63024"),
    ("LLM Engine",    "ollama-localhost",    "OLLAMA_LOCALHOST_PORT",          "11434"),
    ("Neo4j",         "localhost",           "NEO4J_LOCALHOST_BOLT_PORT",      "7687"),
    ("Weaviate",      "localhost",           "WEAVIATE_LOCALHOST_PORT",        "8080"),
    ("STT Provider",  "parakeet-localhost",  "PARAKEET_LOCALHOST_PORT",        "63022"),
    ("STT Provider",  "whisper-cpp-localhost","WHISPER_CPP_LOCALHOST_PORT",    "63025"),
    ("TTS Provider",  "chatterbox-localhost","CHATTERBOX_LOCALHOST_PORT",      "63027"),
]


def _wizard_steps(env_overrides: dict | None = None):
    """Build the wizard's prompt steps via _build_steps_and_rows for a
    fresh .env.example baseline + optional overrides. Returns the list
    of PromptSteps."""
    from pathlib import Path
    from core.config_parser import ConfigParser
    from ui.textual.integration import _build_steps_and_rows
    from utils.hosts_manager import HostsManager

    repo_root = Path(__file__).resolve().parent.parent.parent
    cp = ConfigParser(str(repo_root))
    cp.parse_env_file()
    if env_overrides:
        for k, v in env_overrides.items():
            cp.env_vars[k] = v
    hm = HostsManager(cp)
    steps, _rows, _info, _bp, _state, _cloud = _build_steps_and_rows(cp, hm)
    return steps


@pytest.mark.parametrize("display,option_value,env_var,default", LOCALHOST_WIRING)
def test_localhost_option_carries_secondary_number(display, option_value, env_var, default):
    """For each (service, localhost option), the matching PromptOption
    on its source step carries a SecondaryNumberInput pointing at the
    expected env_var with the expected default."""
    steps = _wizard_steps()
    source_step = next(
        (s for s in steps if s.service_name == display and "source" in s.title.lower()),
        None,
    )
    assert source_step is not None, (
        f"Could not find a source step for service {display!r}. "
        f"Available steps: {[(s.service_name, s.title) for s in steps]}"
    )
    matching_opt = next(
        (o for o in source_step.options if o.value == option_value),
        None,
    )
    assert matching_opt is not None, (
        f"Source step for {display!r} has no option with value "
        f"{option_value!r}. Options: {[o.value for o in source_step.options]}"
    )
    cfg = matching_opt.secondary_number
    assert cfg is not None, (
        f"Option {display}/{option_value} should carry a "
        f"SecondaryNumberInput but doesn't."
    )
    assert cfg.env_var == env_var
    assert cfg.unit_suffix == "port"
    assert cfg.number_min == 1024
    assert cfg.number_max == 65535
    assert str(cfg.default_value) == default


def test_non_localhost_options_carry_no_secondary_number():
    """Container / external / disabled options never carry a config —
    the inline textbox only makes sense for localhost sources."""
    steps = _wizard_steps()
    for s in steps:
        for opt in s.options:
            if opt.value and "localhost" not in opt.value:
                if opt.secondary_number is not None:
                    # Allowed exception: Ray's container-cpu / container-gpu
                    # rows carry RAY_WORKER_COUNT — that's not a port.
                    if opt.secondary_number.env_var == "RAY_WORKER_COUNT":
                        continue
                    assert False, (
                        f"Option {s.service_name}/{opt.value} carries a "
                        f"SecondaryNumberInput ({opt.secondary_number.env_var}) "
                        f"but it's not a -localhost option. "
                        f"This widget is only for localhost ports + Ray workers."
                    )
```

- [ ] **Step 2: Run the test — expect FAIL for all 10 cases**

```bash
cd bootstrapper && uv run pytest tests/test_localhost_port_override.py -v 2>&1 | tail -25
```
Expected: 10 parametrized failures (`secondary_number` is None on every localhost option — the wiring isn't in place yet).

- [ ] **Step 3: Add the localhost-port wiring helper in `integration.py`**

In `bootstrapper/ui/textual/integration.py`, near the existing Ray wiring (around line 245), add a new helper above the `for i, svc in enumerate(services_info):` loop:

```python
    # Per-service localhost-port wiring. Each entry maps a service's
    # source-step display name + the option value(s) eligible for the
    # inline-port widget → the matching env var name + the well-known
    # default. PromptOption.secondary_number is attached for any option
    # whose (service, value) appears here. Generic by construction —
    # the widget doesn't know about ports; this table is the only
    # place that does. Adding a new localhost-capable service is one
    # row here + a manifest entry per Task 7.
    LOCALHOST_PORT_WIRING: dict[tuple[str, str], tuple[str, int]] = {
        ("ComfyUI",      "localhost"):            ("COMFYUI_LOCALHOST_PORT", 8000),
        ("Docling",      "docling-localhost"):    ("DOCLING_LOCALHOST_PORT", 63021),
        ("Hermes",       "localhost"):            ("HERMES_LOCALHOST_PORT", 63028),
        ("OpenClaw",     "localhost"):            ("OPENCLAW_LOCALHOST_PORT", 63024),
        ("LLM Engine",   "ollama-localhost"):     ("OLLAMA_LOCALHOST_PORT", 11434),
        ("Neo4j",        "localhost"):            ("NEO4J_LOCALHOST_BOLT_PORT", 7687),
        ("Weaviate",     "localhost"):            ("WEAVIATE_LOCALHOST_PORT", 8080),
        ("STT Provider", "parakeet-localhost"):   ("PARAKEET_LOCALHOST_PORT", 63022),
        ("STT Provider", "whisper-cpp-localhost"):("WHISPER_CPP_LOCALHOST_PORT", 63025),
        ("TTS Provider", "chatterbox-localhost"): ("CHATTERBOX_LOCALHOST_PORT", 63027),
    }

    def _localhost_port_config(display: str, opt_value: str, env_vars: dict) -> "SecondaryNumberInput | None":
        """Build the per-option SecondaryNumberInput for a localhost row,
        or None if this (service, option) isn't in the wiring table."""
        wiring = LOCALHOST_PORT_WIRING.get((display, opt_value))
        if wiring is None:
            return None
        env_var, default_port = wiring
        raw = (env_vars.get(env_var) or str(default_port)).strip()
        try:
            current = int(raw) if raw else int(default_port)
        except ValueError:
            current = int(default_port)
        current = max(1024, min(65535, current))
        return SecondaryNumberInput(
            env_var=env_var,
            description=f"Host port for {display.lower()} in localhost mode (1024-65535).",
            default_value=current,
            number_min=1024,
            number_max=65535,
            unit_suffix="port",
        )
```

- [ ] **Step 4: Wire `_localhost_port_config` into the per-option list-comprehension**

In `bootstrapper/ui/textual/integration.py`, find the per-service PromptOption list comprehension (modified in Task 4) and extend the `secondary_number=` expression to fall back to `_localhost_port_config` when the Ray attachment doesn't fire:

```python
        opts = [
            PromptOption(
                value=opt,
                label=opt,
                hint=_option_hint(opt),
                badges=_badges_for_option(opt, recommended=(opt == svc.current_value)),
                secondary_number=(
                    # Ray's container variants → worker-count.
                    ray_secondary
                    if ray_secondary is not None
                       and opt in ("ray-container-cpu", "ray-container-gpu")
                    # Otherwise: per-localhost-row port widget (None if
                    # this option isn't a localhost variant in the wiring).
                    else _localhost_port_config(svc.display_name, opt, env_vars)
                ),
            )
            for opt in svc.options
        ]
```

- [ ] **Step 5: Run the parametrized test**

```bash
cd bootstrapper && uv run pytest tests/test_localhost_port_override.py -v 2>&1 | tail -25
```
Expected: all 10 PASS + the negative `non_localhost_options_carry_no_secondary_number` test PASS.

- [ ] **Step 6: Full suite green**

```bash
cd bootstrapper && uv run pytest -q 2>&1 | tail -5
```

- [ ] **Step 7: Manual smoke (visual confirmation)**

```bash
cd /Users/kaveh/repos/genai-vanilla && ./start.sh
```
Walk through the wizard. On each localhost-capable service's source step, confirm the inline textbox shows on the matching `*-localhost` row with the correct default port and the `port` suffix label. Hit Ctrl+C before launching to abort — this is a visual smoke only.

- [ ] **Step 8: Commit**

```bash
git add bootstrapper/ui/textual/integration.py bootstrapper/tests/test_localhost_port_override.py
git commit -m "$(cat <<'EOF'
wizard: attach inline port-override textbox to every localhost source row

Adds LOCALHOST_PORT_WIRING table mapping (service, localhost option) →
(env_var, default port) for the 10 localhost-capable services
(ComfyUI, Docling, Hermes, OpenClaw, Ollama, Neo4j, Weaviate, STT×2,
TTS). Each matching PromptOption now carries a SecondaryNumberInput
that shows up as the inline integer textbox.

The textbox defaults to the current .env value when set, else the
service's well-known default. Range is 1024-65535 (privileged-port
floor + IANA max).
EOF
)"
```

---

## Phase 5 — Migration: rewrite `.env` from URL to PORT

### Task 11: `migration_v2.py` implementation

**Files:**
- Create: `bootstrapper/services/migrations/migration_v2.py`
- Create: `bootstrapper/tests/test_migration_v2.py`

- [ ] **Step 1: Write failing tests**

Create `bootstrapper/tests/test_migration_v2.py`:

```python
"""migration_v2: rewrite <SVC>_LOCALHOST_URL → <SVC>_LOCALHOST_PORT in .env.

Triggered when BOOTSTRAPPER_PORT_LAYOUT_VERSION is < 2. For each of
the 7 legacy URL vars, extract the port via regex and append a
matching PORT entry; comment out the old URL line (don't delete) so a
mis-extraction is recoverable by hand."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.migrations.migration_v2 import (
    apply as apply_v2,
    needs_migration as needs_v2,
    stamp_version as stamp_v2,
    URL_VAR_TO_PORT_VAR,
)


LEGACY_URL_VARS = list(URL_VAR_TO_PORT_VAR.keys())


def _write_env(tmp_path: Path, content: str) -> Path:
    p = tmp_path / ".env"
    p.write_text(content, encoding="utf-8")
    return p


def test_default_port_url_rewrites_to_port_var(tmp_path):
    """A user with the default URL like COMFYUI_LOCALHOST_URL=http://...:8000
    gets COMFYUI_LOCALHOST_PORT=8000 appended; old URL is commented out."""
    p = _write_env(tmp_path,
        "COMFYUI_LOCALHOST_URL=http://host.docker.internal:8000\n"
        "OTHER=unrelated\n"
    )
    apply_v2(p)
    out = p.read_text()
    assert "COMFYUI_LOCALHOST_PORT=8000" in out
    assert "# COMFYUI_LOCALHOST_URL=" in out, (
        f"old URL line should be commented out, not deleted. .env:\n{out}"
    )


def test_custom_port_preserved(tmp_path):
    """User's customized port survives end-to-end."""
    p = _write_env(tmp_path,
        "DOCLING_LOCALHOST_URL=http://host.docker.internal:9876\n"
    )
    apply_v2(p)
    assert "DOCLING_LOCALHOST_PORT=9876" in p.read_text()


def test_custom_hostname_dropped_with_warning(tmp_path, capsys):
    """Non-default hostname is dropped; the port is still extracted;
    a warning is printed so the user sees it."""
    p = _write_env(tmp_path,
        "OPENCLAW_LOCALHOST_URL=http://192.168.1.10:9000\n"
    )
    apply_v2(p)
    out = p.read_text()
    assert "OPENCLAW_LOCALHOST_PORT=9000" in out
    captured = capsys.readouterr()
    assert "OPENCLAW_LOCALHOST_URL" in (captured.out + captured.err)
    assert "192.168.1.10" in (captured.out + captured.err)


def test_empty_url_no_port_emitted(tmp_path):
    """Empty URL value: comment the line, do NOT emit a PORT entry —
    service will use the manifest default at compose-render time."""
    p = _write_env(tmp_path, "HERMES_LOCALHOST_URL=\n")
    apply_v2(p)
    out = p.read_text()
    assert "HERMES_LOCALHOST_PORT" not in out
    assert "# HERMES_LOCALHOST_URL=" in out


def test_url_without_port_skipped(tmp_path):
    """A malformed URL with no :port: skip cleanly, comment out, warn."""
    p = _write_env(tmp_path,
        "HERMES_LOCALHOST_URL=http://host.docker.internal\n"
    )
    apply_v2(p)
    out = p.read_text()
    assert "HERMES_LOCALHOST_PORT" not in out
    assert "# HERMES_LOCALHOST_URL=" in out


def test_url_var_absent_no_change(tmp_path):
    """When the URL var is missing entirely, no PORT var added; .env
    rest unchanged."""
    p = _write_env(tmp_path, "OTHER=unrelated\n")
    before = p.read_text()
    apply_v2(p)
    after = p.read_text()
    # Allow trailing newline normalization but no semantic content change.
    assert "LOCALHOST_PORT" not in after
    assert "OTHER=unrelated" in after


def test_idempotent_when_already_migrated(tmp_path):
    """Re-running on a .env that already has both URL (commented) and
    PORT is a no-op."""
    p = _write_env(tmp_path,
        "# COMFYUI_LOCALHOST_URL=http://host.docker.internal:8000\n"
        "COMFYUI_LOCALHOST_PORT=8000\n"
    )
    before = p.read_text()
    apply_v2(p)
    assert p.read_text() == before


def test_needs_migration_false_when_sentinel_at_2(tmp_path):
    p = _write_env(tmp_path, "BOOTSTRAPPER_PORT_LAYOUT_VERSION=2\n")
    assert needs_v2(p) is False


def test_needs_migration_true_when_sentinel_at_1(tmp_path):
    p = _write_env(tmp_path, "BOOTSTRAPPER_PORT_LAYOUT_VERSION=1\n")
    assert needs_v2(p) is True


def test_needs_migration_true_when_sentinel_absent(tmp_path):
    p = _write_env(tmp_path, "FOO=bar\n")
    assert needs_v2(p) is True


def test_stamp_version_writes_2(tmp_path):
    p = _write_env(tmp_path, "BOOTSTRAPPER_PORT_LAYOUT_VERSION=1\n")
    stamp_v2(p)
    assert "BOOTSTRAPPER_PORT_LAYOUT_VERSION=2" in p.read_text()
```

- [ ] **Step 2: Run the test — expect ImportError (module doesn't exist)**

```bash
cd bootstrapper && uv run pytest tests/test_migration_v2.py -v 2>&1 | tail -10
```
Expected: `ModuleNotFoundError: No module named 'services.migrations.migration_v2'`.

- [ ] **Step 3: Implement `migration_v2.py`**

Create `bootstrapper/services/migrations/migration_v2.py`:

```python
"""URL → PORT .env schema migration (v1 → v2 of BOOTSTRAPPER_PORT_LAYOUT_VERSION).

Replaces 7 monolithic <SVC>_LOCALHOST_URL env vars with corresponding
integer-port <SVC>_LOCALHOST_PORT vars. The full URL is reconstructed
at compose-render time and Kong-config-generation time as
``http://host.docker.internal:${<SVC>_LOCALHOST_PORT:-<default>}``.

This module is the FROZEN snapshot of the v1→v2 migration at
2026-05-25. Do NOT edit when the schema changes again — author a
sibling migration_v3.py instead.

Triggered from start.py::run_port_migration when needs_migration()
returns True. After successful apply, call stamp_version() to update
the sentinel to 2.
"""

from __future__ import annotations

import re
from pathlib import Path


# Maps each legacy URL env var to its replacement PORT env var.
URL_VAR_TO_PORT_VAR: dict[str, str] = {
    "COMFYUI_LOCALHOST_URL":     "COMFYUI_LOCALHOST_PORT",
    "DOCLING_LOCALHOST_URL":     "DOCLING_LOCALHOST_PORT",
    "HERMES_LOCALHOST_URL":      "HERMES_LOCALHOST_PORT",
    "OPENCLAW_LOCALHOST_URL":    "OPENCLAW_LOCALHOST_PORT",
    "PARAKEET_LOCALHOST_URL":    "PARAKEET_LOCALHOST_PORT",
    "WHISPER_CPP_LOCALHOST_URL": "WHISPER_CPP_LOCALHOST_PORT",
    "CHATTERBOX_LOCALHOST_URL":  "CHATTERBOX_LOCALHOST_PORT",
}


# Tolerant sentinel matcher (mirrors migration_v1 conventions).
_SENTINEL_RE = re.compile(
    r"""^\s*BOOTSTRAPPER_PORT_LAYOUT_VERSION\s*=\s*
        (["']?)(\d+)\1
        \s*(?:\#.*)?\s*$""",
    re.VERBOSE,
)

# URL line matcher: captures (var_name, hostname, port).
# Tolerates http:// or https://, optional trailing path.
_URL_LINE_RE = re.compile(
    r"""^(?P<key>[A-Z_]+_LOCALHOST_URL)\s*=\s*
        (?:https?://(?P<host>[^:/\s]+)(?::(?P<port>\d+))?(?P<path>[^\s#]*))?
        \s*(?P<tail>(?:\#.*)?)\s*$""",
    re.VERBOSE,
)


def needs_migration(env_path: Path) -> bool:
    """True iff .env's BOOTSTRAPPER_PORT_LAYOUT_VERSION < 2 (or absent)."""
    if not env_path.is_file():
        return False  # fresh install — defaults already include PORT vars
    for line in env_path.read_text().splitlines():
        m = _SENTINEL_RE.match(line)
        if m:
            try:
                return int(m.group(2)) < 2
            except ValueError:
                return True
    return True


def apply(env_path: Path) -> None:
    """Rewrite .env in place. Idempotent on re-run.

    For each legacy URL var present:
      • Extract the port via regex.
      • Append <SVC>_LOCALHOST_PORT=<port> if not already present.
      • Comment out the old URL line.
      • If the hostname isn't host.docker.internal, print a warning.
      • If the URL has no port (malformed/empty), skip the PORT line.
    """
    if not env_path.is_file():
        return

    lines = env_path.read_text().splitlines(keepends=True)
    existing_keys: set[str] = set()
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        existing_keys.add(key)

    out: list[str] = []
    appended: list[str] = []
    for line in lines:
        # Match the line stripped of its newline for regex; keep newline
        # style for write-back.
        if line.endswith("\r\n"):
            eol = "\r\n"
            body = line[:-2]
        elif line.endswith("\n"):
            eol = "\n"
            body = line[:-1]
        else:
            eol = ""
            body = line
        m = _URL_LINE_RE.match(body.strip())
        if not m or m.group("key") not in URL_VAR_TO_PORT_VAR:
            out.append(line)
            continue
        url_var = m.group("key")
        host = m.group("host") or ""
        port = m.group("port") or ""
        port_var = URL_VAR_TO_PORT_VAR[url_var]

        # Warn on non-default host.
        if host and host != "host.docker.internal":
            print(
                f"[migration_v2] {url_var} had hostname {host!r}; "
                f"dropping it (PORT-only override). Set the URL var by "
                f"hand-edit if you need a custom hostname.",
                flush=True,
            )

        # Comment out the old URL line.
        out.append(f"# {body}  # migrated to {port_var} by migration_v2{eol}")

        # Emit the PORT line if extractable and not already present.
        if port and port_var not in existing_keys:
            appended.append(f"{port_var}={port}{eol or chr(10)}")
            existing_keys.add(port_var)
        elif not port:
            print(
                f"[migration_v2] {url_var} had no extractable :port; "
                f"skipping PORT emission. Service will use manifest "
                f"default at compose-render time.",
                flush=True,
            )

    if appended:
        # Ensure a separating newline before appending.
        if out and not out[-1].endswith(("\n", "\r\n")):
            out[-1] += "\n"
        out.extend(appended)

    env_path.write_text("".join(out))


def stamp_version(env_path: Path, version: int = 2) -> None:
    """Append or update BOOTSTRAPPER_PORT_LAYOUT_VERSION in .env to 2."""
    if not env_path.is_file():
        return
    lines = env_path.read_text().splitlines(keepends=True)
    found = False
    for i, line in enumerate(lines):
        if _SENTINEL_RE.match(line):
            lines[i] = f"BOOTSTRAPPER_PORT_LAYOUT_VERSION={version}\n"
            found = True
            break
    if not found:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(f"BOOTSTRAPPER_PORT_LAYOUT_VERSION={version}\n")
    env_path.write_text("".join(lines))
```

- [ ] **Step 4: Run the test — expect PASS**

```bash
cd bootstrapper && uv run pytest tests/test_migration_v2.py -v 2>&1 | tail -20
```
Expected: 12 tests pass.

- [ ] **Step 5: Commit**

```bash
git add bootstrapper/services/migrations/migration_v2.py bootstrapper/tests/test_migration_v2.py
git commit -m "$(cat <<'EOF'
services: migration_v2 rewrites <SVC>_LOCALHOST_URL to <SVC>_LOCALHOST_PORT in .env

Frozen snapshot of the v1→v2 migration of BOOTSTRAPPER_PORT_LAYOUT_VERSION.
For each of the 7 legacy URL vars (Comfyui, Docling, Hermes, Openclaw,
Parakeet, Whisper-cpp, Chatterbox), extracts the port via regex and
appends a matching PORT entry, comment-outs the old URL line. Custom
hostnames are dropped with a printed warning so the user sees the
behaviour change rather than silently losing their config.

Migration is idempotent — re-running on a .env with both URL (commented)
and PORT entries is a no-op.
EOF
)"
```

### Task 12: Wire `migration_v2` into `start.py` + sentinel bump

**Files:**
- Modify: `bootstrapper/start.py:17-21` (import block)
- Modify: `bootstrapper/start.py:687-770` (`run_port_migration` method)

- [ ] **Step 1: Update the imports at the top of `start.py`**

Replace lines 17-21:

```python
from services.migrations.migration_v1 import (
    apply as _apply_v1,
    needs_migration as _needs_v1,
    stamp_version as _stamp_v1,
)
from services.migrations.migration_v2 import (
    apply as _apply_v2,
    needs_migration as _needs_v2,
    stamp_version as _stamp_v2,
)
```

- [ ] **Step 2: Read the current `run_port_migration` body**

```bash
grep -n "def run_port_migration\|_apply_v1\|_needs_v1\|_stamp_v1" bootstrapper/start.py | head
```

- [ ] **Step 3: Extend `run_port_migration` to also run v1→v2**

Inside `bootstrapper/start.py::run_port_migration`, after the existing v1 application (find the end of the `_apply_v1(...)` block + `_stamp_v1(...)` call), insert:

```python
        # v1 → v2: URL → PORT schema rewrite. Idempotent on re-run.
        # Runs after v1 so the sentinel transitions cleanly 0/none → 1 → 2
        # rather than skipping intermediate state on a v0 .env (the
        # combined behavior is what we want for users on older checkouts
        # who haven't run any bootstrapper since the topology refactor).
        if _needs_v2(env_path):
            if no_port_migrate:
                self.banner.console.print(
                    "[dim]Skipping LOCALHOST schema migration "
                    "(--no-port-migrate); will re-prompt next run.[/dim]"
                )
            else:
                self.banner.show_status_message(
                    "Migrating .env to LOCALHOST_PORT schema (v2) ...",
                    "info",
                )
                _apply_v2(env_path)
                _stamp_v2(env_path)
                self.banner.show_status_message(
                    "LOCALHOST schema migration complete (v2). "
                    "Old <SVC>_LOCALHOST_URL lines are commented out for "
                    "audit; new <SVC>_LOCALHOST_PORT lines drive both "
                    "compose runtime and Kong routes.",
                    "success",
                )
```

- [ ] **Step 4: Manual smoke + full suite green**

```bash
cd bootstrapper && uv run pytest -q 2>&1 | tail -5
```

For manual smoke, simulate a v1-state .env:

```bash
cd /Users/kaveh/repos/genai-vanilla && cp .env .env.smoke-backup \
  && sed -i.bak 's/BOOTSTRAPPER_PORT_LAYOUT_VERSION=2/BOOTSTRAPPER_PORT_LAYOUT_VERSION=1/' .env \
  && echo "COMFYUI_LOCALHOST_URL=http://host.docker.internal:9999" >> .env \
  && ./start.sh --no-tui 2>&1 | head -30
```
Expected: see "Migrating .env to LOCALHOST_PORT schema (v2)" + "complete" messages; `.env` now has `COMFYUI_LOCALHOST_PORT=9999` + commented-out URL.

After verifying, restore: `mv .env.smoke-backup .env`.

- [ ] **Step 5: Commit**

```bash
git add bootstrapper/start.py
git commit -m "$(cat <<'EOF'
bootstrapper: run migration_v2 after v1 in run_port_migration

Chains the schema migration onto the existing port-layout migration so
a single `./start.sh` invocation on a stale .env upgrades through both
versions cleanly. --no-port-migrate skips v2 the same way it skips v1;
the sentinel stays at v1 in that case and re-prompts next run.

User-facing banner lines call out what the migration touched (commented
URL lines, new PORT lines) so the .env diff isn't a mystery.
EOF
)"
```

---

## Phase 6 — Final UX + verification

### Task 13: Port-collision warning in the pre-launch summary

**Files:**
- Modify: pre-launch summary builder (find via grep — likely `bootstrapper/ui/state_builder.py` or `bootstrapper/start.py::build_pre_launch_summary_table`)
- Create: `bootstrapper/tests/test_port_collision_warning.py`

The warning surfaces when a user-typed localhost port also appears as a container-mode port elsewhere in the stack — alerting them that compose-up may fail to bind.

- [ ] **Step 1: Locate the pre-launch summary builder**

```bash
grep -rn "build_pre_launch_summary_table\|pre_launch_summary\|pre-launch summary" bootstrapper/ 2>&1 | head -10
```
Note the exact file:line where the summary table is built. The implementer fills in this path at task time.

- [ ] **Step 2: Write a failing test**

Create `bootstrapper/tests/test_port_collision_warning.py` — this file uses the function name from Step 1; if it's named differently, rename `_build_summary` accordingly:

```python
"""When a user-typed localhost port collides with another row's host
port (e.g. typing 64000 for ollama-localhost when Kong is also at
64000), the pre-launch summary table flags it with a warning line.
Doesn't block launch — just informs."""

from __future__ import annotations

import pytest


def test_port_collision_flagged_in_summary(tmp_path, monkeypatch):
    # TODO: replace `build_pre_launch_summary_table` with the actual
    # function name from Step 1.
    from <module> import build_pre_launch_summary_table  # type: ignore

    # Build a fake services state with a deliberate collision: ollama
    # localhost port == kong http port.
    services_state = [
        {"name": "Kong", "source": "container", "port": ":64000"},
        {"name": "LLM Engine", "source": "ollama-localhost", "port": ":64000"},
    ]
    rendered = build_pre_launch_summary_table(services_state)
    text = str(rendered)
    assert ("collision" in text.lower()) or ("⚠" in text), (
        f"Expected a collision warning in the rendered summary; got:\n{text}"
    )
    assert "64000" in text
    assert "ollama" in text.lower() or "LLM Engine" in text
    assert "kong" in text.lower()


def test_no_collision_no_warning():
    from <module> import build_pre_launch_summary_table  # type: ignore
    services_state = [
        {"name": "Kong", "source": "container", "port": ":64000"},
        {"name": "LLM Engine", "source": "ollama-localhost", "port": ":11434"},
    ]
    rendered = build_pre_launch_summary_table(services_state)
    text = str(rendered)
    assert "collision" not in text.lower()
    assert "⚠" not in text
```

- [ ] **Step 3: Run the test — expect FAIL (warning not implemented)**

```bash
cd bootstrapper && uv run pytest tests/test_port_collision_warning.py -v 2>&1 | tail -10
```

- [ ] **Step 4: Implement the warning**

In the pre-launch summary builder identified in Step 1, after the rows table is constructed, add a collision-detection pass:

```python
def _detect_port_collisions(rows: list) -> list[str]:
    """Return human-readable warning strings, one per colliding port.

    A collision is two or more rows whose 'port' value (the ':<num>'
    suffix or just the number) is equal AND nonempty. Empty / None /
    disabled rows don't participate.
    """
    by_port: dict[str, list[str]] = {}
    for r in rows:
        port = (getattr(r, "port", None) or r.get("port") if isinstance(r, dict) else "") or ""
        port = port.lstrip(":").strip()
        if not port:
            continue
        name = (getattr(r, "name", None) or r.get("name") if isinstance(r, dict) else "")
        by_port.setdefault(port, []).append(name)
    warnings: list[str] = []
    for port, names in by_port.items():
        if len(names) >= 2:
            warnings.append(
                f"⚠  port {port} used by {' + '.join(names)} — "
                f"compose-up may fail to bind."
            )
    return warnings
```

Then in the summary builder, append the warnings (one per line, styled in yellow if Rich is available):

```python
    warnings = _detect_port_collisions(rows)
    if warnings:
        for w in warnings:
            table.add_row(w)  # or whatever the existing API is
```

(Exact rendering will depend on what the existing builder returns — adapt the append to match.)

- [ ] **Step 5: Run the test — expect PASS**

- [ ] **Step 6: Full suite + manual smoke**

```bash
cd bootstrapper && uv run pytest -q 2>&1 | tail -5
```

- [ ] **Step 7: Commit**

```bash
git add <changed files> bootstrapper/tests/test_port_collision_warning.py
git commit -m "$(cat <<'EOF'
wizard: pre-launch summary flags port collisions (warn-don't-block)

When two rows resolve to the same host port (e.g. user picks
ollama-localhost on 64000 while Kong is also at 64000), the
pre-launch summary table shows a warning line. Launch still proceeds —
user has agency to ack and continue, or go back and pick another port.

Compose-up would otherwise fail with an opaque "address already in
use" error from Docker.
EOF
)"
```

### Task 14: Full-suite green + docs drift + manual smoke

**Files:** (none — verification only)

- [ ] **Step 1: Run the full pytest suite from a clean state**

```bash
cd bootstrapper && uv run pytest -q 2>&1 | tail -5
```
Expected: `XXX passed`; XXX is baseline 342 + new tests added across phases (Tasks 1, 5, 6/7 add ~15-20 cases; Task 8 adds ~10 parametrized cases; Task 9 adds ~5; Task 10 adds ~11; Task 11 adds ~12; Task 13 adds ~2). Total ~395-410 passed.

- [ ] **Step 2: Run every audit gate**

```bash
cd /Users/kaveh/repos/genai-vanilla && PYTHONPATH=bootstrapper python -m bootstrapper.docs.regen --all --check
python scripts/check_doc_links.py
python scripts/check-compose-source-deps.py
python scripts/check-kong-routes.py
```
Expected: each exits 0 with `PASS` / no-drift output.

- [ ] **Step 3: End-to-end manual smoke**

```bash
cd /Users/kaveh/repos/genai-vanilla
./start.sh --base-port 64000
```
Walk through the wizard and verify:
- For each of: ComfyUI, Docling, Hermes, OpenClaw, LLM Engine, Neo4j, Weaviate, STT, TTS — the localhost source row shows an inline textbox with the correct default port and the `port` suffix.
- Type a non-default value (e.g. 9999) for one service's localhost port.
- Complete the wizard and let the stack come up.
- Verify the chosen port lands in `.env` (`<SVC>_LOCALHOST_PORT=9999`).
- Verify Kong's localhost route for the affected service targets `host.docker.internal:9999` (`docker exec genai-kong-api-gateway cat /home/kong/kong.yml | grep -A2 <svc>.localhost`).
- Stop the stack: `./stop.sh`.

- [ ] **Step 4: Push the branch + open PR**

```bash
cd /Users/kaveh/repos/genai-vanilla/.claude/worktrees/localhost-port-override
git push -u origin worktree-localhost-port-override
gh pr create --base main --head worktree-localhost-port-override \
  --title "Localhost port override on the inline wizard textbox" \
  --body "$(cat <<'EOF'
Implements `docs/specs/2026-05-25-localhost-port-override-design.md`.

## Summary
- Generalizes the `SecondaryNumberInput` widget API from step-level to per-option config; Ray migrates retroactively.
- 10 localhost-capable services get inline port-override textboxes (Comfyui, Docling, Hermes, OpenClaw, Ollama, Neo4j, Weaviate, STT×2, TTS).
- 7 services refactored from `<SVC>_LOCALHOST_URL` env vars to `<SVC>_LOCALHOST_PORT`; 3 new services (ollama, neo4j, weaviate) gain new `<SVC>_LOCALHOST_PORT` vars.
- `migration_v2` rewrites stale `.env` files automatically (`BOOTSTRAPPER_PORT_LAYOUT_VERSION` 1→2).
- Pre-launch summary surfaces port collisions as warnings (warn-don't-block).

## Test plan
- [x] `uv run pytest -q` — all green (~395-410 tests pass).
- [x] `PYTHONPATH=bootstrapper python -m bootstrapper.docs.regen --all --check` — no drift.
- [x] `python scripts/check-kong-routes.py` — PASS.
- [x] Manual: change ollama-localhost port to 9999, confirm `.env` write, Kong route update, runtime endpoint match.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
Expected: PR URL printed. Wait for the 3 required CI checks to go green, then `gh pr merge --squash --delete-branch`.

- [ ] **Step 5: Sync local main + clean up the worktree**

```bash
cd /Users/kaveh/repos/genai-vanilla
git fetch origin
git reset --hard origin/main
git worktree remove .claude/worktrees/localhost-port-override
git branch -D worktree-localhost-port-override
```

---

## Plan self-review (done before sharing this doc)

**Spec coverage:** every section of the spec maps to at least one task — §3 widget API → Tasks 1-4; §4 manifests → Tasks 5-7; §5 Kong → Task 8; §6 state_builder → Task 9; §7 wizard wiring → Task 10; §8 migration → Tasks 11-12; §9 testing strategy is realized as the failing-first tests in each task; §10 pre-launch UX → Task 13; §11 verification → Task 14.

**Placeholder scan:** Task 13 contains `<module>` placeholders pending Step 1 grep — that's a known structural unknown until the implementer finds the actual function name. All other tasks contain real file paths, real code, real commands.

**Type consistency:** `SecondaryNumberInput` shape is identical across every task that references it (env_var, description, default_value, number_min, number_max, unit_suffix — no other fields). `PromptOption.secondary_number` is referenced by the same name in Tasks 1, 2, 3, 4, 10. `localhost_port_var` is referenced by the same name in Tasks 5, 6, 7, 9, 10. `_localhost_url(port_var, default)` signature is the same wherever invoked in Task 8.
