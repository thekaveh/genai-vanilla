# bootstrapper/tests/test_lightrag_config.py
"""Tests for _generate_lightrag_config()."""
from __future__ import annotations

from unittest.mock import MagicMock

from services.service_config import ServiceConfig


_BASE_ENV = {
    "PROJECT_NAME": "genai",
    "LIGHTRAG_LOCALHOST_PORT": "63068",
}


def _make(source: str) -> ServiceConfig:
    sc = ServiceConfig(config_parser=MagicMock())
    sc.localhost_host = "localhost"
    sc.service_sources = {"LIGHTRAG_SOURCE": source}
    sc.config_parser.parse_env_file.return_value = dict(_BASE_ENV)
    return sc


def test_disabled_clears_endpoint_and_scales():
    sc = _make("disabled")
    env = sc._generate_lightrag_config()
    assert env["LIGHTRAG_ENDPOINT"] == ""
    assert env["LIGHTRAG_SCALE"] == "0"
    assert env["LIGHTRAG_INIT_SCALE"] == "0"


def test_container_endpoint_and_scales():
    sc = _make("container")
    env = sc._generate_lightrag_config()
    assert env["LIGHTRAG_ENDPOINT"] == "http://lightrag:9621"
    assert env["LIGHTRAG_SCALE"] == "1"
    assert env["LIGHTRAG_INIT_SCALE"] == "1"


def test_localhost_uses_LIGHTRAG_LOCALHOST_PORT():
    sc = _make("localhost")
    env = sc._generate_lightrag_config()
    assert env["LIGHTRAG_ENDPOINT"] == "http://localhost:63068"
    assert env["LIGHTRAG_SCALE"] == "0"
    assert env["LIGHTRAG_INIT_SCALE"] == "0"
