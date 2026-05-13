"""Hook for the chatterbox manifest.

Chatterbox is a GPU TTS engine. Activated when
`TTS_PROVIDER_SOURCE=chatterbox-container-gpu`. The `chatterbox-localhost`
variant uses the user's host install (no container), so it sets
CHATTERBOX_SCALE=0 too — only the container variant brings up the
service.
"""

from __future__ import annotations


def apply(env: dict[str, str]) -> dict[str, str]:
    tts = env.get("TTS_PROVIDER_SOURCE", "")
    env["CHATTERBOX_SCALE"] = "1" if tts == "chatterbox-container-gpu" else "0"
    return env
