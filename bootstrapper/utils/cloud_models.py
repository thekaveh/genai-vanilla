"""
Live cloud-provider model discovery for the wizard's multi-select.

Three public functions, one per provider:

* ``list_openai_models(api_key)``
* ``list_anthropic_models(api_key)``
* ``list_openrouter_models()``        (no auth required)

Each returns a ``list[ModelInfo]``, filtered down to models that make
sense in a chat/embedding context. The wizard's options_provider calls
these synchronously when the user advances to the cloud multi-select
step (timeout 5s per call). On any failure (network, auth, timeout,
empty result post-filter) the caller falls back to the curated
``CLOUD_CATALOG`` from ``llm_catalog.py``.

Filtering rationale per provider:

* **OpenAI** — ``/v1/models`` returns 50–150 entries including
  DALL-E, Whisper, TTS, snapshots, fine-tunes, deprecated bases.
  Without filtering the picker is unusable. We use an allow-list of
  prefix patterns + a deny-list to drop noise.
* **Anthropic** — already clean (~5–15 ``claude-*`` entries). We use
  ``display_name`` for the picker label and dedup snapshots that share
  a display name.
* **OpenRouter** — already clean and rich (``id``, ``name``,
  ``description``, ``context_length``). We cap at 50 to keep the
  picker usable; sort alphabetically.

Maintenance cadence
-------------------
The OpenAI allow/deny patterns are the most likely to drift — every
new family from OpenAI (gpt-6, o4, o5, etc.) needs a prefix added to
``_OPENAI_ALLOW_PREFIXES``. Suggested cadence:

  • **At each major OpenAI release**: add new family prefixes to the
    allow-list. Audit ``_OPENAI_DENY_SUBSTRINGS`` for new noise patterns
    (audio, image, deprecated families).
  • **Anthropic / OpenRouter**: rarely need maintenance — Anthropic's
    response shape is stable, OpenRouter's curated catalog handles its
    own filtering. Touch only if the response format changes.

When the upstream catalog drifts faster than we update these filters,
the wizard's worst-case behavior is silently dropping new models from
the picker — the user can still type the name into the catalog directly
or activate the row via ``UPDATE public.llms``.
"""

from __future__ import annotations

import json
import re
import socket
import http.client
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional


# Type alias for the failure-reason logger. The wizard passes its
# ``_safe_log`` adapter so transport / parse / empty-result failures
# end up in the launch log alongside the rest of the wizard's events.
WarnFn = Callable[[str], None]


def _format_url_error(exc: BaseException) -> str:
    """Compress a urllib/socket exception into one human-readable line."""
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code} {exc.reason}"
    if isinstance(exc, urllib.error.URLError):
        return f"URLError {exc.reason}"
    if isinstance(exc, socket.timeout):
        return "timeout"
    return f"{type(exc).__name__}: {exc}"


def _emit(on_warn: Optional[WarnFn], msg: str) -> None:
    if on_warn is None:
        return
    try:
        on_warn(msg)
    except Exception:
        pass


@dataclass
class ModelInfo:
    """One row in the cloud multi-select picker.

    ``id`` is what we store in ``public.llms.name`` and what
    ``litellm-init`` puts in ``model_list[].model_name`` — stable.
    ``label`` is what the user sees in the wizard. ``description``
    is shown as the row hint.
    """
    id: str
    label: str
    description: str = ""


# ─── OpenAI ───────────────────────────────────────────────────────────

# Allow-list: model id starts with one of these prefixes.
_OPENAI_ALLOW_PREFIXES = (
    "gpt-5",
    "gpt-4o",
    "gpt-4.1",
    "gpt-4-turbo",
    "o1",
    "o3",
    "o4",
    "chatgpt-",
    "text-embedding-3",
)

# Deny-list: deny-substring patterns and regexes. If any matches, the
# model is dropped EVEN IF the allow-list said yes.
_OPENAI_DENY_SUBSTRINGS = (
    "dall-e",
    "whisper",
    "tts-",
    "gpt-image",
    "realtime-preview",
    "audio-preview",
    "search-preview",
    "-instruct",
    "babbage",
    "davinci",
    "text-embedding-ada",
    "text-similarity",
    "ft-",  # fine-tune marker
)

# Snapshot suffixes — drop ``foo-2024-01-15`` and ``foo-1106`` style
# variants when the unsuffixed alias is also in the response.
_OPENAI_SNAPSHOT_RE = re.compile(r"-(?:\d{4}-\d{2}-\d{2}|\d{4})$")


def _openai_pass_filter(model_id: str) -> bool:
    mid = model_id.lower()
    if not any(mid.startswith(p) for p in _OPENAI_ALLOW_PREFIXES):
        return False
    if any(s in mid for s in _OPENAI_DENY_SUBSTRINGS):
        return False
    return True


def _dedup_openai_snapshots(ids: list[str]) -> list[str]:
    """Drop dated snapshots when the unsuffixed alias is present.

    e.g. if the response has both ``gpt-4o`` and ``gpt-4o-2024-08-06``,
    keep only ``gpt-4o``.
    """
    bare = {mid for mid in ids if not _OPENAI_SNAPSHOT_RE.search(mid)}
    out: list[str] = []
    for mid in ids:
        m = _OPENAI_SNAPSHOT_RE.search(mid)
        if m:
            alias = mid[: m.start()]
            if alias in bare:
                continue
        out.append(mid)
    return out


def list_openai_models(api_key: str, timeout: float = 5.0,
                       on_warn: Optional[WarnFn] = None) -> list[ModelInfo]:
    """GET https://api.openai.com/v1/models with the user's key.
    Returns filtered list. Empty on any failure (with reason emitted via
    ``on_warn`` when supplied).
    """
    if not api_key:
        _emit(on_warn, "[warn/openai-fetch] no OPENAI_API_KEY set — falling back to catalog")
        return []
    try:
        req = urllib.request.Request(
            "https://api.openai.com/v1/models",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError,
            http.client.HTTPException) as exc:
        _emit(on_warn, f"[warn/openai-fetch] live /v1/models failed — falling back to catalog (cause: {_format_url_error(exc)})")
        return []
    try:
        data = json.loads(body)
    except (ValueError, TypeError):
        _emit(on_warn, "[warn/openai-fetch] /v1/models returned non-JSON body — falling back to catalog")
        return []
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        _emit(on_warn, "[warn/openai-fetch] /v1/models response missing data[] — falling back to catalog")
        return []
    raw_ids = [r["id"] for r in rows if isinstance(r, dict) and isinstance(r.get("id"), str)]
    filtered = [mid for mid in raw_ids if _openai_pass_filter(mid)]
    deduped = _dedup_openai_snapshots(filtered)
    deduped.sort()
    if not deduped:
        _emit(on_warn, f"[warn/openai-fetch] /v1/models returned {len(raw_ids)} ids but none passed the filter — falling back to catalog")
    return [ModelInfo(id=mid, label=mid, description="") for mid in deduped]


# ─── Anthropic ───────────────────────────────────────────────────────

def list_anthropic_models(api_key: str, timeout: float = 5.0,
                          on_warn: Optional[WarnFn] = None) -> list[ModelInfo]:
    """GET https://api.anthropic.com/v1/models with the user's key.
    Anthropic's response is already clean — only minor dedup needed.
    """
    if not api_key:
        _emit(on_warn, "[warn/anthropic-fetch] no ANTHROPIC_API_KEY set — falling back to catalog")
        return []
    try:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError,
            http.client.HTTPException) as exc:
        _emit(on_warn, f"[warn/anthropic-fetch] live /v1/models failed — falling back to catalog (cause: {_format_url_error(exc)})")
        return []
    try:
        data = json.loads(body)
    except (ValueError, TypeError):
        _emit(on_warn, "[warn/anthropic-fetch] /v1/models returned non-JSON body — falling back to catalog")
        return []
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        _emit(on_warn, "[warn/anthropic-fetch] /v1/models response missing data[] — falling back to catalog")
        return []
    # Each row: {id, display_name, type, created_at}. Dedup snapshots
    # that share a display_name — keep the entry with the most recent
    # created_at (string-sortable ISO).
    by_label: dict[str, dict] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        rid = r.get("id")
        label = r.get("display_name") or rid
        created = r.get("created_at") or ""
        if not isinstance(rid, str) or not isinstance(label, str):
            continue
        prev = by_label.get(label)
        if prev is None or str(created) > str(prev.get("created_at", "")):
            by_label[label] = {"id": rid, "label": label, "created_at": created}
    out = [ModelInfo(id=v["id"], label=v["label"]) for v in by_label.values()]
    out.sort(key=lambda m: m.label)
    return out


# ─── OpenRouter ──────────────────────────────────────────────────────

def list_openrouter_models(timeout: float = 5.0, cap: int = 50,
                           on_warn: Optional[WarnFn] = None) -> list[ModelInfo]:
    """GET https://openrouter.ai/api/v1/models (no auth).
    OpenRouter returns 200+ models with rich metadata. Cap at ``cap``
    so the wizard multi-select stays usable.
    """
    try:
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/models",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, socket.timeout, ConnectionError, OSError,
            http.client.HTTPException) as exc:
        _emit(on_warn, f"[warn/openrouter-fetch] live /api/v1/models failed — falling back to catalog (cause: {_format_url_error(exc)})")
        return []
    try:
        data = json.loads(body)
    except (ValueError, TypeError):
        _emit(on_warn, "[warn/openrouter-fetch] /api/v1/models returned non-JSON body — falling back to catalog")
        return []
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        _emit(on_warn, "[warn/openrouter-fetch] /api/v1/models response missing data[] — falling back to catalog")
        return []
    out: list[ModelInfo] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        rid = r.get("id")
        if not isinstance(rid, str):
            continue
        # The catalog model_names are prefixed ``openrouter/...`` so
        # LiteLLM routes via the OpenRouter API. The OpenRouter API's
        # ``id`` field is normally the bare slug (e.g.
        # ``anthropic/claude-sonnet-4-6``); we add the prefix so it
        # matches the per-provider routing rules in services/litellm/init/scripts/init.py.
        # Defensive check against double-prefixing in case OpenRouter's
        # response format ever includes the prefix already.
        oid = rid if rid.startswith("openrouter/") else f"openrouter/{rid}"
        label = r.get("name") or oid
        desc = r.get("description") or ""
        if isinstance(desc, str) and len(desc) > 120:
            desc = desc[:117] + "…"
        out.append(ModelInfo(id=oid, label=str(label), description=desc))
    # Sort alphabetically by label; cap.
    out.sort(key=lambda m: m.label.lower())
    return out[:cap]
