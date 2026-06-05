"""Unit test for ServiceConfig._generate_spark_config()."""
from unittest.mock import MagicMock
from services.service_config import ServiceConfig


def _build_config(source_value: str, worker_count: str = "2"):
    sc = ServiceConfig(config_parser=MagicMock())
    sc.localhost_host = "host.docker.internal"
    sc.service_sources = {"SPARK_SOURCE": source_value}
    sc.yaml_config = {
        "source_configurable": {
            "spark": {
                source_value: {"environment": {}, "scale": 1, "deploy": {}, "extra_hosts": []}
            }
        }
    }
    sc.config_parser.parse_env_file.return_value = {"SPARK_WORKER_COUNT": worker_count}
    return sc._generate_spark_config()


def test_spark_disabled_sets_all_scales_to_zero():
    env_vars = _build_config("disabled")
    assert env_vars["SPARK_MASTER_SCALE"] == "0"
    assert env_vars["SPARK_WORKER_SCALE"] == "0"
    assert env_vars["SPARK_HISTORY_SCALE"] == "0"
    assert env_vars["SPARK_INIT_SCALE"] == "0"


def test_spark_container_with_default_worker_count():
    env_vars = _build_config("container", worker_count="2")
    assert env_vars["SPARK_MASTER_SCALE"] == "1"
    assert env_vars["SPARK_WORKER_SCALE"] == "2"
    assert env_vars["SPARK_HISTORY_SCALE"] == "1"
    assert env_vars["SPARK_INIT_SCALE"] == "1"


def test_spark_container_respects_worker_count_override():
    env_vars = _build_config("container", worker_count="5")
    assert env_vars["SPARK_WORKER_SCALE"] == "5"


def test_spark_container_clamps_worker_count():
    env_vars_low = _build_config("container", worker_count="0")
    assert env_vars_low["SPARK_WORKER_SCALE"] == "1", "below-1 clamped to 1"
    env_vars_high = _build_config("container", worker_count="42")
    assert env_vars_high["SPARK_WORKER_SCALE"] == "8", "above-8 clamped to 8"
