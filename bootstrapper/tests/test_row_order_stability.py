"""Row order in the wizard's overview is fixed by topology canonical
order — source/port changes must never reorder rows.

Two regressions used to hide here:
  * `wizard_screen.action_confirm` re-sorted `self._services` by ascending
    displayed port after every confirm. A localhost source surfacing a
    small port pushed that row to the top, breaking adjacency.
  * `recompute_ports_for_base` and the launch-flow construction did the
    same on base-port change.

Both have been removed. This test pins the contract.
"""

from __future__ import annotations


def _canonical_names() -> list[str]:
    from services.topology import get_topology
    return [r.display_name for r in get_topology().rows]


def test_recompute_ports_preserves_canonical_order():
    """`recompute_ports_for_base` returns rows in the same order it was
    handed — does not re-sort by port."""
    from core.config_parser import ConfigParser
    from ui.textual.integration import recompute_ports_for_base
    from ui.textual.widgets.service_table import ServiceRow

    cp = ConfigParser(str(__import__("pathlib").Path(__file__).resolve().parent.parent.parent))
    names = _canonical_names()
    input_rows = [ServiceRow(name=n, source="container") for n in names]
    # Use the existing port offsets from topology (relative to default base).
    from services.topology import get_topology
    t = get_topology(base_port=63000)
    port_offsets = {pv: p - 63000 for pv, p in t.port_defaults.items()}

    out = recompute_ports_for_base(63100, input_rows, cp, port_offsets)
    assert [r.name for r in out] == names, (
        "recompute_ports_for_base must not re-sort rows"
    )


def test_canonical_order_places_llm_engine_immediately_after_litellm():
    """The original report was 'ComfyUI comes right after LiteLLM and
    LLM Engine shows up well after ComfyUI'. The contract is that LLM
    Engine sits immediately after LiteLLM, before any Media row."""
    names = _canonical_names()
    i_litellm = names.index("LiteLLM")
    i_llm_engine = names.index("LLM Engine")
    i_comfyui = names.index("ComfyUI")
    assert i_llm_engine == i_litellm + 1, (
        f"LLM Engine should immediately follow LiteLLM in canonical order, "
        f"but indices are LiteLLM={i_litellm}, LLM Engine={i_llm_engine}"
    )
    assert i_llm_engine < i_comfyui, (
        f"LLM Engine must come before any Media row (incl. ComfyUI)"
    )
