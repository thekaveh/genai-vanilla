---
category-fit: media
generated: 2026-05-19
license: SSPL-1.0
name: Browserless
referenced-by: [n8n, searxng]
slug: browserless
type: external-service
upstream: https://github.com/browserless/browserless
---

# Browserless

## Headline
Containerised headless-Chrome service with a REST + WebSocket API, used as the browser backend for n8n's "Browserless" node and for Playwright/Puppeteer scrapes.

## Problem it solves
n8n workflows that need to scrape JavaScript-heavy pages, render PDFs, or capture screenshots currently have no in-stack option — the user must reach out to an external service or write custom Code nodes. Browserless slots cleanly between n8n and SearXNG: SearXNG returns links, Browserless renders them, doc_processor parses the resulting PDF/HTML. It also unlocks ComfyUI gallery captures and Open WebUI document-pulls.

## Stack wiring sketch
- n8n → browserless via `http://browserless:3000` (the n8n Browserless community node and HTTP-request node both target this endpoint).
- browserless → searxng for follow-up link discovery within the same workflow (n8n orchestrates both).
- backend → browserless for ad-hoc renders behind a FastAPI route.
- doc_processor consumes browserless-rendered PDFs/HTML for downstream extraction.

## Effort
small — single-image deployment (`ghcr.io/browserless/chromium`), one new manifest with `BROWSERLESS_TOKEN` and a Kong alias. No DB; ephemeral.

## Risks & open questions
- SSPL-1.0 licensing for browserless v2 — fine for self-host, blocks redistribution.
- Memory footprint: Chromium + workers easily ~1.5 GiB; needs a deploy-resources block.
- Token-based auth only; rotating `BROWSERLESS_TOKEN` requires container restart.

## Why now (and why not sooner)
local-deep-researcher and n8n research workflows currently fall back to plain HTTP fetches, which silently skip JS-rendered content. Adding browserless completes the "search → render → extract → embed" pipeline already half-built by searxng + doc_processor + weaviate.

## Upstream evidence
- https://github.com/browserless/browserless
- https://docs.browserless.io/
- https://www.npmjs.com/package/n8n-nodes-browserless

## Cross-references
- `../rows/searxng.md` — search → render → extract pipeline.
