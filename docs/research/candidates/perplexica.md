---
category-fit: apps
generated: 2026-05-19
license: MIT
name: Perplexica (Vane)
referenced-by: [searxng]
slug: perplexica
type: external-service
upstream: https://github.com/ItzCrazyKns/Perplexica
---

# Perplexica (Vane)

## Headline
Self-hosted, privacy-focused "AI answering engine" that turns SearXNG results into cited, conversational answers — drops in next to Open WebUI as a dedicated research-style chat.

## Problem it solves
SearXNG already returns ranked link results, but the stack has no UI that *combines* those results with an LLM call to produce a Perplexity-style cited answer in one turn. Open WebUI's RAG-web-search feature does retrieval-augmented chat but isn't optimised for that flow, and local-deep-researcher is async/multi-step. Perplexica is the missing single-shot "ask the web" front-end that uses the SearXNG instance already running.

## Stack wiring sketch
- perplexica → searxng via `SEARXNG_API_URL=http://searxng:8080` for the search backend.
- perplexica → litellm via `OPENAI_API_BASE_URL=http://litellm:4000/v1` (Perplexica supports OpenAI-compatible endpoints, so LiteLLM's gateway covers every provider in the stack).
- perplexica → ollama via `OLLAMA_API_URL=http://ollama:11434` for local embeddings when LiteLLM passthrough is undesirable.
- kong → perplexica as `perplexica.localhost` alias for browser access.

## Effort
small — single docker image (`itzcrazykns1337/vane:latest`), one new manifest under `services/perplexica/`, two env vars, one Kong alias. No DB (uses SearXNG + LLM at request time).

## Risks & open questions
- Project was recently renamed Perplexica → Vane; upstream image tag and config keys may shift. Pin to a known-good tag.
- Duplicates some Open WebUI functionality once `ENABLE_RAG_WEB_SEARCH` is wired (see searxng row, missing-pair #1). Worth keeping both only if the UX really diverges.
- Requires SearXNG `formats: [..., json]` to be enabled (already true in `services/searxng/config/settings.yml`).
- No native auth; sits behind Kong but Kong does not currently enforce auth on alias routes.

## Why now (and why not sooner)
SearXNG + LiteLLM + Ollama are all in place, and an `ENABLE_RAG_WEB_SEARCH` wiring for Open WebUI (the higher-priority gap) covers most of the use case. Perplexica becomes interesting once users want a UI tuned specifically for cited web answers rather than a general chat with a toggle.

## Upstream evidence
- https://github.com/ItzCrazyKns/Perplexica
- Docker setup documented at the repo root README, including `SEARXNG_API_URL=http://your-searxng-url:8080`.
