"""
InfoPanel — bordered, brand-titled info panel anchoring the wizard screen.

Mockup 003 layout:

    ┌─────────────────────────────────────────────────────────────────┐
    │ GENAI VANILLA                Kaveh · Apache-2.0 · github.com/.. │
    │                                                                 │
    │ █  ⌕  Filter services...                                        │
    │ █  ▸ ● supabase-db   INFRA  supabase.localhost  :63001 …        │
    │ █  · ● supabase-stu  INFRA  studio.localhost    :63009 …        │
    │ █                                                               │
    │ █  Command:  ./start.sh --llm-provider-source ollama  [▶ copy]  │
    │ 14 container · 2 local · 1 gpu · 2 off                          │
    └─────────────────────────────────────────────────────────────────┘

Module name `info_box.py` retained for back-compat with import paths;
class is renamed `InfoPanel`. `InfoBox` alias kept too.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from .. import palette as P


@dataclass
class ServiceSummary:
    name: str
    source: str = ""
    port: str = ""
    alias: str = ""

    @property
    def is_disabled(self) -> bool:
        return self.source.lower() == "disabled" or not self.source

    @property
    def is_localhost_or_external(self) -> bool:
        s = self.source.lower()
        return "localhost" in s or "external" in s or s == "api"

    @property
    def is_gpu(self) -> bool:
        return "gpu" in (self.source or "").lower()


@dataclass
class BrandInfo:
    name: str = "GenAI Vanilla"
    tagline: str = "Gen-AI Development Suite"
    creator: str = "Kaveh Razavi"
    creator_email: str = "kaveh.razavi@gmail.com"
    license: str = "Apache License 2.0"
    repo: str = "github.com/thekaveh/genai-vanilla"
    version: str = ""


@dataclass
class InfoBoxState:
    brand: BrandInfo = field(default_factory=BrandInfo)
    services: list[ServiceSummary] = field(default_factory=list)


class InfoBoxFooter(Static):
    """Service-count summary line: 14 container · 2 local · 1 gpu · 2 off."""

    def __init__(self, services: list[ServiceSummary] | None = None) -> None:
        super().__init__(classes="info-footer")
        self._services: list[ServiceSummary] = list(services or [])

    def set_services(self, services: Iterable[ServiceSummary]) -> None:
        self._services = list(services)
        self.refresh()

    def _counts(self) -> tuple[int, int, int, int]:
        container = local = off = gpu = 0
        for s in self._services:
            if s.is_disabled:
                off += 1
            elif s.is_gpu:
                gpu += 1
            elif s.is_localhost_or_external:
                local += 1
            else:
                container += 1
        return container, local, gpu, off

    def render(self) -> Text:
        container, local, gpu, off = self._counts()
        line = Text()
        line.append(f"{container} container", style=P.OK)
        line.append("  ·  ", style=P.TEXT_FAINT)
        line.append(f"{local} local", style=P.ACCENT)
        line.append("  ·  ", style=P.TEXT_FAINT)
        line.append(f"{gpu} gpu", style=P.RESOURCE)
        line.append("  ·  ", style=P.TEXT_FAINT)
        line.append(f"{off} off", style=P.TEXT_MUTED)
        return line


class InfoPanel(Container):
    """Bordered info panel hosting brand title, accent bar, body slot, counts."""

    DEFAULT_CSS = """
    InfoPanel {
        border: round #2b2f4a;
        background: #0e0f18;
        padding: 0 1;
        height: auto;
        width: 100%;
    }
    InfoPanel > .info-body { height: auto; min-height: 4; }
    InfoPanel > InfoBoxFooter { height: 1; padding-top: 1; }
    """

    def __init__(
        self,
        state: InfoBoxState | None = None,
        *,
        body_widgets: list | None = None,
        title: str = "",
        id: str | None = None,
    ) -> None:
        super().__init__(id=id)
        self.state = state or InfoBoxState()
        self._body_widgets = list(body_widgets or [])
        self._body = Container(*self._body_widgets, classes="info-body")
        self._footer = InfoBoxFooter(self.state.services)
        self._title = title

    def on_mount(self) -> None:
        # Set border title on Container (Textual native — renders inline
        # with the top border).
        if self._title:
            self.border_title = self._title

    def compose(self) -> ComposeResult:
        yield self._body
        yield self._footer

    def update_state(self, state: InfoBoxState) -> None:
        self.state = state
        self._footer.set_services(state.services)

    @property
    def body(self) -> Container:
        return self._body


# Back-compat alias
InfoBox = InfoPanel
