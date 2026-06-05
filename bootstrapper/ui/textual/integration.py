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

# Wizard step title for ComfyUI model multiselect — canonical source of
# truth lives in wizard/comfyui_steps.py; imported here to keep the drain
# loop (selections.get(COMFYUI_MODELS_TITLE)) aligned with what the step
# registers without duplicating the string literal.
from wizard.comfyui_steps import COMFYUI_MODELS_TITLE


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

# Log-pane tag taxonomy. INTENTIONALLY DIFFERENT from the six topology
# categories (infra/data/llm/media/agents/apps) — log-stream coloring uses
# its own five-tag palette (INFRA/LLM/ML/DATA/TOOL) that groups services by
# the visual shape of their log output rather than their stack role. Notable
# divergences from `services.topology` categories:
#   • backend (apps category) → "ML"  — ML-heavy logs
#   • supabase (data category) → "INFRA" — substrate, treated as plumbing
#   • n8n/searxng (media in topology) → "TOOL" — workflow-style logs
# Topology already exports a category-tag mapping (`palette.CAT_*`) for
# wizard/info-box rendering — those are different on purpose. If a new
# service is added without an entry here, `_tag_for` returns "" (uncolored)
# which is the desired fallback.
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
    "n8n": "TOOL", "searxng": "TOOL", "openclaw": "TOOL", "hermes": "TOOL", "jupyterhub": "TOOL",
    "prometheus": "INFRA", "node-exporter": "INFRA", "cadvisor": "INFRA",
    "grafana": "INFRA",
    "postgres-exporter": "DATA", "redis-exporter": "DATA",
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
    if s == "disabled":
        return "Skip this service entirely"
    return ""


def recompute_ports_for_base(
    new_base: int,
    current_rows,
    config_parser,
    port_offsets: dict,
):
    """Re-derive every ServiceRow's port + alias_port from ``new_base``.

    Single implementation shared by the wizard (``run_setup_flow``) and
    the CLI-driven launch path (``run_launch_flow``). Both call this
    whenever the user re-enters the base-port step or when the launch
    flow recomputes ports after an override.

    Builds a synthetic env dict where each container port_var is
    re-derived from ``new_base``; localhost endpoint vars come straight
    from the live .env so localhost sources still resolve to the host
    machine's port.
    """
    from ui.state_builder import lookup_service_meta, resolve_port as _resolve_port
    from .widgets.service_table import ServiceRow as _SR

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
            category=r.category,
            pending=r.pending,
        ))
    # Preserve the canonical input order — `current_rows` arrives in
    # category/topology order from `_build_steps_and_rows`, and changing
    # the base port only re-derives port values, not row positions.
    return new_rows


def _build_steps_and_rows(config_parser, hosts_manager):
    """Build the wizard steps + service rows from real config."""
    from wizard.service_discovery import ServiceDiscovery
    from ui.state_builder import build_app_state
    from core.config_parser import DEFAULT_BASE_PORT
    from .widgets.prompt_panel import PromptOption, PromptStep
    from .widgets.service_table import ServiceRow

    services_info = ServiceDiscovery(config_parser).discover()
    env_vars = config_parser.parse_env_file()
    # ``dict.get(key, default)`` returns "" when the key is present-
    # but-blank, not the default. Guard against that.
    _raw = (env_vars.get("BASE_PORT") or "").strip()
    try:
        current_base_port = int(_raw) if _raw else DEFAULT_BASE_PORT
    except ValueError:
        current_base_port = DEFAULT_BASE_PORT

    # Build canonical order index once — shared by both sorts below.
    from services.topology import get_topology
    _topology = get_topology()
    _canonical_index: dict[str, int] = {
        r.display_name: idx for idx, r in enumerate(_topology.rows)
    }

    def _svc_canonical_key(svc) -> tuple:
        return (_canonical_index.get(svc.display_name, 999), svc.display_name)

    services_info = sorted(services_info, key=_svc_canonical_key)

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
    # Ray follow-up steps (worker count + external address) live in
    # wizard/ray_steps.py; spliced in right after the Ray source step.
    from wizard.ray_steps import build_ray_followup_steps
    # ComfyUI model multiselect lives in wizard/comfyui_steps.py;
    # spliced in right after the ComfyUI source step.
    from wizard.comfyui_steps import build_comfyui_steps
    from .widgets.prompt_panel import SecondaryNumberInput

    # Per-service localhost-port wiring. Each entry maps a service's
    # source-step display name + the option value(s) eligible for the
    # inline-port widget → the matching env var name + the well-known
    # default. PromptOption.secondary_number is attached for any option
    # whose (service, value) appears here. Generic by construction —
    # the widget doesn't know about ports; this table is the only
    # place that does. Adding a new localhost-capable service is one
    # row here + a manifest entry per Task 7.
    LOCALHOST_PORT_WIRING: dict[tuple[str, str], tuple[str, int]] = {
        ("ComfyUI",            "localhost"):             ("COMFYUI_LOCALHOST_PORT", 8000),
        ("Document Processor", "docling-localhost"):     ("DOCLING_LOCALHOST_PORT", 63021),
        ("Hermes Agent",       "localhost"):             ("HERMES_LOCALHOST_PORT", 63028),
        ("OpenClaw",           "localhost"):             ("OPENCLAW_LOCALHOST_PORT", 63024),
        ("LLM Engine",         "ollama-localhost"):      ("OLLAMA_LOCALHOST_PORT", 11434),
        ("Neo4j Graph DB",     "localhost"):             ("NEO4J_LOCALHOST_BOLT_PORT", 7687),
        ("Weaviate",           "localhost"):             ("WEAVIATE_LOCALHOST_PORT", 8080),
        ("STT Provider",       "parakeet-localhost"):    ("PARAKEET_LOCALHOST_PORT", 63022),
        ("STT Provider",       "whisper-cpp-localhost"): ("WHISPER_CPP_LOCALHOST_PORT", 63025),
        ("TTS Provider",       "chatterbox-localhost"):  ("CHATTERBOX_LOCALHOST_PORT", 63027),
    }

    def _localhost_port_config(display: str, opt_value: str) -> "SecondaryNumberInput | None":
        """Build the per-option SecondaryNumberInput for a localhost row,
        or None if this (service, option) isn't in the wiring table."""
        wiring = LOCALHOST_PORT_WIRING.get((display, opt_value))
        if wiring is None:
            return None
        env_var, default_port = wiring
        raw = (env_vars.get(env_var) or str(default_port)).strip()
        try:
            current = int(raw) if raw else int(default_port)
        except ValueError:
            current = int(default_port)
        current = max(1024, min(65535, current))
        return SecondaryNumberInput(
            env_var=env_var,
            description=f"Host port for {display.lower()} in localhost mode (1024-65535).",
            default_value=current,
            number_min=1024,
            number_max=65535,
            unit_suffix="port",
        )

    for i, svc in enumerate(services_info):
        # Per-option secondary_number: attach the inline integer input to
        # the specific option rows where it makes sense.
        # • Ray: worker count on the container-cpu / container-gpu rows.
        # • Localhost-port overrides: attached per-localhost-row in
        #   Task 10. None of the localhost-attachments live here today.
        ray_secondary: SecondaryNumberInput | None = None
        if svc.key in ("ray", "ray-head") or svc.display_name == "Ray":
            raw_default = (env_vars.get("RAY_WORKER_COUNT") or "2").strip()
            try:
                worker_default = max(0, min(64, int(raw_default)))
            except ValueError:
                worker_default = 2
            ray_secondary = SecondaryNumberInput(
                env_var="RAY_WORKER_COUNT",
                description=(
                    "Ray worker replicas alongside the head node "
                    "(0 = head-only single-node cluster). 0-64."
                ),
                default_value=worker_default,
                number_min=0,
                number_max=64,
                unit_suffix="workers",
            )
        # Spark mirrors Ray's worker-count widget. Spark's runtime_sc has
        # four containers (master + worker + history + connect); spark-init
        # is filtered out the same way Ray's ray-worker is. ServiceDiscovery
        # anchors on `spark-master` via the source_mapping shim, so the
        # svc.key check accepts both forms defensively.
        spark_secondary: SecondaryNumberInput | None = None
        if svc.key in ("spark", "spark-master") or svc.display_name == "Apache Spark":
            raw_default = (env_vars.get("SPARK_WORKER_COUNT") or "2").strip()
            try:
                spark_worker_default = max(1, min(8, int(raw_default)))
            except ValueError:
                spark_worker_default = 2
            spark_secondary = SecondaryNumberInput(
                env_var="SPARK_WORKER_COUNT",
                description=(
                    "Number of spark-worker replicas alongside the master. 1-8."
                ),
                default_value=spark_worker_default,
                number_min=1,
                number_max=8,
                unit_suffix="workers",
            )
        opts = [
            PromptOption(
                value=opt,
                label=opt,
                hint=_option_hint(opt),
                badges=_badges_for_option(opt, recommended=(opt == svc.current_value)),
                secondary_number=(
                    # Ray's container variants → worker-count.
                    ray_secondary
                    if ray_secondary is not None
                       and opt in ("ray-container-cpu", "ray-container-gpu")
                    # Spark's container variant → worker-count.
                    else spark_secondary
                    if spark_secondary is not None and opt == "container"
                    # Otherwise: per-localhost-row port widget (None if
                    # this option isn't a localhost variant in the wiring).
                    else _localhost_port_config(svc.display_name, opt)
                ),
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
            # secondary_number REMOVED from PromptStep — config is now
            # on individual PromptOption entries above.
        ))
        # Splice the entire LLM cluster RIGHT AFTER the LLM Engine
        # source step: Ollama variants, then cloud-provider key+model
        # pairs. Keeps engine + local + cloud adjacent in the wizard
        # flow instead of separating them with unrelated service-source
        # steps. Each spliced sub-step has its own skip_if_prev gating.
        if svc.display_name == "LLM Engine":
            steps.extend(build_ollama_steps(env_vars, _wizard_warn))
            steps.extend(build_cloud_steps(env_vars, _wizard_warn))
        # Splice Ray follow-up prompts RIGHT AFTER the Ray source step.
        # Each sub-step carries its own skip_if_prev predicate so only
        # the appropriate prompt fires for the chosen source.
        # Ray's runtime_sc has two containers (`ray-head` + `ray-worker`),
        # so ServiceDiscovery assigns the family key `ray-head` to the
        # discovery anchor. Match both forms defensively.
        if svc.key in ("ray", "ray-head") or svc.display_name == "Ray":
            steps.extend(build_ray_followup_steps(env_vars, {
                "RAY_SOURCE": svc.current_value or "disabled",
            }))
        # Splice ComfyUI model multiselect RIGHT AFTER the ComfyUI source
        # step. The step's skip_if_prev guard fires when COMFYUI_SOURCE is
        # not container-cpu / container-gpu (localhost, external, disabled),
        # so only container users see the model picker.
        if svc.display_name == "ComfyUI":
            steps.extend(build_comfyui_steps(env_vars, _wizard_warn))

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

    state = build_app_state(config_parser, hosts_manager)
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

    def _svc_row_canonical_key(svc) -> tuple:
        """Sort by canonical topology order. Services not in the
        topology (infra-only rows) sort to the bottom."""
        return (_canonical_index.get(svc.name, 999), svc.name)

    sorted_services = sorted(state.services, key=_svc_row_canonical_key)
    rows = [
        ServiceRow(
            name=s.name, source=(s.source or "container"),
            alias=(s.alias or ""), port=(s.port or ""),
            alias_port=(kong_port if (s.alias or "") else ""),
            tag=_tag_for(s.name.lower().replace(" ", "_")),
            default_source=(s.source or "container"),
            configurable=(s.name in configurable_names),
            category=s.category,
            pending=(s.name in configurable_names),  # locked rows start not-pending
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

    # ComfyUI model multiselect — parallel to the Ollama models block
    # above. The wizard step (declared in T15) writes a set under
    # COMFYUI_MODELS_TITLE; we convert it to a sorted CSV here so
    # apply_user_model_selections can persist it as COMFYUI_USER_MODELS.
    comfyui_user_models: dict = {}
    comfyui_models_v = selections.get(COMFYUI_MODELS_TITLE, set())
    if comfyui_models_v:
        out_names = sorted(comfyui_models_v) if isinstance(comfyui_models_v, set) else \
            sorted({n.strip() for n in str(comfyui_models_v).split(",") if n.strip()})
        comfyui_user_models["COMFYUI_USER_MODELS"] = ",".join(out_names)

    # Inline secondary integer inputs — any prompt step that mounted a
    # ``SecondaryNumberInput`` writes its value under a synthetic key
    # ``__secondary__:<ENV_VAR>`` in the selections dict (see
    # WizardScreen._action_confirm). Drain all of them into the env-write
    # bag here so the same ``apply_user_model_selections`` pipeline
    # persists them. Generic — works for RAY_WORKER_COUNT today and any
    # future localhost-port override tomorrow.
    for sel_key, sel_val in selections.items():
        if isinstance(sel_key, str) and sel_key.startswith("__secondary__:"):
            env_var = sel_key.split(":", 1)[1]
            if env_var:
                ollama_user_models[env_var] = sel_val

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
        "comfyui_user_models": comfyui_user_models,
    }


# ─── main entry ──────────────────────────────────────────────────────

def run_setup_flow(
    config_parser, hosts_manager, *,
    starter=None,
    no_port_migrate: bool = False,
) -> int:
    """Run wizard + pipeline + docker compose all in ONE Textual screen.

    Returns exit code: 0 on success / cancellation.
    """
    from .widgets import BrandInfo
    from .screens.wizard_screen import WizardScreen

    # Port-layout v0 → v1 migration runs BEFORE the wizard reads .env so
    # the user sees post-migration port values in the box. start.py has
    # already called setup_env_file + backfill_missing_env_vars; the
    # helper is idempotent and a no-op once the v1 sentinel is stamped.
    if starter is not None:
        starter.run_port_migration(no_port_migrate)

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
    port_offsets = PortManager(str(config_parser.root_dir)).port_offsets()

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
        return recompute_ports_for_base(
            new_base, current_rows, config_parser, port_offsets,
        )

    class _SetupApp(App):
        CSS_PATH = str(_THEME_PATH)
        # TITLE is set dynamically in on_mount so it honors BRAND_NAME
        # overrides (forks that rebrand via BRAND_* env vars get their own
        # window title without code changes).
        TITLE = "Setup"
        BINDINGS = [Binding("ctrl+c", "interrupt", "Quit", priority=True)]

        def on_mount(self) -> None:
            self.title = f"{brand.name or 'GenAI Vanilla'} — Setup"
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
    no_port_migrate: bool = False,
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

    # Port-layout v0 → v1 migration runs BEFORE the launch overview reads
    # .env so the displayed ports match the post-migration topology.
    # start.py has already called setup_env_file + backfill; the helper
    # is idempotent once the v1 sentinel is stamped.
    starter.run_port_migration(no_port_migrate)

    _pm = PortManager(str(config_parser.root_dir))

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

    port_offsets = _pm.port_offsets()
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
            category=r.category,
            pending=False,  # launch-flow rows are fully resolved before display
        ))

    # `state.services` already arrives in canonical topology order; the
    # source-resolved `new_rows` list preserves that order (the loop above
    # iterates `state.services` in input order).

    # Same recompute / resolve callbacks as run_setup_flow — harmless
    # in CLI mode where they're never triggered, but keeps WizardScreen
    # construction symmetrical.
    def _resolve_port_for_service(name: str, source: str) -> str:
        meta = lookup_service_meta(name)
        port_var = (meta or {}).get("port_var") if meta else None
        env = config_parser.parse_env_file()
        return _resolve_port(name, source, port_var, env) or ""

    def _recompute_ports(new_base: int, current_rows):
        return recompute_ports_for_base(
            new_base, current_rows, config_parser, port_offsets,
        )

    state_holder = {"interrupted": False, "exit_code": 0}

    class _LaunchApp(App):
        CSS_PATH = str(_THEME_PATH)
        # TITLE is set dynamically in on_mount so it honors BRAND_NAME
        # overrides (forks that rebrand via BRAND_* env vars get their own
        # window title without code changes).
        TITLE = "Launch"
        BINDINGS = [Binding("ctrl+c", "interrupt", "Quit", priority=True)]

        def on_mount(self) -> None:
            self.title = f"{brand.name or 'GenAI Vanilla'} — Launch"
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
