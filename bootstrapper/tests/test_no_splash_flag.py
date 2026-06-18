import inspect

from ui.textual import integration
import start as start_mod


def test_flows_accept_no_splash():
    assert "no_splash" in inspect.signature(integration.run_setup_flow).parameters
    assert "no_splash" in inspect.signature(integration.run_launch_flow).parameters


def test_cli_declares_no_splash():
    names = {p.name for p in start_mod.main.params}  # Click params
    assert "no_splash" in names
