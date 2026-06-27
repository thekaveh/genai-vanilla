"""Regression: litellm-init must load `model_resolver` as LOOSE modules.

litellm-init exec-loads ``/catalog/model_resolver.py`` via importlib. Its
CONTAINER code path falls back to ``import llm_catalog`` /
``from cloud_providers import CLOUD_PROVIDERS`` because there is no ``utils``
package inside ``/catalog``. That fallback only resolves if ``/catalog`` is on
``sys.path`` — and ``importlib.exec_module`` does NOT add it. The original bug
(``ModuleNotFoundError: No module named 'llm_catalog'``) aborted the whole
stack at ``litellm-init``.

The rest of the bootstrapper test suite runs IN-PROCESS, where ``utils`` is an
importable package, so ``model_resolver``'s ``try: from utils import …`` branch
always wins and the loose fallback is never exercised — which is exactly why
this slipped through. This test runs init.py in a SUBPROCESS with NO ``utils``
package reachable, faithfully replicating the container, and asserts
``_load_catalog_module('model_resolver')`` + ``active_models({})`` succeed.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
UTILS_DIR = REPO_ROOT / "bootstrapper" / "utils"
SERVICES_DIR = REPO_ROOT / "services"
INIT_PY = REPO_ROOT / "services" / "litellm" / "init" / "scripts" / "init.py"

# Driver runs INSIDE the subprocess. It first proves `utils` is unreachable
# (replicating /catalog, which has no `utils` package), then drives the real
# init.py loader exactly as the container does.
_DRIVER = """
import importlib.util, sys, types, os, pathlib

# Replicate the container's /catalog: it has NO `utils` package. The
# bootstrapper venv exposes `utils` (editable/.pth), and a clean subprocess env
# is not enough to hide it — so actively strip every sys.path dir that makes
# `utils` importable (and purge any cached utils.* modules). This forces
# model_resolver's `from utils import ...` to fail and the loose fallback to
# run, exactly as in the container.
for _ in range(20):
    spec = importlib.util.find_spec("utils")
    if spec is None:
        break
    parents = {
        str(pathlib.Path(loc).parent)
        for loc in (spec.submodule_search_locations or [])
    }
    if spec.origin and spec.origin not in ("namespace", None):
        parents.add(str(pathlib.Path(spec.origin).parent.parent))
    sys.path[:] = [p for p in sys.path if p not in parents]
    for mod in [m for m in sys.modules if m == "utils" or m.startswith("utils.")]:
        del sys.modules[mod]
assert importlib.util.find_spec("utils") is None, (
    "could not isolate `utils` from sys.path: " + repr(sys.path)
)

# init.py imports psycopg2 at module scope; stub it (unused by active_models).
sys.modules.setdefault("psycopg2", types.ModuleType("psycopg2"))

init_py = os.environ["INIT_PY_PATH"]
spec = importlib.util.spec_from_file_location("litellm_init", init_py)
init = importlib.util.module_from_spec(spec)
sys.modules["litellm_init"] = init
spec.loader.exec_module(init)

# The exact call path that failed in the report: init.py:265 fetch_active_models
# -> _load_catalog_module("model_resolver") -> model_resolver loose imports.
mr = init._load_catalog_module("model_resolver")
actives = mr.active_models({})
assert actives, "active_models({}) returned empty"
print("OK", len(actives))
"""


def _flat_models_dir(tmp_path) -> str:
    """Build the container's flat ``/atlas-models`` layout —
    ``<dir>/<service>-models.yaml`` — from the repo's nested catalogs (#154)."""
    d = tmp_path / "atlas-models"
    d.mkdir()
    for svc in ("ollama", "litellm"):
        (d / f"{svc}-models.yaml").write_text(
            (SERVICES_DIR / svc / "models.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    return str(d)


@pytest.mark.parametrize("layout", ["nested", "flat"])
def test_model_resolver_loads_as_loose_modules_in_container(tmp_path, layout):
    """Faithful container check, both model-catalog layouts:

    * the loose-import path (no ``utils`` package) must resolve (#157), AND
    * ``llm_catalog`` must find the YAMLs in BOTH the repo's nested
      ``<svc>/models.yaml`` form and the container's flat
      ``/atlas-models/<svc>-models.yaml`` form (#154).
    """
    driver = tmp_path / "driver.py"
    driver.write_text(_DRIVER, encoding="utf-8")

    models_dir = str(SERVICES_DIR) if layout == "nested" else _flat_models_dir(tmp_path)

    env = dict(os.environ)
    env["ATLAS_CATALOG_DIR"] = str(UTILS_DIR)     # the modules dir (= /catalog)
    env["ATLAS_MODELS_DIR"] = models_dir          # nested repo dir OR flat /atlas-models
    env["INIT_PY_PATH"] = str(INIT_PY)
    # Do NOT inherit the bootstrapper root on the path — that is what makes
    # `utils` an importable package in-process and hides the container bug.
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [sys.executable, "driver.py"],
        cwd=str(tmp_path),   # neutral cwd: sys.path[0] holds no `utils`
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"litellm-init loose-module import regression ({layout} models layout) — "
        "model_resolver failed to load without a `utils` package "
        "(the container's /catalog context):\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    assert "OK" in result.stdout, result.stdout
