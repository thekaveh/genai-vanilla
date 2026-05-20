---
slug: unmute
name: Unmute (Kyutai)
type: external-service
category-fit: media
generated: 2026-05-19
upstream: https://github.com/kyutai-labs/unmute
license: MIT
referenced-by: [tts-provider]
---

# Unmute (Kyutai)

## Headline
A self-hosted, MIT-licensed WebSocket service that wraps any text LLM with Kyutai's streaming STT + TTS in an OpenAI-Realtime-compatible protocol.

## Problem it solves
Today the stack's voice loop is half-duplex: open-webui or backend records a full utterance, sends it to parakeet/speaches for transcription, calls LiteLLM, then waits for the full WAV back from chatterbox/speaches. End-to-end latency is several seconds and there's no barge-in. Unmute terminates a single browser WebSocket and streams partial tokens in both directions, matching the OpenAI Realtime API format the JS SDKs already speak, so it slots in without rewriting clients.

## Stack wiring sketch
- open-webui → unmute via WebSocket (Kong route `unmute.localhost` → `ws://unmute:8000/v1/realtime`)
- unmute → litellm via `http://litellm:4000/v1/chat/completions` (the wrapped text LLM)
- unmute → parakeet (STT) and chatterbox / speaches (TTS) — reuses the engines already in the stack as the audio I/O legs
- backend → unmute for server-initiated voice sessions (e.g. hermes voice agent)

## Effort
large — Kong needs WebSocket route handling, the bootstrapper needs an `UNMUTE_SOURCE` toggle, and unmute brings its own Kyutai STT/TTS models that may compete with parakeet/speaches for VRAM.

## Risks & open questions
- Kyutai's bundled STT/TTS may not be substitutable with parakeet/speaches without forking unmute; if not, this is a third audio stack rather than a wrapper.
- 16 GB VRAM minimum on x86_64 only; no aarch64 / Apple Silicon — would need a `localhost`-equivalent fallback path.
- Protocol is "based on" OpenAI Realtime with "extra messages" — Open WebUI / SDK compatibility needs verification.
- Watermarking / licensing of Kyutai voices for commercial use needs separate audit.

## Why now (and why not sooner)
The OpenAI Realtime API became the de-facto streaming voice protocol over 2025; open-source clones (unmute, plus Pipecat etc.) only stabilised in late 2025. Before that, the stack would have had to invent its own duplex protocol. Unmute now gives us the spec for free.

## Upstream evidence
- https://github.com/kyutai-labs/unmute — README confirms MIT license, Docker Compose deploy, OpenAI Realtime-format WebSocket, 16 GB VRAM requirement, custom `voices.yaml`.
