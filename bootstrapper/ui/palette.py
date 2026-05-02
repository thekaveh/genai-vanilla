"""
Single source of truth for colors used by the anchored-box presentation.

Palette: **Tokyo Night-inspired**, four-color discipline (selected by the
user as the professionally-proven harmony for this project). Modeled after
the Tokyo Night dev-terminal theme, which pairs cleanly with the blue
GenAI Vanilla logo gradient above the box.

Four core colors carry all meaning inside the box:

    1. COLOR_TEXT       — pale blue-white     #c0caf5  · service names, body
    2. COLOR_TITLE/ACCENT — bright sky cyan   #7dcfff  · headings, accents,
                                                         localhost/cloud choice
    3. COLOR_CONTAINER   — soft green         #98c379  · container running dots
                                                         and the "container" choice
    4. COLOR_DIM/OFF/    — slate-blue         #565f89  · disabled services,
       BORDER/SEPARATOR                                  borders, hints, footer

Two warm contrast colors (amber + coral red) are reserved EXCLUSIVELY for
warnings and errors — never used for normal content.

The blue LOGO_GRADIENT (color 17 → 195) is reserved EXCLUSIVELY for the
ASCII logo block in `ui/logo.py`. It must NOT be used elsewhere — the
four-color box palette stays distinct from the logo's blue ramp.
"""

# --- Foundational colors (Tokyo Night-inspired) ----------------------------

# Background: terminal default — the box blends with the user's theme.
COLOR_BG = ""

# Body text — pale blue-white. Tokyo Night's foreground color.
COLOR_TEXT = "color(189)"

# Section / panel titles, "Stack Overview" / "Setup Wizard" header,
# subtitle text. Pale blue-white, bold — matches body text but pops by
# being bold against the deeper border color.
COLOR_TITLE = "bold color(189)"

# User-choice accent — the source label for non-default sources
# (local / ext / cloud) AND highlight color for the currently-selected
# wizard option. Same hue as TITLE so the box stays cohesive.
COLOR_ACCENT = "color(81)"

# Container running — soft Tokyo Night green. Used for both the dot color
# and the choice label of any service whose source is a `container*` form.
# The green visually distinguishes "running here as a docker container"
# from "running elsewhere" (cyan) and "off" (slate).
COLOR_CONTAINER = "bold color(150)"

# Slate-blue. Three roles: dim text, off services, inline separators.
# Tokyo Night's `comment` color — quiet but legible.
COLOR_DIM = "color(60)"
COLOR_OFF = COLOR_DIM
COLOR_SEPARATOR = "color(60)"

# Box border — Tokyo Night's `comment` slate-blue (#5f5f87). Restrained,
# matches the dim/separator tone so the box edge feels structural without
# competing with the data inside. Pairs with COLOR_TITLE (pale blue-white,
# bold) for clear contrast in the title bar inside this border.
COLOR_BORDER = "color(60)"

# COLOR_OK is the "success" log/status level color — same green as
# COLOR_CONTAINER. Used by `style_for_level('ok'|'success')` in log_pane.
COLOR_OK = COLOR_CONTAINER

# --- Contrast colors (the only non-blue/cyan/green/slate values) -----------
# Reserved EXCLUSIVELY for warnings and errors. Never used for normal box
# content — they exist to interrupt the user's attention.

# Warnings — amber. Used for port mismatches, dependency auto-disable,
# localhost unreachable, and similar "you may want to know" signals.
COLOR_WARN = "color(214)"

# Errors — coral red. Used for hard failures and must-act conditions
# (missing Supabase keys, dependency violations that can't auto-resolve).
COLOR_ERR = "color(203)"

# --- Log source hues (for log_pane source-column color-coding) ------------
# Six stable hues drawn from the existing palette plus two muted partners
# from the Tokyo Night ramp. Each docker compose service hashes to one of
# these so the eye can pick out a single service in a wall of logs.
# Bodies of log lines stay in the level color (info/warn/error); only the
# source column is hue-coded.
SOURCE_HUES = (
    COLOR_ACCENT,      # sky cyan
    COLOR_CONTAINER,   # soft green
    "color(141)",      # soft purple
    "color(180)",      # soft tan/amber (quieter than COLOR_WARN)
    "color(108)",      # muted teal
    "color(110)",      # soft blue
)


def color_for_source(name: str) -> str:
    """
    Map a docker source name to a stable hue from SOURCE_HUES. Same input
    always returns the same color, so 'n8n' is consistently one color and
    'supabase-realtime' another. Empty / None falls back to COLOR_DIM.
    """
    if not name:
        return COLOR_DIM
    return SOURCE_HUES[hash(name) % len(SOURCE_HUES)]


# --- Logo gradient (LOGO-ONLY, do not use elsewhere) -----------------------

# Eight-step DRAMATIC blue gradient applied per LETTER to the GenAI
# Vanilla ASCII art in `ui/logo.py`. Each letter shape gets a single
# solid color, producing a left-to-right ramp from a deep saturated
# midnight navy at the dark end to a soft pale azure at the light end —
# all squarely in the blue family. This palette is RESERVED for the
# logo; do NOT reach for these colors elsewhere — the four-color box
# palette (above) stays visually distinct from the logo's ramp.
LOGO_GRADIENT = [
    "#0A1A55",   # [0]  deep midnight navy (saturated, rich blue)
    "#14338B",   # [1]  dark royal navy
    "#1F4FBE",   # [2]  strong royal blue
    "#316DDF",   # [3]  vivid royal blue
    "#4F8AED",   # [4]  bright blue
    "#74A6F4",   # [5]  light blue
    "#9CC0F9",   # [6]  pale sky blue
    "#BFD8FD",   # [7]  soft pale azure
]

# --- Status dot glyph -------------------------------------------------------

# Single solid dot glyph for every service in the box; the color (driven by
# the user's source CHOICE via `style_for_source`) carries the meaning.
DOT_RUNNING = "●"

# --- Level → style helpers --------------------------------------------------

_LEVEL_STYLES = {
    "info": COLOR_TEXT,
    "ok": COLOR_OK,
    "success": COLOR_OK,
    "warn": COLOR_WARN,
    "warning": COLOR_WARN,
    "err": COLOR_ERR,
    "error": COLOR_ERR,
    "dim": COLOR_DIM,
    "title": COLOR_TITLE,
    "accent": COLOR_ACCENT,
}


def style_for_level(level: str) -> str:
    """Return the Rich style string for a named log/status level."""
    return _LEVEL_STYLES.get(level, COLOR_TEXT)


def style_for_source(source: str) -> str:
    """
    Map a SOURCE value to a dot/label color — the user's CHOICE drives
    the color, not transient docker state.

        container / *-cpu / *-gpu          → COLOR_CONTAINER (green)
        localhost / external / api         → COLOR_ACCENT    (sky cyan)
        disabled                           → COLOR_OFF       (slate)
        anything else                      → COLOR_OFF       (safe default)
    """
    if not source or source == "disabled":
        return COLOR_OFF
    if "container" in source or source.endswith("-cpu") or source.endswith("-gpu"):
        return COLOR_CONTAINER
    if "localhost" in source or "external" in source or source == "api":
        return COLOR_ACCENT
    return COLOR_OFF
