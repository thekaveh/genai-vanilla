---
category-fit: infra
generated: 2026-05-19
license: Apache-2.0
name: OpenLIT
referenced-by: [ollama]
slug: openlit
type: external-service
upstream: https://github.com/openlit/openlit
---

# OpenLIT

## Headline
OpenTelemetry-native observability for LLM, vector DB, and GPU calls — single `openlit.init()` instruments Ollama, LiteLLM, Weaviate, and HTTP frameworks.

## Problem it solves
The stack lacks any OTel surface. Existing telemetry (Docker logs) cannot answer "which call burned the most tokens?", "which embedding query was slowest?", or "what is GPU utilisation per model?". OpenLIT emits OTel traces and metrics that any standard backend (Tempo, Jaeger, ClickHouse, Grafana Cloud) can consume.

## Stack wiring sketch
- backend → OpenLIT via `openlit.init()` at FastAPI startup; auto-instruments calls to Ollama, LiteLLM, Weaviate, Neo4j drivers.
- hermes → OpenLIT via the same `openlit.init()` call in the skill runtime.
- jupyterhub → OpenLIT via a notebook-level `openlit.init(otlp_endpoint=...)`, giving researchers per-cell traces.
- weaviate → OpenLIT picks up the Weaviate Python client side automatically; complements its native Prometheus metrics.
- litellm → OpenLIT consumes LiteLLM's existing OTel exporter (no extra wiring beyond setting `OTEL_EXPORTER_OTLP_ENDPOINT`).
- openlit's UI → exposed via Kong alias `openlit.localhost`.

## Effort
small — single container (`ghcr.io/openlit/openlit`) plus a ClickHouse sidecar; instrumenting consumers is a one-line SDK call.

## Risks & open questions
- Overlaps significantly with Langfuse if both are adopted — pick one or document distinct purposes (Langfuse = product analytics + prompt mgmt; OpenLIT = infra-grade OTel).
- ClickHouse footprint duplicates whatever Langfuse would pull in; sharing a ClickHouse across both is feasible but undocumented upstream.
- SDK adds an import to every Python consumer; opt-in via `OPENLIT_ENABLED` env var.

## Why now (and why not sooner)
OpenLIT shipped native Ollama instrumentation in 2024 — including GPU utilisation scraped from `/api/ps` — and ships an OTel exporter that doesn't lock the stack to a single backend. Adopting it now keeps the option open to swap visualisation later.

## Upstream evidence
- https://github.com/openlit/openlit
- https://docs.openlit.io/latest/integrations/ollama
