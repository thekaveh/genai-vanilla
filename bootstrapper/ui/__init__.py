"""
GenAI Vanilla Stack — anchored-box presentation UI package.

Houses the Rich-based "info box on top, logs streaming underneath" presentation
used by start.py for both the interactive wizard and normal startup. Pure
renderables (info_box, log_pane, status_ribbon) sit on top of a Live shell
(presentation_app) that owns the whole screen during startup.

Design source: docs/superpowers/specs/2026-04-25-startup-presentation-redesign-design.md
(also archived at /Users/kaveh/.claude/plans/what-happened-to-your-jolly-widget.md)
"""
