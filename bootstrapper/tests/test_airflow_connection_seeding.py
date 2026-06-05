"""Verify that init-airflow.sh gates connection seeding on every sibling source."""
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO / "services" / "airflow" / "init" / "scripts" / "init-airflow.sh"


def test_init_script_exists_and_is_executable():
    assert SCRIPT.exists(), "init-airflow.sh missing"
    assert (SCRIPT.stat().st_mode & 0o111), "init-airflow.sh not executable"


def test_init_script_gates_each_sibling_connection():
    body = SCRIPT.read_text(encoding="utf-8")
    # Each conditional must reference the matching sibling _SOURCE env var.
    assert 'if [ "${SPARK_SOURCE}" = "container" ]' in body
    assert 'if [ "${MINIO_SOURCE}" = "container" ]' in body
    assert 'if [ "${LITELLM_SOURCE}" != "disabled" ]' in body
    assert 'if [ "${WEAVIATE_SOURCE}" != "disabled" ]' in body
    assert 'if [ "${NEO4J_SOURCE}" != "disabled" ]' in body
    assert 'if [ "${REDIS_SOURCE}" != "disabled" ]' in body


def test_init_script_seeds_unconditional_supabase():
    body = SCRIPT.read_text(encoding="utf-8")
    # supabase is required, not optional — seed always.
    assert 'add_conn postgres_supabase' in body
