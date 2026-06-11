"""URL → PORT .env schema migration (v1 → v2 of BOOTSTRAPPER_PORT_LAYOUT_VERSION).

Replaces 7 monolithic <SVC>_LOCALHOST_URL env vars with corresponding
integer-port <SVC>_LOCALHOST_PORT vars. The full URL is reconstructed
at compose-render time and Kong-config-generation time as
``http://host.docker.internal:${<SVC>_LOCALHOST_PORT:-<default>}``.

This module is the FROZEN snapshot of the v1→v2 migration at
2026-05-26. Do NOT edit when the schema changes again — author a
sibling migration_v3.py instead.

Triggered from start.py::run_port_migration when needs_migration()
returns True. After successful apply, call stamp_version() to update
the sentinel to 2.
"""

from __future__ import annotations

import re
from pathlib import Path


# Maps each legacy URL env var to its replacement PORT env var.
URL_VAR_TO_PORT_VAR: dict[str, str] = {
    "COMFYUI_LOCALHOST_URL":     "COMFYUI_LOCALHOST_PORT",
    "DOCLING_LOCALHOST_URL":     "DOCLING_LOCALHOST_PORT",
    "HERMES_LOCALHOST_URL":      "HERMES_LOCALHOST_PORT",
    "OPENCLAW_LOCALHOST_URL":    "OPENCLAW_LOCALHOST_PORT",
    "PARAKEET_LOCALHOST_URL":    "PARAKEET_LOCALHOST_PORT",
    "WHISPER_CPP_LOCALHOST_URL": "WHISPER_CPP_LOCALHOST_PORT",
    "CHATTERBOX_LOCALHOST_URL":  "CHATTERBOX_LOCALHOST_PORT",
}


# Tolerant sentinel matcher (mirrors migration_v1 conventions).
_SENTINEL_RE = re.compile(
    r"""^\s*BOOTSTRAPPER_PORT_LAYOUT_VERSION\s*=\s*
        (["']?)(\d+)\1
        \s*(?:\#.*)?\s*$""",
    re.VERBOSE,
)

# URL line matcher: captures (var_name, hostname, port).
# Tolerates http:// or https://, optional trailing path.
_URL_LINE_RE = re.compile(
    r"""^(?P<key>[A-Z_]+_LOCALHOST_URL)\s*=\s*
        (?P<quote>["']?)
        (?:https?://(?P<host>[^:/\s"']+)(?::(?P<port>\d+))?(?P<path>[^\s#"']*))?
        (?P=quote)
        \s*(?P<tail>(?:\#.*)?)\s*$""",
    re.VERBOSE,
)


def needs_migration(env_path: Path) -> bool:
    """True iff .env's BOOTSTRAPPER_PORT_LAYOUT_VERSION < 2 (or absent)."""
    if not env_path.is_file():
        return False  # fresh install — defaults already include PORT vars
    for line in env_path.read_text(encoding="utf-8").splitlines():
        m = _SENTINEL_RE.match(line)
        if m:
            try:
                return int(m.group(2)) < 2
            except ValueError:
                return True
    return True


def apply(env_path: Path) -> None:
    """Rewrite .env in place. Idempotent on re-run.

    For each legacy URL var present:
      • Extract the port via regex.
      • Append <SVC>_LOCALHOST_PORT=<port> if not already present.
      • Comment out the old URL line.
      • If the hostname isn't host.docker.internal, print a warning.
      • If the URL has no port (malformed/empty), skip the PORT line.
    """
    if not env_path.is_file():
        return

    lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True)
    existing_keys: set[str] = set()
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key = line.split("=", 1)[0].strip()
        existing_keys.add(key)

    out: list[str] = []
    appended: list[str] = []
    for line in lines:
        if line.endswith("\r\n"):
            eol = "\r\n"
            body = line[:-2]
        elif line.endswith("\n"):
            eol = "\n"
            body = line[:-1]
        else:
            eol = ""
            body = line
        m = _URL_LINE_RE.match(body.strip())
        if not m or m.group("key") not in URL_VAR_TO_PORT_VAR:
            out.append(line)
            continue
        url_var = m.group("key")
        host = m.group("host") or ""
        port = m.group("port") or ""
        port_var = URL_VAR_TO_PORT_VAR[url_var]

        # Warn on non-default host.
        if host and host != "host.docker.internal":
            print(
                f"[migration_v2] {url_var} had hostname {host!r}; "
                f"dropping it (PORT-only override). Set the URL var by "
                f"hand-edit if you need a custom hostname.",
                flush=True,
            )

        # Emit the PORT line if extractable and not already present.
        if port and port_var not in existing_keys:
            out.append(f"# {body}  # migrated by migration_v2{eol}")
            appended.append(f"{port_var}={port}{eol or chr(10)}")
            existing_keys.add(port_var)
        elif port:
            # PORT var already present — just comment the URL line.
            out.append(f"# {body}  # migrated by migration_v2{eol}")
        else:
            # No extractable :port — comment the URL line and warn.
            out.append(f"# {body}  # migration_v2 skipped (no :port){eol}")
            print(
                f"[migration_v2] {url_var} had no extractable :port; "
                f"skipping PORT emission. Service will use manifest "
                f"default at compose-render time.",
                flush=True,
            )

    if appended:
        if out and not out[-1].endswith(("\n", "\r\n")):
            out[-1] += "\n"
        out.extend(appended)

    env_path.write_text("".join(out), encoding="utf-8")


def stamp_version(env_path: Path, version: int = 2) -> None:
    """Append or update BOOTSTRAPPER_PORT_LAYOUT_VERSION in .env to 2."""
    if not env_path.is_file():
        return
    lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True)
    found = False
    for i, line in enumerate(lines):
        if _SENTINEL_RE.match(line):
            lines[i] = f"BOOTSTRAPPER_PORT_LAYOUT_VERSION={version}\n"
            found = True
            break
    if not found:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(f"BOOTSTRAPPER_PORT_LAYOUT_VERSION={version}\n")
    env_path.write_text("".join(lines), encoding="utf-8")
