"""Hook for the comfyui manifest.

Computes COMFYUI_ENDPOINT, IS_LOCAL_COMFYUI, and COMFYUI_DEPLOY_RESOURCES
from COMFYUI_SOURCE + BASE_PORT + COMFYUI_PORT. Source variants:
  - container-cpu   → endpoint = http://comfyui:18188; CPU mode
  - container-gpu   → endpoint = http://comfyui:18188; GPU deploy block
  - localhost       → endpoint = COMFYUI_LOCALHOST_URL; IS_LOCAL_COMFYUI=true
  - external        → endpoint = COMFYUI_EXTERNAL_URL
  - disabled        → endpoint = ""; scale=0
"""

from __future__ import annotations


def apply(env: dict[str, str]) -> dict[str, str]:
    """Mutate env in place. Returns env for chaining."""
    source = env.get("COMFYUI_SOURCE", "container-cpu")

    if source == "container-cpu":
        env["COMFYUI_ENDPOINT"] = "http://comfyui:18188"
        env["IS_LOCAL_COMFYUI"] = "false"
        env["COMFYUI_DEPLOY_RESOURCES"] = "~"
    elif source == "container-gpu":
        env["COMFYUI_ENDPOINT"] = "http://comfyui:18188"
        env["IS_LOCAL_COMFYUI"] = "false"
        env["COMFYUI_DEPLOY_RESOURCES"] = (
            "reservations:\n  devices:\n    - driver: nvidia\n      capabilities: [gpu]"
        )
    elif source == "localhost":
        env["COMFYUI_ENDPOINT"] = env.get(
            "COMFYUI_LOCALHOST_URL", "http://host.docker.internal:8000"
        )
        env["IS_LOCAL_COMFYUI"] = "true"
        env["COMFYUI_DEPLOY_RESOURCES"] = "~"
    elif source == "external":
        env["COMFYUI_ENDPOINT"] = env.get("COMFYUI_EXTERNAL_URL", "")
        env["IS_LOCAL_COMFYUI"] = "false"
        env["COMFYUI_DEPLOY_RESOURCES"] = "~"
    elif source == "disabled":
        env["COMFYUI_ENDPOINT"] = ""
        env["IS_LOCAL_COMFYUI"] = "false"
        env["COMFYUI_DEPLOY_RESOURCES"] = "~"
    return env
