#!/usr/bin/env python3
"""Check docker-compose hard dependencies against SOURCE-replaceable services.

Compose `depends_on` is only safe for services that must always be started as
containers. SOURCE-replaceable services can be `localhost`, `external`, or
`disabled`, so consumers should reference them through endpoint environment
variables and runtime readiness/feature checks instead of static `depends_on`.

Zero-arg checker. Invoke as ``python scripts/check-compose-source-deps.py``.

Exit codes:
    0  — all PASS
    1  — at least one FAIL line printed
    2  — internal failure (PyYAML missing, or docker compose config
         errored with stderr surfaced)
"""
from __future__ import annotations

from pathlib import Path
import sys

try:
    import yaml
except ImportError:  # pragma: no cover - developer environment guard
    print("FAIL import: PyYAML is required to parse docker-compose.yml", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "docker-compose.yml"

# Edges where the dependency target is SOURCE-replaceable and should not be a
# hard compose startup prerequisite. Keep this list intentionally explicit so
# changes are reviewed service-by-service instead of hidden in broad heuristics.
FORBIDDEN_OPTIONAL_DEPENDS_ON = {
    ("n8n", "weaviate"),
    ("n8n-worker", "weaviate"),
    ("jupyterhub", "weaviate"),
    ("jupyterhub", "ollama"),
    ("jupyterhub", "neo4j-graph-db"),
    ("weaviate", "multi2vec-clip"),
}

# Edges that are expected after the SOURCE-safe dependency cleanup. These are
# guardrails for the normal launch flow: core services should still wait for the
# infrastructure they genuinely require.
REQUIRED_DEPENDS_ON = {
    ("n8n", "supabase-db-init"),
    ("n8n", "redis"),
    ("n8n-worker", "supabase-db-init"),
    ("n8n-worker", "redis"),
    ("jupyterhub", "supabase-db-init"),
    ("jupyterhub", "redis"),
    ("weaviate", "supabase-db"),
    ("weaviate", "weaviate-init"),
    # LiteLLM is mandatory and not source-replaceable. Every LLM consumer
    # hard-depends on it. Ollama remains source-replaceable (see FORBIDDEN
    # above) — consumers reach Ollama through LiteLLM.
    ("litellm", "litellm-init"),
    ("litellm", "supabase-db"),
    ("litellm", "redis"),
    ("open-web-ui", "litellm"),
    ("backend", "litellm"),
    ("n8n", "litellm"),
    ("n8n-worker", "litellm"),
    ("n8n-init", "litellm"),
    ("jupyterhub", "litellm"),
    ("local-deep-researcher", "litellm"),
    ("openclaw-gateway", "litellm"),
    ("hermes-init", "litellm"),
    ("hermes", "litellm"),
    ("weaviate-init", "litellm"),
    ("weaviate", "litellm"),
}


def load_compose() -> dict:
    """Load the merged compose shape.

    The top-level docker-compose.yml uses `include:` to pull in per-service
    fragments under services/<name>/compose.yml. yaml.safe_load on the raw
    file would only see the empty `services:` block at the top, so we
    delegate to `docker compose config` which renders the merged shape.

    Falls back to `.env.example` when `.env` is missing (matching CI's
    `cp .env.example .env` step), and only falls back to the raw parse
    when the docker CLI itself isn't available — a `docker compose config`
    that exits non-zero is an audit-script failure, not a recoverable
    condition. Silently returning the wrapper's empty `services:` block
    would emit spurious `missing required dependency` lines for every
    edge in REQUIRED_DEPENDS_ON.
    """
    import subprocess  # local import — keeps script importable without docker

    env_file = ROOT / ".env"
    env_fallback = ROOT / ".env.example"
    args = ["docker", "compose"]
    if env_file.is_file():
        args.extend(["--env-file", str(env_file)])
    elif env_fallback.is_file():
        args.extend(["--env-file", str(env_fallback)])
    args.extend(["-f", str(COMPOSE_FILE), "config"])
    try:
        result = subprocess.run(args, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        # docker not on PATH — fall through to the raw parse so the script
        # is still importable / linter-runnable on machines without docker.
        with COMPOSE_FILE.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    if result.returncode != 0:
        # docker is present but `compose config` failed — surface the
        # stderr instead of producing wrong-answer output.
        print(
            "FAIL load_compose: `docker compose config` exited "
            f"{result.returncode}",
            file=sys.stderr,
        )
        if result.stderr.strip():
            print(result.stderr.rstrip(), file=sys.stderr)
        sys.exit(2)
    return yaml.safe_load(result.stdout) or {}


def dependency_names(service_def: dict) -> set[str]:
    depends_on = service_def.get("depends_on") or {}
    if isinstance(depends_on, dict):
        return set(depends_on)
    if isinstance(depends_on, list):
        return set(depends_on)
    return set()


def main() -> int:
    compose = load_compose()
    services = compose.get("services") or {}
    edges = {
        (service_name, dependency)
        for service_name, service_def in services.items()
        for dependency in dependency_names(service_def)
    }

    forbidden = sorted(FORBIDDEN_OPTIONAL_DEPENDS_ON & edges)
    missing_required = sorted(REQUIRED_DEPENDS_ON - edges)

    failed = False
    if forbidden:
        failed = True
        print("FAIL optional_provider_depends_on")
        for service, dependency in forbidden:
            print(f"  {service} must not hard depend_on SOURCE-replaceable {dependency}")
    else:
        print("PASS optional_provider_depends_on")

    if missing_required:
        failed = True
        print("FAIL required_core_depends_on")
        for service, dependency in missing_required:
            print(f"  {service} is missing required core dependency {dependency}")
    else:
        print("PASS required_core_depends_on")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
