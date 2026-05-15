"""Regenerates docs/diagrams/architecture.dot from the topology.

Run: cd bootstrapper && uv run python -m tools.generate_architecture_diagram
"""

from __future__ import annotations

from pathlib import Path

from services.topology import (
    CATEGORY_COLORS,
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    get_topology,
)


def generate(services_root: Path, output: Path) -> None:
    topology = get_topology(services_root)
    by_category: dict[str, list[str]] = {c: [] for c in CATEGORY_ORDER}
    for name in topology.canonical_order:
        cat = topology.category_of[name]
        if cat in by_category:
            by_category[cat].append(name)

    lines: list[str] = [
        'digraph stack {',
        '  rankdir=TB;',
        '  bgcolor="#0e0f18";',
        '  node [shape=box, style="filled,rounded", fontname="Helvetica", fontcolor="#c0caf5", color="#2b2f4a"];',
        '  edge [color="#3d4261"];',
        '',
    ]

    for cat in CATEGORY_ORDER:
        members = by_category[cat]
        if not members:
            continue
        lines.append(f'  subgraph "cluster_{cat}" {{')
        lines.append(f'    label="{CATEGORY_LABELS[cat]}";')
        lines.append(f'    fontcolor="{CATEGORY_COLORS[cat]}";')
        lines.append(f'    color="{CATEGORY_COLORS[cat]}";')
        for m in members:
            lines.append(f'    "{m}" [fillcolor="{CATEGORY_COLORS[cat]}33"];')
        lines.append('  }')
        lines.append('')

    # Edges
    from services.manifests import load_manifests
    for m in load_manifests(services_root):
        for dep in m.depends_on.required:
            lines.append(f'  "{dep}" -> "{m.name}";')

    lines.append('}')
    output.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent.parent
    generate(
        project_root / "services",
        project_root / "docs" / "diagrams" / "architecture.dot",
    )
    print(f"Wrote {project_root / 'docs' / 'diagrams' / 'architecture.dot'}")
