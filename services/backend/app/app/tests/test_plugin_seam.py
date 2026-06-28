import importlib, sys, types
from pathlib import Path


def test_load_plugins_includes_router(tmp_path, monkeypatch):
    # Arrange: a fake plugin package exposing `router`
    pkg = tmp_path / "demoplugin"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        "from fastapi import APIRouter\n"
        "router = APIRouter()\n"
        "@router.get('/__demoplugin__')\n"
        "def ping():\n"
        "    return {'ok': True}\n"
    )
    from fastapi import FastAPI
    app = FastAPI()
    monkeypatch.setenv("BACKEND_PLUGINS_DIR", str(tmp_path))

    import plugin_seam  # the module we will create
    plugin_seam.load_plugins(app)

    paths = {r.path for r in app.router.routes}
    assert "/__demoplugin__" in paths


def test_load_plugins_noop_when_dir_missing(monkeypatch):
    from fastapi import FastAPI
    app = FastAPI()
    before = len(app.router.routes)
    monkeypatch.setenv("BACKEND_PLUGINS_DIR", "/nonexistent/path/xyz")
    import plugin_seam
    plugin_seam.load_plugins(app)
    assert len(app.router.routes) == before
