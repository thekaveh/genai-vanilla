"""Verify that init-airflow.sh gates connection seeding on every sibling source."""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "services" / "airflow" / "init" / "scripts" / "init-airflow.sh"


def test_init_script_exists_and_is_executable():
    assert SCRIPT.exists(), "init-airflow.sh missing"
    assert (SCRIPT.stat().st_mode & 0o111), "init-airflow.sh not executable"


def test_init_script_gates_each_sibling_connection():
    """Gating convention is `= "container"` (NOT `!= "disabled"`).

    The `!= "disabled"` form silently includes the `localhost` source
    variant for services that support it (weaviate / neo4j) and would seed
    a Connection pointing at in-Compose DNS that doesn't resolve in
    host-mode.

    Also locks the canonical var name `NEO4J_GRAPH_DB_SOURCE` (NOT
    `NEO4J_SOURCE` — the latter does not exist in .env.example; a pre-2026-06
    bug silently dropped the neo4j_default connection because the script
    read an undefined var).
    """
    body = SCRIPT.read_text(encoding="utf-8")
    assert 'if [ "${SPARK_SOURCE}" = "container" ]' in body
    assert 'if [ "${MINIO_SOURCE}" = "container" ]' in body
    assert 'if [ "${WEAVIATE_SOURCE}" = "container" ]' in body
    assert 'if [ "${NEO4J_GRAPH_DB_SOURCE}" = "container" ]' in body
    # No conditional should reference the bogus NEO4J_SOURCE name.
    # (the canonical name appears in the prose comment that documents the
    # fix; we only forbid it as a shell variable expansion.)
    assert '${NEO4J_SOURCE}' not in body, (
        "init-airflow.sh should expand canonical ${NEO4J_GRAPH_DB_SOURCE}, "
        "not ${NEO4J_SOURCE} (which is silently undefined)."
    )


def test_init_script_seeds_always_on_connections_unconditionally():
    body = SCRIPT.read_text(encoding="utf-8")
    # Required deps and always-on services seed without gates.
    assert 'add_conn postgres_supabase' in body
    assert 'add_conn litellm_default' in body
    assert 'add_conn redis_default' in body
    # LiteLLM and Redis must NOT sit inside an `if`-guard — search for
    # the conditional patterns to be sure.
    assert 'if [ "${LITELLM_SOURCE}"' not in body
    assert 'if [ "${REDIS_SOURCE}"' not in body
