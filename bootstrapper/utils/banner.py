"""
Banner display utilities with gradient colors and responsive sizing.

Python implementation of banner functions from start.sh.
"""

import shutil
from typing import List, Optional
from rich.console import Console
from rich.text import Text
from rich.align import Align


class BannerDisplay:
    """Handles banner display with gradient colors and terminal responsiveness."""

    def __init__(self):
        self.console = Console()

    def get_terminal_width(self) -> int:
        """
        Get the current terminal width.

        Returns:
            int: Terminal width in characters
        """
        return shutil.get_terminal_size().columns

    def center_text(self, text: str, width: Optional[int] = None) -> str:
        """
        Center text based on terminal width.
        Replicates the center_text() function from start.sh.

        Args:
            text: Text to center
            width: Terminal width (uses current if None)

        Returns:
            str: Centered text with appropriate padding
        """
        if width is None:
            width = self.get_terminal_width()

        text_length = len(text)
        if text_length >= width:
            return text

        padding = (width - text_length) // 2
        return " " * padding + text

    def apply_enhanced_gradient(
        self, text: str, gradient_colors: Optional[List[str]] = None
    ) -> Text:
        """
        Apply rich multi-color gradient to text.
        Replicates the apply_enhanced_gradient() function from start.sh with 256-color palette.

        Args:
            text: Text to apply gradient to
            gradient_colors: List of color codes for the gradient

        Returns:
            rich.Text: Text with gradient applied
        """
        if gradient_colors is None:
            # Rich blue hue palette based on the original Bash script
            # 256-color codes matching the Bash implementation
            gradient_colors = [
                "color(17)",  # Dark Navy Blue
                "color(18)",  # Dark Blue
                "color(19)",  # Medium Dark Blue
                "color(20)",  # Royal Blue
                "color(21)",  # Bright Blue
                "color(26)",  # Blue-Cyan
                "color(27)",  # Cyan-Blue
                "color(33)",  # Bright Cyan-Blue
                "color(39)",  # Light Cyan-Blue
                "color(45)",  # Cyan
                "color(51)",  # Bright Cyan
                "color(87)",  # Light Blue-Cyan
                "color(123)",  # Light Blue
                "color(159)",  # Very Light Blue
                "color(195)",  # Pale Blue
            ]

        rich_text = Text()
        text_length = len(text)

        if text_length == 0:
            return rich_text

        # Enhanced gradient algorithm matching the original Bash implementation
        for i, char in enumerate(text):
            # Calculate color index with smoother gradient distribution
            # This matches the original algorithm: $((i * palette_size / length))
            color_index = int((i * len(gradient_colors)) // text_length)
            if color_index >= len(gradient_colors):
                color_index = len(gradient_colors) - 1

            color = gradient_colors[color_index]
            rich_text.append(char, style=f"bold {color}")

        return rich_text

    def get_ascii_art_full(self) -> List[str]:
        """
        Get the full ASCII art banner.
        Based on the ASCII art in start.sh show_full_banner() function.

        Returns:
            list: List of ASCII art lines
        """
        return [
            "██████╗ ███████╗███╗   ██╗       █████╗ ██╗",
            "██╔════╝ ██╔════╝████╗  ██║      ██╔══██╗██║",
            "██║  ███╗█████╗  ██╔██╗ ██║█████╗███████║██║",
            "██║   ██║██╔══╝  ██║╚██╗██║╚════╝██╔══██║██║",
            "╚██████╔╝███████╗██║ ╚████║      ██║  ██║██║",
            " ╚═════╝ ╚══════╝╚═╝  ╚═══╝      ╚═╝  ╚═╝╚═╝",
            "",
            "██╗   ██╗ █████╗ ███╗   ██╗██╗██╗     ██╗      █████╗ ",
            "██║   ██║██╔══██╗████╗  ██║██║██║     ██║     ██╔══██╗",
            "██║   ██║███████║██╔██╗ ██║██║██║     ██║     ███████║",
            "╚██╗ ██╔╝██╔══██║██║╚██╗██║██║██║     ██║     ██╔══██║",
            " ╚████╔╝ ██║  ██║██║ ╚████║██║███████╗███████╗██║  ██║",
            "  ╚═══╝  ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝╚══════╝╚══════╝╚═╝  ╚═╝",
        ]

    def get_ascii_art_compact(self) -> List[str]:
        """
        Get the compact ASCII art banner for narrow terminals.
        Based on the show_compact_banner() function from start.sh.

        Returns:
            list: List of compact ASCII art lines
        """
        return [
            "╔═══════════════════════════════════╗",
            "║          Gen-AI Vanilla           ║",
            "║      🤖 AI Development Suite      ║",
            "╚═══════════════════════════════════╝",
        ]

    def show_banner(self, force_compact: bool = False) -> None:
        """
        Display the appropriate banner based on terminal width.
        Replicates the show_banner() function from start.sh.

        Args:
            force_compact: Force compact banner regardless of terminal width
        """
        terminal_width = self.get_terminal_width()

        # Use compact banner for narrow terminals (< 70 chars) or when forced (matches original Bash script)
        if terminal_width < 70 or force_compact:
            self.show_compact_banner()
        else:
            self.show_full_banner()

    def show_full_banner(self) -> None:
        """
        Display the full branded ASCII banner with gradient colors and centering.
        Replicates the show_full_banner() function from start.sh.
        """
        ascii_art = self.get_ascii_art_full()

        self.console.print()  # Empty line

        for line in ascii_art:
            # Apply gradient and center the line
            gradient_text = self.apply_enhanced_gradient(line)
            centered_line = Align.center(gradient_text)
            self.console.print(centered_line)

        # Add tagline
        tagline = "🚀 Modularized, Cross-Platform Gen-AI Vanilla Stack"
        tagline_text = Text(tagline, style="bold cyan")
        self.console.print(Align.center(tagline_text))

        # Add credit information matching original Bash script
        self.console.print()  # Empty line

        # Credit information with colors matching the original (\e[1;94m = bright blue, \e[1;96m = bright cyan, \e[1;93m = bright yellow)
        credit_text = Text("Developed by Kaveh Razavi", style="bold bright_blue")
        self.console.print(Align.center(credit_text))

        url_text = Text(
            "https://github.com/thekaveh/genai-vanilla", style="bold bright_cyan"
        )
        self.console.print(Align.center(url_text))

        license_text = Text("Apache License 2.0", style="bold bright_yellow")
        self.console.print(Align.center(license_text))

        self.console.print()  # Empty line

    def show_compact_banner(self) -> None:
        """
        Display a compact banner for narrow terminals.
        Replicates the show_compact_banner() function from start.sh.
        """
        ascii_art = self.get_ascii_art_compact()

        self.console.print()  # Empty line

        for line in ascii_art:
            # Apply gradient and center the line - using 256-color compact palette
            compact_gradient = [
                "color(51)",
                "color(27)",
                "color(21)",
                "color(19)",
                "color(129)",
            ]  # cyan to blue to magenta
            gradient_text = self.apply_enhanced_gradient(line, compact_gradient)
            centered_line = Align.center(gradient_text)
            self.console.print(centered_line)

        # Add compact tagline
        tagline = "🚀 AI Dev Suite"
        tagline_text = Text(tagline, style="bold cyan")
        self.console.print(Align.center(tagline_text))

        # Add credit information for compact banner (same as full banner)
        self.console.print()  # Empty line

        credit_text = Text("Developed by Kaveh Razavi", style="bold bright_blue")
        self.console.print(Align.center(credit_text))

        url_text = Text(
            "https://github.com/thekaveh/genai-vanilla", style="bold bright_cyan"
        )
        self.console.print(Align.center(url_text))

        license_text = Text("Apache License 2.0", style="bold bright_yellow")
        self.console.print(Align.center(license_text))

        self.console.print()  # Empty line

    def show_section_header(self, title: str, icon: str = "🔧") -> None:
        """
        Display a section header with consistent formatting.

        Args:
            title: Section title
            icon: Icon to display before the title
        """
        header_text = Text(f"{icon} {title}", style="bold bright_white")
        self.console.print(header_text)

    def show_status_message(self, message: str, status: str = "info") -> None:
        """
        Display a status message with appropriate styling.

        Args:
            message: Message to display
            status: Status type ("info", "success", "warning", "error")
        """
        icons = {"info": "📋", "success": "✅", "warning": "⚠️", "error": "❌"}

        colors = {
            "info": "bright_white",
            "success": "bright_green",
            "warning": "bright_yellow",
            "error": "bright_red",
        }

        icon = icons.get(status, "📋")
        color = colors.get(status, "bright_white")

        status_text = Text(f"{icon} {message}", style=color)
        self.console.print(status_text)

    def show_service_table_header(self) -> None:
        """Display the service status table header."""
        self.console.print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        self.console.print("🎯 GenAI Vanilla Stack - Service Status")
        self.console.print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        # Table header
        header_format = "%-25s %-15s %-35s %-8s"
        header_line = header_format % ("Service", "Source", "Endpoint", "Scale")
        header_text = Text(header_line, style="bold bright_white underline")
        self.console.print(header_text)
        self.console.print("─" * 90)

    def show_service_table_footer(self) -> None:
        """Display the service status table footer."""
        self.console.print(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
