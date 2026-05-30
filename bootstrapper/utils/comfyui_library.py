"""ComfyUI model catalog — scraper, cache, and types.

Mirrors `bootstrapper/utils/ollama_library.py`'s role for the ComfyUI
side. Wizard build-time entrypoint is `list_catalog()` (added later).
"""
from __future__ import annotations

from dataclasses import dataclass


# ── Category enum ──────────────────────────────────────────────────────
# Closed enum mapping to in-container target directories.
# Adding a category here means:
#   1. Update CATEGORY_TARGET_DIR (this file).
#   2. Add a `mkdir -p` line in services/comfyui/init/scripts/download_models.sh.
#   3. Place it in a display group in CATEGORY_DISPLAY_GROUPS below.
CATEGORY_TARGET_DIR: dict[str, str] = {
    "checkpoint":   "checkpoints",
    "vae":          "vae",
    "lora":         "loras",
    "controlnet":   "controlnet",
    "ipadapter":    "ipadapter",
    "instantid":    "instantid",
    "upscaler":     "upscale_models",
    "embedding":    "embeddings",
    "clip":         "clip",
    "animatediff":  "animatediff_models",
    "motion_lora":  "animatediff_motion_lora",
    "video_model":  "checkpoints",  # HunyuanVideo / CogVideoX per upstream
    "voice_model":  "voice",
    "audio_model":  "audio",
    "mesh_model":   "mesh_models",
}

VALID_CATEGORIES = frozenset(CATEGORY_TARGET_DIR.keys())

# Display groups drive the wizard's filter chips.
CATEGORY_DISPLAY_GROUPS: dict[str, frozenset[str]] = {
    "All":         VALID_CATEGORIES,
    "Image":       frozenset({"checkpoint", "vae", "lora", "upscaler",
                              "embedding", "clip"}),
    "Image-edit":  frozenset({"controlnet", "ipadapter", "instantid"}),
    "Video":       frozenset({"animatediff", "motion_lora", "video_model"}),
    "Audio":       frozenset({"voice_model", "audio_model"}),
    "3D":          frozenset({"mesh_model"}),
}


@dataclass(frozen=True)
class ComfyUILibraryEntry:
    """One catalog row.

    `pulled` is computed at wizard build time from a filesystem scan;
    every other field is static catalog metadata.
    """
    name: str
    family: str
    category: str
    size_gb: float
    url: str
    sha256: str | None
    target_dir: str
    min_vram_gb: float | None
    cpu_supported: bool
    requires_custom_node: tuple[str, ...]
    popularity: int
    source: str  # "huggingface" | "civitai" | "curated" | "fallback" | "custom"
    pulled: bool
    cloud_only: bool = False


# ── HF + civitai response parsers ──────────────────────────────────────
# These transform raw API JSON into ComfyUILibraryEntry instances.
# Live HTTP calls land in Task 5; parsers are pure-functional +
# fixture-tested here.

_HF_RESOLVE_BASE = "https://huggingface.co"

# HF tags → custom_nodes required. Conservative list — only add when verified
# against the upstream node's README.
_HF_TAG_TO_CUSTOM_NODE: dict[str, str] = {
    "gguf":           "ComfyUI-GGUF",
    "animatediff":    "ComfyUI-AnimateDiff-Evolved",
    "image-to-3d":    "ComfyUI-3D-Pack",
    "text-to-3d":     "ComfyUI-3D-Pack",
    "instantid":      "ComfyUI_InstantID",
    "ip-adapter":     "ComfyUI_IPAdapter_plus",
}

_VALID_MODEL_EXTENSIONS = (".safetensors", ".ckpt", ".bin", ".gguf", ".pt")


def _pick_primary_file(siblings: list[dict]) -> dict | None:
    """Pick the largest compatible model file from a HF repo's siblings array.

    Returns None if no compatible file. Compatible = ends with one of
    _VALID_MODEL_EXTENSIONS. When multiple, prefer largest by size; ties
    broken by shortest filename (proxy for "base" vs "variant").
    """
    candidates = [
        s for s in siblings
        if isinstance(s, dict)
        and isinstance(s.get("rfilename"), str)
        and s["rfilename"].lower().endswith(_VALID_MODEL_EXTENSIONS)
    ]
    if not candidates:
        return None
    candidates.sort(
        key=lambda s: (s.get("size", 0), -len(s.get("rfilename", ""))),
        reverse=True,
    )
    return candidates[0]


def _family_from_id(model_id: str) -> str:
    """Heuristic family label: last segment of the HF model id, with
    common suffixes trimmed."""
    name = model_id.rsplit("/", 1)[-1]
    for suffix in ("-v1.0", "-base", "-dev", "-schnell", "-pruned"):
        if name.lower().endswith(suffix):
            name = name[: -len(suffix)]
    return name.replace("_", "-").title()


def _custom_nodes_from_tags(tags: list[str]) -> tuple[str, ...]:
    nodes: list[str] = []
    for t in tags:
        node = _HF_TAG_TO_CUSTOM_NODE.get(str(t).lower())
        if node and node not in nodes:
            nodes.append(node)
    return tuple(nodes)


def _parse_hf_response(
    raw: list[dict],
    category: str,
) -> list[ComfyUILibraryEntry]:
    """Convert a single-category HF /api/models response into entries.

    Raises ValueError for unknown category.
    """
    if category not in VALID_CATEGORIES:
        raise ValueError(f"unknown category: {category}")
    target_dir = CATEGORY_TARGET_DIR[category]
    out: list[ComfyUILibraryEntry] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        siblings = item.get("siblings") or []
        if not isinstance(siblings, list):
            continue
        primary = _pick_primary_file(siblings)
        if primary is None:
            continue
        model_id = item.get("id") or item.get("modelId")
        if not model_id:
            continue
        rfilename = primary["rfilename"]
        url = f"{_HF_RESOLVE_BASE}/{model_id}/resolve/main/{rfilename}"
        size_bytes = primary.get("size") or 0
        size_gb = round(size_bytes / (1024 ** 3), 2) if size_bytes else 0.0
        tags = item.get("tags") or []
        out.append(ComfyUILibraryEntry(
            name=model_id.replace("/", "--"),
            family=_family_from_id(model_id),
            category=category,
            size_gb=size_gb,
            url=url,
            sha256=None,
            target_dir=target_dir,
            min_vram_gb=None,
            cpu_supported=("cpu" in tags or category in ("vae", "embedding", "clip")),
            requires_custom_node=_custom_nodes_from_tags(tags),
            popularity=int(item.get("downloads") or 0),
            source="huggingface",
            pulled=False,
        ))
    return out


def _parse_civitai_response(
    raw: dict | list,
    category: str,
) -> list[ComfyUILibraryEntry]:
    """Convert civitai /api/v1/models response into entries.

    Civitai wraps results in {"items": [...]}. Each item has a
    modelVersions[].files[] array; pick the primary file (primary=True
    or first .safetensors).
    """
    if category not in VALID_CATEGORIES:
        raise ValueError(f"unknown category: {category}")
    items = raw.get("items", []) if isinstance(raw, dict) else raw
    target_dir = CATEGORY_TARGET_DIR[category]
    out: list[ComfyUILibraryEntry] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        versions = item.get("modelVersions") or []
        if not versions:
            continue
        primary_version = versions[0]
        files = primary_version.get("files") or []
        primary_file = next(
            (f for f in files if isinstance(f, dict) and f.get("primary") is True),
            files[0] if files else None,
        )
        if not isinstance(primary_file, dict):
            continue
        url = primary_file.get("downloadUrl")
        if not url:
            continue
        size_kb = primary_file.get("sizeKB") or 0
        size_gb = round(size_kb / (1024 * 1024), 2) if size_kb else 0.0
        stats = item.get("stats") or {}
        out.append(ComfyUILibraryEntry(
            name=f"civitai-{item.get('id', 'unknown')}",
            family=str(item.get("name", "Unknown"))[:40],
            category=category,
            size_gb=size_gb,
            url=url,
            sha256=(primary_file.get("hashes") or {}).get("SHA256"),
            target_dir=target_dir,
            min_vram_gb=None,
            cpu_supported=False,
            requires_custom_node=(),
            popularity=int(stats.get("downloadCount") or 0),
            source="civitai",
            pulled=False,
        ))
    return out
