"""
UI rendering for the interactive setup wizard.

Handles the banner, progress bar, and command preview using Rich.
All visual output between InquirerPy prompts flows through this module.
Uses the full ASCII logo but without credits to fit wizard prompts.
"""

import shutil
from typing import Dict, Optional

from rich.console import Console
from rich.text import Text
from rich.align import Align
from rich.progress_bar import ProgressBar
from rich.columns import Columns

from utils.banner import BannerDisplay


class UIRenderer:
    """Renders wizard UI elements using Rich."""

    def __init__(self):
        self.console = Console()
        self.banner = BannerDisplay()

    def _clear_screen(self) -> None:
        """Clear the visible screen and reposition cursor at the top."""
        self.console.clear()

    def _render_wizard_banner(self) -> None:
        """Render the full ASCII logo with gradient and credits.

        Uses the same banner as the normal startup via show_full_banner().
        """
        self.banner.show_full_banner()

    def _render_header(self) -> None:
        """Render the wizard header: logo + subtitle."""
        self._render_wizard_banner()
        self.console.print()
        subtitle = Text("Interactive Setup Wizard", style="bold color(75)")
        self.console.print(Align.center(subtitle))

    def render_service_screen(
        self,
        step: int,
        total: int,
        selections: Dict[str, str],
        env_defaults: Optional[Dict[str, str]] = None,
    ) -> None:
        """Render the screen for a service selection prompt."""
        self._clear_screen()
        self._render_header()
        self._render_progress_bar(step, total)
        self._render_command_preview(selections, env_defaults)
        self._render_nav_hints()
        self.console.print()

    def render_stack_options_screen(
        self,
        selections: Dict[str, str],
        step: int,
        total: int,
        env_defaults: Optional[Dict[str, str]] = None,
    ) -> None:
        """Render the screen for stack options (port, cold, hosts)."""
        self._clear_screen()
        self._render_header()
        self._render_progress_bar(step, total)
        self._render_command_preview(selections, env_defaults)
        self._render_nav_hints()
        self.console.print()

    def render_completed_screen(
        self,
        total: int,
        selections: Dict[str, str],
        env_defaults: Optional[Dict[str, str]] = None,
    ) -> None:
        """Render the screen with 100% green progress bar after all steps are done."""
        self._clear_screen()
        self._render_header()
        self._render_progress_bar(total, total, completed=True)
        self._render_command_preview(selections, env_defaults)
        self.console.print()
        self.console.print(
            Align.center(Text("✅ Configuration complete", style="bold bright_green"))
        )
        self.console.print()

    def _render_progress_bar(
        self, step: int, total: int, completed: bool = False
    ) -> None:
        """Render a sleek progress bar using Rich's built-in ProgressBar.

        The bar reflects completed steps: when viewing step N, N-1 steps are done.
        Pass completed=True after the last step to show 100% in green.
        """
        terminal_width = shutil.get_terminal_size().columns
        bar_width = min(terminal_width - 30, 40)
        bar_width = max(bar_width, 10)

        done = total if completed else step - 1
        pct = int((done / total) * 100) if total > 0 else 0
        label_str = "Complete " if completed else f"Step {step}/{total} "
        label = Text(label_str, style="bright_green" if completed else "color(245)")
        bar = ProgressBar(
            total=total,
            completed=done,
            width=bar_width,
            complete_style="bright_green" if completed else "color(75)",
            finished_style="bright_green",
        )
        pct_text = Text(f" {pct}%", style="bright_green" if completed else "color(245)")

        self.console.print(Align.center(Columns([label, bar, pct_text], padding=0)))

    def _render_nav_hints(self) -> None:
        """Render keyboard shortcut hints in a subtle, centered style."""
        hint = Text()
        hint.append("esc ", style="color(245)")
        hint.append("restart", style="color(240)")
        hint.append("  ·  ", style="color(238)")
        hint.append("ctrl+c ", style="color(245)")
        hint.append("quit", style="color(240)")
        self.console.print(Align.center(hint))

    def _render_command_preview(
        self,
        selections: Dict[str, str],
        env_defaults: Optional[Dict[str, str]] = None,
    ) -> None:
        """Render the live command preview, showing only flags that differ from defaults."""
        if not selections:
            return

        changed = {}
        for service_key, value in selections.items():
            env_var = service_key.upper().replace("-", "_") + "_SOURCE"
            default_value = (env_defaults or {}).get(env_var, "")
            if value != default_value:
                changed[service_key] = value

        if not changed:
            cmd = Text("Command: ", style="color(245)")
            cmd.append("./start.sh", style="bright_white")
            cmd.append("  (using .env defaults)", style="color(245)")
            self.console.print(Align.center(cmd))
            return

        cmd = Text("Command: ", style="color(245)")
        cmd.append("./start.sh", style="bright_white")

        for service_key, value in changed.items():
            flag = " --" + service_key.replace("_", "-") + "-source"
            cmd.append(flag, style="color(75)")
            cmd.append(f" {value}", style="color(123)")

        self.console.print(Align.center(cmd))
