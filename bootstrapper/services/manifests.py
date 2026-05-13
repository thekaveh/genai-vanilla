"""
Service manifest loader for the per-service configuration layout.

Each `services/<name>/service.yml` is the single source of truth about one
service family (env vars, source variants, dependencies, image refs). This
module loads, validates, and exposes those manifests as typed dataclasses.

This module is intentionally side-effect-free: it does not touch the
environment, the bootstrapper state, or docker-compose. The
manifest_validator module performs the cross-manifest checks; this module
only handles per-file load + schema validation + per-manifest sanity checks.

Phase A: pure-additive scaffolding. Not wired into start.py yet.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaError


# ────────────────────────────────────────────────────────────────────────────
# Public dataclasses
# ────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EnvVarDecl:
    """One entry from a manifest's `env:` list."""

    name: str
    default: Any = ""
    description: str = ""
    auto_managed: bool = False
    secret: bool = False


@dataclass(frozen=True)
class ImageRef:
    """One entry from `images:`."""

    var: str
    default: str
    container: str
    notes: str = ""


@dataclass(frozen=True)
class SourceOption:
    """One option inside `sources.options`."""

    id: str
    label: str
    effects: dict[str, Any] = field(default_factory=dict)
    requires: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SourcesBlock:
    """The `sources:` block of a manifest, present only for source-configurable services."""

    var: str
    default: str
    options: list[SourceOption]


@dataclass(frozen=True)
class DependsOn:
    """Logical dependencies (NOT the compose-level depends_on, which lives in compose.yml)."""

    required: list[str] = field(default_factory=list)
    optional: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExportRef:
    """An env var this manifest exports to other services."""

    name: str
    consumers: list[str]


@dataclass(frozen=True)
class Manifest:
    """Parsed services/<name>/service.yml."""

    name: str
    label: str
    category: str
    env: list[EnvVarDecl]
    containers: list[str] = field(default_factory=list)
    virtual: bool = False
    docs: str = ""
    images: list[ImageRef] = field(default_factory=list)
    sources: SourcesBlock | None = None
    depends_on: DependsOn = field(default_factory=DependsOn)
    exports: list[ExportRef] = field(default_factory=list)
    hook: str | None = None
    # Slices of the legacy bootstrapper/service-configs.yml structure, owned
    # by this manifest. sc_synthesizer.synthesize_legacy() concatenates these
    # across manifests to produce the dict the bootstrapper used to load from
    # the YAML file. Loaded as opaque mappings; the synthesizer interprets
    # the shape (which mirrors service-configs.yml's `source_configurable:`,
    # `adaptive_services:`, and `service_dependencies:` blocks respectively).
    runtime_sc: dict = field(default_factory=dict)
    runtime_adaptive: dict = field(default_factory=dict)
    runtime_deps: dict = field(default_factory=dict)
    # Globals-only. Equivalent to the legacy `dependencies:` block.
    runtime_dependency_tiers: dict = field(default_factory=dict)
    source_path: Path | None = None


# ────────────────────────────────────────────────────────────────────────────
# Errors
# ────────────────────────────────────────────────────────────────────────────


class ManifestLoadError(Exception):
    """Raised when one or more service.yml files fail to load or validate.

    The message lists every failure encountered in a single pass so the user
    can fix them all without playing whack-a-mole.
    """


# ────────────────────────────────────────────────────────────────────────────
# Schema loading (cached)
# ────────────────────────────────────────────────────────────────────────────


_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "service.schema.json"
_validator_singleton: Draft202012Validator | None = None


def _get_validator() -> Draft202012Validator:
    global _validator_singleton
    if _validator_singleton is None:
        schema = json.loads(_SCHEMA_PATH.read_text())
        _validator_singleton = Draft202012Validator(schema)
    return _validator_singleton


# ────────────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────────────


def load_manifests(services_root: Path) -> list[Manifest]:
    """Discover, parse, and validate every manifest under services_root.

    Each immediate subfolder of services_root (skipping ones whose name starts
    with `_` or `.`) must contain a `service.yml`. Returns manifests sorted
    alphabetically by folder name for deterministic ordering.

    Raises ManifestLoadError with an aggregated message if any manifest fails.
    """

    services_root = Path(services_root)
    if not services_root.is_dir():
        return []

    errors: list[str] = []
    manifests: list[Manifest] = []
    candidates = sorted(p for p in services_root.iterdir() if _is_service_dir(p))

    for service_dir in candidates:
        try:
            manifests.append(_load_one(service_dir))
        except _PerManifestError as e:
            errors.append(str(e))

    if errors:
        raise ManifestLoadError(
            "Failed to load one or more service manifests:\n  - "
            + "\n  - ".join(errors)
        )
    return manifests


# ────────────────────────────────────────────────────────────────────────────
# Internals
# ────────────────────────────────────────────────────────────────────────────


class _PerManifestError(Exception):
    """Internal exception type accumulated per-file then surfaced once."""


def _is_service_dir(path: Path) -> bool:
    return path.is_dir() and not path.name.startswith(("_", "."))


def _load_one(service_dir: Path) -> Manifest:
    manifest_path = service_dir / "service.yml"
    if not manifest_path.is_file():
        raise _PerManifestError(
            f"services/{service_dir.name}/service.yml is missing"
        )

    try:
        raw = yaml.safe_load(manifest_path.read_text())
    except yaml.YAMLError as e:
        raise _PerManifestError(
            f"services/{service_dir.name}/service.yml: invalid YAML — {e}"
        ) from e

    if not isinstance(raw, dict):
        raise _PerManifestError(
            f"services/{service_dir.name}/service.yml: top-level must be a mapping, got {type(raw).__name__}"
        )

    # JSON-Schema validation collects every error in one pass.
    schema_errors = sorted(
        _get_validator().iter_errors(raw),
        key=lambda e: list(e.absolute_path),
    )
    if schema_errors:
        details = "; ".join(_format_jsonschema_error(e) for e in schema_errors)
        raise _PerManifestError(
            f"services/{service_dir.name}/service.yml: schema violation(s): {details}"
        )

    # Cross-field sanity (things JSON Schema can't express ergonomically).
    if raw["name"] != service_dir.name:
        raise _PerManifestError(
            f"services/{service_dir.name}/service.yml: manifest.name='{raw['name']}' "
            f"does not match folder name '{service_dir.name}'"
        )

    container_set = set(raw.get("containers", []))
    for img in raw.get("images") or []:
        if img["container"] not in container_set:
            raise _PerManifestError(
                f"services/{service_dir.name}/service.yml: images[].container='{img['container']}' "
                f"is not listed in containers={sorted(container_set)}"
            )

    sources = raw.get("sources")
    if sources is not None:
        option_ids = {opt["id"] for opt in sources["options"]}
        if sources["default"] not in option_ids:
            raise _PerManifestError(
                f"services/{service_dir.name}/service.yml: sources.default='{sources['default']}' "
                f"is not one of options[].id={sorted(option_ids)}"
            )

    return _to_dataclass(raw, manifest_path)


def _to_dataclass(raw: dict[str, Any], source_path: Path) -> Manifest:
    env = [
        EnvVarDecl(
            name=e["name"],
            default=e.get("default", ""),
            description=e.get("description", ""),
            auto_managed=bool(e.get("auto_managed", False)),
            secret=bool(e.get("secret", False)),
        )
        for e in raw.get("env", [])
    ]

    images = [
        ImageRef(
            var=i["var"],
            default=i["default"],
            container=i["container"],
            notes=i.get("notes", ""),
        )
        for i in raw.get("images") or []
    ]

    sources_raw = raw.get("sources")
    sources_block: SourcesBlock | None = None
    if sources_raw is not None:
        sources_block = SourcesBlock(
            var=sources_raw["var"],
            default=sources_raw["default"],
            options=[
                SourceOption(
                    id=opt["id"],
                    label=opt["label"],
                    effects=dict(opt.get("effects", {})),
                    requires=list(opt.get("requires", [])),
                )
                for opt in sources_raw["options"]
            ],
        )

    deps_raw = raw.get("depends_on") or {}
    depends_on = DependsOn(
        required=list(deps_raw.get("required", [])),
        optional=list(deps_raw.get("optional", [])),
    )

    exports = [
        ExportRef(name=x["name"], consumers=list(x["consumers"]))
        for x in raw.get("exports") or []
    ]

    return Manifest(
        name=raw["name"],
        label=raw["label"],
        category=raw["category"],
        docs=raw.get("docs", ""),
        containers=list(raw.get("containers", [])),
        virtual=bool(raw.get("virtual", False)),
        env=env,
        images=images,
        sources=sources_block,
        depends_on=depends_on,
        exports=exports,
        hook=raw.get("hook"),
        runtime_sc=dict(raw.get("runtime_sc") or {}),
        runtime_adaptive=dict(raw.get("runtime_adaptive") or {}),
        runtime_deps=dict(raw.get("runtime_deps") or {}),
        runtime_dependency_tiers=dict(raw.get("runtime_dependency_tiers") or {}),
        source_path=source_path,
    )


def _format_jsonschema_error(err: JsonSchemaError) -> str:
    """Compact one-line summary of a jsonschema error."""
    path = "/".join(str(p) for p in err.absolute_path) or "<root>"
    return f"{path}: {err.message}"
