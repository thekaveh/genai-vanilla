"""ComfyUI model-picker wizard step.

Mirrors bootstrapper/wizard/llm_steps.py's role for ComfyUI's model
selection. Single 'ComfyUI · models' step with filter chips for the 6
display groups (All / Image / Image-edit / Video / Audio / 3D), name
search, and warn-only badges for custom-node requirements + hardware
mismatches.

Data source: `assemble_wizard_catalog()` (HF + civitai live scrape +
curated + fallback). Pulled flags computed from filesystem scan of the
comfyui-models volume. NO DB query — the wizard runs BEFORE
comfyui-catalog-init populates public.comfyui_models.
"""
from __future__ import annotations

import functools
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List

from utils.comfyui_library import (
    ComfyUILibraryEntry,
    CATEGORY_DISPLAY_GROUPS,
)
from ui.textual.widgets.prompt_panel import (
    PromptOption,
    PromptStep,
)


COMFYUI_MODELS_TITLE = "ComfyUI  ·  models"

# Filter chip tags parallel CATEGORY_DISPLAY_GROUPS (minus "All" which is
# always implicit via the [ALL] chip).
_FILTER_TAGS: tuple[str, ...] = ("Image", "Image-edit", "Video", "Audio", "3D")


@dataclass
class _ComfyUIOption:
    """Internal option row produced by _merged_comfyui_options().

    Has the same core shape as PromptOption (value, label, hint, badges)
    plus two extra fields (group, checked) used at registration time to
    seed filter chips and default_values. The tests access these via
    getattr so the real PromptOption (which lacks group/checked) remains
    unmodified.
    """
    value: str
    label: str
    hint: str
    badges: list[str]
    group: str      # display group for the filter chip system
    checked: bool   # True → pre-selected in the wizard's default_values


@functools.lru_cache(maxsize=1)
def _detect_gpu_memory_gb() -> float | None:
    """Best-effort GPU memory detection via nvidia-smi.

    Returns None on CPU-only / no nvidia-smi / errors.
    """
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, check=True, timeout=5,
        )
        values = [int(v.strip()) for v in out.stdout.splitlines() if v.strip()]
        if not values:
            return None
        return max(values) / 1024  # MiB → GiB
    except Exception:  # noqa: BLE001 — best-effort
        return None


def _scan_pulled(volume_root: Path) -> set[str]:
    """Walk the comfyui-models volume; return set of filenames present
    with non-zero size.
    """
    pulled: set[str] = set()
    if not volume_root.is_dir():
        return pulled
    for p in volume_root.rglob("*"):
        if p.is_file() and p.stat().st_size > 0:
            pulled.add(p.name)
    return pulled


def _filename_of(url: str) -> str:
    """Extract the filename from a download URL (before any query params)."""
    return url.rsplit("/", 1)[-1].split("?", 1)[0]


def _display_group_for(category: str) -> str:
    """Map a category string to its CATEGORY_DISPLAY_GROUPS group name."""
    for group, cats in CATEGORY_DISPLAY_GROUPS.items():
        if group == "All":
            continue
        if category in cats:
            return group
    return "All"


def _badges_for_entry(
    entry: ComfyUILibraryEntry,
    is_pulled: bool,
    gpu_mem_gb: float | None,
) -> list[str]:
    """Compose the badge list for one catalog entry.

    Badge order: family, category, size, [pulled], custom-node warns,
    hardware-mismatch warns. Warn-only — nothing is suppressed from
    the option list based on hardware.
    """
    out: list[str] = [
        f"[{entry.family}]",
        entry.category,
        f"{entry.size_gb:.2f}GB",
    ]
    if is_pulled:
        out.append("[pulled]")
    if entry.requires_custom_node:
        nodes = " + ".join(entry.requires_custom_node)
        out.append(f"⚠ node: {nodes}")
    if gpu_mem_gb is None and not entry.cpu_supported:
        out.append("⚠ requires GPU")
    elif (
        gpu_mem_gb is not None
        and entry.min_vram_gb is not None
        and entry.min_vram_gb > gpu_mem_gb
    ):
        out.append(f"⚠ requires {entry.min_vram_gb:.0f} GB VRAM")
    return out


def _merged_comfyui_options(
    catalog: list[ComfyUILibraryEntry],
    sidecar: list[ComfyUILibraryEntry],
    pulled_names: set[str],
    default_selected: set[str],
    gpu_mem_gb: float | None = None,
    warn: Callable[[str], None] | None = None,
) -> list[_ComfyUIOption]:
    """Build the wizard's option list.

    Args:
        catalog: from assemble_wizard_catalog()
        sidecar: from load_custom_models(); always rendered in Custom group
        pulled_names: from _scan_pulled() — filenames present on disk
        default_selected: parsed from COMFYUI_USER_MODELS env
        gpu_mem_gb: from _detect_gpu_memory_gb() — None = CPU-only / unknown
        warn: optional callback for warnings; if None, prints to stderr
    """
    # Sidecar last so sidecar wins on name collision via dict insertion-order semantics.
    by_name: dict[str, ComfyUILibraryEntry] = {
        e.name: e for e in list(catalog) + list(sidecar)
    }

    # Warn on unresolved defaults — same pattern as integration.py for Ollama.
    for n in default_selected:
        if n not in by_name:
            msg = (f"COMFYUI_USER_MODELS entry {n!r} not found in catalog "
                   f"or sidecar; ignoring.")
            if warn is not None:
                warn(msg)
            else:
                print(f"⚠️  {msg}", file=sys.stderr)

    options: list[_ComfyUIOption] = []
    for entry in by_name.values():
        is_pulled = (
            entry.name in pulled_names
            or _filename_of(entry.url) in pulled_names
        )
        group = (
            "Custom" if entry.source == "custom"
            else _display_group_for(entry.category)
        )
        badges = _badges_for_entry(entry, is_pulled, gpu_mem_gb)
        # Hint = space-joined badge text (rendered on the row's second line).
        # Also used by tests via o.hint to surface badges.
        hint = " ".join(badges)
        # For filter chip matching, include the display group as a badge
        # so the panel's "tag not in opt.badges" filter works.
        full_badges = [group] + badges
        options.append(_ComfyUIOption(
            value=entry.name,
            label=entry.name,
            hint=hint,
            badges=full_badges,
            group=group,
            checked=(entry.name in default_selected),
        ))

    pop_by_name = {name: e.popularity for name, e in by_name.items()}
    options.sort(key=lambda o: (-pop_by_name.get(o.value, 0), o.value))
    return options


def _to_prompt_option(opt: _ComfyUIOption) -> PromptOption:
    """Convert an internal _ComfyUIOption to a real PromptOption for the
    wizard's PromptStep. The group is already embedded in opt.badges;
    checked is handled via default_values on the step, not per-option.
    """
    return PromptOption(
        value=opt.value,
        label=opt.label,
        hint=opt.hint,
        badges=opt.badges,
    )


def build_comfyui_steps(
    env_vars: Dict[str, str],
    warn: Callable[[str], None] | None = None,
    volume_root: Path | None = None,
) -> List[PromptStep]:
    """Build the ComfyUI model multiselect step.

    Parallel to build_ollama_steps(). Activated right after the ComfyUI
    source step via a skip_if_prev guard: fires only when
    COMFYUI_SOURCE is container-cpu or container-gpu.

    Args:
        env_vars: the current .env snapshot (read at wizard build time)
        warn: optional log sink for diagnostic messages
        volume_root: override the comfyui-models scan path (for tests)
    """
    _warn = warn or (lambda _msg: None)

    # ── Resolve existing user selection ──────────────────────────────
    existing_names: set[str] = {
        s.strip()
        for s in (env_vars.get("COMFYUI_USER_MODELS", "") or "").split(",")
        if s.strip()
    }

    # ── Resolve sidecar path ─────────────────────────────────────────
    sidecar_path = (env_vars.get("COMFYUI_CUSTOM_MODELS_FILE", "") or "").strip()

    # ── options_provider closure ─────────────────────────────────────
    def _comfyui_options_provider(selections: dict) -> list[PromptOption]:
        from utils.comfyui_library import assemble_wizard_catalog, load_custom_models

        # Live catalog scrape with curated/fallback fallback inside.
        catalog = assemble_wizard_catalog()
        if not catalog:
            _warn(
                "[warn/comfyui-fetch] assemble_wizard_catalog() returned no entries "
                "— check network access"
            )
            return [PromptOption(
                value="",
                label="(catalog unreachable — HF/civitai scrape failed)",
                hint="check network access; comfyui-init will use the bundled fallback",
                badges=[],
            )]

        sidecar: list[ComfyUILibraryEntry] = []
        if sidecar_path:
            sidecar = load_custom_models(sidecar_path)

        # Filesystem scan for already-downloaded models.
        scan_root = volume_root or Path("/opt/comfyui/models")
        pulled = _scan_pulled(scan_root)

        # GPU memory detection.
        gpu_mem = _detect_gpu_memory_gb()

        raw = _merged_comfyui_options(
            catalog=catalog,
            sidecar=sidecar,
            pulled_names=pulled,
            default_selected=existing_names,
            gpu_mem_gb=gpu_mem,
            warn=_warn,
        )
        return [_to_prompt_option(o) for o in raw]

    # Pre-checked values seed from env (parallel to ollama_default_values).
    comfyui_default_values = sorted(existing_names) if existing_names else []

    def _skip_unless_container(sel: dict) -> bool:
        """Skip this step when ComfyUI is NOT running as a container."""
        src = sel.get("COMFYUI_SOURCE", "") or (
            env_vars.get("COMFYUI_SOURCE", "") or ""
        )
        if not src:
            # Fall back: check the step title's selection key
            comfyui_title = "ComfyUI  ·  source"
            src = sel.get(comfyui_title, "") or ""
        return src not in ("container-cpu", "container-gpu")

    return [
        PromptStep(
            title=COMFYUI_MODELS_TITLE,
            step_index=0, step_total=0,
            heading="Which ComfyUI models to download?",
            subtitle=(
                "Models are downloaded by comfyui-init at container start. "
                "[pulled] = file already on disk in the comfyui-models volume. "
                "⚠ badges are warnings only — models are NOT hidden for hardware "
                "mismatches. Filter by category using the chips above; "
                "press `f` to cycle, Tab or `/` for name search. "
                "Space toggles, Enter confirms."
            ),
            options=[],
            default_values=comfyui_default_values,
            service_name="",
            kind="multiselect",
            skip_if_prev=_skip_unless_container,
            options_provider=_comfyui_options_provider,
            filter_tags=_FILTER_TAGS,
        ),
    ]
