#!/usr/bin/env python3
"""Local documentation drift checks for GenAI Vanilla.

Default scope excludes historical audit/plan files, bootstrapper/Textual parallel work,
local virtualenvs, and generated dependency directories.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
EXCLUDED_PARTS = {
    '.git', 'bootstrapper', 'textual', '__pycache__', '.venv', 'venv',
    'tts-venv', 'site-packages', 'plans', '.mypy_cache', '.superpowers', '.kilo',
    '.claude',  # Claude Code's worktrees / scratch dirs are ephemeral, not source
}
EXCLUDED_FILES = {'repo-issues-report.md'}

LINK_RE = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
URL_RE = re.compile(r'^[a-z][a-z0-9+.-]*:', re.I)


def included(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if path.name in EXCLUDED_FILES:
        return False
    return not any(part in EXCLUDED_PARTS for part in rel.parts)


def markdown_files():
    for p in ROOT.rglob('*.md'):
        if included(p):
            yield p


def _strip_fenced_code_blocks(text: str) -> str:
    """Replace fenced ``` code blocks with same-length blanks so line
    numbers and match offsets stay aligned but `[text](url)` inside
    code samples doesn't false-flag as a real link."""
    out = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith('```'):
            in_fence = not in_fence
            out.append('\n' if line.endswith('\n') else '')
            continue
        if in_fence:
            out.append('\n' if line.endswith('\n') else '')
        else:
            out.append(line)
    return ''.join(out)


def check_links():
    broken = []
    for p in markdown_files():
        raw = p.read_text(errors='ignore')
        text = _strip_fenced_code_blocks(raw)
        for match in LINK_RE.finditer(text):
            url = match.group(1).split()[0].strip('<>')
            if URL_RE.match(url) or url.startswith('#') or url.startswith('mailto:'):
                continue
            target = url.split('#', 1)[0]
            if not target:
                continue
            if not (p.parent / target).resolve().exists():
                line = text[:match.start()].count('\n') + 1
                broken.append(f'{p.relative_to(ROOT)}:{line}: broken link {url}')
    return broken


def check_stale_architecture_refs():
    stale_terms = ['architecture.mermaid', 'generate_diagram.sh', '@mermaid-js/mermaid-cli', 'regenerate with Mermaid', '```mermaid']
    hits = []
    for p in markdown_files():
        text = p.read_text(errors='ignore')
        for line_no, line in enumerate(text.splitlines(), 1):
            for term in stale_terms:
                if term in line:
                    hits.append(f'{p.relative_to(ROOT)}:{line_no}: stale architecture term {term}')
    return hits


def check_source_matrix():
    env = (ROOT / '.env.example').read_text(errors='ignore')
    guide = (ROOT / 'docs/deployment/source-configuration.md').read_text(errors='ignore')
    missing = []
    for var in sorted(set(re.findall(r'^([A-Z0-9_]+_SOURCE)=', env, re.M))):
        if var not in guide:
            missing.append(f'docs/deployment/source-configuration.md: missing {var}')
    return missing


def check_required_files():
    required = [
        'docs/deployment/ports-and-routes.md',
        'docs/diagrams/architecture.dot',
        'docs/diagrams/architecture.svg',
        'docs/diagrams/README.md',
    ]
    return [f'missing required docs artifact {path}' for path in required if not (ROOT / path).exists()]


def check_placeholder_urls():
    hits = []
    for p in markdown_files():
        text = p.read_text(errors='ignore')
        for line_no, line in enumerate(text.splitlines(), 1):
            if 'github.com/your-repo' in line:
                hits.append(f'{p.relative_to(ROOT)}:{line_no}: placeholder GitHub URL')
    return hits


def main():
    checks = {
        'links': check_links(),
        'architecture_refs': check_stale_architecture_refs(),
        'source_matrix': check_source_matrix(),
        'required_files': check_required_files(),
        'placeholder_urls': check_placeholder_urls(),
    }
    failed = False
    for name, issues in checks.items():
        if issues:
            failed = True
            print(f'FAIL {name}')
            for issue in issues:
                print(f'  {issue}')
        else:
            print(f'PASS {name}')
    if failed:
        sys.exit(1)

if __name__ == '__main__':
    main()
