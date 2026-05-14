"""
Regression tests for the four single-source-of-truth dicts/lists that
wire host-aliased Kong routes through the stack:

  - ``KongConfigGenerator.generate_litellm_service()`` (the new always-on route)
  - ``KongConfigGenerator.get_adaptive_services()`` (the orchestrator that calls it)
  - ``HostsManager.GENAI_HOSTS`` (the ``--setup-hosts`` source of truth)
  - ``state_builder._HOST_ALIAS`` (the wizard service-box source of truth)

Together these four surfaces define every Kong-aliased URL the stack
exposes. A drift between any two (e.g. ``litellm.localhost`` added to
the generator but not the hosts list) shows up as a "the URL is in the
wizard but my browser can't resolve it" UX bug — silent unless caught
at the source. These tests pin the four surfaces against each other.

Coverage focus is on the LiteLLM Kong alias added in this round of
work; the assertions also implicitly cover Hermes / Backend / n8n / etc.
to the extent that the four surfaces must agree about each entry.
"""

from __future__ import annotations

import pytest

# Imports are top-level so a syntax error in any of the four modules
# fails the test collection step with a clear traceback.
from utils.hosts_manager import HostsManager
from utils.kong_config_generator import KongConfigGenerator
from ui.state_builder import _HOST_ALIAS


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
# HostsManager.GENAI_HOSTS AND state_builder._HOST_ALIAS. Drift here means
# the wizard advertises a URL that can't resolve, or --setup-hosts writes
# an entry that nothing else uses.
# ────────────────────────────────────────────────────────────────────────────


def test_hosts_manager_genai_hosts_unique():
    """No duplicate entries in GENAI_HOSTS."""
    hosts = HostsManager.GENAI_HOSTS
    assert len(hosts) == len(set(hosts)), f"duplicate host in GENAI_HOSTS: {hosts}"


def test_host_alias_dict_values_unique():
    """No two display-names point at the same alias."""
    aliases = list(_HOST_ALIAS.values())
    assert len(aliases) == len(set(aliases)), (
        f"duplicate alias in _HOST_ALIAS: {aliases}"
    )


def test_host_alias_and_genai_hosts_agree():
    """The alias values in ``_HOST_ALIAS`` must equal the entries in
    ``GENAI_HOSTS`` as sets. If a display-name has an alias but
    ``--setup-hosts`` won't write it, the wizard URL won't resolve;
    conversely if ``--setup-hosts`` writes an alias that no service
    advertises, that's a stale /etc/hosts entry.
    """
    alias_set = set(_HOST_ALIAS.values())
    hosts_set = set(HostsManager.GENAI_HOSTS)
    only_in_alias = alias_set - hosts_set
    only_in_hosts = hosts_set - alias_set
    assert not only_in_alias, (
        f"aliases without corresponding /etc/hosts entry: {sorted(only_in_alias)}. "
        f"Add them to HostsManager.GENAI_HOSTS."
    )
    assert not only_in_hosts, (
        f"/etc/hosts entries with no advertised alias: {sorted(only_in_hosts)}. "
        f"Either add them to _HOST_ALIAS or remove from GENAI_HOSTS."
    )


def test_litellm_localhost_is_in_both_surfaces():
    """Spot-check for THIS round of work — ``litellm.localhost`` must be
    in both surfaces. Covered transitively by the agreement test above,
    but kept as a focused regression guard."""
    assert "litellm.localhost" in HostsManager.GENAI_HOSTS
    assert _HOST_ALIAS.get("LiteLLM") == "litellm.localhost"
