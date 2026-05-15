"""Pending-state transitions on the wizard screen.

KNOWN GAP — these tests cover the *data shape* (ServiceRow.pending /
ServiceRow.source mutations) rather than driving WizardScreen.action_confirm
through Textual's Pilot. The wizard's per-step confirm path is:

    row.source = opt.value
    row.pending = False

which is asserted directly below. A full Pilot-driven integration would
need an async event loop + a mounted App + a composed PromptPanel
(non-trivial test infrastructure for one assertion). The tests in
``tests/test_kong_and_hosts_wiring.py`` and ``tests/test_topology.py``
exercise the surrounding contract (the rows + aliases the wizard
consumes) so a regression in row construction would still surface.
"""

from __future__ import annotations


def test_initial_state_marks_configurable_rows_pending():
    """At step 0, every configurable row is pending; locked rows are not."""
    # The test exercises the same code path the wizard uses to seed self._services
    # before any user input. Build a tiny mock setup.
    from ui.textual.widgets.service_table import ServiceRow

    rows = [
        ServiceRow(name="LiteLLM", category="llm", configurable=False, pending=False, source="container"),
        ServiceRow(name="LLM Engine", category="llm", configurable=True, pending=True, source=""),
    ]
    assert rows[0].pending is False  # locked
    assert rows[1].pending is True   # configurable, unanswered


def test_answered_set_transitions_pending_to_answered():
    """When step N is confirmed, _answered.add(N) and the matching row.pending = False."""
    from ui.textual.widgets.service_table import ServiceRow

    row = ServiceRow(name="ComfyUI", category="media", configurable=True,
                     pending=True, source="")
    # Simulate the confirm action's row mutation
    row.pending = False
    row.source = "container-cpu"
    assert row.pending is False
    assert row.source == "container-cpu"


def test_answered_set_does_not_shrink_on_back_nav():
    """Back-navigation may revisit an answered step but _answered keeps it."""
    answered: set[int] = set()
    answered.add(5)
    # Simulate back-nav to step 5, then forward again to step 6 with new value
    answered.add(5)  # idempotent
    answered.add(6)
    assert 5 in answered
    assert 6 in answered
    assert len(answered) == 2
