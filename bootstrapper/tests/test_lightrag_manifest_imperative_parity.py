"""Manifest ↔ imperative parity for `LIGHTRAG_RERANK_BINDING_HOST`.

Two declarations of the same env-var contract:

  1. **Manifest** — `services/lightrag/service.yml`
     `runtime_adaptive.lightrag.environment_adaptation.LIGHTRAG_RERANK_BINDING_HOST`
     declares ``"${TEI_RERANKER_ENDPOINT}/rerank"``.

  2. **Imperative** — `bootstrapper/services/service_config.py:1095` emits
     ``f'{tei_endpoint.rstrip("/")}/rerank'`` at .env-render time.

Per `project_post_merge_env_staleness` memory: when these two drift,
the manifest looks correct in code review but the runtime value comes
from the imperative path — exactly the bug class that lost ~30
post-migration literals before the fix shipped 2026-06-04. Guard both
sites end in `/rerank` (or both omit it) so a future edit to one
without the other fails CI loudly.
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


def test_manifest_rerank_binding_includes_rerank_path():
    """The manifest's declared value must end in `/rerank`. LightRAG's `jina`
    binding POSTs to the host URL verbatim — without the path the request
    lands on TEI's root and 404s.
    """
    value = _manifest_rerank_binding()
    assert value.endswith("/rerank"), (
        f"services/lightrag/service.yml::runtime_adaptive.lightrag"
        f".environment_adaptation.LIGHTRAG_RERANK_BINDING_HOST = {value!r}; "
        f"must end with '/rerank' or LightRAG's jina binding will 404 against "
        f"TEI's root endpoint."
    )


def test_imperative_emission_appends_rerank_path():
    """The imperative emitter in service_config.py must append '/rerank'.

    Light text scan rather than a runtime invocation — the runtime path
    requires a full bootstrapper fixture setup. If the literal `/rerank`
    string disappears from the LIGHTRAG_RERANK_BINDING_HOST emission block,
    fail loudly so the manifest-vs-imperative pair stays in sync.
    """
    src = SERVICE_CONFIG.read_text(encoding="utf-8")
    # Find the block that emits LIGHTRAG_RERANK_BINDING_HOST.
    needle = "LIGHTRAG_RERANK_BINDING_HOST"
    assert needle in src, (
        f"{needle} no longer appears in service_config.py; either the "
        f"emitter moved (update this test to point at the new path) or "
        f"the manifest declaration is now dead."
    )
    # Locate the next non-empty assignment for LIGHTRAG_RERANK_BINDING_HOST
    # and confirm it produces a string ending in /rerank.
    idx = src.find(needle)
    # Window the next ~400 chars (long enough to cover the f-string).
    window = src[idx : idx + 400]
    assert "/rerank" in window, (
        f"service_config.py's LIGHTRAG_RERANK_BINDING_HOST emission no "
        f"longer appends '/rerank' (window: {window!r}). LightRAG's jina "
        f"binding would 404 against TEI's root; align the manifest too."
    )
