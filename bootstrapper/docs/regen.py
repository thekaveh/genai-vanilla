"""Per-service docs + diagram regenerator.

Usage:
  python -m bootstrapper.docs.regen <service> [--out-root PATH] [--dry-run]
                                              [--section-only] [--check]
  python -m bootstrapper.docs.regen --all     [same flags]

Exit codes:
  0 — success.
  1 — manifest error.
  2 — drift detected (--check mode only).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .deps_resolver import build_doc_graph, doc_folder_to_manifests
from .deps_section_writer import render_section
from .diagram_renderer import render_html, render_svg

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_SERVICES = REPO_ROOT / "docs" / "services"
SERVICES_DIR = REPO_ROOT / "services"

DEPS_HEADER = "## Dependencies & Integrations"
DEPS_SECTION_FENCE_RE = re.compile(
    r"^## Dependencies & Integrations\b.*?(?=^## |\Z)",
    re.DOTALL | re.MULTILINE,
)


def _enumerate_doc_folders() -> list[str]:
    return sorted(
        p.name for p in DOCS_SERVICES.iterdir()
        if p.is_dir() and (p / "README.md").exists()
    )


def _upsert_section(readme_text: str, section: str) -> str:
    """Replace an existing Dependencies section, or append it if missing."""
    if DEPS_HEADER in readme_text:
        return DEPS_SECTION_FENCE_RE.sub(section.rstrip() + "\n\n", readme_text, count=1).rstrip() + "\n"
    return readme_text.rstrip() + "\n\n" + section


def _process(name: str, out_root: Path, dry_run: bool, section_only: bool, check: bool) -> int:
    graph = build_doc_graph(name, SERVICES_DIR)
    target_dir = out_root / name
    section = render_section(graph)

    # README.md
    readme_path = target_dir / "README.md"
    existing_readme = readme_path.read_text() if readme_path.exists() else ""
    new_readme = _upsert_section(existing_readme, section)

    artifacts: list[tuple[Path, str]] = [(readme_path, new_readme)]
    if not section_only:
        artifacts.append((target_dir / "architecture.svg", render_svg(graph)))
        artifacts.append((target_dir / "architecture.html", render_html(graph)))

    drift = 0
    for path, content in artifacts:
        existing = path.read_text() if path.exists() else ""
        if existing != content:
            if check:
                drift += 1
                print(f"DRIFT: {path}")
            elif dry_run:
                print(f"would write {path}")
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
    return drift


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="bootstrapper.docs.regen")
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("service", nargs="?", help="Single doc folder name (e.g. hermes).")
    grp.add_argument("--all", action="store_true", help="Process every doc folder under docs/services/.")
    ap.add_argument("--out-root", type=Path, default=DOCS_SERVICES)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--section-only", action="store_true", help="Only write README's deps section; skip HTML+SVG.")
    ap.add_argument("--check", action="store_true", help="Exit 2 if any artifact would change. Implies --dry-run.")
    args = ap.parse_args(argv)

    targets = _enumerate_doc_folders() if args.all else [args.service]
    if not args.all and args.service not in _enumerate_doc_folders():
        # Allow regen of a doc folder before its README exists (initial run).
        if args.service not in {f.split("/")[-1] for f in _enumerate_doc_folders()}:
            # As long as build_doc_graph won't raise — give it a shot
            pass

    total_drift = 0
    for name in targets:
        try:
            total_drift += _process(name, args.out_root, args.dry_run, args.section_only, args.check)
        except KeyError as e:
            print(f"manifest error for {name}: {e}", file=sys.stderr)
            return 1

    if args.check and total_drift:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
