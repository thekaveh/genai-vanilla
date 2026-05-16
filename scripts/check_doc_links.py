#!/usr/bin/env python3
"""Internal-markdown-link validator.

Scans markdown files for relative `[label](./path.md)` and `[label](path.md)`
links and asserts every target resolves to an existing file. External links
(http://, https://, mailto:) are skipped. Anchors (`#section`) are not
required to exist; the file half is still checked.

Default scan set when invoked with no args:
  - README.md
  - CHANGELOG.md (top-level if present)
  - docs/ (recursive, *.md only)

Exit codes:
  0 — every link resolves.
  1 — one or more broken links; details printed to stdout.
  2 — usage error (e.g. nonexistent input path).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Match `[label](target)` where target does NOT start with http://, https://,
# mailto:, or `#`. Greedy on label; non-greedy avoidance not needed because
# the link is opaque to label content (we only consume up to the matching `)`).
_LINK_RE = re.compile(r"\[(?P<label>[^\]]+)\]\((?P<target>(?!https?://|mailto:|#)[^)]+)\)")

# Strip fenced code blocks (```...```) — non-greedy, multiline.
_FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
# Strip inline code (`...`) — same line only, non-greedy.
_INLINE_CODE_RE = re.compile(r"`[^`\n]*`")


def _strip_code(text: str) -> str:
    text = _FENCED_CODE_RE.sub("", text)
    text = _INLINE_CODE_RE.sub("", text)
    return text


def _collect_md_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for r in roots:
        if r.is_file() and r.suffix == ".md":
            files.append(r)
        elif r.is_dir():
            files.extend(sorted(r.rglob("*.md")))
    return files


def _default_roots() -> list[Path]:
    """Repo-default scan set."""
    roots = []
    for candidate in (REPO_ROOT / "README.md", REPO_ROOT / "CHANGELOG.md", REPO_ROOT / "docs"):
        if candidate.exists():
            roots.append(candidate)
    return roots


def _check_file(md: Path) -> list[str]:
    """Return a list of broken-link error strings for this markdown file.

    Fenced (```...```) and inline (`...`) code blocks are stripped before
    link extraction so that documentation containing markdown-link examples
    does not produce false positives.
    """
    errors: list[str] = []
    text = _strip_code(md.read_text(encoding="utf-8", errors="replace"))
    for m in _LINK_RE.finditer(text):
        target = m.group("target").strip()
        # Strip anchor suffix; we don't require anchor existence.
        file_part = target.split("#", 1)[0]
        if not file_part:
            # Pure anchor like `#section` — same-page, skip.
            continue
        resolved = (md.parent / file_part).resolve()
        if not resolved.exists():
            errors.append(f"{md}: broken link [{m.group('label')}]({target}) → {resolved}")
    return errors


def main(argv: list[str]) -> int:
    if argv:
        raw_paths = [Path(p) for p in argv]
        for p in raw_paths:
            if not p.exists():
                print(f"error: path does not exist: {p}", file=sys.stderr)
                return 2
        roots = raw_paths
    else:
        roots = _default_roots()
        if not roots:
            print("error: no default paths exist (README.md / CHANGELOG.md / docs/)", file=sys.stderr)
            return 2

    all_errors: list[str] = []
    for md in _collect_md_files(roots):
        all_errors.extend(_check_file(md))

    if all_errors:
        for e in all_errors:
            print(e)
        print(f"\n{len(all_errors)} broken link(s).")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
