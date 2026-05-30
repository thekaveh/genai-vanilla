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
