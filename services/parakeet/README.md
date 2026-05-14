# services/parakeet — NVIDIA Parakeet STT (GPU)

One of three STT engines in the stack. Parakeet **owns the
`STT_PROVIDER_SOURCE` var** — that's the stack-wide selector enumerating
all valid STT options (`parakeet-*`, `speaches-*`, `whisper-cpp-localhost`,
`disabled`). Some of those options activate sibling services
(`speaches-*` turns on the [speaches](../speaches/) container; the
`whisper-cpp-localhost` option is host-install).

Engine-neutral consumers (n8n, backend, jupyterhub, open-webui,
hermes-init) reference `${STT_ENDPOINT}` — auto-resolved to whichever
engine is active.

## Containers

| Container | Role | Image var |
|---|---|---|
| `parakeet-gpu` | NVIDIA-accelerated Faster-Whisper-shaped Parakeet worker, OpenAI-compatible | `PARAKEET_GPU_IMAGE` |

## Subfolders

- **`provider/`** — source-variant code:
  - `gpu/` — Dockerfile + `transcribe.py` + `requirements.txt` for the
    in-stack GPU container.
  - `mlx/` — macOS Apple-Silicon path (host install via MLX). README, API
    server, requirements.
  - `whisper-cpp/` — README documenting the `whisper-cpp-localhost`
    host-install path (this folder ships no code; whisper.cpp lives on
    the user's machine).
  - `shared/` — common scaffolding reused by GPU + MLX (`api_server.py`,
    `utils.py`).

## See also

- [`docs/services/stt-provider.md`](../../docs/services/stt-provider.md) — full STT-engine matrix, source IDs, env vars.
- [`services/speaches/`](../speaches/) — sibling STT/TTS engine.
- [`provider/README.md`](provider/README.md) — quick-start per provider variant.
