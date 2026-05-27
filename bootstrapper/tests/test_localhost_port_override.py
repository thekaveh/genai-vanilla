"""End-to-end tests for the localhost-port-override wizard wiring.

For each of the 10 localhost-capable services, the source step has
the matching localhost option(s) carrying a SecondaryNumberInput with
the correct env_var, default, min/max, unit_suffix='port'."""

from __future__ import annotations

from pathlib import Path

import pytest


# (service display name, localhost option value, expected env var, expected default port)
LOCALHOST_WIRING = [
    ("ComfyUI",            "localhost",            "COMFYUI_LOCALHOST_PORT",     "8000"),
    ("Document Processor", "docling-localhost",    "DOCLING_LOCALHOST_PORT",     "63021"),
    ("Hermes Agent",       "localhost",            "HERMES_LOCALHOST_PORT",      "63028"),
    ("OpenClaw",           "localhost",            "OPENCLAW_LOCALHOST_PORT",    "63024"),
    ("LLM Engine",         "ollama-localhost",     "OLLAMA_LOCALHOST_PORT",      "11434"),
    ("Neo4j Graph DB",     "localhost",            "NEO4J_LOCALHOST_BOLT_PORT",  "7687"),
    ("Weaviate",           "localhost",            "WEAVIATE_LOCALHOST_PORT",    "8080"),
    ("STT Provider",       "parakeet-localhost",   "PARAKEET_LOCALHOST_PORT",    "63022"),
    ("STT Provider",       "whisper-cpp-localhost","WHISPER_CPP_LOCALHOST_PORT", "63025"),
    ("TTS Provider",       "chatterbox-localhost", "CHATTERBOX_LOCALHOST_PORT",  "63027"),
]


def _wizard_steps():
    """Build the wizard's prompt steps via _build_steps_and_rows for the
    current repo state."""
    from core.config_parser import ConfigParser
    from ui.textual.integration import _build_steps_and_rows
    from utils.hosts_manager import HostsManager

    repo_root = Path(__file__).resolve().parent.parent.parent
    cp = ConfigParser(str(repo_root))
    cp.parse_env_file()
    hm = HostsManager()
    steps, _rows, _info, _bp, _state, _cloud = _build_steps_and_rows(cp, hm)
    return steps


@pytest.mark.parametrize("display,option_value,env_var,default", LOCALHOST_WIRING)
def test_localhost_option_carries_secondary_number(display, option_value, env_var, default):
    """For each (service, localhost option), the matching PromptOption
    on its source step carries a SecondaryNumberInput pointing at the
    expected env_var with the expected default."""
    steps = _wizard_steps()
    source_step = next(
        (s for s in steps if s.service_name == display and "source" in s.title.lower()),
        None,
    )
    assert source_step is not None, (
        f"Could not find a source step for service {display!r}. "
        f"Available steps: {[(s.service_name, s.title) for s in steps]}"
    )
    matching_opt = next(
        (o for o in source_step.options if o.value == option_value),
        None,
    )
    assert matching_opt is not None, (
        f"Source step for {display!r} has no option with value "
        f"{option_value!r}. Options: {[o.value for o in source_step.options]}"
    )
    cfg = matching_opt.secondary_number
    assert cfg is not None, (
        f"Option {display}/{option_value} should carry a "
        f"SecondaryNumberInput but doesn't."
    )
    assert cfg.env_var == env_var
    assert cfg.unit_suffix == "port"
    assert cfg.number_min == 1024
    assert cfg.number_max == 65535
    assert str(cfg.default_value) == default


def test_non_localhost_options_carry_no_secondary_number():
    """Container / external / disabled options never carry a config —
    the inline textbox only makes sense for localhost sources (Ray
    container variants carry RAY_WORKER_COUNT, which is allowed)."""
    steps = _wizard_steps()
    for s in steps:
        for opt in s.options:
            if opt.value and "localhost" not in opt.value:
                if opt.secondary_number is not None:
                    # Allowed exception: Ray's container-cpu / container-gpu
                    # rows carry RAY_WORKER_COUNT — that's not a port.
                    if opt.secondary_number.env_var == "RAY_WORKER_COUNT":
                        continue
                    assert False, (
                        f"Option {s.service_name}/{opt.value} carries a "
                        f"SecondaryNumberInput ({opt.secondary_number.env_var}) "
                        f"but it's not a -localhost option. "
                        f"This widget is only for localhost ports + Ray workers."
                    )
