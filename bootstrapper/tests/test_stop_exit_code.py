"""stop.py must propagate a failed `docker compose down` via its exit code.

Regression guard: stop_services() used to return True on both branches,
so a failed stop was undetectable to scripts and CI.
"""
from __future__ import annotations

import click.testing

import stop as stop_module


def _stopper_with_stop_result(monkeypatch, rc: int):
    stopper = stop_module.AtlasStopper()
    monkeypatch.setattr(
        stopper.docker_manager, "stop_services",
        lambda remove_volumes, remove_orphans: rc,
    )
    return stopper


def test_stop_services_returns_false_on_compose_failure(monkeypatch):
    stopper = _stopper_with_stop_result(monkeypatch, rc=1)
    assert stopper.stop_services(cold_stop=False, project_name="genai") is False


def test_stop_services_returns_true_on_success(monkeypatch):
    stopper = _stopper_with_stop_result(monkeypatch, rc=0)
    assert stopper.stop_services(cold_stop=False, project_name="genai") is True


def test_main_exits_nonzero_when_stop_fails(monkeypatch):
    monkeypatch.setattr(
        stop_module.AtlasStopper, "show_configuration_info",
        lambda self, cold, clean: "genai",
    )
    monkeypatch.setattr(
        stop_module.AtlasStopper, "stop_services",
        lambda self, cold, project_name: False,
    )
    result = click.testing.CliRunner().invoke(stop_module.main, [])
    assert result.exit_code == 1


def test_main_exits_zero_when_stop_succeeds(monkeypatch):
    monkeypatch.setattr(
        stop_module.AtlasStopper, "show_configuration_info",
        lambda self, cold, clean: "genai",
    )
    monkeypatch.setattr(
        stop_module.AtlasStopper, "stop_services",
        lambda self, cold, project_name: True,
    )
    result = click.testing.CliRunner().invoke(stop_module.main, [])
    assert result.exit_code == 0
