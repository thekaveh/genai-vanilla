"""
Live-region wizard — interactive setup wizard whose prompts render inside
the anchored top box's bottom region (see `ui/presentation_app.py`).

The wizard owns the AppState's wizard chrome (progress bar, command preview,
box_mode) and drives selections via app.prompt_*. The box stays anchored
the whole time — no clear-screen between steps.

`run()` returns:
    (source_args: dict[click_param_name → SOURCE value],
     stack_options: {base_port, cold, setup_hosts, skip_hosts, launch_confirmed})
"""

from __future__ import annotations

import sys
from typing import Dict, Tuple

from core.config_parser import ConfigParser, DEFAULT_BASE_PORT
from utils.system import is_elevated
from wizard.service_discovery import ServiceDiscovery, ServiceInfo, get_option_hint

from ui.select_widget import Choice


class TUIWizard:
    """
    Drives the wizard flow inside an active PresentationApp Live region.

    The caller is responsible for:
      - Entering the PresentationApp before calling run()
      - Setting box_mode="wizard" before run() (or letting run() do it)
      - Setting box_mode="normal" after run() returns
    """

    def __init__(self, config_parser: ConfigParser, app):
        self.config_parser = config_parser
        self.app = app
        self.service_discovery = ServiceDiscovery(config_parser)
        self.selections: Dict[str, str] = {}

    def run(self) -> Tuple[Dict[str, str], dict]:
        """
        Run the wizard. Returns (source_args, stack_options) on success.
        Esc on any prompt restarts the wizard from step 1.
        Ctrl+C raises KeyboardInterrupt for the caller to handle.
        """
        # Outer loop: restart-on-Esc.
        while True:
            self.selections = {}

            services = self.service_discovery.discover()
            env_vars = self.config_parser.parse_env_file()
            current_base_port = int(env_vars.get('SUPABASE_DB_PORT', DEFAULT_BASE_PORT))

            num_services = len(services)
            # Steps: services + (base port, cold start, hosts, launch confirm)
            total = num_services + 4

            self.app.set_box_mode("wizard")
            restart = False

            # --- Service prompts -----------------------------------------
            # `step` is the number of COMPLETED answers (0..total). At
            # i=0 we're about to ask the first question, so pass step=0.
            for i, service in enumerate(services):
                self._update_chrome(step=i, total=total)
                selected = self._prompt_service(service)
                if selected is None:  # Esc
                    restart = True
                    break
                self.selections[service.key] = selected
                # Live sync — update the matching service in the box state
                # so the dot/port/choice flip immediately as the user picks.
                self.app.apply_wizard_selection(service.key, selected, self.config_parser)
                self._resolve_dependencies(service.key, selected, services)

            if restart:
                continue

            # --- Base port -----------------------------------------------
            self._update_chrome(step=num_services, total=total)
            base_port = self._prompt_base_port(current_base_port)
            if base_port is None:
                continue

            # --- Cold start ----------------------------------------------
            self._update_chrome(step=num_services + 1, total=total)
            cold = self._prompt_cold_start()
            if cold is None:
                continue

            # --- Hosts setup ---------------------------------------------
            self._update_chrome(step=num_services + 2, total=total)
            hosts_config = self._prompt_hosts_setup()
            if hosts_config is None:
                continue

            # --- Launch confirmation (last wizard step) ------------------
            # Asking inside the wizard means cold-start cleanup, supabase
            # key generation, and other pipeline work only fire AFTER the
            # user confirms — no flicker between wizard end and launch.
            self._update_chrome(step=num_services + 3, total=total)
            launch_confirmed = self._prompt_launch_confirmation()
            if launch_confirmed is None:
                continue

            # --- Completion beat -----------------------------------------
            self._update_chrome(step=total, total=total)
            self.app.status(message="✅ Configuration complete", level="ok")
            # Brief pause so the user sees the green flash before the box
            # mode flips back to normal.
            import time
            time.sleep(0.5)

            # Early sudo check if setup_hosts was chosen.
            if hosts_config['setup_hosts'] and not is_elevated():
                self.app.log(
                    "Setting up hosts requires admin privileges.",
                    level="warn",
                )
                self.app.log(
                    "Please restart with: sudo ./start.sh",
                    level="dim",
                )
                # Brief pause so the messages are readable before Live tears down.
                time.sleep(2)
                sys.exit(1)

            return self._build_source_args(), {
                'base_port': base_port,
                'cold': cold,
                'setup_hosts': hosts_config['setup_hosts'],
                'skip_hosts': hosts_config['skip_hosts'],
                'launch_confirmed': launch_confirmed,
            }

    # --- Chrome / status helpers -------------------------------------------

    def _update_chrome(self, step: int, total: int) -> None:
        """
        Refresh the box's wizard progress + command preview.

        `step` is the number of COMPLETED answers (0..total). The
        ribbon label stays user-facing 1-indexed: "Step 1 of N" while
        answering question 1, "Step N of N" only after the final answer.
        """
        cmd = self._build_command_preview()
        self.app.set_wizard(step=step, total=total, command_preview=cmd)
        display_step = total if step >= total else step + 1
        self.app.status(message=f"Step {display_step} of {total}", level="info")

    def _build_command_preview(self) -> str:
        """
        Build the live './start.sh --foo bar …' preview, showing only flags
        that differ from current .env defaults.
        """
        env_defaults = self.config_parser.parse_env_file()
        changed = {}
        for service_key, value in self.selections.items():
            env_var = service_key.upper().replace("-", "_") + "_SOURCE"
            default_value = env_defaults.get(env_var, "")
            if value != default_value:
                changed[service_key] = value

        if not changed:
            return "./start.sh  (using .env defaults)"

        parts = ["./start.sh"]
        for service_key, value in changed.items():
            flag = "--" + service_key.replace("_", "-") + "-source"
            parts.append(f"{flag} {value}")
        return " ".join(parts)

    # --- Prompt wrappers ---------------------------------------------------

    def _prompt_service(self, service: ServiceInfo):
        choices = [
            Choice(
                value=opt,
                label=opt,
                hint=get_option_hint(opt),
                is_current=(opt == service.current_value),
            )
            for opt in service.options
        ]
        prompt = f"{service.display_name}"
        if service.description:
            prompt += f" · {service.description}"
        return self.app.prompt_select(prompt, choices, default_value=service.current_value)

    def _prompt_base_port(self, current_port: int):
        # First: keep / change?
        choices = [
            Choice(value="keep", label=f"Keep current ({current_port})", is_current=True),
            Choice(value="change", label="Change base port…"),
        ]
        result = self.app.prompt_select(
            "Base port for all services · starting port for service port range",
            choices,
            default_value="keep",
        )
        if result is None:
            return None
        if result == "keep":
            return current_port

        # Then: enter a new number.
        port = self.app.prompt_number(
            "Enter base port (1024–65000):",
            default=current_port,
            min_allowed=1024,
            max_allowed=65000,
        )
        return port

    def _prompt_cold_start(self):
        choices = [
            Choice(value="no", label="No  (keep existing data and volumes)", is_current=True),
            Choice(value="yes", label="Yes  (remove all volumes, rebuild images from scratch)"),
        ]
        result = self.app.prompt_select(
            "Cold start? · removes volumes and rebuilds all images",
            choices,
            default_value="no",
        )
        if result is None:
            return None
        return result == "yes"

    def _prompt_launch_confirmation(self):
        """
        Final wizard step — confirm before any pipeline work runs.

        Returns True (launch), False (cancel), or None (Esc → restart).
        Asking inside the wizard means cold-start cleanup, supabase key
        generation, port handling, etc. only fire AFTER the user
        confirms — no alternate-screen flicker between wizard end and
        launch.
        """
        choices = [
            Choice(value="yes", label="Yes  (launch the stack with this configuration)",
                   is_current=True),
            Choice(value="no", label="No   (cancel and exit without changes)"),
        ]
        result = self.app.prompt_select(
            "Launch the stack with this configuration?",
            choices,
            default_value="yes",
        )
        if result is None:
            return None
        return result == "yes"

    def _prompt_hosts_setup(self):
        choices = [
            Choice(value="default",
                   label="Default  (check /etc/hosts, warn if entries are missing)",
                   is_current=True),
            Choice(value="setup",
                   label="Setup hosts now  (adds entries to /etc/hosts, requires sudo)"),
            Choice(value="skip",
                   label="Skip  (no hosts check, use localhost:PORT URLs only)"),
        ]
        result = self.app.prompt_select(
            "Hosts file configuration · enables friendly URLs like chat.localhost",
            choices,
            default_value="default",
        )
        if result is None:
            return None
        return {
            'setup_hosts': result == 'setup',
            'skip_hosts': result == 'skip',
        }

    # --- Dependency resolution --------------------------------------------

    def _resolve_dependencies(self, service_key: str, selected_value: str, services: list) -> None:
        """
        Mirror InteractiveWizard._check_dependencies — same two-direction
        check, but uses app.prompt_select for the resolution UI.
        """
        yaml_config = self.config_parser.load_yaml_config()
        deps = yaml_config.get('service_dependencies', {})

        def dep_name_to_key(dep_name: str) -> str:
            return {
                'parakeet': 'stt_provider',
                'xtts': 'tts_provider',
                'docling': 'doc_processor',
                'ollama': 'llm_provider',
                'openclaw-gateway': 'openclaw',
            }.get(dep_name, dep_name)

        # Local helper: set selection AND propagate to the box state so the
        # dot/port/choice flip in real time (not just at end of wizard).
        def _set(key: str, value: str) -> None:
            self.selections[key] = value
            self.app.apply_wizard_selection(key, value, self.config_parser)

        # Direction 1: disabling this service breaks others
        if selected_value == 'disabled':
            for dep_service, dep_config in deps.items():
                requires = dep_config.get('requires', [])
                for req in requires:
                    if dep_name_to_key(req) == service_key:
                        dependent_key = dep_name_to_key(dep_service)
                        dependent_value = self.selections.get(dependent_key)
                        if dependent_value and dependent_value != 'disabled':
                            err = dep_config.get('error_message', f"{dep_service} requires {req}")
                            res = self._prompt_dep_resolution(dep_service, service_key, err)
                            if res == 'enable_dependency':
                                _set(service_key, 'container')
                            else:
                                _set(dependent_key, 'disabled')

        # Direction 2: enabling this service requires a disabled dependency
        dep_config = deps.get(service_key, {})
        if not dep_config:
            for dep_name, config in deps.items():
                if dep_name_to_key(dep_name) == service_key:
                    dep_config = config
                    break

        if dep_config and selected_value != 'disabled':
            requires = dep_config.get('requires', [])
            for req in requires:
                req_key = dep_name_to_key(req)
                req_value = self.selections.get(req_key)
                if req_value == 'disabled':
                    err = dep_config.get('error_message', f"{service_key} requires {req}")
                    res = self._prompt_dep_resolution(service_key, req_key, err)
                    if res == 'enable_dependency':
                        _set(req_key, 'container')
                    else:
                        _set(service_key, 'disabled')

    def _prompt_dep_resolution(self, service_name: str, dependency_name: str, err: str) -> str:
        choices = [
            Choice(value="enable_dependency",
                   label=f"Enable {dependency_name}  (set to container)"),
            Choice(value="disable_service",
                   label=f"Disable {service_name}"),
        ]
        result = self.app.prompt_select(
            f"⚠ Dependency conflict: {err}",
            choices,
            default_value="enable_dependency",
        )
        # If user pressed Esc here, default to enabling the dependency
        # (safest auto-resolve — keeps both services usable).
        return result or "enable_dependency"

    # --- Output adapter ---------------------------------------------------

    def _build_source_args(self) -> Dict[str, str]:
        """Convert selections to Click parameter-style keys (matches legacy)."""
        return {
            key.replace('-', '_') + '_source': value
            for key, value in self.selections.items()
        }
