"""
Textual-based TUI for Atlas.

Screens / app are not imported eagerly — pulling them in only when the
caller asks (e.g. ``from .app import AtlasApp``) keeps the
widget package importable on its own.
"""

__all__ = []
