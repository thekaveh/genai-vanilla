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
    assert 'add_conn postgres_supabase' in body, "postgres_supabase Connection seed missing"
    assert 'add_conn litellm_default' in body, "litellm_default Connection seed missing"
    assert 'add_conn redis_default' in body, "redis_default Connection seed missing"
    # LiteLLM and Redis must NOT sit inside an `if`-guard — search for
    # the conditional patterns to be sure.
    assert 'if [ "${LITELLM_SOURCE}"' not in body, "LITELLM_SOURCE gate snuck back in"
    assert 'if [ "${REDIS_SOURCE}"' not in body, "REDIS_SOURCE gate snuck back in"


def test_init_script_neo4j_uses_canonical_compose_dns_and_credentials():
    """neo4j_default Connection must point at the canonical compose service
    name (`neo4j-graph-db`, NOT `neo4j` — the latter does not resolve) and
    must carry GRAPH_DB_USER/GRAPH_DB_PASSWORD credentials (Neo4j is
    auth-on by default; missing creds → Neo.ClientError.Security.Unauthorized).
    Pre-Pass-6 the script wrote `bolt://neo4j` with no creds and any
    Neo4jOperator DAG would error at run time.
    """
    body = SCRIPT.read_text(encoding="utf-8")
    assert "bolt://neo4j-graph-db" in body, (
        "neo4j_default Connection must use compose-canonical "
        "bolt://neo4j-graph-db (NOT bolt://neo4j — that DNS name doesn't exist)"
    )
    assert "${GRAPH_DB_USER}" in body, (
        "neo4j_default Connection must pass --conn-login ${GRAPH_DB_USER}"
    )
    assert "${GRAPH_DB_PASSWORD}" in body, (
        "neo4j_default Connection must pass --conn-password ${GRAPH_DB_PASSWORD}"
    )


def test_init_script_re_applies_airflow_db_password():
    """ALTER ROLE airflow WITH PASSWORD ... must run every cold start so
    AIRFLOW_DB_PASSWORD rotations in .env take effect — CREATE ROLE only
    fires the first time. Pre-Pass-6 a rotated password sat in .env but
    Postgres still authenticated only the old value.
    """
    body = SCRIPT.read_text(encoding="utf-8")
    assert "ALTER ROLE ${AIRFLOW_DB_USER} WITH PASSWORD" in body, (
        "init-airflow.sh must ALTER ROLE the airflow role's password every "
        "run; without this, AIRFLOW_DB_PASSWORD rotations don't take effect."
    )


def test_init_script_orphan_cleanup_pass_present():
    """An unconditional `airflow connections delete` pass must run before
    the gated add_conn calls so that toggling a sibling source from
    container → disabled doesn't leave an orphan Connection pointing at
    a dead host (which a DAG referencing the connection would then hit).
    """
    body = SCRIPT.read_text(encoding="utf-8")
    assert "for orphan in spark_default minio_default weaviate_default neo4j_default" in body


def test_init_script_alters_database_owner_for_pg15_public_schema():
    """Postgres 15+ tightened the public schema: ALL PRIVILEGES on a
    database no longer grants CREATE on `public`; only the database
    OWNER (via pg_database_owner) can create objects. ALTER DATABASE
    airflow OWNER TO ${AIRFLOW_DB_USER} flips ownership so `airflow db
    migrate` succeeds. Without this the stack ships supabase/postgres:17.x
    and every cold start would fail at db migrate with permission denied.
    """
    body = SCRIPT.read_text(encoding="utf-8")
    assert "ALTER DATABASE airflow OWNER TO" in body, (
        "init-airflow.sh must re-own the airflow database to the airflow "
        "role; otherwise PG15+ blocks CREATE TABLE in the public schema."
    )
