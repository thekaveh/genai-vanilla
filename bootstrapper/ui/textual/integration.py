"""
Production bridge between the Textual TUI and ``bootstrapper/start.py``.

Single public entry: ``run_setup_flow(starter, hosts_manager)``.

The whole user-facing flow lives inside ONE Textual ``WizardScreen``:
the wizard prompts run in the lower pane during the setup phase, then
the same pane swaps in log filter chips + a live log surface for the
pipeline (validate / ports / kong / supabase / hosts / encryption /
localhost) and the docker compose build / up / verify / logs.

start.py just calls this and exits when it returns.
"""

from __future__ import annotations

from pathlib import Path

from textual.app import App
from textual.binding import Binding


_THEME_PATH = Path(__file__).parent / "theme.css"


# Module-level sink for wizard-time diagnostic warnings (cloud /v1/models
# fetch failures, etc.). The WizardScreen populates this with a thin
# adapter around its ``_safe_log`` once the screen exists; the cloud
# options_provider closures (built BEFORE the screen) read from it.
# ``None`` until the screen wires it; closures must guard against that.
_WIZARD_WARN_SINK = None


def _set_wizard_warn_sink(fn) -> None:
    """Called by WizardScreen.__init__ to register a logger callable
    of shape ``(msg: str) -> None``. Idempotent; reset to None on
    screen teardown.
    """
    global _WIZARD_WARN_SINK
    _WIZARD_WARN_SINK = fn


def _wizard_warn(msg: str) -> None:
    fn = _WIZARD_WARN_SINK
    if fn is None:
        return
    try:
        fn(msg)
    except Exception:
        pass


# ─── helpers ─────────────────────────────────────────────────────────

_TAG_BY_KEY = {
    "supabase": "INFRA", "supabase-db": "INFRA", "supabase-studio": "INFRA",
    "redis": "INFRA", "kong": "INFRA", "kong_api_gateway": "INFRA",
    "litellm": "LLM", "litellm-init": "LLM",
    "llm_provider": "LLM", "ollama": "LLM",
    "open_webui": "TOOL", "open-webui": "TOOL",
    "comfyui": "ML", "stt_provider": "ML", "tts_provider": "ML",
    "backend": "ML", "doc_processor": "ML", "multi2vec_clip": "ML",
    "multi2vec-clip": "ML",
    "weaviate": "DATA", "minio": "DATA", "neo4j": "DATA", "neo4j_graph_db": "DATA",
    "neo4j-graph-db": "DATA",
    "n8n": "TOOL", "searxng": "TOOL", "openclaw": "TOOL", "jupyterhub": "TOOL",
}


def _tag_for(key: str) -> str:
    k = (key or "").lower().replace(" ", "_")
    if k in _TAG_BY_KEY:
        return _TAG_BY_KEY[k]
    for prefix, tag in _TAG_BY_KEY.items():
        if k.startswith(prefix):
            return tag
    return ""


def _badges_for_option(opt: str, *, recommended: bool = False) -> list[str]:
    s = (opt or "").lower()
    badges: list[str] = []
    if recommended: badges.append("rec.")
    if "container-gpu" in s or s.endswith("-gpu"): badges.append("GPU")
    elif "container-cpu" in s or s.endswith("-cpu"): badges.append("CPU")
    if "localhost" in s: badges.append("local")
    if s == "external": badges.append("external")
    if s == "none": badges.append("cloud-only")
    if s == "disabled": badges.append("disabled")
    return badges


def _option_hint(opt: str) -> str:
    s = (opt or "").lower()
    if "container-gpu" in s or s.endswith("-gpu"):
        return "Run in a container with NVIDIA GPU acceleration"
    if "container-cpu" in s or s.endswith("-cpu"):
        return "Run in a container on CPU only"
    if s == "container":
        return "Run as a Docker container alongside the rest of the stack"
    if "localhost" in s:
        return "Use an instance you already run on this host"
    if "external" in s:
        return "Connect to an instance running elsewhere"
    if s == "api":
        return "Use a hosted cloud API (OpenAI / Anthropic / OpenRouter)"
    if s == "disabled":
        return "Skip this service entirely"
    return ""


def _build_steps_and_rows(config_parser, hosts_manager):
    """Build the wizard steps + service rows from real config."""
    from wizard.service_discovery import ServiceDiscovery
    from ui.state_builder import build_app_state
    from core.config_parser import DEFAULT_BASE_PORT
    from .widgets.prompt_panel import PromptOption, PromptStep
    from .widgets.service_table import ServiceRow

    services_info = ServiceDiscovery(config_parser).discover()
    env_vars = config_parser.parse_env_file()
    current_base_port = int(env_vars.get("SUPABASE_DB_PORT", DEFAULT_BASE_PORT))

    # Sort the wizard's service-source questions to match the stack
    # overview's port-ascending order. The overview sorts by the
    # service's *displayed* port — which for localhost sources comes
    # from the endpoint env var (e.g. LITELLM_BASE_URL) and may be very
    # different from the container offset (a localhost ComfyUI shows
    # :8000, not :63018). So sort by the resolved port, not the offset.
    from ui.state_builder import lookup_service_meta, resolve_port as _resolve_port
    from core.port_manager import PortManager  # noqa: F401 (kept for callers below)

    def _svc_port_key(svc) -> tuple:
        meta = lookup_service_meta(svc.display_name)
        port_var = (meta or {}).get("port_var") if meta else None
        source = svc.current_value or ""
        resolved = _resolve_port(svc.display_name, source, port_var, env_vars)
        if not resolved:
            return (1, svc.display_name)
        try:
            return (0, int(resolved.lstrip(":")))
        except ValueError:
            return (1, svc.display_name)

    services_info = sorted(services_info, key=_svc_port_key)

    steps: list = []
    # Inline step_total values below are illustrative only — Ollama and
    # cloud sub-steps are spliced in dynamically below, so the count
    # isn't knowable up-front. The screen recomputes ``step_total`` at
    # display time from the final ``len(self._steps)`` (see
    # WizardScreen._render_step / dataclasses.replace), and we
    # rewrite each step's ``step_total`` once the list is complete
    # below — so the inline values seeded here never reach the UI.
    total = 0  # placeholder; rewritten below after the dynamic splice

    # Base port is asked FIRST so all subsequent service-port displays
    # reflect the chosen base port immediately.
    steps.append(PromptStep(
        title="Base port  ·  range", step_index=1, step_total=total,
        heading="Which base port range do you want?",
        subtitle="Every service port is computed as base_port + offset. "
                 "Type a port (1024–65000), or press Enter to keep the current value.",
        options=[],
        default_value=str(current_base_port),
        service_name="",
        kind="number",
        number_min=1024,
        number_max=65000,
    ))

    # LLM cluster steps (Ollama variants + cloud secret/multiselect
    # pairs) live in wizard/llm_steps.py; spliced in below right after
    # the LLM Engine source step so the LLM section reads coherently.
    from wizard.llm_steps import build_ollama_steps, build_cloud_steps

    for i, svc in enumerate(services_info):
        opts = [
            PromptOption(
                value=opt, label=opt, hint=_option_hint(opt),
                badges=_badges_for_option(opt, recommended=(opt == svc.current_value)),
            )
            for opt in svc.options
        ]
        default = svc.current_value if svc.current_value in svc.options else (
            svc.options[0] if svc.options else None
        )
        steps.append(PromptStep(
            title=f"{svc.display_name}  ·  source",
            step_index=i + 2, step_total=total,
            heading=f"How should {svc.display_name} run?",
            subtitle=svc.description or "",
            options=opts, default_value=default, service_name=svc.display_name,
            service_key=svc.key,
        ))
        # Splice the entire LLM cluster RIGHT AFTER the LLM Engine
        # source step: Ollama variants, then cloud-provider key+model
        # pairs. Keeps engine + local + cloud adjacent in the wizard
        # flow instead of separating them with unrelated service-source
        # steps. Each spliced sub-step has its own skip_if_prev gating.
        if svc.display_name == "LLM Engine":
            steps.extend(build_ollama_steps(env_vars, _wizard_warn))
            steps.extend(build_cloud_steps(env_vars, _wizard_warn))

    steps.append(PromptStep(
        title="Cold start  ·  rebuild", step_index=len(services_info) + 2,
        step_total=total,
        heading="Reset the existing stack state?",
        subtitle="Cold start removes all containers & volumes, then re-creates them.",
        options=[
            PromptOption("no", "No — keep existing data",
                         "fast — reuses volumes, current containers"),
            PromptOption("yes", "Yes — rebuild from scratch",
                         "slow — drops volumes; cleanest reset"),
        ],
        default_value="no", service_name="",
    ))
    steps.append(PromptStep(
        title="Hosts setup  ·  /etc/hosts", step_index=len(services_info) + 3,
        step_total=total,
        heading="Configure the *.localhost host entries?",
        subtitle="Required for Kong's wildcard routing.",
        options=[
            PromptOption("default", "Default — warn if missing", "no sudo needed"),
            PromptOption("setup", "Setup now (requires sudo)",
                         "writes /etc/hosts entries for *.localhost services"),
            PromptOption("skip", "Skip — I'll handle it manually",
                         "no warnings, no changes"),
        ],
        default_value="default", service_name="",
    ))
    steps.append(PromptStep(
        title="Confirm  ·  launch the stack", step_index=0, step_total=0,
        heading="Launch the stack with this configuration?",
        subtitle="Last chance to back out — Yes will start docker compose.",
        options=[
            PromptOption("yes", "Yes — launch now", "starts docker compose"),
            PromptOption("no", "No — exit without starting",
                         "keeps your .env changes but doesn't launch"),
        ],
        default_value="yes", service_name="",
    ))

    # Second pass: now that every dynamically-spliced step is in place,
    # stamp the final 1-based ``step_index`` and total ``step_total``
    # so callers that read the seed values (e.g. one-off renders that
    # bypass WizardScreen._render_step) see correct numbers.
    total = len(steps)
    from dataclasses import replace as _dc_replace
    steps = [
        _dc_replace(s, step_index=i + 1, step_total=total)
        for i, s in enumerate(steps)
    ]

    state = build_app_state(config_parser, hosts_manager, box_mode="wizard")
    # Build the parallel CloudApiSummary list — same data the overview
    # box renders, derived from .env via state_builder.all_cloud_apis().
    from .widgets.info_box import CloudApiSummary as _CloudApiSummary
    cloud_summaries = [
        _CloudApiSummary(name=ca.name, enabled=ca.enabled, key_set=ca.key_set)
        for ca in state.cloud_apis
    ]

    # Kong's listener port — every Kong-routed alias URL uses this port
    # (virtual-host routing on a single listener), not the upstream
    # service's own port.
    kong_port = env_vars.get("KONG_HTTP_PORT", "").strip()
    # Set of display names whose source the user CAN configure. Used
    # to drive the lock-icon column in the overview — services not in
    # this set are always-on infrastructure.
    configurable_names = {svc.display_name for svc in services_info}

    def _port_key(svc) -> tuple:
        """Sort by numeric port ascending. Services without a port
        (disabled, no port assigned) sort to the bottom."""
        raw = (svc.port or "").lstrip(":").strip()
        try:
            return (0, int(raw)) if raw else (1, 0)
        except ValueError:
            return (1, 0)

    sorted_services = sorted(state.services, key=_port_key)
    rows = [
        ServiceRow(
            name=s.name, source=(s.source or "container"),
            alias=(s.alias or ""), port=(s.port or ""),
            alias_port=(kong_port if (s.alias or "") else ""),
            tag=_tag_for(s.name.lower().replace(" ", "_")),
            default_source=(s.source or "container"),
            configurable=(s.name in configurable_names),
        )
        for s in sorted_services
    ]
    return steps, rows, services_info, current_base_port, state, cloud_summaries


def _selections_to_args(
    selections: dict,
    services_info,
    current_base_port: int,
    env_vars: dict | None = None,
):
    """Map wizard selections back to (source_args, stack_options).

    ``env_vars`` is the resolved .env snapshot at wizard-build time;
    used to auto-promote SECRET_KEEP+disabled+key-already-set into
    ``--cloud-X-source enabled`` so the multiselect picks aren't inert.
    """
    from .widgets.prompt_panel import SECRET_KEEP, SECRET_CLEAR
    from utils.cloud_providers import CLOUD_PROVIDERS
    from wizard.llm_steps import (
        OLLAMA_CUSTOM_TITLE,
        OLLAMA_MODELS_TITLE,
        cloud_models_title,
        cloud_secret_title,
    )
    env_vars = env_vars or {}

    source_args: dict = {}
    for svc in services_info:
        v = selections.get(f"{svc.display_name}  ·  source")
        if v is None: continue
        source_args[svc.key.replace("-", "_") + "_source"] = v

    # ─── Cloud-provider selections ───────────────────────────────────
    # Each provider has up to two wizard outputs:
    #   • Secret step  → API key (or SECRET_KEEP / SECRET_CLEAR sentinel)
    #   • Multiselect  → comma-separated active model names
    #
    # Single pass over the canonical (name, source_var, api_key_var)
    # tuple lets us keep the per-provider decisions adjacent: the
    # secret step's enable/disable and the multiselect's
    # "0 selected → disable" override are reconciled below before we
    # move on to the next provider.
    cloud_api_keys: dict = {}
    cloud_user_models: dict = {}
    for provider in CLOUD_PROVIDERS:
        name, source_var, api_key_var = provider.name, provider.source_var, provider.api_key_var
        cli_arg = source_var.lower()       # CLOUD_OPENAI_SOURCE → cloud_openai_source
        models_var = f"{name.upper()}_USER_MODELS"

        secret_v = selections.get(cloud_secret_title(name))
        # Secret-step intent.
        #   None              → step never visited; leave .env as-is.
        #   SECRET_KEEP       → user pressed Enter past existing key.
        #                       Auto-promote source to ``enabled`` IF the
        #                       .env source was disabled but a key is
        #                       already present — matches the wizard's
        #                       skip predicate, which only forwards to
        #                       the multiselect when it intends to enable.
        #                       Otherwise leave alone.
        #   SECRET_CLEAR / "" → disable + wipe key + wipe models.
        #   real key string   → enable + persist key.
        if secret_v is None:
            pass
        elif secret_v == SECRET_KEEP:
            existing_source = (env_vars.get(source_var, 'disabled') or '').strip().lower()
            existing_key = (env_vars.get(api_key_var, '') or '').strip()
            if existing_source != 'enabled' and existing_key:
                # Auto-promote: user proceeded past a disabled-with-key
                # provider, the multiselect rendered → they want it on.
                source_args[cli_arg] = "enabled"
        elif secret_v == SECRET_CLEAR or secret_v == "":
            # User cleared the key → disable provider, wipe key, and
            # empty the model list so .env doesn't accumulate stale
            # CSV that's now functionally inert.
            source_args[cli_arg] = "disabled"
            cloud_api_keys[api_key_var] = ""
            cloud_user_models[models_var] = ""
        else:
            source_args[cli_arg] = "enabled"
            cloud_api_keys[api_key_var] = secret_v

        # Multiselect intent (renders only when the provider is
        # enabled — otherwise skip_if_prev hides the step).
        models_v = selections.get(cloud_models_title(name))
        if models_v is None:
            continue
        cloud_user_models[models_var] = models_v
        # Explicit "0 selected" → user walked through the list and
        # unchecked everything. Treat as "I don't want this provider":
        # disable the source AND wipe the key for symmetry with
        # SECRET_CLEAR (otherwise .env would keep a stale key for a
        # disabled provider, which is misleading).
        if models_v.strip() == "":
            source_args[cli_arg] = "disabled"
            cloud_api_keys[api_key_var] = ""

    # Single unified Ollama models step (replaces the previous
    # pulled+library split). Container modes show library only;
    # localhost/external show a merged [pulled]/[library] list. The
    # CSV is already the user's final selection — no union needed.
    ollama_user_models: dict = {}
    models_v = selections.get(OLLAMA_MODELS_TITLE)
    if models_v is not None:
        names = sorted({n.strip() for n in models_v.split(",") if n.strip()})
        ollama_user_models["OLLAMA_USER_MODELS"] = ",".join(names)
    # Free-text custom models — honor SECRET_KEEP/SECRET_CLEAR
    # sentinels so an empty Enter on a re-run doesn't silently wipe
    # an existing OLLAMA_CUSTOM_MODELS value.
    custom = selections.get(OLLAMA_CUSTOM_TITLE)
    if custom is not None and custom != SECRET_KEEP:
        if custom == SECRET_CLEAR:
            ollama_user_models["OLLAMA_CUSTOM_MODELS"] = ""
        else:
            ollama_user_models["OLLAMA_CUSTOM_MODELS"] = custom

    bp = selections.get("Base port  ·  range")
    try:
        base_port_val = int(bp) if bp else current_base_port
    except ValueError:
        base_port_val = current_base_port
    cold = selections.get("Cold start  ·  rebuild") == "yes"
    hosts = selections.get("Hosts setup  ·  /etc/hosts", "default")
    launch = selections.get("Confirm  ·  launch the stack") == "yes"
    return source_args, {
        "base_port": base_port_val, "cold": cold,
        "setup_hosts": (hosts == "setup"), "skip_hosts": (hosts == "skip"),
        "launch_confirmed": launch,
        "cloud_api_keys": cloud_api_keys,
        "cloud_user_models": cloud_user_models,
        "ollama_user_models": ollama_user_models,
    }


# ─── main entry ──────────────────────────────────────────────────────

def run_setup_flow(config_parser, hosts_manager, *, starter=None) -> int:
    """Run wizard + pipeline + docker compose all in ONE Textual screen.

    Returns exit code: 0 on success / cancellation.
    """
    from .widgets import BrandInfo
    from .screens.wizard_screen import WizardScreen

    steps, rows, services_info, current_base_port, state, cloud_summaries = (
        _build_steps_and_rows(config_parser, hosts_manager)
    )
    brand = BrandInfo(
        name=getattr(state, "brand_name", None) or "GenAI Vanilla",
        tagline=getattr(state, "tagline", None) or "Gen-AI Development Suite",
        creator=getattr(state, "creator", None) or "",
        creator_email=getattr(state, "creator_email", None) or "",
        license=getattr(state, "license", None) or "",
        repo=getattr(state, "repo_url", None) or "",
        version=getattr(state, "version", None) or "",
    )

    state_holder = {"interrupted": False, "exit_code": 0}

    # Snapshot env vars at wizard-build time so the cloud auto-promotion
    # logic in _selections_to_args has the .env state to compare against.
    _env_snapshot = config_parser.parse_env_file()

    def _resolve(selections: dict) -> tuple[dict, dict]:
        return _selections_to_args(
            selections, services_info, current_base_port, _env_snapshot,
        )

    # Single source of truth for "what port should this service show
    # given its current source": delegates to state_builder.resolve_port
    # which already knows about localhost endpoint vars
    # (LITELLM_BASE_URL, COMFYUI_ENDPOINT, etc.) for localhost sources
    # and falls back to the container port var otherwise.
    from core.port_manager import PortManager
    from ui.state_builder import lookup_service_meta, resolve_port as _resolve_port
    port_offsets = PortManager.PORT_MAPPING

    def _resolve_port_for_service(name: str, source: str) -> str:
        """Live re-derive a service's displayed port for the given
        source. Re-reads ``.env`` so localhost endpoint changes (and
        any other manual edits) are picked up on every confirm —
        effectively the "refresh" the user asked for."""
        meta = lookup_service_meta(name)
        port_var = (meta or {}).get("port_var") if meta else None
        env = config_parser.parse_env_file()
        return _resolve_port(name, source, port_var, env) or ""

    def _recompute_ports(new_base: int, current_rows):
        from .widgets.service_table import ServiceRow as _SR
        # Build a synthetic env dict where the container port_vars are
        # re-derived from the new base port; localhost endpoint vars
        # come straight from the live .env so localhost sources still
        # resolve to the host machine's port.
        live_env = config_parser.parse_env_file()
        synth_env = dict(live_env)
        for pv, off in port_offsets.items():
            synth_env[pv] = str(new_base + off)
        new_kong = str(new_base + port_offsets.get("KONG_HTTP_PORT", 2))
        new_rows = []
        for r in current_rows:
            meta = lookup_service_meta(r.name)
            port_var = (meta or {}).get("port_var") if meta else None
            new_port = _resolve_port(r.name, r.source, port_var, synth_env) or ""
            new_rows.append(_SR(
                name=r.name, source=r.source, alias=r.alias,
                port=new_port,
                alias_port=(new_kong if r.alias else ""),
                tag=r.tag, default_source=r.default_source,
                configurable=r.configurable,
            ))
        # Preserve the port-ascending sort.
        def _key(row):
            raw = (row.port or "").lstrip(":").strip()
            try:
                return (0, int(raw)) if raw else (1, 0)
            except ValueError:
                return (1, 0)
        new_rows.sort(key=_key)
        return new_rows

    class _SetupApp(App):
        CSS_PATH = str(_THEME_PATH)
        TITLE = "GenAI Vanilla — Setup"
        BINDINGS = [Binding("ctrl+c", "interrupt", "Quit", priority=True)]

        def on_mount(self) -> None:
            self.push_screen(WizardScreen(
                steps=steps, services=rows, brand=brand,
                starter=starter,
                stack_options_resolver=_resolve,
                on_base_port_change=_recompute_ports,
                resolve_port_for_service=_resolve_port_for_service,
                cloud_apis=cloud_summaries,
            ))

        def action_interrupt(self) -> None:
            state_holder["interrupted"] = True
            state_holder["exit_code"] = 130
            self.exit()

    _SetupApp().run()
    return state_holder["exit_code"]


# ─── CLI-flag-driven launch (no wizard) ──────────────────────────────

def run_launch_flow(
    config_parser, hosts_manager, *,
    starter,
    source_args: dict,
    stack_options: dict,
) -> int:
    """Push the same Textual launch screen the wizard transitions to,
    but pre-loaded with CLI args — no wizard prompts in between.

    Used when ``./start.sh`` is invoked with explicit source / stack
    flags so the user gets the same in-screen pipeline + log streaming
    UX as the wizard path.

    Returns exit code: 0 on detach, non-zero on interrupt.
    """
    from .widgets import BrandInfo
    from .screens.wizard_screen import WizardScreen
    from core.port_manager import PortManager
    from ui.state_builder import lookup_service_meta, resolve_port as _resolve_port

    _, rows, services_info, current_base_port, state, cloud_summaries = (
        _build_steps_and_rows(config_parser, hosts_manager)
    )
    brand = BrandInfo(
        name=getattr(state, "brand_name", None) or "GenAI Vanilla",
        tagline=getattr(state, "tagline", None) or "Gen-AI Development Suite",
        creator=getattr(state, "creator", None) or "",
        creator_email=getattr(state, "creator_email", None) or "",
        license=getattr(state, "license", None) or "",
        repo=getattr(state, "repo_url", None) or "",
        version=getattr(state, "version", None) or "",
    )

    port_offsets = PortManager.PORT_MAPPING
    env_vars = config_parser.parse_env_file()

    # Resolve the effective base port. CLI ``--base-port N`` wins; else
    # whatever's in .env today.
    base_port = stack_options.get("base_port")
    if base_port is None:
        base_port = current_base_port
    base_port = int(base_port)

    # Build a synthetic env dict that reflects the effective post-launch
    # configuration: container ports re-derived from the chosen base port,
    # plus the CLI source overrides applied. ``resolve_port`` picks the
    # localhost endpoint port for ``*-localhost`` sources and the
    # synth-env container port otherwise.
    synth_env = dict(env_vars)
    for pv, off in port_offsets.items():
        synth_env[pv] = str(base_port + off)
    kong_port = str(base_port + port_offsets.get("KONG_HTTP_PORT", 2))

    # Map CLI source-arg keys (e.g. "llm_provider_source") onto the
    # corresponding display name from the wizard's services_info list,
    # so we can splice the override into the right ServiceRow.
    overrides_by_name: dict[str, str] = {}
    for svc in services_info:
        cli_key = svc.key.replace("-", "_") + "_source"
        v = source_args.get(cli_key)
        if v:
            overrides_by_name[svc.display_name] = v

    # Splice CLI overrides onto the rows + re-derive ports + alias_port.
    new_rows = []
    for r in rows:
        new_source = overrides_by_name.get(r.name, r.source)
        meta = lookup_service_meta(r.name)
        port_var = (meta or {}).get("port_var") if meta else None
        new_port = _resolve_port(r.name, new_source, port_var, synth_env) or ""
        from .widgets.service_table import ServiceRow as _SR
        new_rows.append(_SR(
            name=r.name, source=new_source, alias=r.alias,
            port=new_port,
            alias_port=(kong_port if r.alias else ""),
            tag=r.tag, default_source=r.default_source,
            configurable=r.configurable,
        ))

    # Re-sort by ascending port — same rule as the wizard's overview.
    def _key(row):
        raw = (row.port or "").lstrip(":").strip()
        try:
            return (0, int(raw)) if raw else (1, 0)
        except ValueError:
            return (1, 0)
    new_rows.sort(key=_key)

    # Same recompute / resolve callbacks as run_setup_flow — harmless
    # in CLI mode where they're never triggered, but keeps WizardScreen
    # construction symmetrical.
    def _resolve_port_for_service(name: str, source: str) -> str:
        meta = lookup_service_meta(name)
        port_var = (meta or {}).get("port_var") if meta else None
        env = config_parser.parse_env_file()
        return _resolve_port(name, source, port_var, env) or ""

    def _recompute_ports(new_base: int, current_rows):
        from .widgets.service_table import ServiceRow as _SR
        live_env = config_parser.parse_env_file()
        sx = dict(live_env)
        for pv, off in port_offsets.items():
            sx[pv] = str(new_base + off)
        new_kong = str(new_base + port_offsets.get("KONG_HTTP_PORT", 2))
        out = []
        for r in current_rows:
            meta = lookup_service_meta(r.name)
            port_var = (meta or {}).get("port_var") if meta else None
            np = _resolve_port(r.name, r.source, port_var, sx) or ""
            out.append(_SR(
                name=r.name, source=r.source, alias=r.alias,
                port=np, alias_port=(new_kong if r.alias else ""),
                tag=r.tag, default_source=r.default_source,
                configurable=r.configurable,
            ))
        out.sort(key=_key)
        return out

    state_holder = {"interrupted": False, "exit_code": 0}

    class _LaunchApp(App):
        CSS_PATH = str(_THEME_PATH)
        TITLE = "GenAI Vanilla — Launch"
        BINDINGS = [Binding("ctrl+c", "interrupt", "Quit", priority=True)]

        def on_mount(self) -> None:
            # ``steps=[]`` is fine because auto_launch=True bypasses
            # the wizard entirely; the prompt panel is composed but
            # immediately removed by the launch transition.
            self.push_screen(WizardScreen(
                steps=[], services=new_rows, brand=brand,
                starter=starter,
                on_base_port_change=_recompute_ports,
                resolve_port_for_service=_resolve_port_for_service,
                cloud_apis=cloud_summaries,
                auto_launch=True,
                prefilled_source_args=dict(source_args),
                prefilled_stack_options=dict(stack_options,
                                             base_port=base_port),
            ))

        def action_interrupt(self) -> None:
            state_holder["interrupted"] = True
            state_holder["exit_code"] = 130
            self.exit()

    _LaunchApp().run()
    return state_holder["exit_code"]
