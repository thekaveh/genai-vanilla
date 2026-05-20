---
slug: graphiti
name: Graphiti
type: external-service
category-fit: agents
generated: 2026-05-19
upstream: https://github.com/getzep/graphiti
license: Apache-2.0
referenced-by: [neo4j]
---

# Graphiti

## Headline
Temporal knowledge-graph framework for AI agents — episodes are timestamped, entities are versioned, and Neo4j is the storage backend.

## Problem it solves
Agent memory in this stack today is either Postgres rows (LangMem) or none at all. Graphiti gives Hermes / backend a structured, time-aware memory store with native bi-temporal modelling (event-time + ingestion-time), entity dedup via embeddings, and Cypher-level recall. Better than a flat KV cache for multi-turn agent reasoning.

## Stack wiring sketch
- `hermes` → graphiti Python SDK → `neo4j` via `bolt://neo4j-graph-db:7687`
- `backend` → graphiti SDK for cross-service shared memory
- `n8n` → graphiti REST service (optional sidecar) for workflow-driven memory writes
- `local-deep-researcher` → graphiti for persisting research provenance across runs
- Graphiti embeddings call → `litellm` (OpenAI-compatible)

## Effort
small — Graphiti is a Python library, not a service; lives inside hermes / backend images. Only adds a dependency + a Neo4j schema bootstrap step. No new container is mandatory; the upstream offers an optional REST server if other languages need access.

## Risks & open questions
- Schema collisions if multiple consumers write episodes — need a `group_id` convention per service.
- Embedding cost: Graphiti embeds every node and edge; budget vs LiteLLM rate limits.
- Versioning churn — Graphiti is pre-1.0; breaking changes are likely.

## Why now (and why not sooner)
Hermes and the backend both lack durable agent memory. With Neo4j already wired in, Graphiti is the lowest-friction way to bolt structured long-term memory onto the agents without standing up a new database.

## Upstream evidence
- https://github.com/getzep/graphiti
- https://help.getzep.com/graphiti/getting-started/welcome
