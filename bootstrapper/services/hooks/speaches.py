"""Hook for the speaches manifest.

Speaches is a unified TTS + STT container. Activation is driven externally —
by EITHER `STT_PROVIDER_SOURCE` (owned by parakeet's manifest, with
`speaches-container-{cpu,gpu}` as two of its source options) OR
`TTS_PROVIDER_SOURCE` (owned by the tts-provider virtual manifest, with
the same two options).

When both pick speaches, only one container runs (the deploy.replicas
key dedupes since both source effects would set SPEACHES_SCALE=1). When
neither picks speaches, SPEACHES_SCALE=0 and the container stays down.

Pattern mirrors `services.hooks.cloud_providers` (multi-input aggregation
that can't be expressed by a single sources.options[].effects mapping).
"""

from __future__ import annotations


def apply(env: dict[str, str]) -> dict[str, str]:
    stt = env.get("STT_PROVIDER_SOURCE", "")
    tts = env.get("TTS_PROVIDER_SOURCE", "")
    on = stt.startswith("speaches-") or tts.startswith("speaches-")
    env["SPEACHES_SCALE"] = "1" if on else "0"
    return env
