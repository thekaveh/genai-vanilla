"""End-to-end env generation across LightRAG + TEI Reranker source values."""
from __future__ import annotations

import shutil
import pytest
from pathlib import Path
from core.config_parser import ConfigParser
from services.service_config import ServiceConfig


REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = REPO_ROOT / ".env.example"


@pytest.fixture
def env_copy(tmp_path):
    env = tmp_path / ".env"
    shutil.copy(ENV_EXAMPLE, env)
    return env


def _make(env_path: Path, sources: dict) -> ServiceConfig:
    """Build a ServiceConfig using the real ConfigParser and given env_path.

    Writes the desired SOURCE values directly into the env file so that
    ConfigParser.parse_service_sources() (called inside load_config) reads
    the correct values — ServiceConfig.load_config() overwrites self.service_sources
    from the file, so mutations made after construction would be lost.
    """
    # Patch SOURCE values into the env file in-place.
    text = env_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    out = []
    replaced = set()
    for line in lines:
        matched = False
        for var, val in sources.items():
            if line.startswith(f"{var}=") and var not in replaced:
                out.append(f"{var}={val}")
                replaced.add(var)
                matched = True
                break
        if not matched:
            out.append(line)
    # Append any sources that weren't found in the file.
    for var, val in sources.items():
        if var not in replaced:
            out.append(f"{var}={val}")
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")

    # root_dir must point at the real repo root so load_yaml_config() can
    # find services/ manifests; env_file_path is overridden to the tmp copy
    # so parse_service_sources() / parse_env_file() read our patched values.
    cp = ConfigParser(str(REPO_ROOT))
    cp.env_file_path = env_path
    sc = ServiceConfig(config_parser=cp)
    sc.localhost_host = "localhost"
    return sc


@pytest.mark.parametrize("lightrag_source", ["disabled", "container", "localhost"])
def test_lightrag_env_generation_each_source(env_copy, lightrag_source):
    sc = _make(env_copy, {
        "LIGHTRAG_SOURCE": lightrag_source,
        "TEI_RERANKER_SOURCE": "disabled",
    })
    env = sc.generate_service_environment()
    assert "LIGHTRAG_ENDPOINT" in env
    assert "LIGHTRAG_SCALE" in env
    if lightrag_source == "disabled":
        assert env["LIGHTRAG_ENDPOINT"] == ""
        assert env["LIGHTRAG_SCALE"] == "0"
    elif lightrag_source == "container":
        assert "lightrag" in env["LIGHTRAG_ENDPOINT"]
        assert env["LIGHTRAG_SCALE"] == "1"
    elif lightrag_source == "localhost":
        assert "localhost:63068" in env["LIGHTRAG_ENDPOINT"]
        assert env["LIGHTRAG_SCALE"] == "0"


@pytest.mark.parametrize("tei_source", [
    "disabled", "container-cpu", "container-gpu", "localhost"
])
def test_tei_reranker_env_generation_each_source(env_copy, tei_source):
    sc = _make(env_copy, {
        "LIGHTRAG_SOURCE": "disabled",
        "TEI_RERANKER_SOURCE": tei_source,
    })
    env = sc.generate_service_environment()
    assert "TEI_RERANKER_ENDPOINT" in env
    assert "TEI_RERANKER_SCALE" in env
    if tei_source == "disabled":
        assert env["TEI_RERANKER_ENDPOINT"] == ""
        assert env["TEI_RERANKER_SCALE"] == "0"
    elif tei_source == "localhost":
        assert "localhost:63031" in env["TEI_RERANKER_ENDPOINT"]
    else:  # container variants
        assert env["TEI_RERANKER_ENDPOINT"] == "http://tei-reranker:80"
        assert env["TEI_RERANKER_SCALE"] == "1"


def test_lightrag_adaptive_picks_up_tei_endpoint(env_copy):
    sc = _make(env_copy, {
        "LIGHTRAG_SOURCE": "container",
        "TEI_RERANKER_SOURCE": "container-cpu",
    })
    env = sc.generate_service_environment()
    # LIGHTRAG_RERANK_BINDING_HOST should mirror TEI_RERANKER_ENDPOINT
    # plus the /rerank path — LightRAG's `jina` rerank binding POSTs to
    # the host URL as-is without auto-appending any path.
    assert env.get("LIGHTRAG_RERANK_BINDING_HOST") == "http://tei-reranker:80/rerank"


def test_lightrag_adaptive_blanks_rerank_when_tei_disabled(env_copy):
    sc = _make(env_copy, {
        "LIGHTRAG_SOURCE": "container",
        "TEI_RERANKER_SOURCE": "disabled",
    })
    env = sc.generate_service_environment()
    assert env.get("LIGHTRAG_RERANK_BINDING_HOST", "") == ""


# ---------------------------------------------------------------------------
# Storage adaptive var tests — 6 newly-emitted vars
# ---------------------------------------------------------------------------

def test_lightrag_pg_uri_populated_when_supabase_enabled(env_copy):
    sc = _make(env_copy, {
        "LIGHTRAG_SOURCE": "container",
        "SUPABASE_SOURCE": "container",
    })
    env = sc.generate_service_environment()
    assert env.get("LIGHTRAG_PG_URI", "").startswith("postgresql://")
    assert "supabase-db:5432" in env["LIGHTRAG_PG_URI"]


def test_lightrag_pg_uri_blank_when_supabase_disabled(env_copy):
    sc = _make(env_copy, {
        "LIGHTRAG_SOURCE": "container",
        "SUPABASE_SOURCE": "disabled",
    })
    env = sc.generate_service_environment()
    assert env.get("LIGHTRAG_PG_URI", "") == ""


def test_lightrag_neo4j_uri_populated_when_neo4j_enabled(env_copy):
    sc = _make(env_copy, {
        "LIGHTRAG_SOURCE": "container",
        "NEO4J_GRAPH_DB_SOURCE": "container",
    })
    env = sc.generate_service_environment()
    assert env.get("LIGHTRAG_NEO4J_URI") == "bolt://neo4j:7687"
    assert env.get("LIGHTRAG_NEO4J_USERNAME") == "neo4j"
    assert env.get("LIGHTRAG_NEO4J_PASSWORD")  # truthy — non-empty from .env.example


def test_lightrag_neo4j_blank_when_neo4j_disabled(env_copy):
    sc = _make(env_copy, {
        "LIGHTRAG_SOURCE": "container",
        "NEO4J_GRAPH_DB_SOURCE": "disabled",
    })
    env = sc.generate_service_environment()
    assert env.get("LIGHTRAG_NEO4J_URI", "") == ""
    assert env.get("LIGHTRAG_NEO4J_USERNAME", "") == ""
    assert env.get("LIGHTRAG_NEO4J_PASSWORD", "") == ""


def test_lightrag_redis_uri_populated_when_redis_enabled(env_copy):
    sc = _make(env_copy, {
        "LIGHTRAG_SOURCE": "container",
        "REDIS_SOURCE": "container",
    })
    env = sc.generate_service_environment()
    assert env.get("LIGHTRAG_REDIS_URI", "").startswith("redis://")
    assert "redis:6379/2" in env["LIGHTRAG_REDIS_URI"]


def test_lightrag_docling_endpoint_mirrors_DOCLING_ENDPOINT(env_copy):
    sc = _make(env_copy, {
        "LIGHTRAG_SOURCE": "container",
        "DOC_PROCESSOR_SOURCE": "docling-container-gpu",
    })
    env = sc.generate_service_environment()
    assert "docling" in env.get("LIGHTRAG_DOCLING_ENDPOINT", "")


def test_lightrag_storage_blanks_when_lightrag_disabled(env_copy):
    sc = _make(env_copy, {
        "LIGHTRAG_SOURCE": "disabled",
        "SUPABASE_SOURCE": "container",
        "NEO4J_GRAPH_DB_SOURCE": "container",
        "REDIS_SOURCE": "container",
    })
    env = sc.generate_service_environment()
    # LightRAG disabled → storage adaptive vars are blank
    assert env.get("LIGHTRAG_PG_URI", "") == ""
    assert env.get("LIGHTRAG_NEO4J_URI", "") == ""
    assert env.get("LIGHTRAG_NEO4J_USERNAME", "") == ""
    assert env.get("LIGHTRAG_NEO4J_PASSWORD", "") == ""
    assert env.get("LIGHTRAG_REDIS_URI", "") == ""
    assert env.get("LIGHTRAG_DOCLING_ENDPOINT", "") == ""


def test_lightrag_rerank_blank_when_lightrag_disabled(env_copy):
    sc = _make(env_copy, {
        "LIGHTRAG_SOURCE": "disabled",
        "TEI_RERANKER_SOURCE": "container-cpu",  # tei is on
    })
    env = sc.generate_service_environment()
    # Even though TEI is on, LightRAG is disabled — its rerank var must be blank
    assert env.get("LIGHTRAG_RERANK_BINDING_HOST", "") == ""
