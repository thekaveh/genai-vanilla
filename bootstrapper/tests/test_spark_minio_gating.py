"""Spark's source-step selection must hard-fail when MINIO_SOURCE=disabled.

spark-init bootstraps the spark-history bucket via minio-init and
``depends_on: minio-init: condition: service_completed_successfully``.
Without MinIO, minio-init never runs and the stack hangs at compose-up.
Mirrors the Zeppelin → Spark gate in test_zeppelin_spark_gating.py."""
from unittest.mock import MagicMock
import pytest
from services.service_config import ServiceConfig


def _sc_with_sources(**sources) -> ServiceConfig:
    sc = ServiceConfig(config_parser=MagicMock())
    sc.service_sources = sources
    sc.config_parser.parse_env_file.return_value = {"SPARK_WORKER_COUNT": "2"}
    return sc


def test_spark_disabled_returns_all_scales_zero():
    sc = _sc_with_sources(SPARK_SOURCE="disabled", MINIO_SOURCE="disabled")
    out = sc._generate_spark_config()
    assert out["SPARK_MASTER_SCALE"] == "0"
    assert out["SPARK_WORKER_SCALE"] == "0"
    assert out["SPARK_HISTORY_SCALE"] == "0"
    assert out["SPARK_INIT_SCALE"] == "0"
    assert out["SPARK_CONNECT_SCALE"] == "0"


def test_spark_container_with_minio_container_returns_full_scales():
    sc = _sc_with_sources(SPARK_SOURCE="container", MINIO_SOURCE="container")
    out = sc._generate_spark_config()
    assert out["SPARK_MASTER_SCALE"] == "1"
    assert out["SPARK_WORKER_SCALE"] == "2"
    assert out["SPARK_HISTORY_SCALE"] == "1"
    assert out["SPARK_INIT_SCALE"] == "1"
    assert out["SPARK_CONNECT_SCALE"] == "1"


def test_spark_container_with_minio_disabled_raises():
    sc = _sc_with_sources(SPARK_SOURCE="container", MINIO_SOURCE="disabled")
    with pytest.raises(ValueError, match="Spark requires MinIO"):
        sc._generate_spark_config()
