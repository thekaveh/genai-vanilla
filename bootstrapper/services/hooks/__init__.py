"""
Per-service hooks for complex auto-managed env var logic.

A manifest may declare `hook: services.hooks.<name>`. The bootstrapper imports
the module and calls its `apply(env)` function AFTER the declarative effects
have been applied. The hook can read/mutate any var in `env`, but the
validator restricts mutations to auto_managed vars owned by the manifest.

Phase A/B/C: hooks are defined as data-only modules with `apply()` callables.
They are NOT yet invoked by start.py — that wiring is the deferred
bootstrapper refactor follow-up. Tests in bootstrapper/tests/test_hooks.py
exercise the apply() functions directly.
"""
