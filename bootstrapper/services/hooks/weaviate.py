"""Hook for the weaviate manifest.

Computes:
  - WEAVIATE_OLLAMA_ENDPOINT — mirrors OLLAMA_ENDPOINT (so Weaviate's
    text2vec-ollama vectorizer reaches the same upstream).
  - WEAVIATE_LITELLM_BASE_URL — derived from LITELLM_PORT + BASE_PORT
    (this is the HOST-side URL, since the Weaviate text2vec-openai module
    runs the LiteLLM call from outside-container context in some setups).
  - WEAVIATE_LITELLM_API_KEY — mirrors LITELLM_MASTER_KEY.
  - CLIP_SCALE, CLIP_ENABLE_CUDA — driven by MULTI2VEC_CLIP_SOURCE.
"""

from __future__ import annotations


def apply(env: dict[str, str]) -> dict[str, str]:
    env["WEAVIATE_OLLAMA_ENDPOINT"] = env.get("OLLAMA_ENDPOINT", "")

    # WEAVIATE_LITELLM_BASE_URL: in-container default is fine; the in-stack
    # URL is what Weaviate uses when calling LiteLLM from inside the network.
    env["WEAVIATE_LITELLM_BASE_URL"] = "http://litellm:4000/v1"
    env["WEAVIATE_LITELLM_API_KEY"] = env.get("LITELLM_MASTER_KEY", "")

    clip_source = env.get("MULTI2VEC_CLIP_SOURCE", "container-cpu")
    if clip_source == "container-cpu":
        env["CLIP_SCALE"] = "1"
        env["CLIP_ENABLE_CUDA"] = "0"
    elif clip_source == "container-gpu":
        env["CLIP_SCALE"] = "1"
        env["CLIP_ENABLE_CUDA"] = "1"
    elif clip_source == "disabled":
        env["CLIP_SCALE"] = "0"
        env["CLIP_ENABLE_CUDA"] = "0"
    return env
