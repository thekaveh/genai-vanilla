"""Hook for the cloud-providers virtual manifest.

Aggregates three independent CLOUD_*_SOURCE toggles into the LITELLM_*_ENABLED
flags and the comma-separated LITELLM_ENABLED_PROVIDERS list consumed by
llm-catalog-init.
"""

from __future__ import annotations


_PROVIDERS = ("openai", "anthropic", "openrouter")


def apply(env: dict[str, str]) -> dict[str, str]:
    enabled: list[str] = []
    for provider in _PROVIDERS:
        source_var = f"CLOUD_{provider.upper()}_SOURCE"
        flag_var = f"LITELLM_{provider.upper()}_ENABLED"
        is_enabled = env.get(source_var, "disabled") == "enabled"
        env[flag_var] = "true" if is_enabled else "false"
        if is_enabled:
            enabled.append(provider)
    env["LITELLM_ENABLED_PROVIDERS"] = ",".join(enabled)
    return env
