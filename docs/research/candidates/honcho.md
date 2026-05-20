---
slug: honcho
name: Honcho
type: external-service
category-fit: data
generated: 2026-05-19
upstream: https://github.com/plastic-labs/honcho
license: AGPL-3.0
referenced-by: [openclaw]
---

# Honcho

## Headline
Self-hostable user-and-session memory service that gives AI agents a durable model of each user across applications.

## Problem it solves
The stack currently has no shared, agent-agnostic memory layer: Hermes session state lives in its own volume, OpenClaw conversations vanish when the channel session ends, and Open WebUI history is per-app. Honcho provides a single REST surface where multiple agents (OpenClaw, Hermes, backend) can read and write per-user facts, theory-of-mind summaries, and session traces — enabling continuity across channels (Slack → Telegram → web UI) and across the agents themselves. OpenClaw's docs explicitly list Honcho as a supported memory engine, so wiring is a configuration job, not a custom-adapter job.

## Stack wiring sketch
- openclaw → honcho via `http://honcho:8000/v1/apps/<app>/users/<user>/sessions` (memory engine backend)
- hermes → honcho via REST tool for cross-session recall
- backend → honcho via REST for user-profile features
- honcho → supabase via `postgresql://supabase-db:5432/honcho` (Postgres backing store, schema-isolated)

## Effort
medium — adding a new container family (manifest + compose fragment + Kong alias + init for Postgres schema bootstrap) plus per-consumer client wiring; no GPU, modest memory, and the Postgres dependency reuses Supabase.

## Risks & open questions
- License is AGPL-3.0 — fine for self-host, may complicate downstream redistribution.
- Honcho's "theory of mind" derivations call an LLM; needs LiteLLM gateway integration to keep traffic on-stack.
- Schema migrations on upgrades — pin a tag rather than `:latest`.
- Multi-tenant isolation across agents (single Honcho app vs. per-agent apps) not yet decided.

## Why now (and why not sooner)
Memory continuity was a "later" feature while the stack was still establishing core inference, RAG, and channel surfaces. With both Hermes (long-running agent runtime) and OpenClaw (multi-channel adapter) now in the stack, the lack of a shared memory layer is the single most visible UX gap — a user who talks to the same model on Telegram and Open WebUI sees two strangers. Honcho is also one of the few self-hostable, Postgres-backed memory engines OpenClaw natively recognizes.

## Upstream evidence
- https://github.com/plastic-labs/honcho
- https://docs.openclaw.ai/llms.txt (lists Honcho among memory-engine providers)
