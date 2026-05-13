"""Hook for the openclaw manifest.

OpenClaw has a gateway+bridge port pair and three source variants. The
gateway/bridge ports already have their own dedicated env vars; the hook
only handles the endpoint URL.
"""

from __future__ import annotations


def apply(env: dict[str, str]) -> dict[str, str]:
    source = env.get("OPENCLAW_SOURCE", "disabled")
    if source == "container":
        env["OPENCLAW_SCALE"] = "1"
        env["OPENCLAW_INIT_SCALE"] = "1"
        env["OPENCLAW_ENDPOINT"] = "http://openclaw-gateway:18789"
    elif source == "localhost":
        env["OPENCLAW_SCALE"] = "0"
        env["OPENCLAW_INIT_SCALE"] = "0"
        env["OPENCLAW_ENDPOINT"] = env.get(
            "OPENCLAW_LOCALHOST_URL", "http://host.docker.internal:63024"
        )
    elif source == "disabled":
        env["OPENCLAW_SCALE"] = "0"
        env["OPENCLAW_INIT_SCALE"] = "0"
        env["OPENCLAW_ENDPOINT"] = ""
    return env
