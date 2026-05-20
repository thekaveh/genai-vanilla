---
category-fit: media
generated: 2026-05-19
license: BSD-2-Clause
name: WhisperX
referenced-by: [stt-provider]
slug: whisperx
type: external-service
upstream: https://github.com/m-bain/whisperx
---

# WhisperX

## Headline
A drop-in fourth STT engine that adds speaker diarization and wav2vec2 word-aligned timestamps — capabilities no engine in the stack ships today.

## Problem it solves
Speaches (Faster-Whisper) and Parakeet both transcribe but neither attributes utterances to speakers, and Whisper's native timestamps are utterance-level only. Meeting summaries, podcast pipelines, and conversational analytics all need "who said what when" — which today requires bolting pyannote.audio on by hand. WhisperX wraps Faster-Whisper + wav2vec2 alignment + pyannote diarization behind one CLI/Python surface.

## Stack wiring sketch
- backend → whisperx via `POST http://whisperx:8000/v1/audio/transcriptions` (OpenAI-shape wrapper around `whisperx.transcribe`)
- whisperx → minio via `s3://transcripts/<session-id>.json` for diarized transcript artifacts
- n8n → whisperx via the same HTTP endpoint for meeting-recording workflows
- weaviate ← whisperx-emitted utterance chunks (speaker-keyed) for semantic search across long-form audio
- hermes → whisperx as a skill, surfacing speaker-attributed transcripts as agent context

## Effort
medium — no upstream Docker image is published, so we ship a thin FastAPI wrapper + Dockerfile under `services/whisperx/` and add a `whisperx-*` SOURCE option to the existing `STT_PROVIDER_SOURCE` matrix. Diarization needs an HF token for the pyannote model.

## Risks & open questions
- pyannote diarization model is HF-gated — requires `HUGGING_FACE_HUB_TOKEN` with explicit ToS acceptance.
- WhisperX is CPU-viable but realistically GPU-only for long files; would need a `container-gpu` variant only.
- BSD-2 + MIT (pyannote) license stack is permissive but the diarization model weights have their own non-commercial caveats — needs a docs callout.
- Maintenance velocity: WhisperX historically lags upstream Whisper releases; we'd pin a known-good revision.

## Why now (and why not sooner)
The stack already runs three STT engines behind one OpenAI shape, so adding a fourth is a configuration concern rather than an architectural one. The gap only becomes obvious once `openclaw` brings in multi-party voice messages and once `n8n` workflows start ingesting meeting recordings — both currently in scope.

## Upstream evidence
- https://github.com/m-bain/whisperx — "70x realtime", word-level alignment via wav2vec2, speaker diarization via pyannote.
- https://github.com/pyannote/pyannote-audio — MIT-licensed speaker diarization toolkit WhisperX depends on.
