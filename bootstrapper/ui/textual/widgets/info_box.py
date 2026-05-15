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
# state_builder doesn't import from widgets, so this top-level import is
# circular-safe. Keeps render() free of deferred imports.
from ...state_builder import cloud_api_status_text


@dataclass
class ServiceSummary:
    name: str
    source: str = ""
    port: str = ""
    alias: str = ""
    pending: bool = False

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
class CloudApiSummary:
    """One cloud LLM provider — displayed in the Cloud APIs sub-block."""
    name: str           # e.g. "OpenAI"
    enabled: bool = False
    key_set: bool = False


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
    # Cloud LLM provider toggles — rendered in their own sub-block
    # below the service grid, NOT counted as services.
    cloud_apis: list[CloudApiSummary] = field(default_factory=list)


class InfoBoxFooter(Static):
    """Service-count summary line: 14 container · 2 local · 1 gpu · 2 off."""

    def __init__(
        self,
        services: list[ServiceSummary] | None = None,
        cloud_apis: list[CloudApiSummary] | None = None,
    ) -> None:
        super().__init__(classes="info-footer")
        self._services: list[ServiceSummary] = list(services or [])
        self._cloud_apis: list[CloudApiSummary] = list(cloud_apis or [])

    def set_services(self, services: Iterable[ServiceSummary]) -> None:
        self._services = list(services)
        self.refresh()

    def set_cloud_apis(self, cloud_apis: Iterable[CloudApiSummary]) -> None:
        self._cloud_apis = list(cloud_apis)
        self.refresh()

    def _counts(self) -> tuple[int, int, int, int, int]:
        pending = container = local = off = gpu = 0
        for s in self._services:
            if s.pending:
                pending += 1
            elif s.is_disabled:
                off += 1
            elif s.is_gpu:
                gpu += 1
            elif s.is_localhost_or_external:
                local += 1
            else:
                container += 1
        return pending, container, local, gpu, off

    def render(self) -> Text:
        pending, container, local, gpu, off = self._counts()
        line = Text()
        if pending:
            line.append(f"{pending} pending", style=P.WARN)
            line.append("  ·  ", style=P.TEXT_FAINT)
        line.append(f"{container} container", style=P.OK)
        line.append("  ·  ", style=P.TEXT_FAINT)
        line.append(f"{local} local", style=P.ACCENT)
        line.append("  ·  ", style=P.TEXT_FAINT)
        line.append(f"{gpu} gpu", style=P.RESOURCE)
        line.append("  ·  ", style=P.TEXT_FAINT)
        line.append(f"{off} off", style=P.TEXT_MUTED)
        # Cloud APIs are NOT services — separate count, separated by a
        # wider gutter so the eye reads them as a different category.
        # Three-state count mirrors CloudApisRow's per-chip status:
        # "ready" (enabled + key set), "missing key" (enabled but
        # key is empty — defensive, validator should auto-disable),
        # and "off" (disabled). Previously the footer math collapsed
        # "enabled but missing key" into "off", contradicting the
        # body row's ``enabled · key MISSING ⚠`` label.
        if self._cloud_apis:
            cloud_ready = sum(1 for c in self._cloud_apis if c.enabled and c.key_set)
            cloud_missing = sum(1 for c in self._cloud_apis if c.enabled and not c.key_set)
            cloud_off = sum(1 for c in self._cloud_apis if not c.enabled)
            line.append("    ·    ", style=P.TEXT_FAINT)
            line.append(
                f"{cloud_ready} cloud {'api' if cloud_ready == 1 else 'apis'} ready",
                style=P.INFO if cloud_ready else P.TEXT_MUTED,
            )
            if cloud_missing:
                line.append("  ·  ", style=P.TEXT_FAINT)
                line.append(f"{cloud_missing} missing key", style=P.WARN)
            line.append("  ·  ", style=P.TEXT_FAINT)
            line.append(f"{cloud_off} off", style=P.TEXT_MUTED)
        return line


class CloudApisRow(Static):
    """One-line summary of cloud LLM provider toggles.

    Renders inside the InfoPanel body, below the service table. Each
    provider gets a chip with its name + status: ``enabled · key set``,
    ``disabled``, or ``enabled · key MISSING`` (defensive label — the
    validator should prevent this state from reaching docker compose).
    """

    DEFAULT_CSS = """
    CloudApisRow {
        height: auto;
        padding: 1 0 0 0;
        color: #c0caf5;
    }
    """

    def __init__(self, cloud_apis: list[CloudApiSummary] | None = None) -> None:
        super().__init__()
        self._cloud_apis: list[CloudApiSummary] = list(cloud_apis or [])

    def set_cloud_apis(self, cloud_apis: Iterable[CloudApiSummary]) -> None:
        self._cloud_apis = list(cloud_apis)
        self.refresh()

    def render(self) -> Text:
        out = Text()
        out.append("Cloud APIs   ", style=f"bold {P.TEXT}")
        if not self._cloud_apis:
            out.append("(none)", style=P.TEXT_FAINT)
            return out
        first = True
        for c in self._cloud_apis:
            if not first:
                out.append("    ", style=P.TEXT_FAINT)
            first = False
            out.append(c.name, style=P.TEXT)
            out.append("  ", style=P.TEXT_FAINT)
            # Status string is shared with the Rich pre-launch panel
            # in start.py via state_builder.cloud_api_status_text — only
            # the styling is renderer-specific.
            status = cloud_api_status_text(c.enabled, c.key_set)
            if c.enabled and c.key_set:
                style = P.OK
            elif c.enabled and not c.key_set:
                style = P.WARN
            else:
                style = P.TEXT_MUTED
            out.append(status, style=style)
        return out


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
    InfoPanel > .info-body { height: auto; min-height: 5; }
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
        self._footer = InfoBoxFooter(self.state.services, self.state.cloud_apis)
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
        self._footer.set_cloud_apis(state.cloud_apis)
        # Propagate to any CloudApisRow in the body so the visible row
        # tracks the footer count. Without this, a caller passing a
        # fresh ``state.cloud_apis`` got an updated footer over a stale
        # body row — a footgun that previously required every site to
        # remember to call ``cloud_apis_row.set_cloud_apis(...)`` next
        # to ``info_panel.update_state(...)``.
        for w in self._body_widgets:
            if isinstance(w, CloudApisRow):
                w.set_cloud_apis(state.cloud_apis)

    @property
    def body(self) -> Container:
        return self._body


# Back-compat alias
InfoBox = InfoPanel
