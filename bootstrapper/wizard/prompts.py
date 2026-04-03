"""
InquirerPy prompt generation for the interactive setup wizard.

Builds styled prompts for service SOURCE selection, stack options,
and confirmation. All service options are derived dynamically from
ServiceInfo — nothing is hardcoded per service.

Navigation: Escape restarts the wizard, Ctrl+C quits.
"""

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.utils import InquirerPyStyle

from wizard.service_discovery import ServiceInfo


# Keyboard shortcut hint shown below every prompt
NAV_HINT = "esc restart · ctrl+c quit"

# Custom keybindings: map Escape to skip (restart) action
WIZARD_KEYBINDINGS = {
    "skip": [{"key": "escape"}],
}

# GitHub-dark inspired color palette with dark navy/black background.
# The "" key sets the default background for the entire prompt area
# via prompt_toolkit's Style.from_dict().
WIZARD_STYLE = InquirerPyStyle({
    "": "bg:#0d1117 #c9d1d9",
    "questionmark": "#58a6ff bold",
    "question": "#c9d1d9 bold",
    "answer": "#3fb950 bold",
    "pointer": "#3fb950 bold bg:#0d1117",
    "highlighted": "#58a6ff bg:#1a1e2e",
    "instruction": "#8b949e",
    "long_instruction": "#484f58",
    "input": "#c9d1d9 bg:#0d1117",
    "text": "#c9d1d9 bg:#0d1117",
})


def get_option_hint(option_name: str) -> str:
    """
    Derive a contextual hint from a SOURCE option name.

    Pattern-based — not hardcoded per service. If a new option name
    follows existing patterns, it gets the right hint automatically.
    """
    if 'container-gpu' in option_name or option_name.endswith('-gpu'):
        return "requires NVIDIA GPU"
    if 'container-cpu' in option_name or option_name.endswith('-cpu'):
        return "CPU only, works everywhere"
    if 'localhost' in option_name:
        return "uses local installation"
    if 'external' in option_name:
        return "remote instance"
    if option_name == 'api':
        return "cloud API (OpenAI/Anthropic)"
    if option_name == 'disabled':
        return "service will not run"
    if option_name == 'container':
        return "Docker container"
    return ""


def _build_choice_name(option: str, hint: str, is_current: bool) -> str:
    """Build the display string for an option choice."""
    parts = [option]
    annotations = []
    if hint:
        annotations.append(hint)
    if is_current:
        annotations.append("current")
    if annotations:
        parts.append(f"({', '.join(annotations)})")
    return "  ".join(parts)


def prompt_service_source(service: ServiceInfo):
    """
    Present an interactive prompt for selecting a service's SOURCE.

    Returns the selected SOURCE value, or None if user pressed Escape (restart).
    """
    choices = []
    default_value = None

    for option in service.options:
        hint = get_option_hint(option)
        is_current = (option == service.current_value)
        name = _build_choice_name(option, hint, is_current)
        choices.append(Choice(value=option, name=name))
        if is_current:
            default_value = option

    description = f" · {service.description}" if service.description else ""

    return inquirer.select(
        message=f"{service.display_name}{description}",
        choices=choices,
        default=default_value,
        style=WIZARD_STYLE,
        qmark="◆",
        amark="◆",
        pointer="→",
        instruction="(↑↓ navigate, enter select)",
        mandatory=False,
        keybindings=WIZARD_KEYBINDINGS,
    ).execute()


def prompt_base_port(current_port: int):
    """Prompt for the base port number. Returns int or None (restart)."""
    result = inquirer.select(
        message="Base port for all services · starting port for service port range",
        choices=[
            Choice(value="keep", name=f"Keep current  ({current_port})"),
            Choice(value="change", name="Change base port..."),
        ],
        default="keep",
        style=WIZARD_STYLE,
        qmark="◆",
        amark="◆",
        pointer="→",
        mandatory=False,
        keybindings=WIZARD_KEYBINDINGS,
    ).execute()

    if result is None:
        return None
    if result == "keep":
        return current_port

    # User wants to change — prompt for a number
    port = inquirer.number(
        message="Enter base port (1024-65000):",
        default=current_port,
        style=WIZARD_STYLE,
        qmark="◆",
        amark="◆",
        min_allowed=1024,
        max_allowed=65000,
        mandatory=False,
        keybindings=WIZARD_KEYBINDINGS,
    ).execute()

    if port is None:
        return None
    return int(port)


def prompt_cold_start():
    """Prompt for cold start option. Returns bool or None (restart)."""
    result = inquirer.select(
        message="Cold start? · removes volumes and rebuilds all images",
        choices=[
            Choice(value="no", name="No  (keep existing data and volumes)"),
            Choice(value="yes", name="Yes  (remove all volumes, rebuild images from scratch)"),
        ],
        default="no",
        style=WIZARD_STYLE,
        qmark="◆",
        amark="◆",
        pointer="→",
        mandatory=False,
        keybindings=WIZARD_KEYBINDINGS,
    ).execute()

    if result is None:
        return None
    return result == "yes"


def prompt_hosts_setup():
    """
    Prompt for hosts file setup preference.

    Returns dict with setup_hosts and skip_hosts booleans, or None (restart).
    """
    result = inquirer.select(
        message="Hosts file configuration · enables friendly URLs like chat.localhost, n8n.localhost",
        choices=[
            Choice(value="default",
                   name="Default  (check /etc/hosts, warn if entries are missing)"),
            Choice(value="setup",
                   name="Setup hosts now  (adds entries to /etc/hosts, requires sudo)"),
            Choice(value="skip",
                   name="Skip  (no hosts check, use localhost:PORT URLs only)"),
        ],
        default="default",
        style=WIZARD_STYLE,
        qmark="◆",
        amark="◆",
        pointer="→",
        mandatory=False,
        keybindings=WIZARD_KEYBINDINGS,
    ).execute()

    if result is None:
        return None

    return {
        'setup_hosts': result == 'setup',
        'skip_hosts': result == 'skip',
    }


def prompt_confirmation():
    """Final confirmation before launching the stack. Returns bool or None (cancel)."""
    result = inquirer.confirm(
        message="Launch the stack with this configuration?",
        default=True,
        style=WIZARD_STYLE,
        qmark="▲",
        amark="▲",
        mandatory=False,
        keybindings=WIZARD_KEYBINDINGS,
    ).execute()
    if result is None:
        return False
    return result


def prompt_dependency_resolution(
    service_name: str,
    dependency_name: str,
    error_message: str,
) -> str:
    """
    Prompt the user to resolve a dependency conflict.

    Returns 'enable_dependency' or 'disable_service'.
    """
    return inquirer.select(
        message=f"Dependency conflict: {error_message}",
        choices=[
            Choice(
                value="enable_dependency",
                name=f"Enable {dependency_name}  (set to container)",
            ),
            Choice(
                value="disable_service",
                name=f"Disable {service_name}",
            ),
        ],
        style=WIZARD_STYLE,
        qmark="⚠",
        amark="⚠",
        pointer="→",
    ).execute()
