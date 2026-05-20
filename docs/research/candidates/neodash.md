---
slug: neodash
name: NeoDash
type: external-service
category-fit: apps
generated: 2026-05-19
upstream: https://github.com/neo4j-labs/neodash
license: Apache-2.0
referenced-by: [neo4j]
---

# NeoDash

## Headline
Low-code dashboard builder for Neo4j — design Cypher-powered dashboards (charts, tables, graphs, maps) without writing a custom UI.

## Problem it solves
Today the only way to look at the graph is the raw Neo4j Browser at `graph.localhost`, which targets developers, not analysts. NeoDash adds a shareable dashboard layer so non-Cypher users can explore data the stack writes into Neo4j (e.g. agent traces, doc-extracted entities, n8n workflow runs).

## Stack wiring sketch
- Browser → `kong` (route `dash.localhost`) → neodash container
- neodash → `neo4j` via `bolt://neo4j-graph-db:7687`
- (optional) neodash dashboard definitions stored in `neo4j` itself, persisted across restarts

## Effort
small — official `neo4jlabs/neodash` Docker image, single env var (`ssoEnabled=false` plus the Neo4j connection details). Just needs a `services/neodash/` family with a Kong alias.

## Risks & open questions
- Auth: NeoDash reuses Neo4j creds; can't gate behind Supabase auth without extra work.
- Dashboards live per-user in browser localStorage unless explicitly saved to the DB.

## Why now (and why not sooner)
Once multiple services (backend, n8n, llm-graph-builder, graphiti) start writing into Neo4j, visualisation demand follows immediately. NeoDash is by far the cheapest way to satisfy it.

## Upstream evidence
- https://github.com/neo4j-labs/neodash
- https://neo4j.com/labs/neodash/
