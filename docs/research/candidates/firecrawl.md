---
category-fit: media
generated: 2026-05-19
license: AGPL-3.0
name: Firecrawl
referenced-by: [local-deep-researcher]
slug: firecrawl
type: external-service
upstream: https://github.com/mendableai/firecrawl
---

# Firecrawl

## Headline
Self-hostable JS-rendering web scraper that returns clean LLM-ready markdown or structured JSON from `/v1/scrape` and `/v1/crawl`.

## Problem it solves
local-deep-researcher's `FETCH_FULL_PAGE=true` path uses DuckDuckGo to pull raw HTML and naively strips tags; JavaScript-rendered pages (SPAs, paywalls, infinite scroll) come back empty or noisy, so the running_summary ends up citing snippets rather than full content. n8n flows that want to ingest a single URL into Weaviate face the same gap. Firecrawl handles JS rendering, deduplicates boilerplate, and emits markdown directly, raising the signal-to-noise of every LDR loop.

## Stack wiring sketch
- local-deep-researcher → firecrawl via `POST http://firecrawl:3002/v1/scrape` (replaces the inlined `urllib`/`requests` fetch in the LDR `web_research` node when `FETCH_FULL_PAGE=true`).
- n8n → firecrawl via HTTP Request node for ad-hoc URL ingestion into weaviate.
- backend → firecrawl via the existing `httpx.AsyncClient` pattern in `services/backend/app/app/research_client.py`.
- hermes → firecrawl as a custom tool returning markdown for an arbitrary URL.

## Effort
medium — Firecrawl ships an official docker-compose with API + worker + Playwright service + Redis dependency; adding it means one new service folder with three containers (api, worker, playwright), a Kong alias, and a SOURCE toggle. Reusing the stack's existing Redis avoids spinning up a second cache.

## Risks & open questions
- AGPL-3.0 license is stricter than the rest of the stack's MIT/Apache mix; review whether the AGPL boundary at a network API is acceptable.
- Playwright sub-service is ~1.5 GB and pulls Chromium; large image for CPU-only deployments.
- Firecrawl requires its own Redis queue — needs to be isolated by db-index from the stack's existing usage (n8n /0, open-webui /2, LDR /3).
- Self-hosted Firecrawl historically lags the SaaS in features (search endpoint, agent endpoint); verify which API paths are available in the OSS build.

## Why now (and why not sooner)
LDR's existing search backends (SearXNG, DuckDuckGo) return snippets, not full pages. As soon as researchers ask "summarise this single URL", the stack has no good answer — Docling handles PDFs only. Firecrawl fills that gap without forcing a cloud dependency.

## Upstream evidence
- https://github.com/mendableai/firecrawl
- https://docs.firecrawl.dev/introduction
- https://github.com/mendableai/firecrawl/tree/main/docker-compose.yaml
