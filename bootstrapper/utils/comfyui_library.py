"""ComfyUI model catalog — scrapers, parsers, and types.

Mirrors `bootstrapper/utils/llm_catalog.py`'s role for the ComfyUI side:
a pure-functional, side-effect-free catalog module imported BOTH by the
wizard (host-side, build time) AND by the comfyui-catalog-init container
(via the /catalog bind mount) to seed ``public.comfyui_models``.

There is no host-side file cache — the wizard runs once per invocation
and assembles the catalog live, then comfyui-catalog-init re-assembles
it at container start and UPSERTs into Postgres. The DB row is the
single source of truth for downstream consumers (comfyui-init,
the backend's /comfyui/db/models routes, the Open WebUI tool,
the n8n workflow).
"""
from __future__ import annotations

import json as _json
import sys as _sys
from dataclasses import dataclass
from pathlib import Path as _Path

import requests as _requests
import yaml as _yaml


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
    notes: str | None = None  # Optional one-line subtitle for wizard rendering (T15).


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
        if not isinstance(versions, list):
            continue
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


# ── Curated allowlist ──────────────────────────────────────────────────
# Hand-picked entries for categories where HF tag search is noisy.
# Add to this list with PRs. Sizes / popularity approximate; accuracy
# improves over time via community contributions.

_CURATED_ENTRIES: tuple[dict, ...] = (
    # ── VAE ────────────────────────────────────────────────────────────
    {
        "name": "vae-ft-mse-840000-ema-pruned",
        "family": "SD1.5", "category": "vae", "size_gb": 0.32,
        "url": "https://huggingface.co/stabilityai/sd-vae-ft-mse-original/resolve/main/vae-ft-mse-840000-ema-pruned.safetensors",
        "min_vram_gb": None, "cpu_supported": True,
        "requires_custom_node": (), "popularity": 80,
    },
    {
        "name": "sdxl-vae",
        "family": "SDXL", "category": "vae", "size_gb": 0.32,
        "url": "https://huggingface.co/stabilityai/sdxl-vae/resolve/main/sdxl_vae.safetensors",
        "min_vram_gb": None, "cpu_supported": True,
        "requires_custom_node": (), "popularity": 85,
    },
    # ── ipadapter ──────────────────────────────────────────────────────
    {
        "name": "ip-adapter-plus_sdxl_vit-h",
        "family": "SDXL", "category": "ipadapter", "size_gb": 0.85,
        "url": "https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors",
        "min_vram_gb": 6.0, "cpu_supported": False,
        "requires_custom_node": ("ComfyUI_IPAdapter_plus",), "popularity": 70,
    },
    {
        "name": "ip-adapter-faceid-plusv2_sdxl",
        "family": "SDXL", "category": "ipadapter", "size_gb": 0.50,
        "url": "https://huggingface.co/h94/IP-Adapter-FaceID/resolve/main/ip-adapter-faceid-plusv2_sdxl.bin",
        "min_vram_gb": 6.0, "cpu_supported": False,
        "requires_custom_node": ("ComfyUI_IPAdapter_plus",), "popularity": 65,
    },
    # ── instantid ──────────────────────────────────────────────────────
    {
        "name": "instantid-ip-adapter",
        "family": "InstantID", "category": "instantid", "size_gb": 1.20,
        "url": "https://huggingface.co/InstantX/InstantID/resolve/main/ip-adapter.bin",
        "min_vram_gb": 8.0, "cpu_supported": False,
        "requires_custom_node": ("ComfyUI_InstantID",), "popularity": 60,
    },
    # ── upscaler ───────────────────────────────────────────────────────
    {
        "name": "real-esrgan-x4plus",
        "family": "Real-ESRGAN", "category": "upscaler", "size_gb": 0.07,
        "url": "https://huggingface.co/lllyasviel/Annotators/resolve/main/RealESRGAN_x4plus.pth",
        "min_vram_gb": None, "cpu_supported": True,
        "requires_custom_node": (), "popularity": 90,
    },
    {
        "name": "4x-ultrasharp",
        "family": "4x-UltraSharp", "category": "upscaler", "size_gb": 0.07,
        "url": "https://huggingface.co/lokCX/4x-Ultrasharp/resolve/main/4x-UltraSharp.pth",
        "min_vram_gb": None, "cpu_supported": True,
        "requires_custom_node": (), "popularity": 88,
    },
    # ── embedding ──────────────────────────────────────────────────────
    {
        "name": "easynegative",
        "family": "EasyNegative", "category": "embedding", "size_gb": 0.0,
        "url": "https://huggingface.co/embed/EasyNegative/resolve/main/EasyNegative.safetensors",
        "min_vram_gb": None, "cpu_supported": True,
        "requires_custom_node": (), "popularity": 85,
    },
    # ── clip ───────────────────────────────────────────────────────────
    {
        "name": "clip-vit-large-patch14",
        "family": "CLIP", "category": "clip", "size_gb": 0.60,
        "url": "https://huggingface.co/openai/clip-vit-large-patch14/resolve/main/pytorch_model.bin",
        "min_vram_gb": 2.0, "cpu_supported": True,
        "requires_custom_node": (), "popularity": 75,
    },
    # ── motion_lora ────────────────────────────────────────────────────
    # Real motion LoRA (zoom-in camera move, ~28 MB); the full motion module
    # v3_sd15_mm.ckpt belongs in animatediff_models/ and is covered by the
    # fallback entry animatediff-mm-sd15-v3 (category: animatediff).
    {
        "name": "animatediff-camera-zoomin-lora",
        "family": "AnimateDiff", "category": "motion_lora", "size_gb": 0.028,
        "url": "https://huggingface.co/guoyww/animatediff-motion-lora-zoom-in/resolve/main/diffusion_pytorch_model.safetensors",
        "min_vram_gb": 6.0, "cpu_supported": False,
        "requires_custom_node": ("ComfyUI-AnimateDiff-Evolved",), "popularity": 65,
    },
    # ── audio_model ────────────────────────────────────────────────────
    {
        "name": "audioldm-text-to-audio",
        "family": "AudioLDM", "category": "audio_model", "size_gb": 1.50,
        "url": "https://huggingface.co/cvssp/audioldm/resolve/main/pytorch_model.bin",
        "min_vram_gb": 6.0, "cpu_supported": False,
        # Audio nodes are an open ecosystem with no canonical wrapper today;
        # surface the model but leave node selection to the user (warn-only).
        "requires_custom_node": (), "popularity": 50,
    },
)


def _dict_to_entry(d: dict, source: str) -> ComfyUILibraryEntry:
    """Translate a dict (curated, fallback, cache, or sidecar/custom) to a
    ComfyUILibraryEntry.

    Coerces `requires_custom_node` to tuple so callers can pass either
    JSON-list (fallback/cache/custom) or native tuple (curated).
    Defaults missing `size_gb` to 0.0 (sidecar makes this optional;
    curated/fallback always supply it). Falls back to CATEGORY_TARGET_DIR
    for `target_dir` when absent. Sets `source` and `pulled=False`
    (pulled is computed at wizard time, never from input).
    """
    cat = d["category"]
    return ComfyUILibraryEntry(
        name=d["name"],
        family=d.get("family", d["name"]),
        category=cat,
        size_gb=d.get("size_gb") or 0.0,
        url=d["url"],
        sha256=d.get("sha256"),
        target_dir=d.get("target_dir", CATEGORY_TARGET_DIR[cat]),
        min_vram_gb=d.get("min_vram_gb"),
        cpu_supported=d.get("cpu_supported", True),
        requires_custom_node=tuple(d.get("requires_custom_node") or ()),
        popularity=d.get("popularity", 0),
        source=source,
        pulled=False,
        cloud_only=bool(d.get("cloud_only", False)),
        notes=d.get("notes"),
    )


def list_curated() -> list[ComfyUILibraryEntry]:
    """Return curated entries."""
    return [_dict_to_entry(d, "curated") for d in _CURATED_ENTRIES]


# ── Bundled fallback snapshot ──────────────────────────────────────────

_FALLBACK_FILE = _Path(__file__).parent / "data" / "comfyui_catalog_fallback.json"


def list_fallback() -> list[ComfyUILibraryEntry]:
    """Load the bundled fallback snapshot. Used only when both APIs are
    unreachable AND no cached catalog exists.
    """
    if not _FALLBACK_FILE.is_file():
        return []
    raw = _json.loads(_FALLBACK_FILE.read_text())
    return [_dict_to_entry(d, "fallback") for d in raw.get("entries", [])]


# ── HTTP scraping + cache ──────────────────────────────────────────────

_HF_API_BASE = "https://huggingface.co/api/models"
_CIVITAI_API_BASE = "https://civitai.com/api/v1/models"
_HTTP_TIMEOUT_S = 15

# Per-category HF filter sets. Each entry → one API call; results merged.
# Maintain this dict to evolve catalog coverage.
_HF_FILTERS: dict[str, list[dict]] = {
    "checkpoint": [
        {"pipeline_tag": "text-to-image", "library": "diffusers",
         "sort": "downloads", "limit": 30},
    ],
    "lora": [
        {"filter": "lora", "pipeline_tag": "text-to-image",
         "sort": "downloads", "limit": 20},
    ],
    # HF expects `library:` for ControlNet (not `filter:`); per HF API semantics.
    "controlnet": [
        {"library": "controlnet", "sort": "downloads", "limit": 20},
    ],
    "video_model": [
        {"pipeline_tag": "text-to-video", "sort": "downloads", "limit": 15},
    ],
    "voice_model": [
        {"pipeline_tag": "text-to-speech", "sort": "downloads", "limit": 15},
    ],
    "mesh_model": [
        {"filter": "image-to-3d", "sort": "downloads", "limit": 15},
        {"filter": "text-to-3d", "sort": "downloads", "limit": 10},
    ],
    "animatediff": [
        {"filter": "animatediff", "sort": "downloads", "limit": 10},
    ],
}


def list_huggingface_models() -> list[ComfyUILibraryEntry]:
    """Hit the HF API per _HF_FILTERS; parse + merge.

    Always passes ``full=true`` so each model card carries its
    ``siblings[]`` array — without it, HF's /api/models returns the
    lightweight listing shape and ``_pick_primary_file`` silently
    drops every entry. See test_list_huggingface_models_requests_full_metadata.

    Raises requests.RequestException / ConnectionError on transport failure.
    """
    out: list[ComfyUILibraryEntry] = []
    for category, filters in _HF_FILTERS.items():
        for params in filters:
            full_params = {**params, "full": "true"}
            resp = _requests.get(_HF_API_BASE, params=full_params, timeout=_HTTP_TIMEOUT_S)
            resp.raise_for_status()
            out.extend(_parse_hf_response(resp.json(), category=category))
    return out


def list_civitai_loras() -> list[ComfyUILibraryEntry]:
    """Anonymous civitai API for LoRAs.

    We don't fetch checkpoints from civitai — too noisy; HF is the source
    of truth for those.
    """
    out: list[ComfyUILibraryEntry] = []
    for category, ctype in (("lora", "LORA"),):
        resp = _requests.get(
            _CIVITAI_API_BASE,
            params={"sort": "Most Downloaded", "types": ctype, "limit": 20},
            timeout=_HTTP_TIMEOUT_S,
        )
        resp.raise_for_status()
        out.extend(_parse_civitai_response(resp.json(), category=category))
    return out


# ── Merge ──────────────────────────────────────────────────────────────

def _dedupe_by_name(
    entries: list[ComfyUILibraryEntry],
) -> list[ComfyUILibraryEntry]:
    """Last-wins dedupe by name. Caller controls precedence via input order.

    Established precedence for assemble_wizard_catalog (lowest → highest):
        huggingface → civitai → fallback (if used) → curated
    So pass curated LAST when merging; the last write to the dict wins.
    """
    seen: dict[str, ComfyUILibraryEntry] = {}
    for e in entries:
        seen[e.name] = e
    return list(seen.values())


def assemble_wizard_catalog(
    force_refresh: bool = False,
) -> list[ComfyUILibraryEntry]:
    """Live-assembled, merged catalog: HF + civitai + curated
    (+ fallback if both scrapers are down).

    Called once per wizard invocation AND once per comfyui-catalog-init
    container run. NO caching — there is no host-side file cache (the
    DB row is the persistence layer; this function is the producer).
    The ``force_refresh`` parameter is accepted for API parity with
    upstream ``list_*`` helpers but is currently a no-op.

    Dedupe precedence (last wins): huggingface → civitai → fallback → curated.
    Partial failure (one scraper down) → uses whatever returned + curated.
    Total failure (both down) → loads the bundled fallback snapshot.
    """
    del force_refresh  # accepted for API parity; no cache to bypass

    hf_entries: list[ComfyUILibraryEntry] = []
    civ_entries: list[ComfyUILibraryEntry] = []
    hf_ok = True
    civ_ok = True

    try:
        hf_entries = list_huggingface_models()
    except (_requests.RequestException, ConnectionError) as exc:
        print(f"WARNING: HuggingFace catalog fetch failed: {exc}",
              file=_sys.stderr)
        hf_ok = False
    try:
        civ_entries = list_civitai_loras()
    except (_requests.RequestException, ConnectionError) as exc:
        print(f"WARNING: civitai catalog fetch failed: {exc}", file=_sys.stderr)
        civ_ok = False

    curated = list_curated()
    # Order matters — last wins.
    if not hf_ok and not civ_ok:
        # Both APIs down — supplement with bundled fallback before curated.
        print("WARNING: All catalog sources unreachable; using bundled fallback.",
              file=_sys.stderr)
        return _dedupe_by_name(
            hf_entries + civ_entries + list_fallback() + curated
        )
    return _dedupe_by_name(hf_entries + civ_entries + curated)


# ── Sidecar YAML loader ────────────────────────────────────────────────

def load_custom_models(path: str) -> list[ComfyUILibraryEntry]:
    """Parse a sidecar YAML file into entries.

    Invalid entries skipped with stderr warnings; never raises for
    malformed YAML (returns empty list). Required: name, category, url.
    Optional: family, size_gb, sha256, requires_custom_node, cpu_supported,
    min_vram_gb, notes.

    The loader uses `_dict_to_entry` so future schema changes only need
    a single edit point (same path as curated/fallback).
    """
    p = _Path(path)
    if not p.is_file():
        return []
    try:
        raw = _yaml.safe_load(p.read_text()) or {}
    except _yaml.YAMLError as exc:
        print(f"⚠️  custom-models YAML parse failed at {path}: {exc}",
              file=_sys.stderr)
        return []

    raw_models = raw.get("models") or []
    out: list[ComfyUILibraryEntry] = []
    for idx, d in enumerate(raw_models):
        if not isinstance(d, dict):
            print(f"⚠️  custom-models[{idx}] is not a mapping; skipping.",
                  file=_sys.stderr)
            continue
        name = d.get("name")
        category = d.get("category")
        url = d.get("url")
        if not name:
            print(f"⚠️  custom-models[{idx}] missing 'name'; skipping.",
                  file=_sys.stderr)
            continue
        if not url:
            print(f"⚠️  custom-models entry '{name}' missing 'url'; skipping.",
                  file=_sys.stderr)
            continue
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            print(f"⚠️  custom-models entry '{name}' has non-http(s) url; skipping.",
                  file=_sys.stderr)
            continue
        if category not in VALID_CATEGORIES:
            print(f"⚠️  custom-models entry '{name}' has unknown category "
                  f"'{category}'; skipping.", file=_sys.stderr)
            continue
        try:
            out.append(_dict_to_entry(d, source="custom"))
        except (KeyError, ValueError) as exc:
            print(f"⚠️  custom-models entry '{name}' construction failed: {exc}",
                  file=_sys.stderr)
            continue
    return out
