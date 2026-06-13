"""
Ollama library catalog discovery — scrape ``https://ollama.com/library``
for the canonical list of public Ollama models with per-model metadata
(capability tags, sizes, pull counts).

Used by the wizard's Ollama multi-select to present a live, popularity-
sorted catalog that the user can pre-select for ``ollama-pull`` to
fetch at startup, instead of our hardcoded curated subset in
``llm_catalog.py:OLLAMA_DEFAULT_CATALOG``.

For ``ollama-localhost``, ``ollama_discovery.py`` already queries the
live ``/api/tags`` endpoint of the user's running upstream — that path
stays unchanged.

Why scrape?
  Ollama's registry (``registry.ollama.ai/v2/_catalog``) returns 404,
  no public JSON API exists for the library, and ollamadb.dev returns
  empty. The library web page is server-rendered with stable Alpine.js
  ``x-test-*`` attributes on every model card — they're literally test
  hooks, far more stable than CSS classes. We anchor the parser on
  those attributes.

  Per model the page exposes:
    • capability tag(s)  →  ``<span x-test-capability …>VAL</span>``
                           VAL ∈ {tools, thinking, embedding, vision, audio, …}
    • size variant(s)    →  ``<span x-test-size …>VAL</span>``
                           VAL like ``8b``, ``70b``, ``0.6b``
    • pull count         →  ``<span x-test-pull-count>114.2M</span>``
    • last update        →  ``<span x-test-updated>1 year ago</span>``

  We fetch ``?sort=popular`` so the HTML order is already pull-count
  descending; we still apply our own numeric sort downstream as defence
  against the query-param being removed or renamed upstream.

Failure mode: any network / parse error returns an empty list, and the
caller falls back to the curated ``OLLAMA_DEFAULT_CATALOG``. No exceptions
escape this module.
"""

from __future__ import annotations

import re
import socket
import http.client
import urllib.error
import urllib.request
from dataclasses import dataclass

_LIBRARY_URL = "https://ollama.com/library?sort=popular"

# Anchor regexes for the structured parser. All target Alpine.js test
# attributes (``x-test-*``) which are deliberately stable — they exist
# specifically so ollama.com's own QA can pin selectors.
_CARD_RE = re.compile(
    r"<li[^>]*\bx-test-model\b.*?</li>",
    flags=re.DOTALL,
)
_NAME_RE = re.compile(r'href="/library/([a-z0-9._-]+)"')
_CAPABILITY_RE = re.compile(
    r"<span[^>]*\bx-test-capability\b[^>]*>\s*([a-z0-9_-]+)\s*</span>",
)
_SIZE_RE = re.compile(
    r"<span[^>]*\bx-test-size\b[^>]*>\s*([0-9][a-z0-9.]*)\s*</span>",
)
_PULL_COUNT_RE = re.compile(
    r"<span[^>]*\bx-test-pull-count\b[^>]*>\s*([^<]+?)\s*</span>",
)
_UPDATED_RE = re.compile(
    r"<span[^>]*\bx-test-updated\b[^>]*>\s*([^<]+?)\s*</span>",
)
# Ollama Cloud chip — appears next to the model name as a small cyan
# pill. Marks the model as available on Ollama's hosted inference
# service. When the card ALSO has ``x-test-size`` entries the model is
# hybrid (cloud + pullable local variants); when there are no sizes,
# the model is cloud-exclusive and cannot be ``ollama pull``-ed.
_CLOUD_BADGE_RE = re.compile(
    r'<span[^>]*\bbg-cyan-50\b[^>]*>\s*cloud\s*</span>',
    re.IGNORECASE,
)
# Matches ollama.com's relative "updated" strings: e.g.
#   "5 days ago", "10 months ago", "2 weeks ago",
#   "1 year ago", "an hour ago", "a year ago"
_UPDATED_AGE_RE = re.compile(
    r"^(?:about\s+)?(?:an?\s+|(\d+)\s+)(hour|day|week|month|year)s?\s+ago$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class OllamaLibraryEntry:
    """Structured snapshot of one model card on ollama.com/library.

    Frozen + hashable so consumers can put entries in sets / use them
    as dict keys without worrying about identity drift. ``frozenset``
    and ``tuple`` collections are used for the same reason.
    """

    name: str
    capabilities: frozenset[str]
    sizes: tuple[str, ...]
    pulls: int
    updated: str
    # Parsed age of ``updated`` in days. ``None`` when the timestamp
    # was empty or unparseable; downstream sort treats that as "recent"
    # (better than mis-labelling a future Ollama release as legacy).
    age_days: int | None = None
    # True when the listing card carries the ``cloud`` chip AND has no
    # ``x-test-size`` entries — the model is hosted-only on Ollama
    # Cloud and ``ollama pull`` will fail for every tag. The wizard
    # filters these out of the multiselect. Hybrid models (cloud chip
    # *plus* pullable sizes) have ``cloud_only=False`` and stay in
    # the list with their local variants intact.
    cloud_only: bool = False


def _parse_updated_age_days(updated: str) -> int | None:
    """Convert ollama.com's relative "updated" string to age in days.

    Examples::

        "5 days ago"   -> 5
        "2 weeks ago"  -> 14
        "10 months ago"-> 300
        "1 year ago"   -> 365
        "an hour ago"  -> 0
        "today"        -> 0
        "yesterday"    -> 1

    Returns ``None`` for empty or unrecognised strings — downstream
    sort logic treats ``None`` as recent so that an upstream wording
    change doesn't accidentally banish every model to the legacy
    bucket.
    """
    if not updated:
        return None
    s = updated.strip().lower()
    if s in ("today", "just now", "moments ago"):
        return 0
    if s == "yesterday":
        return 1
    m = _UPDATED_AGE_RE.match(s)
    if not m:
        return None
    n = int(m.group(1)) if m.group(1) else 1
    unit = m.group(2).lower()
    # Rough but consistent — sub-day units collapse to 0; month=30,
    # year=365. Ollama only uses relative timestamps so we don't need
    # calendar precision.
    multipliers = {"hour": 0, "day": 1, "week": 7, "month": 30, "year": 365}
    return n * multipliers.get(unit, 365)


def _parse_pull_count(raw: str) -> int:
    """Convert ollama.com's human-formatted pull count to an int.

    Examples:
      ``"114.2M"`` → ``114_200_000``
      ``"85K"``    → ``85_000``
      ``"1.2B"``   → ``1_200_000_000``
      ``"742"``    → ``742``
    Unknown / empty → ``0`` (sorted to the bottom; safe default).
    """
    if not raw:
        return 0
    s = raw.strip().replace(",", "").replace(" ", "")
    if not s:
        return 0
    # Bare integer fast-path.
    if s.isdigit():
        return int(s)
    suffix = s[-1].upper()
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    if suffix in multipliers:
        try:
            return int(float(s[:-1]) * multipliers[suffix])
        except ValueError:
            return 0
    return 0


def list_library_entries(timeout: float = 5.0) -> list[OllamaLibraryEntry]:
    """Fetch and parse ``ollama.com/library?sort=popular``.

    Returns a list of :class:`OllamaLibraryEntry`, deduplicated by
    name and sorted descending by pull count with alphabetical fallback
    (defence-in-depth — the page already returns popular-first, but we
    don't trust the upstream sort order).

    Returns an empty list on any failure (network, timeout, parse).
    Callers fall back to the curated ``OLLAMA_DEFAULT_CATALOG``.
    """
    try:
        req = urllib.request.Request(
            _LIBRARY_URL,
            headers={
                # Ollama's library page is server-rendered; a regular
                # browser UA gets the same HTML. Setting one avoids
                # potential gating on missing UAs.
                "User-Agent": "genai-vanilla-bootstrapper/1.0 (+wizard catalog fetch)",
                "Accept": "text/html",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError,
            http.client.HTTPException):
        return []

    seen: set[str] = set()
    entries: list[OllamaLibraryEntry] = []
    for card_match in _CARD_RE.finditer(html):
        card = card_match.group(0)
        name_match = _NAME_RE.search(card)
        if not name_match:
            continue
        name = name_match.group(1)
        if name in seen:
            continue
        seen.add(name)

        capabilities = frozenset(_CAPABILITY_RE.findall(card))
        sizes = tuple(_SIZE_RE.findall(card))
        pull_raw_match = _PULL_COUNT_RE.search(card)
        pulls = _parse_pull_count(pull_raw_match.group(1)) if pull_raw_match else 0
        updated_match = _UPDATED_RE.search(card)
        updated = updated_match.group(1).strip() if updated_match else ""
        age_days = _parse_updated_age_days(updated)
        # Pure cloud — cloud chip present AND no pullable sizes on
        # the card. Hybrid models (cloud chip + at least one size)
        # stay pullable for their local variants, so we leave them
        # marked False.
        cloud_only = bool(_CLOUD_BADGE_RE.search(card)) and not sizes

        entries.append(OllamaLibraryEntry(
            name=name,
            capabilities=capabilities,
            sizes=sizes,
            pulls=pulls,
            updated=updated,
            age_days=age_days,
            cloud_only=cloud_only,
        ))

    entries.sort(key=lambda e: (-e.pulls, e.name))
    return entries


# ─── per-model detail-page parser ──────────────────────────────────────
#
# The library listing page only exposes aggregated param-count tags
# (``8b``, ``70b``, …) for each model and a single capability set at
# the family level. The detail page ``https://ollama.com/library/{name}``
# is much richer — every Ollama tag the model maker publishes appears
# as its own row with the real on-disk size, context window, and input
# modalities (which let us derive per-variant capability flags like
# vision and audio).
#
# This is more expensive to fetch (one HTTP request per model) so the
# wizard fetches lazily on parent expand and caches per session.

@dataclass(frozen=True)
class OllamaVariant:
    """One specific tag of an Ollama model, parsed from the detail page.

    Tags can be:
      • Plain param counts: ``"8b"``, ``"70b"``, ``"0.6b"``.
      • The synthetic default: ``"latest"`` (pointer to a real tag).
      • Quantization / coding variants: ``"27b-coding-mxfp8"``,
        ``"35b-a3b-mlx-bf16"``, …
    """
    tag: str                          # e.g. "8b", "latest", "27b-coding-mxfp8"
    size_label: str                   # raw size string from upstream: "5.2GB", "523MB"
    context_label: str                # context window: "40K", "256K", "1M"
    input_modalities: tuple[str, ...] # ("Text",) or ("Text", "Image") or ("Audio",)
    updated: str                      # relative timestamp, "7 months ago"
    # Apple-Silicon-optimised MLX weights are published as a separate
    # variant tag (e.g. ``27b-mlx-bf16``). ollama.com decorates those
    # rows with an ``MLX`` chip on the detail page; we surface it as a
    # per-variant capability badge so users on M-series Macs can spot
    # the right tag at a glance.
    mlx: bool = False

    @property
    def capabilities(self) -> frozenset[str]:
        """Per-variant capability tags.

        Derived from the detail-page ``Input`` column (``Image`` →
        ``vision``, ``Audio`` → ``audio``) AND the MLX chip indicator
        when present. Per-variant so leaves can carry capabilities
        that differ from each other under the same parent (a coding
        variant may keep ``thinking`` while dropping ``vision``; an
        MLX-quantized variant carries ``mlx`` while siblings don't).
        """
        caps: set[str] = set()
        for modality in self.input_modalities:
            m = modality.strip().lower()
            if m == "image":
                caps.add("vision")
            elif m == "audio":
                caps.add("audio")
        if self.mlx:
            caps.add("mlx")
        return frozenset(caps)


# Detail-page parsers. The compact (mobile) layout `<a class="sm:hidden ...">`
# block exists once per variant and contains all the metadata in a
# single ``<p>`` summary. The desktop layout duplicates the data in a
# 12-column grid, so we deliberately anchor on ``sm:hidden`` to avoid
# matching each variant twice.
_VARIANT_BLOCK_RE_TPL = (
    r'<a\s+href="/library/{name}:([^"]+)"'
    r'[^>]*class="[^"]*\bsm:hidden\b[^"]*"[^>]*>'
    r'(.*?)</a>'
)
_VARIANT_SUMMARY_RE = re.compile(
    r'<p class="flex text-neutral-500"[^>]*>'
    r'([0-9.]+[GM]?B)\s*·\s*'
    r'([0-9]+[KM]?)\s+context\s+window\s*·\s*'
    r'([^·<]+?)\s*·\s*'
    r'([^<]+?)</p>',
)
# MLX chip — ollama.com renders this as an outlined neutral-grey badge
# (``border border-neutral-600 text-neutral-600``) on every variant
# row whose weights are MLX-quantized. Anchoring on the literal class
# token + the literal text keeps the matcher robust against the
# surrounding markup (size / colour utilities, whitespace).
_VARIANT_MLX_RE = re.compile(
    r'<span[^>]*\bborder-neutral-600\b[^>]*>\s*MLX\s*</span>',
)


def fetch_model_variants(name: str, timeout: float = 5.0) -> list[OllamaVariant] | None:
    """Fetch ``https://ollama.com/library/{name}`` and parse the
    per-variant table.

    Returns a list of :class:`OllamaVariant` instances (one per Ollama
    tag the model publishes), or ``None`` on any failure (network,
    timeout, parse-yields-nothing). Callers fall back to the
    listing-page ``OllamaLibraryEntry.sizes`` tuple, which is less
    granular but always available.
    """
    url = f"https://ollama.com/library/{name}"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "genai-vanilla-bootstrapper/1.0 (+wizard catalog fetch)",
                "Accept": "text/html",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError,
            http.client.HTTPException):
        return None

    block_re = re.compile(
        _VARIANT_BLOCK_RE_TPL.format(name=re.escape(name)),
        flags=re.DOTALL,
    )
    seen: set[str] = set()
    out: list[OllamaVariant] = []
    for m in block_re.finditer(html):
        tag = m.group(1)
        if tag in seen:
            continue
        seen.add(tag)
        block_html = m.group(2)
        summary = _VARIANT_SUMMARY_RE.search(block_html)
        if not summary:
            continue
        size_label, ctx_label, inputs_raw, updated_raw = summary.groups()
        modalities = tuple(
            s.strip() for s in inputs_raw.split(",") if s.strip()
        )
        mlx = bool(_VARIANT_MLX_RE.search(block_html))
        out.append(OllamaVariant(
            tag=tag,
            size_label=size_label.strip(),
            context_label=ctx_label.strip(),
            input_modalities=modalities,
            updated=updated_raw.strip(),
            mlx=mlx,
        ))
    return out or None
