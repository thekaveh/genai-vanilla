"""
Canonical color tokens for the Textual TUI — round-4 plan.

Every hex code below appears in one of the four reference mockups
(``bootstrapper/ui/sketches/00{3,4,5,6}/...``). Widgets reference these
tokens by name; ``theme.css`` exposes them as ``$``-prefixed Textual
variables.

The legacy Rich palette at ``bootstrapper/ui/palette.py`` keeps its
``color(N)`` Rich-format constants for the (still-Rich) log_pane and
status_ribbon renderables. This module is the source of truth for the
Textual layer.
"""

from __future__ import annotations

from typing import Dict


# ─── Background layers (darkest → lightest) ─────────────────────────────
BG_DEEP        = "#080910"  # page / outermost (also: inverted button text)
BG_INSET       = "#0e0f18"  # command preview, code blocks
BG_PANE        = "#10111a"  # log pane (distinct from terminal bg)
BG             = "#12131e"  # terminal window
BG_RIBBON      = "#141525"  # status ribbon, top-panel, card header
BG_CHROME      = "#161728"  # window title bar, standard panel
BG_ELEVATED    = "#1c1d30"  # overlay titlebar, keycap background
BG_KEYCAP      = "#1e1f33"  # keycap inset

# Backwards-compat aliases used by existing widgets
COLOR_BG               = BG
COLOR_BG_DARKEST       = BG_DEEP
COLOR_BG_RIBBON        = BG_RIBBON
COLOR_BG_CHROME        = BG_CHROME
COLOR_SURFACE          = BG_CHROME
COLOR_SURFACE_DARKER   = BG_RIBBON
COLOR_SURFACE_LIGHTER  = BG_ELEVATED
COLOR_SURFACE_DEEP     = BG_INSET

# ─── Borders ────────────────────────────────────────────────────────────
BORDER_HAIRLINE = "#1e2038"  # section dividers (most common)
BORDER          = "#252840"  # window chrome bottom, command preview
BORDER_PANEL    = "#2b2f4a"  # outer panel, filter chip inactive, key badge
BORDER_KEYCAP   = "#3d4261"  # keycap edge

# Backwards-compat
COLOR_BORDER       = BORDER
COLOR_BORDER_LIGHT = BORDER_PANEL
COLOR_BORDER_DIM   = BORDER_HAIRLINE

# ─── Text ───────────────────────────────────────────────────────────────
TEXT_BRIGHT = "#e0e6f2"  # extra-emphasised
TEXT        = "#c0caf5"  # primary
TEXT_MUTED  = "#565f89"  # secondary (timestamps, hints, "off")
TEXT_FAINT  = "#3d4261"  # tertiary (footer, very muted)

COLOR_TEXT        = TEXT
COLOR_TEXT_BRIGHT = TEXT_BRIGHT
COLOR_TEXT_DIM    = TEXT_MUTED
COLOR_TEXT_MUTED  = TEXT_FAINT

# ─── Semantic accents ───────────────────────────────────────────────────
ACCENT       = "#7dcfff"  # selection, active, primary CTA, "local"
ACCENT_HOVER = "#a8d4e6"  # hover intensification
ACCENT_BRIGHT = "#a5d6ff"

OK    = "#98c379"  # success, healthy, "container", recommended
WARN  = "#ffbd2e"  # warnings, "changed"
ERR   = "#ff5f57"  # errors, danger button
ERR_SOFT = "#ff8a80"  # error TEXT (toast titles)
INFO  = "#89aad4"  # info, openwebui
RESOURCE = "#f0a050"  # GPU
CONTAINER = OK

COLOR_ACCENT       = ACCENT
COLOR_ACCENT_DIM   = "#5c8db5"
COLOR_ACCENT_BRIGHT = ACCENT_BRIGHT
COLOR_OK   = OK
COLOR_WARN = WARN
COLOR_ERR  = ERR
COLOR_ERR_SOFT = ERR_SOFT
COLOR_INFO = INFO
COLOR_RESOURCE = RESOURCE
COLOR_CONTAINER = OK

# ─── Service category tags ──────────────────────────────────────────────
TAG_INFRA = "#9a8cc6"
TAG_LLM   = "#7dcfff"
TAG_ML    = "#b8a35a"
TAG_DATA  = "#6a9aaa"
TAG_TOOL  = "#89aad4"

COLOR_TAG_INFRA = TAG_INFRA
COLOR_TAG_LLM   = TAG_LLM
COLOR_TAG_ML    = TAG_ML
COLOR_TAG_DATA  = TAG_DATA
COLOR_TAG_TOOL  = TAG_TOOL

# ─── Per-service hues (consistent across launch / health / chip / log src)
SVC_SUPABASE  = "#7dcfff"
SVC_REDIS     = "#98c379"
SVC_KONG      = "#9a8cc6"
SVC_OLLAMA    = "#b8a35a"
SVC_WEAVIATE  = "#6a9aaa"
SVC_OPENWEBUI = "#89aad4"
SVC_BACKEND   = "#b8a35a"
SVC_COMFYUI   = "#98c379"
SVC_NEO4J     = "#6a9aaa"
SVC_N8N       = "#89aad4"
SVC_SEARXNG   = "#7dcfff"
SVC_DISABLED  = "#565f89"

SOURCE_COLORS: Dict[str, str] = {
    "supabase": SVC_SUPABASE,
    "redis": SVC_REDIS,
    "kong": SVC_KONG,
    "ollama": SVC_OLLAMA,
    "weaviate": SVC_WEAVIATE,
    "openwebui": SVC_OPENWEBUI,
    "open-webui": SVC_OPENWEBUI,
    "backend": SVC_BACKEND,
    "comfyui": SVC_COMFYUI,
    "neo4j": SVC_NEO4J,
    "n8n": SVC_N8N,
    "searxng": SVC_SEARXNG,
    "disabled": SVC_DISABLED,
}

# 1-cell-wide service glyphs.
# Backwards-compat alias names (kept for any external code still using them)
COLOR_SRC_SUPABASE  = SVC_SUPABASE
COLOR_SRC_REDIS     = SVC_REDIS
COLOR_SRC_KONG      = SVC_KONG
COLOR_SRC_OLLAMA    = SVC_OLLAMA
COLOR_SRC_WEAVIATE  = SVC_WEAVIATE
COLOR_SRC_OPENWEBUI = SVC_OPENWEBUI
COLOR_SRC_BACKEND   = SVC_BACKEND
COLOR_SRC_COMFYUI   = SVC_COMFYUI
COLOR_SRC_NEO4J     = SVC_NEO4J
COLOR_SRC_N8N       = SVC_N8N
COLOR_SRC_SEARXNG   = SVC_SEARXNG

# ─── Gradient stops (approximated via multi-color spans in TUI) ─────────
LOGO_GRADIENT = ["#4a9eff", "#7dcfff", "#a8d4e6", "#7dcfff"]   # 4-stop
ACCENT_BAR_STOPS = ["#4a9eff", "#7dcfff", "#98c379", "#7dcfff", "#565f89"]  # 5-stop vertical

# ─── Pre-computed opaque equivalents for CSS rgba effects ───────────────
# Formula: opaque = bg + (fg − bg) × alpha, computed against BG_CHROME.
# Used wherever the mockup says rgba(...) — Textual cannot do alpha.
SEL_SVC_HOVER     = "#181a2c"  # rgba(125,207,255,0.04) over BG_CHROME
SEL_SVC_ACTIVE    = "#1b1f31"  # rgba(125,207,255,0.07)
SEL_OPT_HOVER     = "#181a2c"  # rgba(125,207,255,0.04)
SEL_OPT_ACTIVE    = "#1c2034"  # rgba(125,207,255,0.08)
SEL_LOG_HOVER     = "#161827"  # rgba(125,207,255,0.02)
SECTION_HEADER_BG = "#171829"  # rgba(125,207,255,0.04)

TOAST_WARN_BG     = "#1c1d27"  # rgba(255,189,46,0.05)
TOAST_WARN_BORDER = "#7a6429"  # rgba(255,189,46,0.4)
TOAST_ERR_BG      = "#1d1820"  # rgba(255,95,87,0.05)
TOAST_ERR_BORDER  = "#80393a"  # rgba(255,95,87,0.4)

CONFLICT_BORDER   = "#80393a"  # rgba(255,95,87,0.3) — close enough
HEALTHY_BORDER    = "#3a4d2e"  # rgba(152,195,121,0.3)
STARTING_BORDER   = "#2c3e54"  # rgba(125,207,255,0.3)

# ─── Glyphs (every Unicode char used in the mockups) ────────────────────
DOT_DIAMOND   = "◆"
DOT_RUNNING   = "●"
DOT_HOLLOW    = "○"
DOT_FILLED    = "◉"
DOT_SQUARE    = "▪"
ARROW_RIGHT   = "▸"
SPINNER_CYCLE = ("◐", "◓", "◑", "◒")
GLYPH_HOURGLASS = "⏳"
GLYPH_SEARCH  = "⌕"
GLYPH_COPY    = "⧉"
GLYPH_DOT     = "·"
GLYPH_DASH    = "—"
COLLAPSE_DOWN = "▾"
COLLAPSE_UP   = "▴"
PROGRESS_FILLED = "⣿"
PROGRESS_PARTIAL = ("⣷", "⣽")
PROGRESS_EMPTY = "⣀"
PROG_THIN_FULL  = "▰"
PROG_THIN_EMPTY = "▱"


# ─── Helpers ────────────────────────────────────────────────────────────
def color_for_source(name: str) -> str:
    """Map a service name → stable hue. Falls back to TEXT for unknowns."""
    if not name:
        return TEXT
    norm = name.lower().strip()
    for key, color in SOURCE_COLORS.items():
        if key in norm:
            return color
    return TEXT


def style_for_level(level: str) -> str:
    """Hex color for a log/status level."""
    return {
        "info": TEXT,
        "ok": OK,
        "success": OK,
        "warn": WARN,
        "warning": WARN,
        "err": ERR,
        "error": ERR,
        "dim": TEXT_MUTED,
        "title": ACCENT,
        "accent": ACCENT,
    }.get((level or "").lower(), TEXT)


def spaced_caps(s: str) -> str:
    """Approximate CSS letter-spacing on uppercase labels — used by section
    headers like ``CORE SERVICES`` / ``ACCESS URLS`` / ``OPTIONS``."""
    return " ".join(s.upper())


def style_for_source_choice(source: str) -> str:
    """Dot color driven by user CHOICE (not docker state)."""
    if not source or source == "disabled":
        return TEXT_MUTED
    if "container" in source or source.endswith("-cpu") or source.endswith("-gpu"):
        return OK
    if "localhost" in source or "external" in source or source == "api":
        return ACCENT
    return TEXT_MUTED
