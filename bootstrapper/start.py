#!/usr/bin/env python3
"""
GenAI Vanilla Stack - Start Script

Python implementation of start.sh with full feature parity.
Cross-platform startup script for the GenAI development environment.
"""

import re
import sys
import os
from datetime import date
from pathlib import Path
import click
from typing import Dict, Optional

from services.migrations.migration_v1 import (
    apply as _apply_v1,
    needs_migration as _needs_v1,
    stamp_version as _stamp_v1,
)


def _format_today() -> str:
    """Return today's date as ``YYYY-MM-DD`` for env-backfill markers.
    Factored to a tiny helper so it's trivial to monkey-patch in tests
    without freezing the system clock globally.
    """
    return date.today().isoformat()

# Add the current directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from utils.banner import BannerDisplay
from utils.hosts_manager import HostsManager
from utils.key_generator import KeyGenerator
from utils.localhost_validator import LocalhostValidator
from core.config_parser import ConfigParser, DEFAULT_BASE_PORT
from core.docker_manager import DockerManager
from core.port_manager import PortManager
from services.source_validator import SourceValidator
from services.service_config import ServiceConfig
from services.dependency_manager import DependencyManager
from utils.source_override_manager import SourceOverrideManager

class GenAIStackStarter:
    """Main class for starting the GenAI Stack."""
    
    def __init__(self):
        # Set root directory first
        self.root_dir = Path(__file__).resolve().parent.parent
        
        # Initialize all managers with correct root_dir
        self.banner = BannerDisplay()
        self.hosts_manager = HostsManager()
        self.key_generator = KeyGenerator(str(self.root_dir))
        self.config_parser = ConfigParser(str(self.root_dir))
        self.localhost_validator = LocalhostValidator(self.config_parser)
        self.docker_manager = DockerManager(str(self.root_dir))
        self.port_manager = PortManager(str(self.root_dir))
        self.source_validator = SourceValidator(self.config_parser)
        self.service_config = ServiceConfig(self.config_parser)
        self.dependency_manager = DependencyManager(self.config_parser)
        self.source_override_manager = SourceOverrideManager(self.config_parser)


    def show_banner(self):
        """Display the startup banner."""
        self.banner.show_banner()

    # Note: a hand-written ``show_usage()`` used to live here. Removed
    # because Click's auto-generated ``--help`` already lists every flag
    # (defined just above ``def main(...)`` below); maintaining a second
    # text was a steady source of drift — it lagged the cloud-provider
    # and live-model flags, and listed an obsolete ``api`` value for
    # ``--llm-provider-source`` that no longer exists. Click ``--help``
    # is now the single source of truth.

    def ensure_dependencies_available(self) -> bool:
        """Ensure all required dependencies are available."""
        self.banner.show_section_header("Checking Dependencies", "🔍")
        
        # Check Docker availability
        if not self.docker_manager.check_docker_available():
            self.banner.show_status_message(
                "Docker is not available. Please install Docker and ensure it's running.", 
                "error"
            )
            return False
            
        # Show detected Docker compose command
        compose_cmd = self.docker_manager.get_compose_command_display()
        self.banner.show_status_message(f"Using Docker Compose command: {compose_cmd}", "info")
        
        # Check docker-compose.yml exists
        compose_file = self.root_dir / "docker-compose.yml"
        if not compose_file.exists():
            self.banner.show_status_message(
                f"Docker Compose file not found: {compose_file}", 
                "error"
            )
            return False
        self.banner.show_status_message(f"Docker Compose file found: {compose_file}", "success")
        
        # Python YAML parsing replaces yq dependency
        self.banner.show_status_message("Using native Python YAML parsing (replaces yq dependency)", "info")
        
        return True
    
    def apply_source_overrides(self, **kwargs) -> bool:
        """
        Apply SOURCE overrides from command-line arguments.

        Args:
            **kwargs: Command-line SOURCE override arguments

        Returns:
            bool: True if successful
        """
        overrides = self.source_override_manager.collect_overrides(**kwargs)
        if overrides:
            return self.source_override_manager.apply_overrides(overrides)
        return True

    def apply_cloud_api_keys(self, keys: Dict[str, str]) -> bool:
        """
        Persist cloud LLM provider API keys (OPENAI_API_KEY,
        ANTHROPIC_API_KEY, OPENROUTER_API_KEY) into ``.env``.

        Reuses the in-place .env writer the source-override manager
        already employs, so format and comment lines are preserved.
        Empty values are written verbatim — used to clear a key.

        Args:
            keys: Mapping of env-var name to value (e.g.
                {'OPENAI_API_KEY': 'sk-...'}). Empty dict is a no-op.

        Returns:
            bool: True on success (or no-op).
        """
        if not keys:
            return True
        return self.source_override_manager.update_env_file(keys)

    def apply_user_model_selections(self, selections: Dict[str, str]) -> bool:
        """
        Persist user-selected model lists (OPENAI_USER_MODELS,
        ANTHROPIC_USER_MODELS, OPENROUTER_USER_MODELS, OLLAMA_USER_MODELS,
        OLLAMA_CUSTOM_MODELS) into ``.env``.

        Values are comma-separated model names. ``llm-catalog-init``
        consumes them on the next ``docker compose up`` to set the
        ``active`` flag on the corresponding rows in ``public.llms``.

        Args:
            selections: Mapping of env-var name to comma-separated
                model names. Empty dict is a no-op.

        Returns:
            bool: True on success (or no-op).
        """
        if not selections:
            return True
        return self.source_override_manager.update_env_file(selections)

    def validate_source_configurations(self) -> bool:
        """Validate all SOURCE configurations and scale values against YAML.

        Calls the validator's repair pass first (auto-disables cloud
        providers with missing keys, etc.), then runs the read-only
        validation. Splitting the two lets pure-tooling callers
        (linters, CI dry-runs) run validation alone without mutating
        .env — see SourceValidator.enforce_runtime_invariants.
        """
        # Repair pass — mutates .env when necessary. A failed write
        # (disk full, permissions, etc.) is not silently recoverable:
        # halt before the read-only validate pass, which would
        # otherwise see stale .env.
        if not self.source_validator.enforce_runtime_invariants():
            self.source_validator.print_validation_results()
            return False
        # Read-only validation pass.
        sources_valid = self.source_validator.validate_all_sources()
        if not sources_valid:
            self.source_validator.print_validation_results()
            return False

        scales_valid = self.source_validator.validate_scale_values()
        if not scales_valid:
            self.banner.console.print("[bright_red]❌ Scale validation failed:[/bright_red]")
            for error in self.source_validator.get_validation_errors():
                self.banner.console.print(f"   {error}")
            return False

        return True
        
    def setup_env_file(self, cold_start: bool, base_port: Optional[int] = None) -> bool:
        """
        Setup .env file from .env.example if needed.
        Supports custom .env file paths via GENAI_ENV_FILE environment variable.
        Replicates the .env setup logic from the original start.sh.

        Args:
            cold_start: Whether this is a cold start
            base_port: Optional custom base port

        Returns:
            bool: True if successful
        """
        # Use config_parser paths which respect GENAI_ENV_FILE
        env_file_path = self.config_parser.env_file_path
        env_example_path = self.config_parser.env_example_path

        # Show which env file we're using if custom
        if self.config_parser.is_using_custom_env_file():
            self.banner.show_status_message(
                f"Using custom env file: {env_file_path}",
                "info"
            )

        # Check if .env exists, if not or if cold start is requested, create from .env.example
        if not env_file_path.exists() or cold_start:
            if not env_example_path.exists():
                self.banner.show_status_message(
                    f".env.example file not found: {env_example_path}",
                    "error"
                )
                return False

            self.banner.show_section_header("Setting Up Environment", "📋")

            if cold_start:
                self.banner.show_status_message("Creating new .env file from .env.example (cold start)...", "info")
            else:
                self.banner.show_status_message("Creating new .env file from .env.example", "info")

            try:
                # Ensure parent directory exists (important for custom paths)
                env_file_path.parent.mkdir(parents=True, exist_ok=True)

                # Copy .env.example to target path (default or custom)
                import shutil
                shutil.copy2(env_example_path, env_file_path)
                self.banner.show_status_message(f"  • Copied {env_example_path}", "info")
                self.banner.show_status_message(f"  •     to {env_file_path}", "info")

                # Unset potentially lingering port environment variables if cold start and custom base port are used
                effective_base_port = base_port if base_port is not None else DEFAULT_BASE_PORT
                if cold_start and effective_base_port != DEFAULT_BASE_PORT:
                    self.unset_port_environment_variables()

                self.banner.show_status_message("Environment file setup completed", "success")
                return True

            except Exception as e:
                self.banner.show_status_message(f"Failed to create .env file: {e}", "error")
                return False

        return True  # .env already exists and not cold start

    def backfill_missing_env_vars(self) -> bool:
        """Append variables present in ``.env.example`` but missing from
        the user's ``.env`` (preserving every existing value).

        Catches the merge-from-upstream case: a worktree adds new
        services to ``.env.example`` (e.g. MinIO's ``MINIO_IMAGE``,
        ``MINIO_PORT``, bucket names) but the user's pre-existing
        ``.env`` doesn't carry those keys. ``docker compose config``
        then warns ``variable X not set, defaulting to blank`` and
        fails with ``service has neither an image nor a build context``
        when a critical key like ``${MINIO_IMAGE}`` is empty.

        Preserves the source file's organisation: missing vars are
        emitted under their original section heading (the
        ``# === FOO ===`` banner above them in ``.env.example``),
        with the immediate context comment block kept intact. The
        result reads as if the new entries had been there from the
        start — no flat "everything dumped at the bottom" lump.

        Idempotent — running again with no missing keys is a no-op.
        Only appends new keys; never rewrites existing values or
        reorders the file (so user-edited values and pre-existing
        comments stay put). Auto-managed keys with empty defaults in
        the example (passwords, access keys) are appended blank; the
        cold-start secret-generation step fills them later.
        """
        env_file_path = self.config_parser.env_file_path
        env_example_path = self.config_parser.env_example_path
        if not env_file_path.exists() or not env_example_path.exists():
            return True  # Nothing to backfill against.

        try:
            example_text = env_example_path.read_text()
            env_text = env_file_path.read_text()
        except OSError as e:
            self.banner.show_status_message(
                f"Could not read env files for backfill: {e}", "warning",
            )
            return True  # Non-fatal — surface compose's own error later.

        existing_keys: set[str] = set()
        blank_keys: set[str] = set()
        for line in env_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in stripped:
                key, _, raw_value = stripped.partition("=")
                key = key.strip()
                existing_keys.add(key)
                if not raw_value.split("#", 1)[0].strip():
                    blank_keys.add(key)

        # Build a lookup of .env.example values so we can fill in BLANK
        # entries (a key exists in .env but with no value) using a
        # non-blank manifest default. This handles the case where the
        # user's .env was created when a secret's manifest `default` was
        # different from the current one — e.g., the supabase DB
        # password placeholder got reintroduced to the example after a
        # secret-emission policy change. Intentional autogen blanks
        # (LITELLM_MASTER_KEY etc.) have `default: ""` in the manifest
        # and therefore stay blank in .env.example, so this branch is a
        # no-op for them.
        example_values: dict[str, str] = {}
        for line in example_text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in stripped:
                key, _, raw_value = stripped.partition("=")
                example_values[key.strip()] = raw_value.split("#", 1)[0].strip()
        blank_fills = {
            key: example_values[key]
            for key in blank_keys
            if example_values.get(key)
        }
        if blank_fills:
            new_lines: list[str] = []
            for line in env_text.splitlines(keepends=True):
                stripped = line.strip()
                if "=" in stripped and not stripped.startswith("#"):
                    key, _, raw_value = stripped.partition("=")
                    key = key.strip()
                    if (
                        key in blank_fills
                        and not raw_value.split("#", 1)[0].strip()
                    ):
                        eol = "\r\n" if line.endswith("\r\n") else "\n"
                        new_lines.append(f"{key}={blank_fills[key]}{eol}")
                        continue
                new_lines.append(line)
            env_file_path.write_text("".join(new_lines))
            env_text = env_file_path.read_text()
            self.banner.show_status_message(
                f"Filled {len(blank_fills)} blank value(s) from .env.example: "
                f"{', '.join(sorted(blank_fills)[:4])}"
                f"{' …' if len(blank_fills) > 4 else ''}",
                "info",
            )

        groups = self._parse_env_example_sections(
            example_text, existing_keys,
        )
        if not groups:
            return True

        rendered_lines: list[str] = [
            "",
            "# ────────────────────────────────────────────────────────",
            f"# Auto-backfilled from .env.example on {_format_today()}",
            "# Entries new in .env.example since this .env was written,",
            "# grouped by their source section so the file stays tidy.",
            "# ────────────────────────────────────────────────────────",
        ]
        total = 0
        for section, entries in groups:
            rendered_lines.append("")
            rendered_lines.append(f"# === {section} ===")
            for context, key, value in entries:
                rendered_lines.extend(context)  # 0+ comment lines
                rendered_lines.append(f"{key}={value}")
                total += 1
        rendered_lines.append("")
        appended = "\n".join(rendered_lines)
        if not env_text.endswith("\n"):
            appended = "\n" + appended

        try:
            with open(env_file_path, "a") as f:
                f.write(appended)
        except OSError as e:
            self.banner.show_status_message(
                f"Failed to backfill {env_file_path}: {e}", "error",
            )
            return False

        section_names = ", ".join(s for s, _ in groups[:4])
        suffix = " …" if len(groups) > 4 else ""
        self.banner.show_status_message(
            f"Backfilled {total} missing env var(s) from .env.example, "
            f"grouped under: {section_names}{suffix}",
            "info",
        )
        return True

    @staticmethod
    def _parse_env_example_sections(
        example_text: str, existing_keys: set[str],
    ) -> "list[tuple[str, list[tuple[list[str], str, str]]]]":
        """Walk ``example_text`` and group missing variables by section.

        Returns a list of ``(section_name, entries)`` where entries is
        a list of ``(context_comments, key, value)``. Section name
        comes from the most recent ``# ============`` banner block.
        Context comments are the contiguous comment lines immediately
        preceding the variable (an inline description like
        ``# Optional, only when LLM_PROVIDER_SOURCE=ollama-external:``),
        capped to the previous variable or section banner so the
        backfill doesn't drag unrelated commentary along.
        """
        # Match the 3-line section banner pattern in .env.example:
        #   # ====================
        #   # SECTION NAME
        #   # ====================
        bar_re = re.compile(r"^#\s*={3,}\s*$")
        lines = example_text.splitlines()
        current_section = "(unsectioned)"
        # Buffer of comment lines accumulated since the last variable
        # line or section banner — used as the immediate context for
        # the next variable we encounter.
        comment_buf: list[str] = []
        # Section name → list of (context, key, value).
        per_section: dict[str, list[tuple[list[str], str, str]]] = {}
        ordered_sections: list[str] = []
        seen_keys: set[str] = set()

        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            # Section banner detection: bar, title, bar (3 lines).
            if (
                bar_re.match(line)
                and i + 2 < n
                and lines[i + 1].startswith("#")
                and bar_re.match(lines[i + 2])
            ):
                title = lines[i + 1].lstrip("#").strip()
                if title:
                    current_section = title
                comment_buf = []
                i += 3
                continue
            stripped = line.strip()
            if not stripped:
                # Blank line resets the running comment buffer so we
                # don't paste unrelated text above a variable two
                # sections later.
                comment_buf = []
                i += 1
                continue
            if stripped.startswith("#"):
                comment_buf.append(line)
                i += 1
                continue
            if "=" not in stripped:
                comment_buf = []
                i += 1
                continue
            key, _, raw_value = stripped.partition("=")
            key = key.strip()
            value = raw_value
            if "#" in value:
                # Strip inline `# trailing comment` from the value but
                # keep the value itself verbatim.
                value = value.split("#", 1)[0]
            value = value.rstrip()
            if key and key not in existing_keys and key not in seen_keys:
                seen_keys.add(key)
                if current_section not in per_section:
                    per_section[current_section] = []
                    ordered_sections.append(current_section)
                per_section[current_section].append(
                    (list(comment_buf), key, value),
                )
            comment_buf = []
            i += 1
        return [(s, per_section[s]) for s in ordered_sections]

    def unset_port_environment_variables(self) -> None:
        """
        Unset potentially lingering port environment variables.
        Replicates the unset logic from the original start.sh.
        """
        # List of all port environment variables that need to be unset
        # This matches the exact list from the original Bash script
        port_variables = [
            'SUPABASE_DB_PORT',
            'REDIS_PORT',
            'KONG_HTTP_PORT',
            'KONG_HTTPS_PORT',
            'SUPABASE_META_PORT',
            'SUPABASE_STORAGE_PORT',
            'SUPABASE_AUTH_PORT',
            'SUPABASE_API_PORT',
            'SUPABASE_REALTIME_PORT',
            'SUPABASE_STUDIO_PORT',
            'GRAPH_DB_PORT',
            'GRAPH_DB_DASHBOARD_PORT',
            'LITELLM_PORT',
            'LOCAL_DEEP_RESEARCHER_PORT',
            'SEARXNG_PORT',
            'OPEN_WEB_UI_PORT',
            'BACKEND_PORT',
            'N8N_PORT',
            'COMFYUI_PORT',
            'WEAVIATE_PORT',
            'WEAVIATE_GRPC_PORT',
            'DOC_PROCESSOR_PORT',
            'STT_PROVIDER_PORT',
            'TTS_PROVIDER_PORT',
            'SPEACHES_PORT',
            'CHATTERBOX_PORT',
            'OPENCLAW_GATEWAY_PORT',
            'OPENCLAW_BRIDGE_PORT',
            'HERMES_API_PORT',
            'HERMES_DASHBOARD_PORT',
            'MINIO_PORT',
            'MINIO_CONSOLE_PORT',
            'JUPYTERHUB_PORT'
        ]
        
        self.banner.show_status_message("  • Unsetting potentially lingering port environment variables...", "info")
        for var in port_variables:
            if var in os.environ:
                del os.environ[var]
    
    def validate_supabase_keys(self, cold_start: bool = False) -> bool:
        """
        Ensure required Supabase JWT keys are present.

        Three outcomes:
          - All three keys present → no-op.
          - All three keys blank (fresh clone, or post-cold-reset of .env) →
            auto-generate. No --cold flag required.
          - Mixed state (some present, some blank) → refuse and direct the
            user to ./bootstrapper/generate_supabase_keys.sh, since the anon
            and service keys are HMAC-signed by SUPABASE_JWT_SECRET and the
            generator always rewrites all three. Auto-regenerating here would
            silently clobber whatever values the user hand-pasted.

        Args:
            cold_start: Phrases the status message only. Auto-generation
                triggers on the all-blank case regardless of this flag.

        Returns:
            bool: True if all keys are present or successfully generated.
        """
        env_vars = self.config_parser.parse_env_file()

        keys = {
            'SUPABASE_JWT_SECRET': env_vars.get('SUPABASE_JWT_SECRET', '').strip(),
            'SUPABASE_ANON_KEY': env_vars.get('SUPABASE_ANON_KEY', '').strip(),
            'SUPABASE_SERVICE_KEY': env_vars.get('SUPABASE_SERVICE_KEY', '').strip(),
        }
        missing_keys = [name for name, value in keys.items() if not value]

        if not missing_keys:
            return True

        # Mixed state: some keys set, others blank. Don't auto-regenerate —
        # the SupabaseKeyGenerator rewrites all three together, which would
        # destroy whatever the user pasted into the present ones.
        if len(missing_keys) < len(keys):
            present_keys = [name for name in keys if name not in missing_keys]
            self.banner.show_section_header("Inconsistent Supabase Keys", "⚠️")
            self.banner.show_status_message(
                "Some Supabase keys are set and others are blank — refusing to "
                "auto-regenerate to avoid clobbering the values you've already set.",
                "warning",
            )
            self.banner.show_status_message(
                f"  Present: {', '.join(present_keys)}", "warning",
            )
            self.banner.show_status_message(
                f"  Missing: {', '.join(missing_keys)}", "warning",
            )
            self.banner.show_status_message("  To resolve:", "info")
            self.banner.show_status_message(
                "    • Run ./bootstrapper/generate_supabase_keys.sh to regenerate "
                "ALL three (overwrites existing), or",
                "info",
            )
            self.banner.show_status_message(
                "    • Manually fill in the missing keys in .env so all three "
                "are populated.",
                "info",
            )
            return False

        self.banner.show_section_header("Generating Supabase Keys", "🔐")
        if cold_start:
            self.banner.show_status_message(
                "Cold start detected - generating fresh Supabase JWT keys...",
                "info",
            )
        else:
            self.banner.show_status_message(
                "No Supabase keys found in .env; generating fresh JWT keys...",
                "info",
            )

        from utils.supabase_keys import SupabaseKeyGenerator
        key_generator = SupabaseKeyGenerator(str(self.root_dir))

        if key_generator.generate_and_update_env():
            self.banner.show_status_message(
                "Supabase keys generated and applied successfully!", "success"
            )
            return True

        self.banner.show_status_message("Failed to generate Supabase keys", "error")
        return False
        
    def handle_port_configuration(self, base_port: Optional[int]) -> bool:
        """Handle port configuration and updates."""
        # Use default base port if not specified (matching original Bash behavior)
        if base_port is None:
            base_port = DEFAULT_BASE_PORT
            
        # Validate base port
        if not self.port_manager.validate_base_port(base_port):
            self.banner.show_status_message(
                f"Invalid base port: {base_port}. Must be between 1024 and {65535 - 20}",
                "error"
            )
            return False
            
        # Check for port conflicts
        conflicts = self.port_manager.get_port_conflicts(base_port)
        if conflicts:
            # Check if conflicts are from our own project's containers
            if self.docker_manager.are_project_containers_running():
                self.banner.show_status_message(
                    "Previous instance detected — stopping existing containers...",
                    "info"
                )
                stop_result = self.docker_manager.stop_services(
                    remove_volumes=False, remove_orphans=True
                )
                if stop_result != 0:
                    self.banner.show_status_message(
                        "Failed to stop previous instance", "error"
                    )
                    return False

                self.banner.show_status_message(
                    "Previous instance stopped successfully", "success"
                )

                # Re-check ports after cleanup
                conflicts = self.port_manager.get_port_conflicts(base_port)

            # If conflicts remain, show the original error
            if conflicts:
                self.banner.show_status_message("Port conflicts detected:", "warning")
                for port_var, port in conflicts.items():
                    self.banner.show_status_message(
                        f"  • {port_var}: Port {port} is already in use", "warning"
                    )

                # Suggest alternative base port
                suggested_port = self.port_manager.suggest_available_base_port()
                if suggested_port:
                    self.banner.show_status_message(
                        f"Suggested available base port: {suggested_port}",
                        "info"
                    )
                return False
            
        # Update ports in .env file
        if not self.port_manager.update_env_ports(base_port):
            return False

        return True

    def run_port_migration(self, no_port_migrate: bool) -> None:
        """v0 → v1 port-layout .env migration.

        Idempotent. Reads ``BOOTSTRAPPER_PORT_LAYOUT_VERSION`` from the
        active env file (honors ``GENAI_ENV_FILE``); if absent or < 1,
        rewrites every port var whose current value matches the v0
        default to the topology-derived v1 default. User-customized
        values are left alone.

        When ``no_port_migrate`` is True we skip the rewrite AND skip
        the sentinel stamp so the next run re-prompts — matches the
        user intent "skip this run, ask next time."

        Must be called AFTER setup_env_file + backfill so the file
        exists and is fully populated, and BEFORE any caller that
        relies on the v1 port values.
        """
        env_path = self.config_parser.env_file_path
        if not _needs_v1(env_path):
            return

        if no_port_migrate:
            self.banner.console.print(
                "[dim]Skipping port-layout v1 migration (--no-port-migrate); "
                "will re-prompt next run.[/dim]"
            )
            return

        from services.topology import get_topology as _get_topology
        services_root = self.root_dir / "services"
        env_vars = self.config_parser.parse_env_file()
        # ``.get(key, default)`` returns the empty string when the key is
        # present-but-blank — only missing keys hit the default. A blank
        # BASE_PORT (auto-managed quirk) would crash ``int("")``.
        _raw_base = (env_vars.get("BASE_PORT") or "").strip()
        try:
            base_port = int(_raw_base) if _raw_base else DEFAULT_BASE_PORT
        except ValueError:
            base_port = DEFAULT_BASE_PORT
        topology = _get_topology(services_root, base_port=base_port)
        result = _apply_v1(env_path, topology.port_defaults, base_port=base_port)
        if result.backup_path:
            self.banner.console.print(
                f"[green]• Backed up .env to {result.backup_path}[/green]"
            )
        self.banner.console.print(
            f"[green]• Port layout updated (v0 → v1)[/green]: "
            f"rewrote {len(result.rewritten)} ports; "
            f"preserved {len(result.preserved)} customizations."
        )
        if result.rewritten:
            self.banner.console.print("[dim]  Changes:[/dim]")
            for var, (old, new) in sorted(result.rewritten.items()):
                self.banner.console.print(
                    f"[dim]    {var}: {old} → {new}[/dim]"
                )
        _stamp_v1(env_path, 1)

    def generate_service_configuration(self) -> bool:
        """Generate and update service configuration."""
        return self.service_config.generate_and_update_env()
    
    def generate_litellm_configuration(self) -> bool:
        """Write a STUB volumes/litellm/config.yaml so the bind mount has
        a file to attach to. The real model_list is rendered by
        ``litellm-init`` from public.llms on every ``docker compose up``.

        ``force=True`` here, but the writer is NOT unconditionally
        destructive — ``LiteLLMConfigGenerator.write_config`` checks
        for the litellm-init sentinel header + non-empty model_list
        and preserves that file even with force=True. This protects
        the previous run's real config across re-runs that haven't
        yet completed a docker compose up. Stub / corrupt / missing
        files DO get overwritten. See ``_is_litellm_init_managed``.
        """
        try:
            from utils.litellm_config_generator import LiteLLMConfigGenerator
            generator = LiteLLMConfigGenerator(self.config_parser)
            config_path = self.root_dir / "volumes/litellm/config.yaml"
            # Pre-flight: ensure the bind-mount target directory is
            # writable. Earlier docker compose runs (litellm-init runs
            # as root inside the container) can leave the host directory
            # root-owned, blocking subsequent container writes —
            # symptom is ``PermissionError: '/litellm-config/config.yaml.tmp'``.
            self._ensure_volume_dir_writable(config_path.parent)
            generator.write_config(config_path, force=True)
            return True
        except Exception as e:
            self.banner.show_status_message(f"Failed to generate LiteLLM configuration: {e}", "error")
            return False

    def _ensure_volume_dir_writable(self, path: "Path") -> None:
        """Make sure a bootstrapper-managed host directory is writable
        by both the current host user and any future container that
        bind-mounts it. Earlier container runs can leave the directory
        root-owned with 755 mode, blocking subsequent re-writes.

        Strategy: if the directory exists and is not writable, attempt
        a 777 chmod. If chmod also fails (very rare — usually root-owned
        with strict mode), wipe and recreate. Both branches log what
        they did so the user can see why their permissions changed.

        Never raises — falls back to letting the original write fail
        with its native error if neither chmod nor recreate works.
        """
        import shutil

        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            return
        if not path.is_dir():
            return  # caller's problem; not our job to second-guess
        if os.access(path, os.W_OK):
            return  # already writable, nothing to do

        # Try chmod 0o777 first (cheapest, least destructive).
        try:
            path.chmod(0o777)
            if os.access(path, os.W_OK):
                self.banner.show_status_message(
                    f"  • Relaxed permissions on {path} (was root-owned from a prior container run)",
                    "info",
                )
                return
        except OSError:
            pass

        # chmod failed — last-ditch: wipe and recreate as the current user.
        try:
            shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
            self.banner.show_status_message(
                f"  • Recreated {path} (prior run left it unwritable)",
                "info",
            )
        except OSError as exc:
            self.banner.show_status_message(
                f"  • Could not fix permissions on {path}: {exc} — "
                f"if a container write fails, run `sudo rm -rf {path}` "
                f"and re-run ./start.sh",
                "warning",
            )

    def generate_kong_configuration(self) -> bool:
        """Generate dynamic Kong configuration based on SOURCE values."""
        try:
            from utils.kong_config_generator import KongConfigGenerator
            generator = KongConfigGenerator(self.config_parser)
            # Pre-flight: same root-owned-from-prior-container guard as
            # the litellm bind-mount uses (kong-api-gateway also writes
            # nothing into volumes/api but the bootstrapper drops the
            # dynamic config there for the container to read).
            self._ensure_volume_dir_writable(self.root_dir / "volumes/api")

            kong_config = generator.generate_kong_config()

            errors = generator.validate_config(kong_config)
            if errors:
                self.banner.show_status_message("Kong configuration validation failed:", "error")
                for error in errors:
                    self.banner.console.print(f"  • {error}")
                return False

            config_path = self.root_dir / "volumes/api/kong-dynamic.yml"
            if not generator.write_config(kong_config, config_path):
                return False

            return True

        except Exception as e:
            self.banner.show_status_message(f"Failed to generate Kong configuration: {e}", "error")
            return False
        
    def check_service_dependencies(self) -> bool:
        """Check and enforce service dependencies. Silent on success."""
        dependencies_satisfied = self.dependency_manager.check_service_dependencies()

        if not dependencies_satisfied:
            violations = self.dependency_manager.get_dependency_violations()
            self.banner.show_status_message("Service dependency violations found:", "warning")
            for violation in violations:
                self.banner.console.print(f"   ⚠️  {violation['error_message']}")

            disabled_services = self.dependency_manager.auto_resolve_dependency_violations()
            if disabled_services:
                for service in disabled_services:
                    self.banner.show_status_message(f"Auto-disabled {service} due to missing dependencies", "warning")
                return True
            else:
                self.banner.show_status_message("Could not auto-resolve dependency violations", "error")
                return False

        return True
        
    def handle_hosts_configuration(self, setup_hosts: bool, skip_hosts: bool) -> bool:
        """Handle hosts file configuration. Silent unless setting up or errors."""
        if skip_hosts:
            return True

        if setup_hosts:
            return self.hosts_manager.setup_hosts_entries()

        # Default: silent check, no warnings for missing entries
        return True
            
    def perform_cold_start_cleanup(self) -> bool:
        """Perform cold start cleanup if requested."""
        self.banner.show_section_header("Cold Start Cleanup", "🧹")
        
        self.banner.show_status_message("Performing cold start cleanup...", "info")
        
        # Use the enhanced cold start cleanup
        success = self.docker_manager.perform_cold_start_cleanup()
        
        if not success:
            self.banner.show_status_message("Some issues occurred during cleanup", "warning")
        else:
            self.banner.show_status_message("Cold cleanup completed successfully", "success")
            
        # Add small delay as per original script
        import time
        time.sleep(2)
            
        return True  # Continue even if cleanup had issues
        
    def generate_encryption_keys(self, cold_start: bool = False) -> bool:
        """
        Generate missing encryption keys for services.
        
        BEHAVIORAL DIFFERENCE FROM ORIGINAL BASH:
        - Original: Only generates N8N_ENCRYPTION_KEY on cold start, SearxNG secret only if missing
        - Python: Always generates missing keys, regenerates ALL keys on cold start
        
        This is an IMPROVEMENT as it ensures all required keys are always present.
        
        Args:
            cold_start: If True, regenerate all keys. If False, only generate missing ones.
            
        Returns:
            bool: True if successful
        """
        force_regenerate = cold_start

        try:
            results = self.key_generator.generate_missing_keys(force_regenerate=force_regenerate)

            if all(results.values()):
                return True
            else:
                failed_keys = [key for key, success in results.items() if not success]
                self.banner.show_status_message(
                    f"Failed to generate encryption keys: {', '.join(failed_keys)}",
                    "error"
                )
                return False

        except Exception as e:
            self.banner.show_status_message(f"Error generating encryption keys: {e}", "error")
            return False
    
    def validate_localhost_services(self) -> bool:
        """Validate localhost services are accessible before starting."""
        # Check if any services are configured for localhost
        if not self.localhost_validator.has_localhost_services():
            return True  # No localhost services to validate
            
        self.banner.show_section_header("Validating Localhost Services", "🔍")
        
        try:
            results = self.localhost_validator.validate_all_localhost_services()
            
            if not results:
                return True  # No localhost services found
            
            # Display results
            all_valid = True
            for source_var, (is_valid, messages) in results.items():
                config = self.localhost_validator.SERVICE_CHECKS[source_var]
                service_name = config['service_name']
                level = "info" if is_valid else "warning"

                self.banner.show_status_message(f"  • {service_name}:", level)
                for message in messages:
                    self.banner.show_status_message(f"    {message}", level)

                if not is_valid:
                    all_valid = False

            if all_valid:
                self.banner.show_status_message("All localhost services are accessible", "success")
            else:
                self.banner.show_status_message(
                    "Some localhost services are not accessible (warnings above)",
                    "warning"
                )
                self.banner.show_status_message(
                    "  • The stack will still start, but affected services may not work correctly",
                    "warning",
                )
                self.banner.show_status_message(
                    "  • Please ensure localhost services are running as indicated",
                    "warning",
                )
                
            return True  # Always continue, just show warnings
            
        except Exception as e:
            self.banner.show_status_message(f"Error validating localhost services: {e}", "error")
            return True  # Continue anyway
        
    def start_docker_services(self, cold_start: bool = False) -> bool:
        """Start Docker services with optional fresh build for cold start."""
        self.banner.show_section_header("Starting Services", "🚀")
        
        if cold_start:
            self.banner.show_status_message("Starting containers with fresh build (cold start)...", "info")
            
            # Build images without cache (matching original Bash script behavior)
            print("    - Building images without cache...")
            build_result = self.docker_manager.build_services(no_cache=True, pull=False)
            
            if build_result != 0:
                self.banner.show_status_message("Failed to build some services", "error")
                return False
                
            print("    - Starting containers...")
            # Start with force recreate for cold start 
            result = self.docker_manager.execute_compose_command(['up', '-d', '--force-recreate'])
            
        else:
            self.banner.show_status_message("Starting GenAI Vanilla Stack services...", "info")
            result = self.docker_manager.start_services(detached=True)
        
        if result != 0:
            self.banner.show_status_message("Failed to start some services", "error")
            return False
        else:
            self.banner.show_status_message("All services started successfully", "success")
            return True
            
    def show_pre_launch_summary(self) -> bool:
        """
        Display the combined configuration summary table with access URLs
        and hosted endpoints, then prompt for confirmation.

        Returns:
            bool: True if user confirms, False to cancel.
        """
        table = self.build_pre_launch_summary_table()
        self.banner.console.print(table)
        self.banner.console.print()
        from rich.text import Text as _Text
        from ui.textual.palette import style_for_category as _style_for_category
        from services.topology import CATEGORY_LABELS, CATEGORY_ORDER
        _legend = _Text()
        _first = True
        for _slug in CATEGORY_ORDER:
            if not _first:
                _legend.append("   ")
            _first = False
            _legend.append("▰", style=_style_for_category(_slug))
            _legend.append(f" {CATEGORY_LABELS[_slug]}")
        self.banner.console.print(_legend)
        self.banner.console.print()

        # Confirmation prompt — legacy linear flow only. TUI mode runs the
        # launch confirmation as the wizard's last step; this branch is
        # reached only when --no-tui or non-TTY.
        if sys.stdin.isatty():
            response = self.banner.console.input(
                "  [color(245)]Launch the stack? (Y/n):[/color(245)] "
            ).strip().lower()
            return response in ('', 'y', 'yes')
        return True  # non-TTY: auto-confirm

    def build_pre_launch_summary_table(self):
        """
        Build the configuration summary as a Rich Table renderable —
        used by the --no-tui / non-TTY linear flow (`show_pre_launch_summary`).
        The Textual wizard renders its own info-box and never reaches this
        table.
        """
        from rich.table import Table
        from rich.text import Text
        from rich.box import HEAVY_HEAD
        from ui.state_builder import all_services, all_cloud_apis, alias_for, cloud_api_status_text
        from services.topology import get_topology
        from ui.textual.palette import style_for_category

        _topology = get_topology()
        _category_by_name = {r.display_name: r.category for r in _topology.rows}

        env_vars = self.config_parser.parse_env_file()
        service_sources = self.config_parser.parse_service_sources()
        kong_port = env_vars.get('KONG_HTTP_PORT', '63002')

        # Check if hosts entries are configured (yields the set of hostnames
        # that are PRESENT in /etc/hosts).
        hosts_present = set()
        try:
            existing_missing = self.hosts_manager.check_missing_hosts()
            all_hosts = self.hosts_manager.get_genai_hosts()
            hosts_present = set(all_hosts) - set(existing_missing)
        except Exception:
            pass

        table = Table(
            title="Stack Services Overview",
            title_style="bold bright_white",
            box=HEAVY_HEAD,
            border_style="color(240)",
            header_style="bold bright_white",
            show_lines=True,
            padding=(0, 1),
            expand=True,
        )
        table.add_column("PORT", style="color(248)", justify="left", ratio=1, no_wrap=True)
        table.add_column("SERVICE", style="color(252)", justify="left", ratio=3, no_wrap=True)
        # Category marker — between SERVICE and SOURCE, mirroring the
        # TUI box layout so both surfaces speak the same visual language.
        table.add_column("", justify="left", width=2, no_wrap=True)
        table.add_column("SOURCE", justify="left", ratio=3, no_wrap=True)
        table.add_column("ALIAS", justify="left", ratio=4, no_wrap=True)
        table.add_column("STATUS", justify="left", ratio=2, no_wrap=True)

        # Service definitions come from state_builder.all_services() — single
        # source of truth shared with the TUI info-box (no more inline list
        # to drift out of sync).
        services = list(all_services())

        # Sort by port number ascending; services with no port go to the end.
        def _sort_key(svc):
            name, source_var, port_var, _scale_var = svc
            source = service_sources.get(source_var, env_vars.get(source_var, 'container'))
            if source == 'disabled' or not port_var:
                return (2, 99999)
            if 'localhost' in source:
                lp = self._get_localhost_port(name, env_vars)
                match = re.search(r':(\d+)', lp)
                return (1, int(match.group(1)) if match else 99999)
            try:
                return (0, int(env_vars.get(port_var, '99999')))
            except ValueError:
                return (2, 99999)

        services.sort(key=_sort_key)

        from ui.textual.palette import style_for_source_choice as _style_for_source
        for name, source_var, port_var, scale_var in services:
            source = service_sources.get(source_var, env_vars.get(source_var, 'container'))
            scale = env_vars.get(scale_var, '0') if scale_var else '1'
            status_text, status_style = self._get_service_status(source, scale)
            # Color the SOURCE cell with the same helper the TUI uses:
            # container → green, localhost / external / api → blue,
            # disabled → muted grey. Previously hardcoded grey, which
            # made localhost variants visually indistinguishable from
            # containerised ones.
            source_style = _style_for_source(source)

            # PORT column
            if source == 'disabled':
                port_val = "-"
            elif 'localhost' in source:
                port_val = self._get_localhost_port(name, env_vars)
            elif port_var:
                port_val = f":{env_vars.get(port_var, '?')}"
            else:
                port_val = "-"

            # ALIAS column — alias map from state_builder (single source).
            hostname = alias_for(name)
            if hostname and hostname in hosts_present and source != 'disabled':
                alias_text = Text(f"{hostname}:{kong_port}", style="color(75)")
            else:
                alias_text = Text("-", style="color(243)")

            category = _category_by_name.get(name, "")
            bar = Text("▰", style=style_for_category(category))
            table.add_row(
                port_val,
                name,
                bar,
                Text(source, style=source_style),
                alias_text,
                Text(status_text, style=status_style),
            )

        # Cloud APIs panel — renders below the services table. Cloud
        # providers don't run as containers (scale: 0) so they don't
        # belong as rows in the services grid; this keeps them visible
        # without misleading the user about what's getting started.
        from rich.console import Group
        from rich.panel import Panel
        cloud_lines = []
        for name, source_var, api_key_var in all_cloud_apis():
            source = (
                service_sources.get(source_var, env_vars.get(source_var, 'disabled'))
                or ''
            ).strip().lower()
            key_set = bool((env_vars.get(api_key_var, '') or '').strip())
            enabled = source == 'enabled'
            line = Text()
            line.append(f"  {name:<11}", style="bright_white")
            # Status string is shared with the Textual CloudApisRow via
            # state_builder.cloud_api_status_text — only the Rich style
            # is local to this renderer.
            if enabled and key_set:
                style = "bright_green"
            elif enabled and not key_set:
                style = "bright_yellow"
            else:
                style = "color(243)"
            line.append(cloud_api_status_text(enabled, key_set), style=style)
            cloud_lines.append(line)
        cloud_panel = Panel(
            Group(*cloud_lines) if cloud_lines else Text("(none)", style="color(243)"),
            title="[bold bright_white]Cloud APIs[/bold bright_white]  "
                  "[color(243)](LiteLLM-routed, no containers)[/color(243)]",
            border_style="color(240)",
            padding=(0, 1),
            expand=True,
        )
        return Group(table, cloud_panel)

    @staticmethod
    def _get_localhost_port(service_name: str, env_vars: dict) -> str:
        """Extract the actual localhost port from the service's endpoint env var."""
        from services.topology import get_topology
        _topology = get_topology()
        var = None
        for r in _topology.rows:
            if r.display_name == service_name:
                var = r.localhost_endpoint_var
                break
        if var:
            endpoint = env_vars.get(var, '')
            match = re.search(r':(\d+)', endpoint)
            if match:
                return f":{match.group(1)}"
        return "-"

    @staticmethod
    def _get_service_status(source: str, scale: str) -> tuple:
        """Get a status label with ● indicator and style for a service."""
        if source == 'disabled':
            return "● off", "color(245)"
        if 'localhost' in source:
            return "● local", "bright_cyan"
        if 'external' in source:
            return "● external", "bright_yellow"
        if source == 'api':
            return "● API", "bright_yellow"
        if 'gpu' in source:
            return "● GPU", "bright_green"
        if scale == '0':
            return "● off", "color(245)"
        return "● on", "bright_green"

    def check_comfyui_models(self):
        """Check ComfyUI local models."""
        self.service_config.check_comfyui_local_models()
        
    def show_container_status_and_verify_ports(self, on_line=None):
        """
        Show container status and verify actual vs expected ports.
        Replicates the verification logic from original start.sh.

        When `on_line` is provided (TUI mode), the redundant `docker compose ps`
        text dump is dropped and per-service results route through `on_line`
        with a level keyword ("ok"/"warn"/"error"). When `on_line` is None
        (legacy mode), behavior is unchanged from the original implementation.
        """
        # Get expected ports from .env (used by both branches)
        env_vars = self.config_parser.parse_env_file()

        # Service definitions matching original Bash script
        services_to_check = [
            ("supabase-db", "5432", env_vars.get("SUPABASE_DB_PORT", "")),
            ("redis", "6379", env_vars.get("REDIS_PORT", "")),
            ("supabase-meta", "8080", env_vars.get("SUPABASE_META_PORT", "")),
            ("supabase-storage", "5000", env_vars.get("SUPABASE_STORAGE_PORT", "")),
            ("supabase-auth", "9999", env_vars.get("SUPABASE_AUTH_PORT", "")),
            ("supabase-api", "3000", env_vars.get("SUPABASE_API_PORT", "")),
            ("supabase-realtime", "4000", env_vars.get("SUPABASE_REALTIME_PORT", "")),
            ("supabase-studio", "3000", env_vars.get("SUPABASE_STUDIO_PORT", "")),
            ("neo4j-graph-db", "7687", env_vars.get("GRAPH_DB_PORT", "")),
            ("weaviate", "8080", env_vars.get("WEAVIATE_PORT", "")),
            ("local-deep-researcher", "2024", env_vars.get("LOCAL_DEEP_RESEARCHER_PORT", "")),
            ("open-web-ui", "8080", env_vars.get("OPEN_WEB_UI_PORT", "")),
            ("backend", "8000", env_vars.get("BACKEND_PORT", "")),
            ("kong-api-gateway", "8000", env_vars.get("KONG_HTTP_PORT", "")),
            ("kong-api-gateway", "8443", env_vars.get("KONG_HTTPS_PORT", "")),
            ("n8n", "5678", env_vars.get("N8N_PORT", "")),
            ("searxng", "8080", env_vars.get("SEARXNG_PORT", "")),
            ("jupyterhub", "8888", env_vars.get("JUPYTERHUB_PORT", "")),
        ]

        # LiteLLM is the always-on LLM front door — its host port is the
        # canonical LLM-stack port now.
        services_to_check.append(("litellm", "4000", env_vars.get("LITELLM_PORT", "")))

        # Add conditional services based on their scales
        ollama_scale = env_vars.get("OLLAMA_SCALE", "0")
        if ollama_scale != "0":
            # Ollama upstream is internal-only; no host port mapping to verify.
            pass

        comfyui_scale = env_vars.get("COMFYUI_SCALE", "0")
        if comfyui_scale != "0":
            services_to_check.append(("comfyui", "18188", env_vars.get("COMFYUI_PORT", "")))

        if on_line is None:
            # Legacy linear flow — preserve today's exact behavior including
            # the `docker compose ps` text dump.
            print()
            self.docker_manager.show_container_status()
            print()
            print("🔍 Checking if Docker assigned the expected ports...")

            for service_name, internal_port, expected_port in services_to_check:
                if not expected_port:
                    continue
                actual_port = self.docker_manager.get_service_port(service_name, internal_port)
                if not actual_port:
                    print(f"  • ❌ {service_name}: Could not determine port mapping")
                elif actual_port == expected_port:
                    print(f"  • ✅ {service_name}: Using expected port {expected_port}")
                else:
                    print(f"  • ⚠️  {service_name}: Expected port {expected_port} but got {actual_port}")
            return

        # TUI mode — route per-service lines through on_line, skip the ps dump.
        # The dots in the anchored box already convey "is the container up";
        # this verification is specifically about port-mapping correctness.
        mismatches = 0
        for service_name, internal_port, expected_port in services_to_check:
            if not expected_port:
                continue
            actual_port = self.docker_manager.get_service_port(service_name, internal_port)
            if not actual_port:
                on_line(f"❌ {service_name}: could not determine port mapping", "error")
                mismatches += 1
            elif actual_port == expected_port:
                on_line(f"✅ {service_name}: port {expected_port} ok", "ok")
            else:
                on_line(f"⚠️  {service_name}: expected :{expected_port}, got :{actual_port}", "warn")
                mismatches += 1
        return mismatches
                
    def show_container_logs(self):
        """
        Show container logs with follow option.
        Replicates the logs display from original start.sh.
        """
        try:
            self.docker_manager.show_container_logs(follow=True)
        except KeyboardInterrupt:
            print("\n🔄 Log viewing interrupted by user")
            print("   Use 'docker compose logs -f' to view logs again")
        


@click.command()
@click.option('--base-port', type=int, help=f'Base port for all services (default: {DEFAULT_BASE_PORT})')
@click.option('--cold', is_flag=True, help='Perform cold start with cleanup')
@click.option('--setup-hosts', is_flag=True, help='Setup hosts file entries (requires admin/sudo)')
@click.option('--skip-hosts', is_flag=True, help='Skip hosts file checks and setup')
@click.option('--llm-provider-source',
              type=click.Choice(['ollama-container-cpu', 'ollama-container-gpu', 'ollama-localhost',
                                'ollama-external', 'none'], case_sensitive=False),
              help='Override LLM_PROVIDER_SOURCE (Ollama upstream for the LiteLLM gateway). '
                   'Use "none" for cloud-only operation.')
@click.option('--cloud-openai-source',
              type=click.Choice(['enabled', 'disabled'], case_sensitive=False),
              help='Enable/disable the OpenAI cloud provider in LiteLLM (requires OPENAI_API_KEY).')
@click.option('--cloud-anthropic-source',
              type=click.Choice(['enabled', 'disabled'], case_sensitive=False),
              help='Enable/disable the Anthropic cloud provider in LiteLLM (requires ANTHROPIC_API_KEY).')
@click.option('--cloud-openrouter-source',
              type=click.Choice(['enabled', 'disabled'], case_sensitive=False),
              help='Enable/disable the OpenRouter cloud provider in LiteLLM (requires OPENROUTER_API_KEY).')
@click.option('--openai-api-key', type=str, default=None,
              help='OpenAI API key (sk-...). Persists to .env as OPENAI_API_KEY and '
                   'implies --cloud-openai-source=enabled.')
@click.option('--anthropic-api-key', type=str, default=None,
              help='Anthropic API key (sk-ant-...). Persists to .env as ANTHROPIC_API_KEY '
                   'and implies --cloud-anthropic-source=enabled.')
@click.option('--openrouter-api-key', type=str, default=None,
              help='OpenRouter API key (sk-or-...). Persists to .env as OPENROUTER_API_KEY '
                   'and implies --cloud-openrouter-source=enabled.')
@click.option('--openai-models', type=str, default=None,
              help='Comma-separated OpenAI model names to activate (e.g. "gpt-5,gpt-5-mini,o3"). '
                   'Persists to .env as OPENAI_USER_MODELS; llm-catalog-init activates these in public.llms.')
@click.option('--anthropic-models', type=str, default=None,
              help='Comma-separated Anthropic model names to activate. Persists as ANTHROPIC_USER_MODELS.')
@click.option('--openrouter-models', type=str, default=None,
              help='Comma-separated OpenRouter model names to activate. Persists as OPENROUTER_USER_MODELS.')
@click.option('--ollama-models', type=str, default=None,
              help='Comma-separated Ollama model names to activate from the curated catalog. '
                   'Persists as OLLAMA_USER_MODELS.')
@click.option('--ollama-custom-models', type=str, default=None,
              help='Comma-separated extra Ollama model names to pull (not in catalog). '
                   'Persists as OLLAMA_CUSTOM_MODELS; ollama-pull fetches them at startup.')
@click.option('--comfyui-source', 
              type=click.Choice(['container-cpu', 'container-gpu', 'localhost', 
                                'external', 'disabled'], case_sensitive=False),
              help='Override COMFYUI_SOURCE')
@click.option('--weaviate-source',
              type=click.Choice(['container', 'localhost', 'disabled'], case_sensitive=False),
              help='Override WEAVIATE_SOURCE')
@click.option('--minio-source',
              type=click.Choice(['container', 'disabled'], case_sensitive=False),
              help='Override MinIO source')
@click.option('--n8n-source',
              type=click.Choice(['container', 'disabled'], case_sensitive=False),
              help='Override N8N_SOURCE')
@click.option('--searxng-source',
              type=click.Choice(['container', 'disabled'], case_sensitive=False),
              help='Override SEARXNG_SOURCE')
@click.option('--jupyterhub-source',
              type=click.Choice(['container', 'disabled'], case_sensitive=False),
              help='Override JUPYTERHUB_SOURCE')
@click.option('--open-web-ui-source',
              type=click.Choice(['container', 'disabled'], case_sensitive=False),
              help='Override OPEN_WEB_UI_SOURCE')
@click.option('--local-deep-researcher-source',
              type=click.Choice(['container', 'disabled'], case_sensitive=False),
              help='Override LOCAL_DEEP_RESEARCHER_SOURCE')
@click.option('--stt-provider-source',
              type=click.Choice(['speaches-container-cpu', 'speaches-container-gpu',
                                'parakeet-container-gpu', 'parakeet-localhost',
                                'whisper-cpp-localhost', 'disabled'],
                                case_sensitive=False),
              help='Override STT_PROVIDER_SOURCE')
@click.option('--tts-provider-source',
              type=click.Choice(['speaches-container-cpu', 'speaches-container-gpu',
                                'chatterbox-container-gpu', 'chatterbox-localhost',
                                'disabled'], case_sensitive=False),
              help='Override TTS_PROVIDER_SOURCE')
@click.option('--doc-processor-source',
              type=click.Choice(['docling-container-gpu', 'docling-localhost',
                                'disabled'], case_sensitive=False),
              help='Override DOC_PROCESSOR_SOURCE')
@click.option('--openclaw-source',
              type=click.Choice(['container', 'localhost',
                                'disabled'], case_sensitive=False),
              help='Override OPENCLAW_SOURCE')
@click.option('--hermes-source',
              type=click.Choice(['container', 'localhost',
                                'disabled'], case_sensitive=False),
              help='Override HERMES_SOURCE')
@click.option('--neo4j-graph-db-source',
              type=click.Choice(['container', 'localhost',
                                'disabled'], case_sensitive=False),
              help='Override NEO4J_GRAPH_DB_SOURCE')
@click.option('--multi2vec-clip-source',
              type=click.Choice(['container-cpu', 'container-gpu',
                                'disabled'], case_sensitive=False),
              help='Override MULTI2VEC_CLIP_SOURCE')
@click.option('--ray-source',
              type=click.Choice(['ray-container-cpu', 'ray-container-gpu',
                                'ray-external', 'disabled'], case_sensitive=False),
              help='Override RAY_SOURCE (Ray distributed-compute cluster). '
                   'Use "ray-external" with --ray-external-address pointing at an '
                   'Anyscale or self-hosted Ray cluster URL.')
@click.option('--ray-worker-count', type=int, default=None,
              help='Override RAY_WORKER_COUNT — number of ray-worker replicas '
                   'when --ray-source is ray-container-cpu or ray-container-gpu. '
                   '0 = head-only single-node mode. Defaults to 2 in .env.example.')
@click.option('--ray-external-address', type=str, default=None,
              help='Override RAY_EXTERNAL_ADDRESS — required when --ray-source=ray-external. '
                   'Format: ray://hostname:10001.')
@click.option('--no-tui', is_flag=True,
              help='Disable the TUI (wizard + Textual log app). Falls back to the legacy '
                   'linear flow with passthrough docker output. Useful for log capture, '
                   'debugging, and terminals that don\'t support the alternate screen buffer.')
@click.option('--no-port-migrate', is_flag=True, default=False,
              help='Skip the v0 → v1 port-layout .env rewrite. Still stamps the version '
                   'sentinel so the migration does not re-prompt.')
def main(base_port, cold, setup_hosts, skip_hosts, llm_provider_source,
         cloud_openai_source, cloud_anthropic_source, cloud_openrouter_source,
         openai_api_key, anthropic_api_key, openrouter_api_key,
         openai_models, anthropic_models, openrouter_models,
         ollama_models, ollama_custom_models,
         comfyui_source, weaviate_source, minio_source, n8n_source, searxng_source,
         jupyterhub_source, open_web_ui_source, local_deep_researcher_source,
         stt_provider_source, tts_provider_source,
         doc_processor_source, openclaw_source, hermes_source,
         neo4j_graph_db_source,
         multi2vec_clip_source,
         ray_source, ray_worker_count, ray_external_address,
         no_tui, no_port_migrate):
    """Start the GenAI Vanilla Stack - Cross-platform AI development environment."""

    starter = GenAIStackStarter()

    try:
        # Cloud LLM provider keys passed via CLI flags. Persisting to
        # .env happens later, alongside source overrides — gathered
        # here so the implied --cloud-*-source toggles are applied
        # together with the explicit ones.
        cloud_api_keys: Dict[str, str] = {}
        if openai_api_key is not None:
            cloud_api_keys['OPENAI_API_KEY'] = openai_api_key
            if cloud_openai_source is None:
                cloud_openai_source = 'enabled'
        if anthropic_api_key is not None:
            cloud_api_keys['ANTHROPIC_API_KEY'] = anthropic_api_key
            if cloud_anthropic_source is None:
                cloud_anthropic_source = 'enabled'
        if openrouter_api_key is not None:
            cloud_api_keys['OPENROUTER_API_KEY'] = openrouter_api_key
            if cloud_openrouter_source is None:
                cloud_openrouter_source = 'enabled'

        # User-selected model lists from CLI flags. llm-catalog-init
        # consumes these on the next docker compose up to activate the
        # matching public.llms rows.
        user_model_selections: Dict[str, str] = {}
        if openai_models is not None:
            user_model_selections['OPENAI_USER_MODELS'] = openai_models
        if anthropic_models is not None:
            user_model_selections['ANTHROPIC_USER_MODELS'] = anthropic_models
        if openrouter_models is not None:
            user_model_selections['OPENROUTER_USER_MODELS'] = openrouter_models
        if ollama_models is not None:
            user_model_selections['OLLAMA_USER_MODELS'] = ollama_models
        if ollama_custom_models is not None:
            user_model_selections['OLLAMA_CUSTOM_MODELS'] = ollama_custom_models

        # Warn on cloud --*-models flags passed WITHOUT enabling the
        # provider. llm-catalog-init deactivates every row of a disabled
        # provider, so the persisted CSV would be inert. Surface this to
        # the user instead of silently no-op'ing. The matching key flag
        # implies enabling above; a bare --openai-models is the case to
        # warn on. We check the .env-resolved source too — the user may
        # have already set CLOUD_OPENAI_SOURCE=enabled in .env without
        # passing --cloud-openai-source on this invocation.
        try:
            _existing_env = starter.config_parser.parse_env_file()
        except Exception:  # noqa: BLE001
            _existing_env = {}
        for _models_flag, _source_kwarg, _source_var in (
            (openai_models,     cloud_openai_source,     'CLOUD_OPENAI_SOURCE'),
            (anthropic_models,  cloud_anthropic_source,  'CLOUD_ANTHROPIC_SOURCE'),
            (openrouter_models, cloud_openrouter_source, 'CLOUD_OPENROUTER_SOURCE'),
        ):
            if _models_flag is None:
                continue
            _effective = (_source_kwarg
                          or _existing_env.get(_source_var, 'disabled')
                          or '').strip().lower()
            if _effective != 'enabled':
                _provider = _source_var.removeprefix('CLOUD_').removesuffix('_SOURCE').lower()
                print(
                    f"⚠️  --{_provider}-models was set but {_source_var}={_effective} — "
                    f"llm-catalog-init will deactivate every {_provider} row, so the "
                    f"persisted list won't take effect. Pass --{_provider}-api-key, "
                    f"--cloud-{_provider}-source=enabled, or set {_source_var}=enabled "
                    f"in .env.",
                    file=sys.stderr,
                )

        # Step 1.6: Apply SOURCE overrides from CLI arguments
        source_args = {
            'llm_provider_source': llm_provider_source,
            'cloud_openai_source': cloud_openai_source,
            'cloud_anthropic_source': cloud_anthropic_source,
            'cloud_openrouter_source': cloud_openrouter_source,
            'comfyui_source': comfyui_source,
            'weaviate_source': weaviate_source,
            'minio_source': minio_source,
            'n8n_source': n8n_source,
            'searxng_source': searxng_source,
            'jupyterhub_source': jupyterhub_source,
            'stt_provider_source': stt_provider_source,
            'tts_provider_source': tts_provider_source,
            'doc_processor_source': doc_processor_source,
            'openclaw_source': openclaw_source,
            'hermes_source': hermes_source,
            'neo4j_graph_db_source': neo4j_graph_db_source,
            'multi2vec_clip_source': multi2vec_clip_source,
            'ray_source': ray_source,
        }
        # Ray non-SOURCE settings (worker count + external address) get
        # plumbed via update_env_file the same way the cloud-API keys do.
        if ray_worker_count is not None:
            user_model_selections['RAY_WORKER_COUNT'] = str(ray_worker_count)
        if ray_external_address is not None:
            user_model_selections['RAY_EXTERNAL_ADDRESS'] = ray_external_address

        # Step 0: Early sudo check for CLI --setup-hosts flag
        if setup_hosts:
            from utils.system import is_elevated as _is_elevated
            if not _is_elevated():
                starter.banner.console.print("\n  [bright_yellow]⚠️  --setup-hosts requires admin privileges.[/bright_yellow]")
                starter.banner.console.print("  [bright_white]Please restart with:[/bright_white] [bright_cyan]sudo ./start.sh --setup-hosts[/bright_cyan]")
                sys.exit(1)

        # Determine if wizard mode — only when NO flags are provided at all.
        # Both the model-list flags (--openai-models / --ollama-models / etc.)
        # and the cloud-key flags (--openai-api-key / etc.) count as "non-wizard
        # intent": presence of either means the user is configuring via CLI
        # and the wizard would silently overwrite their input.
        wizard_ran = False
        no_source_flags = all(v is None for v in source_args.values())
        no_stack_flags = (base_port is None and not cold and not setup_hosts and not skip_hosts)
        no_model_flags = not user_model_selections
        no_key_flags = not cloud_api_keys
        will_run_wizard = (
            no_source_flags and no_stack_flags
            and no_model_flags and no_key_flags
            and sys.stdin.isatty()
        )

        # Check dependencies early — silently in wizard mode (wizard clears screen)
        if not will_run_wizard:
            if not starter.ensure_dependencies_available():
                sys.exit(1)
        else:
            if not starter.docker_manager.check_docker_available():
                print("❌ Docker is not available. Please install Docker and ensure it's running.")
                sys.exit(1)

        if will_run_wizard:
            # Setup .env first so wizard can read current defaults.
            if not starter.setup_env_file(cold_start=cold, base_port=base_port):
                sys.exit(1)
            # Backfill any keys added to .env.example since the user's
            # .env was last written — run BEFORE the wizard reads it,
            # otherwise new vars (MinIO image / ports / bucket names,
            # etc.) won't appear as defaults in the wizard's prompts
            # and ``docker compose config`` will fail later with
            # ``variable X not set``.
            if not starter.backfill_missing_env_vars():
                sys.exit(1)

            # The Textual wizard owns the entire interactive flow when the
            # terminal can host it. Non-TUI shells (--no-tui, non-TTY,
            # narrow terminals) skip the wizard and use the user's .env
            # defaults plus any CLI flags they passed.
            from ui.term_caps import is_tui_capable as _is_tui_capable
            if _is_tui_capable(no_tui_flag=no_tui):
                # Single-Textual-app flow: wizard + pipeline + docker
                # compose log streaming all run inside one App. start.py
                # exits when the user detaches.
                from ui.textual.integration import run_setup_flow
                rc = run_setup_flow(
                    starter.config_parser, starter.hosts_manager,
                    starter=starter,
                    no_port_migrate=no_port_migrate,
                )
                sys.exit(rc)

        # CLI-flag mode + TUI capable: skip the wizard but still use the
        # Textual launch screen, pre-loaded with the user's CLI args.
        # Falls through to the linear stdout flow only when --no-tui or
        # the terminal can't host the TUI. This block must run BEFORE
        # the banner / setup_env_file / apply_source_overrides pipeline
        # below so its output stays out of the terminal and ends up
        # inside the log pane.
        if not wizard_ran and not no_tui:
            from ui.term_caps import is_tui_capable as _is_tui_capable
            if _is_tui_capable(no_tui_flag=no_tui):
                # Make sure .env exists so the launch screen can build
                # the Stack overview.
                if not starter.setup_env_file(cold_start=cold, base_port=base_port):
                    sys.exit(1)
                # Backfill new .env.example keys before the launch
                # screen renders the Stack overview from .env.
                if not starter.backfill_missing_env_vars():
                    sys.exit(1)
                from ui.textual.integration import run_launch_flow
                stack_options = {
                    "base_port": base_port,
                    "cold": cold,
                    "setup_hosts": setup_hosts,
                    "skip_hosts": skip_hosts,
                    "launch_confirmed": True,
                    # Forward any CLI-supplied cloud API keys into the
                    # launch pipeline; the wizard pipeline writes them
                    # to .env via SourceOverrideManager.update_env_file.
                    "cloud_api_keys": cloud_api_keys,
                    # Forward any CLI-supplied user model selections
                    # (X_USER_MODELS / OLLAMA_CUSTOM_MODELS). Same path
                    # as the wizard's multiselect output — keys live
                    # in cloud_user_models/ollama_user_models split,
                    # but they all flow through apply_user_model_selections.
                    "cloud_user_models": {
                        k: v for k, v in user_model_selections.items()
                        if k.endswith("_USER_MODELS") and not k.startswith("OLLAMA_")
                    },
                    "ollama_user_models": {
                        k: v for k, v in user_model_selections.items()
                        if k.startswith("OLLAMA_")
                    },
                }
                rc = run_launch_flow(
                    starter.config_parser, starter.hosts_manager,
                    starter=starter,
                    source_args=source_args,
                    stack_options=stack_options,
                    no_port_migrate=no_port_migrate,
                )
                sys.exit(rc)

        # Show banner for normal mode (wizard already displayed its own)
        if not wizard_ran:
            starter.show_banner()

        # Setup .env file (skipped if wizard already did it)
        if not wizard_ran:
            if not starter.setup_env_file(cold_start=cold, base_port=base_port):
                sys.exit(1)

        # Pull in any keys added to .env.example since the user's .env
        # was written (e.g. a worktree merge added a new service like
        # MinIO and its config block). Idempotent; preserves all
        # existing values and auto-generated secrets.
        if not starter.backfill_missing_env_vars():
            sys.exit(1)

        if not starter.apply_source_overrides(**source_args):
            sys.exit(1)

        # Persist any CLI-supplied cloud API keys to .env. No-op when
        # the dict is empty.
        if not starter.apply_cloud_api_keys(cloud_api_keys):
            sys.exit(1)

        # Persist any CLI-supplied user model selections to .env.
        # llm-catalog-init reads these on the next docker compose up.
        if not starter.apply_user_model_selections(user_model_selections):
            sys.exit(1)

        # v0 → v1 port-layout migration. Runs after .env is fully populated
        # (setup_env_file + backfill + overrides) but before port_manager
        # rewrites ports, so we act on the user's pre-existing values rather
        # than ones we've just computed. The TUI flows call this helper
        # themselves immediately after backfill (see run_setup_flow /
        # run_launch_flow); this branch covers the --no-tui linear path.
        starter.run_port_migration(no_port_migrate)

        # Step 1.7: Cold start cleanup if requested (before port check).
        # TUI-capable runs exit before reaching this point; the Textual
        # wizard handles cold cleanup inline. This branch only fires for
        # the --no-tui / non-TTY linear flow.
        if cold:
            starter.perform_cold_start_cleanup()
        
        # Step 2: Validate SOURCE configurations
        if not starter.validate_source_configurations():
            sys.exit(1)
        
        # Step 3: Handle port configuration
        if not starter.handle_port_configuration(base_port):
            sys.exit(1)
        
        # Step 4: Generate service configuration
        if not starter.generate_service_configuration():
            sys.exit(1)
            
        # Step 4.1: Check service dependencies
        if not starter.check_service_dependencies():
            sys.exit(1)
        
        # Step 4.5: Generate dynamic Kong configuration
        if not starter.generate_kong_configuration():
            sys.exit(1)

        # Step 4.55: Write LiteLLM stub config.yaml so the bind mount has
        # a file. The real model_list is rendered later by litellm-init
        # from public.llms — see services/litellm/init/scripts/init.py.
        if not starter.generate_litellm_configuration():
            sys.exit(1)

        # Step 4.6: Validate Supabase keys (auto-generate for cold start)
        if not starter.validate_supabase_keys(cold_start=cold):
            sys.exit(1)
        
        # Step 5: Handle hosts configuration
        if not starter.handle_hosts_configuration(setup_hosts, skip_hosts):
            sys.exit(1)
        
        # Step 6: Generate encryption keys (improved behavior - always ensures keys exist)
        if not starter.generate_encryption_keys(cold_start=cold):
            sys.exit(1)
        
        # Step 7: Validate localhost services before starting
        if not starter.validate_localhost_services():
            sys.exit(1)

        # Defensive final backfill — see notes on the wizard pipeline's
        # matching step. Catches any case where an intermediate pipeline
        # step regenerated .env from a parsed snapshot rather than the
        # in-place regex replacement, dropping keys present in
        # .env.example but not (yet) tracked by service_config.
        if not starter.backfill_missing_env_vars():
            sys.exit(1)

        # Pre-launch summary + docker streaming. TUI-capable runs exit
        # before reaching this point (the Textual wizard owns its own
        # summary, confirmation, and live log streaming). This linear
        # flow runs only for --no-tui / non-TTY contexts: show the
        # Rich-Table summary, prompt for confirm, then stream docker
        # output via TTY passthrough.
        if not starter.show_pre_launch_summary():
            starter.banner.console.print("\n  [color(245)]Launch cancelled.[/color(245)]")
            sys.exit(0)
        if not starter.start_docker_services(cold_start=cold):
            sys.exit(1)
        starter.show_container_status_and_verify_ports()
        starter.check_comfyui_models()
        starter.show_container_logs()

    except KeyboardInterrupt:
        print("\n❌ Startup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()