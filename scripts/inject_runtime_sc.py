#!/usr/bin/env python3
"""One-shot migration: take bootstrapper/service-configs.yml and split its
per-service slices into the corresponding services/<name>/service.yml
manifests under a new `runtime_sc:` field.

After this script runs, every piece of data in service-configs.yml has a
home in some manifest. The sc_synthesizer will reassemble the legacy dict
from these slices.

Run once, then delete service-configs.yml.
"""
from __future__ import annotations
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
SC_FILE = ROOT / "bootstrapper" / "service-configs.yml"
SERVICES_DIR = ROOT / "services"

# Map: service-configs.yml top-level key → manifest folder name
SC_TO_MANIFEST = {
    # supabase family
    "supabase-db": "supabase", "supabase-db-init": "supabase", "supabase-meta": "supabase",
    "supabase-storage": "supabase", "supabase-auth": "supabase", "supabase-api": "supabase",
    "supabase-realtime": "supabase", "supabase-studio": "supabase",
    # weaviate family
    "weaviate": "weaviate", "weaviate-init": "weaviate", "multi2vec-clip": "weaviate",
    # comfyui family
    "comfyui": "comfyui", "comfyui-init": "comfyui",
    # n8n family
    "n8n": "n8n", "n8n-init": "n8n",
    # openclaw family
    "openclaw": "openclaw", "openclaw-init": "openclaw",
    # hermes family
    "hermes": "hermes", "hermes-init": "hermes",
    # ollama family
    "llm_provider": "ollama", "ollama-pull": "ollama",
    # minio family
    "minio": "minio", "minio-init": "minio",
    # cloud providers
    "cloud_openai": "cloud-providers", "cloud_anthropic": "cloud-providers",
    "cloud_openrouter": "cloud-providers",
    # tts/stt
    "stt_provider": "parakeet", "tts_provider": "tts-provider",
    "doc_processor": "docling",
    # singletons
    "litellm": "litellm", "redis": "redis", "neo4j-graph-db": "neo4j",
    "kong-api-gateway": "kong", "searxng": "searxng", "open-web-ui": "open-webui",
    "local-deep-researcher": "local-deep-researcher",
}

# adaptive_services → owning manifest
ADAPTIVE_TO_MANIFEST = {
    "ollama-pull": "ollama",
    "comfyui-init": "comfyui",
    "backend": "backend",
    "weaviate-init": "weaviate",
    "hermes-init": "hermes",
    "hermes": "hermes",
    "n8n": "n8n",
    "jupyterhub": "jupyterhub",
}

# service_dependencies → owning manifest
DEPS_TO_MANIFEST = {
    "n8n": "n8n", "n8n-worker": "n8n",
    "backend": "backend",
    "open-web-ui": "open-webui",
    "local-deep-researcher": "local-deep-researcher",
    "minio": "minio",
    "jupyterhub": "jupyterhub",
    "openclaw-gateway": "openclaw",
    "hermes": "hermes",
}


def main() -> int:
    sc = yaml.safe_load(SC_FILE.read_text())

    # Group every payload by target manifest
    per_manifest_sc: dict[str, dict] = {}
    per_manifest_adaptive: dict[str, dict] = {}
    per_manifest_deps: dict[str, dict] = {}

    for sc_key, payload in sc.get("source_configurable", {}).items():
        target = SC_TO_MANIFEST.get(sc_key)
        if not target:
            print(f"  WARN: source_configurable key '{sc_key}' has no manifest target", file=sys.stderr)
            continue
        per_manifest_sc.setdefault(target, {})[sc_key] = payload

    for adapt_key, payload in sc.get("adaptive_services", {}).items():
        target = ADAPTIVE_TO_MANIFEST.get(adapt_key)
        if not target:
            print(f"  WARN: adaptive_services key '{adapt_key}' has no manifest target", file=sys.stderr)
            continue
        per_manifest_adaptive.setdefault(target, {})[adapt_key] = payload

    for dep_key, payload in sc.get("service_dependencies", {}).items():
        target = DEPS_TO_MANIFEST.get(dep_key)
        if not target:
            print(f"  WARN: service_dependencies key '{dep_key}' has no manifest target", file=sys.stderr)
            continue
        per_manifest_deps.setdefault(target, {})[dep_key] = payload

    # Append blocks to each manifest
    touched = []
    for mnf_name in sorted(set(per_manifest_sc) | set(per_manifest_adaptive) | set(per_manifest_deps)):
        manifest_path = SERVICES_DIR / mnf_name / "service.yml"
        if not manifest_path.is_file():
            print(f"  WARN: manifest {manifest_path} missing", file=sys.stderr)
            continue

        existing = yaml.safe_load(manifest_path.read_text()) or {}
        if "runtime_sc" in existing or "runtime_adaptive" in existing or "runtime_deps" in existing:
            print(f"  SKIP: {mnf_name} already has runtime_* blocks", file=sys.stderr)
            continue

        # Append in a stable order
        blocks_to_add = []
        if mnf_name in per_manifest_sc:
            blocks_to_add.append(("runtime_sc", per_manifest_sc[mnf_name]))
        if mnf_name in per_manifest_adaptive:
            blocks_to_add.append(("runtime_adaptive", per_manifest_adaptive[mnf_name]))
        if mnf_name in per_manifest_deps:
            blocks_to_add.append(("runtime_deps", per_manifest_deps[mnf_name]))

        # Append YAML serialised block, preserving the file's hand-written content
        with manifest_path.open("a", encoding="utf-8") as f:
            f.write("\n# ─────────────────────────────────────────────────────────\n")
            f.write("# Bootstrapper runtime data (migrated from the legacy\n")
            f.write("# bootstrapper/service-configs.yml). Slices owned by this\n")
            f.write("# manifest. Synthesized into the runtime dict by\n")
            f.write("# bootstrapper/services/sc_synthesizer.py.\n")
            f.write("# ─────────────────────────────────────────────────────────\n")
            for key, data in blocks_to_add:
                f.write(yaml.safe_dump({key: data}, sort_keys=False, default_flow_style=False))
                f.write("\n")
        touched.append((mnf_name, [k for k, _ in blocks_to_add]))

    # Globals manifest gets the `dependencies` tier block
    globals_path = SERVICES_DIR / "globals" / "service.yml"
    deps_tiers = sc.get("dependencies", {})
    if deps_tiers and globals_path.is_file():
        existing = yaml.safe_load(globals_path.read_text()) or {}
        if "runtime_dependency_tiers" not in existing:
            with globals_path.open("a", encoding="utf-8") as f:
                f.write("\n# Bootstrapper dependency tiers (data → init → core → app).\n")
                f.write("# Migrated from bootstrapper/service-configs.yml's `dependencies:` block.\n")
                f.write(yaml.safe_dump({"runtime_dependency_tiers": deps_tiers},
                                      sort_keys=False, default_flow_style=False))
            touched.append(("globals", ["runtime_dependency_tiers"]))

    print(f"\nInjected runtime data into {len(touched)} manifests:")
    for name, blocks in touched:
        print(f"  - {name}: {blocks}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
