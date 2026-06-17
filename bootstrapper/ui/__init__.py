"""
Atlas — bootstrapper UI package.

The interactive bootstrapper UI is a Textual app under ``ui/textual/``
(``run_setup_flow`` and ``run_launch_flow`` in ``ui/textual/integration.py``).
The top-level ``ui`` package keeps the framework-agnostic data model
(``state.py``, ``state_builder.py``) consumed by both the Textual wizard
and the ``--no-tui`` linear stdout flow in ``start.py``. ``term_caps.py``
exposes the small ``is_tui_capable`` helper used by ``start.py`` to pick
between the two.
"""
