"""
LiteLLM proxy configuration generator.

Renders volumes/litellm/config.yaml from environment values. The model_list
varies based on:
  - LITELLM_OLLAMA_UPSTREAM (when non-empty, includes Ollama-prefixed models)
  - LITELLM_OPENAI_ENABLED / LITELLM_ANTHROPIC_ENABLED / LITELLM_OPENROUTER_ENABLED
    (each adds a curated set of cloud models)

Static settings (cache, router, master key, database url) use LiteLLM's
`os.environ/VAR` form so they resolve at LiteLLM container start.

Mirrors the pattern in kong_config_generator.py: build a dict, dump as YAML.
Writes only when the destination is absent (preserves user edits); pass
force=True to overwrite.
"""

from pathlib import Path
from typing import Any, Dict, List

import yaml


DEFAULT_OLLAMA_MODELS = [
    "qwen3.6:latest",
    "qwen3-embedding:0.6b",
    "nomic-embed-text",
]

DEFAULT_OPENAI_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "o1",
    "o3-mini",
]

DEFAULT_ANTHROPIC_MODELS = [
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
]

DEFAULT_OPENROUTER_MODELS = [
    "openrouter/auto",
    "openrouter/anthropic/claude-sonnet-4-6",
    "openrouter/openai/gpt-4o",
]


class LiteLLMConfigGenerator:
    """Generates volumes/litellm/config.yaml from environment values."""

    def __init__(self, config_parser):
        self.config_parser = config_parser
        self.env_vars: Dict[str, str] = {}

    def load_environment_variables(self) -> None:
        self.env_vars = self.config_parser.parse_env_file()

    def _get(self, key: str, default: str = "") -> str:
        return self.env_vars.get(key, default)

    def _is_truthy(self, key: str) -> bool:
        return self._get(key, "false").strip().lower() in ("true", "1", "yes", "enabled")

    def _ollama_entries(self) -> List[Dict[str, Any]]:
        upstream = self._get("LITELLM_OLLAMA_UPSTREAM", "").strip()
        if not upstream:
            return []
        return [
            {
                "model_name": f"ollama/{name}",
                "litellm_params": {
                    "model": f"ollama/{name}",
                    "api_base": upstream,
                },
            }
            for name in DEFAULT_OLLAMA_MODELS
        ]

    def _openai_entries(self) -> List[Dict[str, Any]]:
        if not self._is_truthy("LITELLM_OPENAI_ENABLED"):
            return []
        return [
            {
                "model_name": name,
                "litellm_params": {
                    "model": name,
                    "api_key": "os.environ/OPENAI_API_KEY",
                },
            }
            for name in DEFAULT_OPENAI_MODELS
        ]

    def _anthropic_entries(self) -> List[Dict[str, Any]]:
        if not self._is_truthy("LITELLM_ANTHROPIC_ENABLED"):
            return []
        return [
            {
                "model_name": name,
                "litellm_params": {
                    "model": f"anthropic/{name}",
                    "api_key": "os.environ/ANTHROPIC_API_KEY",
                },
            }
            for name in DEFAULT_ANTHROPIC_MODELS
        ]

    def _openrouter_entries(self) -> List[Dict[str, Any]]:
        if not self._is_truthy("LITELLM_OPENROUTER_ENABLED"):
            return []
        return [
            {
                "model_name": name,
                "litellm_params": {
                    "model": name,
                    "api_key": "os.environ/OPENROUTER_API_KEY",
                },
            }
            for name in DEFAULT_OPENROUTER_MODELS
        ]

    def generate_config(self) -> Dict[str, Any]:
        self.load_environment_variables()

        model_list: List[Dict[str, Any]] = []
        model_list.extend(self._ollama_entries())
        model_list.extend(self._openai_entries())
        model_list.extend(self._anthropic_entries())
        model_list.extend(self._openrouter_entries())

        config: Dict[str, Any] = {
            "model_list": model_list,
            "litellm_settings": {
                "cache": True,
                "cache_params": {
                    "type": "redis",
                    "host": "os.environ/REDIS_HOST",
                    "port": "os.environ/REDIS_PORT",
                    "password": "os.environ/REDIS_PASSWORD",
                },
                "drop_params": True,
            },
            "router_settings": {
                "redis_host": "os.environ/REDIS_HOST",
                "redis_port": "os.environ/REDIS_PORT",
                "redis_password": "os.environ/REDIS_PASSWORD",
            },
            "general_settings": {
                "master_key": "os.environ/LITELLM_MASTER_KEY",
                "database_url": "os.environ/DATABASE_URL",
                "store_model_in_db": True,
            },
        }
        return config

    def write_config(self, output_path: Path, force: bool = False) -> bool:
        if output_path.exists() and not force:
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)
        config = self.generate_config()
        with open(output_path, "w") as fh:
            fh.write("# Generated by bootstrapper/utils/litellm_config_generator.py\n")
            fh.write("# Edit this file to customize model_list, fallbacks, or routing rules.\n")
            fh.write("# Re-running ./start.sh preserves manual edits unless --regenerate-litellm is passed.\n\n")
            yaml.safe_dump(config, fh, sort_keys=False, default_flow_style=False)
        return True
