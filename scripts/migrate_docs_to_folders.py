#!/usr/bin/env python3
"""One-shot migration: docs/services/<name>.md → docs/services/<name>/README.md.

Also rewrites every inbound markdown link from the old path to the new path
across the whole repo. Idempotent: re-running on an already-migrated repo is
a no-op and exits 0.

Usage:
  python scripts/migrate_docs_to_folders.py [--repo-root PATH] [--dry-run]

Exit codes:
  0 — success (or dry-run with changes that would be applied).
  1 — error (couldn't move a file, target folder already non-empty, etc.).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def _scan_flat_docs(services_dir: Path) -> list[Path]:
    """Find docs/services/*.md (NOT files inside subfolders)."""
    return sorted(p for p in services_dir.glob("*.md") if p.is_file())


def _move_one(md: Path, dry_run: bool) -> tuple[Path, Path]:
    """Plan: docs/services/foo.md → docs/services/foo/README.md.

    Returns (old_path, new_path). Performs the move if not dry_run.
    """
    target_dir = md.with_suffix("")
    target_file = target_dir / "README.md"
    if target_file.exists():
        # Already migrated; nothing to do.
        return md, target_file
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
        md.rename(target_file)
    return md, target_file


# Captures: full match, label, target ending in /<service>.md (no slash before)
# Negative lookbehind on `/`: avoid double-rewriting an already-migrated path.
def _build_link_re(service_names: set[str]) -> re.Pattern[str]:
    """Match `[label](some/path/foo.md)` or `[label](services/foo.md)` etc.,
    where the basename (sans extension) is in service_names."""
    names = "|".join(sorted(re.escape(n) for n in service_names))
    # Capture group 1 = label, 2 = path-prefix-with-trailing-slash, 3 = service name.
    return re.compile(rf"\[([^\]]+)\]\(((?:[^)\s]*/)?)({names})\.md(#[^)]*)?\)")


def _rewrite_links_in_file(
    md: Path,
    pattern: re.Pattern[str],
    services_dir_relpath: str,
    dry_run: bool,
) -> int:
    """Rewrite inbound links in one markdown file. Returns count of substitutions."""

    text = md.read_text(encoding="utf-8", errors="replace")

    def _sub(m: re.Match[str]) -> str:
        label = m.group(1)
        prefix = m.group(2)  # e.g. "docs/services/" or "./" or "" or "../"
        name = m.group(3)
        anchor = m.group(4) or ""
        # Only rewrite when prefix points at services_dir (or is a bare service.md
        # next to a file already inside services/). Keep it simple: only rewrite
        # when the prefix is the empty string AND md is inside services_dir,
        # OR the prefix ends with "services/".
        if prefix.endswith("services/"):
            return f"[{label}]({prefix}{name}/README.md{anchor})"
        if prefix == "" and md.parent.name == services_dir_relpath.rsplit("/", 1)[-1]:
            return f"[{label}]({name}/README.md{anchor})"
        # Otherwise: leave alone (link is to something else named foo.md).
        return m.group(0)

    new_text, count = pattern.subn(_sub, text)
    if count and not dry_run:
        md.write_text(new_text, encoding="utf-8")
    return count


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    repo = args.repo_root.resolve()
    services_dir = repo / "docs" / "services"
    if not services_dir.is_dir():
        print(f"error: {services_dir} not found", file=sys.stderr)
        return 1

    flat = _scan_flat_docs(services_dir)
    if not flat:
        print("nothing to migrate (no flat docs/services/*.md files found)")
        return 0

    service_names = {p.stem for p in flat}
    print(f"migration plan: {len(flat)} doc(s) to relocate" + (" (dry-run)" if args.dry_run else ""))
    for p in flat:
        print(f"  {p.relative_to(repo)} → {p.relative_to(repo).with_suffix('')}/README.md")
        _move_one(p, args.dry_run)

    pattern = _build_link_re(service_names)
    total_subs = 0
    scan_roots = [
        repo / "README.md",
        repo / "docs",
    ]
    for root in scan_roots:
        if root.is_file() and root.suffix == ".md":
            total_subs += _rewrite_links_in_file(root, pattern, "docs/services", args.dry_run)
        elif root.is_dir():
            for md in sorted(root.rglob("*.md")):
                total_subs += _rewrite_links_in_file(md, pattern, "docs/services", args.dry_run)
    print(f"link rewrites: {total_subs}" + (" (dry-run; no files written)" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
