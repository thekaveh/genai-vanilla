"""
CommandPreview — inline + multi-line command bar.

Mockup 003 (inline, in InfoPanel body):
    Command: ./start.sh --llm-provider-source ollama-localhost   [▶ copy]

Mockup 005 (multi-line, in confirm screen):
    ./start.sh \\
      --llm-provider-source ollama-localhost  // local inference
      --comfyui-source container-gpu          // GPU image gen
      --base-port 63000                       // free port range
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rich.text import Text
from textual.widget import Widget

from .. import palette as P


@dataclass
class FlagLine:
    flag: str
    value: str = ""
    hint: str = ""


@dataclass
class CommandSpec:
    program: str = "./start.sh"
    flags: list[FlagLine] = field(default_factory=list)


class CommandPreview(Widget):
    """Inline (single-line) command-bar."""

    DEFAULT_CSS = """
    CommandPreview {
        height: auto;
        background: #0e0f18;
        padding: 0 1;
        border: solid #1e2038;
        margin: 0 0 1 0;
    }
    """

    def __init__(
        self,
        command: str = "",
        *,
        copyable: bool = True,
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.command = command
        self.copyable = copyable

    def set_command(self, command: str) -> None:
        self.command = command
        self.refresh()

    def render(self) -> Text:
        line = Text()
        line.append("Command: ", style=P.TEXT_MUTED)
        for token in self.command.split(" "):
            if not token:
                continue
            if token.startswith("--"):
                line.append(token + " ", style=P.ACCENT)
            elif token.endswith(".sh") or token.startswith("./"):
                line.append(token + " ", style=P.TEXT_BRIGHT)
            else:
                line.append(token + " ", style=P.TEXT)
        if self.copyable:
            line.append(" ")
            line.append("[▶ copy]", style=P.TEXT_MUTED)
        return line


class CommandPreviewMultiline(Widget):
    """Multi-line command preview (mockup 005)."""

    DEFAULT_CSS = """
    CommandPreviewMultiline {
        height: auto;
        background: #0e0f18;
        padding: 1 2;
        border: solid #1e2038;
        margin: 0 0 1 0;
    }
    """

    def __init__(self, spec: CommandSpec, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self.spec = spec

    def render(self) -> Text:
        out = Text()
        out.append(self.spec.program, style=f"bold {P.TEXT_BRIGHT}")
        if self.spec.flags:
            out.append(" \\", style=P.TEXT_FAINT)
        # Compute padding so // hints align
        max_pair_len = 0
        for f in self.spec.flags:
            pair = f"{f.flag} {f.value}".rstrip()
            max_pair_len = max(max_pair_len, len(pair))

        for f in self.spec.flags:
            out.append("\n  ")
            out.append(f.flag, style=P.ACCENT)
            if f.value:
                out.append(" ")
                out.append(f.value, style=P.TEXT)
            if f.hint:
                pair_len = len(f"{f.flag} {f.value}".rstrip())
                pad = max_pair_len - pair_len + 2
                out.append(" " * pad)
                out.append(f"// {f.hint}", style=P.TEXT_FAINT)
        return out
