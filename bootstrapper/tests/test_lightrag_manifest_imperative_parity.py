"""Manifest ↔ imperative parity for `LIGHTRAG_RERANK_BINDING_HOST`.

Two declarations of the same env-var contract:

  1. **Manifest** — `services/lightrag/service.yml`
     `runtime_adaptive.lightrag.environment_adaptation.LIGHTRAG_RERANK_BINDING_HOST`
     declares ``""``.

  2. **Imperative** — `bootstrapper/services/service_config.py` emits a blank
     host and ``LIGHTRAG_RERANK_BINDING=null`` at .env-render time.

Per `project_post_merge_env_staleness` memory: when these two drift,
the manifest looks correct in code review but the runtime value comes
from the imperative path — exactly the bug class that lost ~30
post-migration literals before the fix shipped 2026-06-04. Guard both
sites keep direct TEI rerank disabled unless an adapter is added.
"""
from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
LIGHTRAG_MANIFEST = REPO_ROOT / "services" / "lightrag" / "service.yml"
SERVICE_CONFIG = REPO_ROOT / "bootstrapper" / "services" / "service_config.py"


def _manifest_rerank_binding() -> str:
    data = yaml.safe_load(LIGHTRAG_MANIFEST.read_text(encoding="utf-8"))
    return (
        data["runtime_adaptive"]["lightrag"]["environment_adaptation"][
            "LIGHTRAG_RERANK_BINDING_HOST"
        ]
    )


def test_manifest_rerank_binding_host_stays_blank_for_direct_tei():
    """Atlas's TEI endpoint expects {query, texts}; LightRAG's direct rerank
    clients send {query, documents}. Keep the manifest host blank until an
    adapter exists.
    """
    value = _manifest_rerank_binding()
    assert value == "", (
        f"services/lightrag/service.yml::runtime_adaptive.lightrag"
        f".environment_adaptation.LIGHTRAG_RERANK_BINDING_HOST = {value!r}; "
        f"must stay blank while direct TEI rerank is incompatible."
    )


def test_imperative_emission_keeps_direct_tei_rerank_disabled():
    """The imperative emitter in service_config.py must keep direct TEI
    rerank disabled by emitting a blank host and literal null binding.

    Light text scan rather than a runtime invocation — the runtime path is
    covered by test_lightrag_tei_source_permutations.
    """
    src = SERVICE_CONFIG.read_text(encoding="utf-8")
    needle = "LIGHTRAG_RERANK_BINDING_HOST"
    assert needle in src, (
        f"{needle} no longer appears in service_config.py; either the "
        f"emitter moved (update this test to point at the new path) or "
        f"the manifest declaration is now dead."
    )
    idx = src.find(needle)
    window = src[idx : idx + 700]
    assert "LIGHTRAG_RERANK_BINDING_HOST'] = ''" in window
    assert "LIGHTRAG_RERANK_BINDING'] = 'null'" in window
    assert "/rerank" not in window, (
        f"service_config.py appears to re-enable direct TEI rerank "
        f"(window: {window!r}); add an adapter before wiring this host."
    )
