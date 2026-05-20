---
slug: open-webui-pipelines
name: Open WebUI Pipelines
type: external-service
category-fit: apps
generated: 2026-05-19
upstream: https://github.com/open-webui/pipelines
license: MIT
referenced-by: [open-webui]
---

# Open WebUI Pipelines

## Headline
First-party plugin server that runs Python "pipes" and "filters" in front of any OpenAI-compatible client, enabling rate-limiting, content filtering, custom RAG, function-calling handlers, and third-party tracing (Langfuse, Opik) without forking Open WebUI.

## Problem it solves
Open WebUI's in-app Python Tools and Functions run in the WebUI process, are per-tool, and cannot intercept the request/response stream across providers. Pipelines provides a sidecar OpenAI-compatible endpoint that LiteLLM and Open WebUI can both target, so cross-cutting concerns (logging, redaction, quota, A/B routing) live in one place and apply uniformly.

## Stack wiring sketch
- open-webui → pipelines via `OPENAI_API_BASE_URLS=http://pipelines:9099` (added alongside the existing LiteLLM URL, or fronted by litellm)
- litellm → pipelines as a regular `openai`-compatible upstream so Hermes and other LiteLLM consumers get the same filter chain
- pipelines → langfuse for trace export (companion candidate)
- kong → pipelines via a `pipelines.localhost` alias for admin UI

## Effort
medium — new compose fragment, new SOURCE variants (container, disabled), Kong alias, and an init step to drop curated pipeline scripts into the pipelines volume; minimal env wiring beyond that.

## Risks & open questions
- Decide whether pipelines fronts LiteLLM or sits behind it — affects which service "owns" the gateway role.
- Pipelines is single-tenant: scaling needs sticky sessions or a queue.
- Filter pipelines require explicit client support — Hermes (non-WebUI client) gets pipe-type only.

## Why now (and why not sooner)
The stack already has the natural consumers (Open WebUI, LiteLLM, Hermes) and an obvious tracing target (Langfuse, also proposed). Earlier, the stack lacked a unified gateway role — LiteLLM filled it in 2025, and Pipelines slots in as the request-time middleware layer next to it.

## Upstream evidence
- https://github.com/open-webui/pipelines — repo, `ghcr.io/open-webui/pipelines:main`, port 9099, MIT license.
- https://docs.openwebui.com/features/ — "Pipelines: Modular plugin framework for filters, providers, and custom logic."
