"""
Textual-based TUI for GenAI Vanilla.

Screens / app are not imported eagerly — pulling them in only when the
caller asks (e.g. ``from .app import GenAIVanillaApp``) keeps the
widget package importable on its own.
"""

__all__ = []
