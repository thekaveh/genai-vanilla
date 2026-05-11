"""
Shared display-name → endpoint-env-var mapping.

Used wherever the bootstrapper needs to look up the host-side port a
``localhost``-mode service is reachable on. Keys are the canonical
display names used in the wizard / overview / CLI flags. Values are
the env vars that hold the endpoint URL (e.g.
``http://localhost:18188``).

Two consumers historically maintained their own copies and a comment
saying "must mirror the other one":

  • ``bootstrapper/ui/state_builder.py:_LOCALHOST_ENDPOINT_VARS``
  • ``bootstrapper/start.py:GenAIStackStarter._get_localhost_port``

Now both import this dict so adding/renaming a service touches one
place. Sibling of ``cloud_providers.py`` — both are zero-knowledge
shared mappings used across UI + start.py + service_config.
"""

from __future__ import annotations

from typing import Dict


LOCALHOST_ENDPOINT_VARS: Dict[str, str] = {
    "LiteLLM":           "LITELLM_BASE_URL",
    "LLM Engine":        "LITELLM_OLLAMA_UPSTREAM",
    "ComfyUI":           "COMFYUI_ENDPOINT",
    "Weaviate":          "WEAVIATE_URL",
    "Neo4j Graph DB":    "NEO4J_URI",
    "STT Provider":      "PARAKEET_ENDPOINT",
    "TTS Provider":      "XTTS_ENDPOINT",
    "Document Processor": "DOCLING_ENDPOINT",
    "OpenClaw":          "OPENCLAW_ENDPOINT",
}
