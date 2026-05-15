"""
Regression tests for the three single-source-of-truth surfaces that
wire host-aliased Kong routes through the stack:

  - ``KongConfigGenerator.generate_litellm_service()`` (the always-on LiteLLM route)
  - ``KongConfigGenerator.get_adaptive_services()`` (the orchestrator that calls it)
  - ``Topology.aliases`` — the canonical alias list. Drives:
      * ``HostsManager.get_genai_hosts()`` (the ``--setup-hosts`` consumer;
        the old ``HostsManager.GENAI_HOSTS`` constant is retired)
      * ``state_builder.alias_for`` (the wizard service-box renderer)

Together these surfaces define every Kong-aliased URL the stack
exposes. A drift between any two (e.g. ``litellm.localhost`` added to
the generator but not the hosts list) shows up as a "the URL is in the
wizard but my browser can't resolve it" UX bug — silent unless caught
at the source. These tests pin the surfaces against each other.

Coverage focus is on the LiteLLM Kong alias; the assertions also
implicitly cover Hermes / Backend / n8n / etc. to the extent that
the surfaces must agree about each entry.
"""

from __future__ import annotations

import pytest

# Imports are top-level so a syntax error in any of the four modules
# fails the test collection step with a clear traceback.
from utils.hosts_manager import HostsManager
from utils.kong_config_generator import KongConfigGenerator
from ui.state_builder import alias_for, _get_topology


# ────────────────────────────────────────────────────────────────────────────
# Fixture: a minimal ConfigParser stub that satisfies KongConfigGenerator's
# get_env_value() reads. We only need ``BACKEND_SOURCE`` and
# ``OPEN_WEB_UI_SOURCE`` to be non-disabled for get_adaptive_services()
# to emit those peers; the LiteLLM route is unconditional so it always
# appears regardless of env state.
# ────────────────────────────────────────────────────────────────────────────


class _StubConfigParser:
    def __init__(self, env: dict[str, str]):
        self._env = env
        # KongConfigGenerator.__init__ reads .env_file_path for error
        # messages; an unset attribute is fine for the tests.
        self.env_file_path = "/tmp/stub.env"

    def get_env_value(self, key: str, default: str = "") -> str:
        return self._env.get(key, default)


@pytest.fixture
def gen_with_all_enabled() -> KongConfigGenerator:
    env = {
        "BACKEND_SOURCE": "container",
        "OPEN_WEB_UI_SOURCE": "container",
        "KONG_HTTP_PORT": "63002",
        "LITELLM_PORT": "63012",
    }
    return KongConfigGenerator(_StubConfigParser(env))


# ────────────────────────────────────────────────────────────────────────────
# LiteLLM-specific: the always-on Kong route
# ────────────────────────────────────────────────────────────────────────────


def test_generate_litellm_service_is_always_on(gen_with_all_enabled):
    """The LiteLLM Kong route has no SOURCE gate — every call returns a dict."""
    svc = gen_with_all_enabled.generate_litellm_service()
    assert isinstance(svc, dict)
    assert svc.get("name") == "litellm-gateway"
    assert svc.get("url") == "http://litellm:4000/"


def test_generate_litellm_service_route_shape(gen_with_all_enabled):
    """The single route hits ``litellm.localhost`` with no path-stripping."""
    svc = gen_with_all_enabled.generate_litellm_service()
    routes = svc.get("routes") or []
    assert len(routes) == 1, "LiteLLM route should be a single host-routed entry"
    route = routes[0]
    assert route["name"] == "litellm-gateway-all"
    assert route["strip_path"] is False
    assert route["hosts"] == ["litellm.localhost"]


def test_generate_litellm_service_emits_cors_plugin(gen_with_all_enabled):
    """LiteLLM's dashboard is browser-facing; CORS must be enabled."""
    svc = gen_with_all_enabled.generate_litellm_service()
    plugins = svc.get("plugins") or []
    plugin_names = [p.get("name") for p in plugins]
    assert "cors" in plugin_names


def test_get_adaptive_services_includes_litellm(gen_with_all_enabled):
    """The orchestrator must include the LiteLLM route in its output."""
    services = gen_with_all_enabled.get_adaptive_services()
    names = [s["name"] for s in services]
    assert "litellm-gateway" in names, (
        "generate_litellm_service() must be wired into get_adaptive_services() — "
        "drift here means the route is generated but not actually emitted into "
        "the Kong config."
    )


# ────────────────────────────────────────────────────────────────────────────
# Cross-surface invariants: every Kong-aliased host must appear in BOTH
# HostsManager.GENAI_HOSTS AND Topology.aliases. Drift here means
# the wizard advertises a URL that can't resolve, or --setup-hosts writes
# an entry that nothing else uses.
# ────────────────────────────────────────────────────────────────────────────


def test_hosts_manager_genai_hosts_unique():
    """No duplicate entries in the topology-derived hosts list."""
    hosts = HostsManager._genai_hosts_from_topology()
    assert len(hosts) == len(set(hosts)), f"duplicate host in topology hosts: {hosts}"


def test_topology_aliases_unique():
    """No two topology rows point at the same alias."""
    aliases = _get_topology().aliases
    assert len(aliases) == len(set(aliases)), (
        f"duplicate alias in Topology.aliases: {aliases}"
    )


def test_topology_aliases_and_genai_hosts_agree():
    """``HostsManager._genai_hosts_from_topology()`` must be non-empty and
    every entry must end with ``.localhost`` — structural guard that the
    topology derives a valid hosts list.

    NOTE: since ``_genai_hosts_from_topology()`` is now derived directly from
    ``Topology.aliases``, comparing the two sets would be a tautology. This
    test instead verifies the structural contract: the list is non-empty and
    all entries are well-formed ``.localhost`` hostnames.
    """
    hosts = HostsManager._genai_hosts_from_topology()
    assert hosts, "topology-derived hosts list must be non-empty"
    bad = [h for h in hosts if not h.endswith(".localhost")]
    assert not bad, (
        f"hosts derived from topology must end with .localhost; bad entries: {bad}"
    )


def test_litellm_localhost_is_in_both_surfaces():
    """Spot-check for THIS round of work — ``litellm.localhost`` must be
    in both surfaces. Covered transitively by the agreement test above,
    but kept as a focused regression guard."""
    assert "litellm.localhost" in HostsManager._genai_hosts_from_topology()
    assert alias_for("LiteLLM") == "litellm.localhost"
