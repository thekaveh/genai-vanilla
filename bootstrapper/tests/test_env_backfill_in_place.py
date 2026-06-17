"""`.env` backfill must insert new keys IN PLACE at their matching
section in the user's `.env`, not dump them in an `(unsectioned)`
trailer at the bottom.

Two bugs were observed live on PR #35's first user launch:

1. **Section-banner regex matched only `=` bars**, but
   `env_assembler.py` actually emits `─` (U+2500) box-drawing bars.
   Every key in `.env.example` was thus invisible to the parser and
   fell into `(unsectioned)`. The user saw `AIRFLOW_DAG_PROCESSOR_SCALE`
   and `SPARK_CONNECT_SCALE` appended at the bottom with no section
   attribution — exactly the "scattered" symptom they reported.

2. **The writer always appended to the bottom**, even for groups whose
   section already existed in the user's `.env`. The docstring promised
   "the result reads as if the new entries had been there from the
   start" — but the code was append-only.

`_splice_backfill_in_place()` is the new helper. Tests cover:
- The exact PR #35 incident (Spark + Airflow scale vars find their
  existing sections)
- Trailer fallback when a section doesn't exist in the user's `.env`
- Multiple groups across multiple sections
- Context comments preserved
- Idempotency
- Backwards-compat with `=` bars
"""
from __future__ import annotations

from start import AtlasStarter


# Use the static method directly — no Starter setup needed.
_splice = AtlasStarter._splice_backfill_in_place


def _build_groups(section_to_entries):
    """Convenience: dict {section: [(key, value)]} → groups shape."""
    return [
        (section, [([], k, v) for k, v in entries])
        for section, entries in section_to_entries.items()
    ]


def test_pr35_incident_spark_and_airflow_scale_vars_land_in_their_sections():
    """The exact reported scenario: user .env has the Spark + Airflow
    sections from before PR #35 added SPARK_CONNECT_SCALE and
    AIRFLOW_DAG_PROCESSOR_SCALE. After backfill, those vars must sit
    at the end of THEIR sections, not at the bottom of the file."""
    env = (
        "# ───────────\n"
        "# agents: Apache Airflow (DAG orchestrator)  (services/airflow/service.yml)\n"
        "# ───────────\n"
        "AIRFLOW_SOURCE=container\n"
        "AIRFLOW_IMAGE=apache/airflow:3.2.2\n"
        "# (auto-managed)\n"
        "AIRFLOW_SCHEDULER_SCALE=1\n"
        "\n"
        "# ───────────\n"
        "# data: Apache Spark (standalone cluster)  (services/spark/service.yml)\n"
        "# ───────────\n"
        "SPARK_SOURCE=container\n"
        "# (auto-managed)\n"
        "SPARK_MASTER_SCALE=1\n"
    )
    groups = _build_groups({
        "data: Apache Spark (standalone cluster)  (services/spark/service.yml)": [
            ("SPARK_CONNECT_SCALE", "1"),
        ],
        "agents: Apache Airflow (DAG orchestrator)  (services/airflow/service.yml)": [
            ("AIRFLOW_DAG_PROCESSOR_SCALE", "1"),
        ],
    })
    new_env, total, in_place, trailer = _splice(env, groups)
    assert total == 2
    assert sorted(in_place) == sorted([
        "data: Apache Spark (standalone cluster)  (services/spark/service.yml)",
        "agents: Apache Airflow (DAG orchestrator)  (services/airflow/service.yml)",
    ])
    assert trailer == []
    # Both new keys must appear within their respective sections, not at EOF.
    spark_section_end = new_env.index("# data: Apache Spark")
    airflow_section_end = new_env.index("# agents: Apache Airflow")
    spark_pos = new_env.index("SPARK_CONNECT_SCALE")
    airflow_pos = new_env.index("AIRFLOW_DAG_PROCESSOR_SCALE")
    # The new keys must come AFTER their section's banner...
    assert spark_pos > spark_section_end
    assert airflow_pos > airflow_section_end
    # ...and the new var must come AFTER the existing var in its section.
    assert spark_pos > new_env.index("SPARK_MASTER_SCALE=1")
    assert airflow_pos > new_env.index("AIRFLOW_SCHEDULER_SCALE=1")
    # No "Auto-backfilled" trailer because both sections existed.
    assert "Auto-backfilled" not in new_env


def test_section_not_in_env_falls_to_trailer():
    """Brand-new service families (whose section doesn't exist in the
    user's older .env) land in an Auto-backfilled trailer."""
    env = (
        "# ───\n"
        "# infra: Kong (API gateway)  (services/kong/service.yml)\n"
        "# ───\n"
        "KONG_HTTP_PORT=64000\n"
    )
    groups = _build_groups({
        "data: Brand New Service  (services/brand-new/service.yml)": [
            ("BRAND_NEW_PORT", "65000"),
        ],
    })
    new_env, total, in_place, trailer = _splice(env, groups)
    assert total == 1
    assert in_place == []
    assert trailer == ["data: Brand New Service  (services/brand-new/service.yml)"]
    assert "Auto-backfilled from .env.example" in new_env
    assert "BRAND_NEW_PORT=65000" in new_env


def test_in_place_and_trailer_mix():
    """Some groups slot in-place, others fall to trailer. Both happen
    in one pass; the trailer carries only the orphan groups."""
    env = (
        "# ───\n"
        "# data: Existing  (services/existing/service.yml)\n"
        "# ───\n"
        "EXISTING_KEY=old\n"
    )
    groups = _build_groups({
        "data: Existing  (services/existing/service.yml)": [("EXISTING_NEW", "1")],
        "apps: Brand New  (services/brand-new/service.yml)": [("BRAND_NEW", "2")],
    })
    new_env, total, in_place, trailer = _splice(env, groups)
    assert total == 2
    assert in_place == ["data: Existing  (services/existing/service.yml)"]
    assert trailer == ["apps: Brand New  (services/brand-new/service.yml)"]
    # Existing-section new var is spliced before the next section / EOF.
    existing_pos = new_env.index("EXISTING_NEW=1")
    trailer_pos = new_env.index("Auto-backfilled from .env.example")
    assert existing_pos < trailer_pos


def test_context_comments_preserved_on_in_place_splice():
    """The variable's preceding comment block must survive the splice."""
    env = (
        "# ───\n"
        "# data: Spark  (services/spark/service.yml)\n"
        "# ───\n"
        "SPARK_SOURCE=container\n"
    )
    groups = [
        ("data: Spark  (services/spark/service.yml)", [
            (["# Resolved by the bootstrapper from SPARK_SOURCE.", "# (auto-managed)"],
             "SPARK_CONNECT_SCALE", "1"),
        ]),
    ]
    new_env, total, in_place, _ = _splice(env, groups)
    assert total == 1 and in_place
    assert "# Resolved by the bootstrapper from SPARK_SOURCE." in new_env
    assert "# (auto-managed)" in new_env
    # And ordered immediately before the value line.
    comment_pos = new_env.index("# Resolved by the bootstrapper from SPARK_SOURCE.")
    var_pos = new_env.index("SPARK_CONNECT_SCALE=1")
    assert comment_pos < var_pos


def test_legacy_equals_bars_tolerated_for_backcompat():
    """Hand-edited .env files might use `=` bars instead of `─`. Both
    forms must be recognized as banners."""
    env = (
        "# =====\n"
        "# data: Spark  (services/spark/service.yml)\n"
        "# =====\n"
        "SPARK_SOURCE=container\n"
    )
    groups = _build_groups({
        "data: Spark  (services/spark/service.yml)": [("SPARK_CONNECT_SCALE", "1")],
    })
    new_env, total, in_place, _ = _splice(env, groups)
    assert total == 1
    assert in_place == ["data: Spark  (services/spark/service.yml)"]


def test_empty_groups_no_op():
    """No groups → input returned untouched, no counters advance."""
    env = "FOO=bar\n"
    new_env, total, in_place, trailer = _splice(env, [])
    assert new_env == env
    assert total == 0 and in_place == [] and trailer == []


def test_splice_lands_after_existing_vars_at_section_tail():
    """The splice must be at the END of the section's body — not after
    the section banner — so the existing key ordering is preserved."""
    env = (
        "# ───\n"
        "# data: Spark  (services/spark/service.yml)\n"
        "# ───\n"
        "SPARK_SOURCE=container\n"
        "SPARK_IMAGE=apache/spark:4.1.2\n"
        "SPARK_MASTER_SCALE=1\n"
        "\n"
        "# ───\n"
        "# llm: LiteLLM  (services/litellm/service.yml)\n"
        "# ───\n"
        "LITELLM_PORT=64030\n"
    )
    groups = _build_groups({
        "data: Spark  (services/spark/service.yml)": [("SPARK_CONNECT_SCALE", "1")],
    })
    new_env, _, _, _ = _splice(env, groups)
    # Order must be: existing 3 spark vars, then new var, then llm section.
    lines = [ln for ln in new_env.splitlines() if ln and not ln.startswith("#")]
    spark_master_idx = lines.index("SPARK_MASTER_SCALE=1")
    spark_connect_idx = lines.index("SPARK_CONNECT_SCALE=1")
    litellm_idx = lines.index("LITELLM_PORT=64030")
    assert spark_master_idx < spark_connect_idx < litellm_idx
