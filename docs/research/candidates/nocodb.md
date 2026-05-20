---
category-fit: apps
generated: 2026-05-19
license: AGPL-3.0
name: NocoDB
referenced-by: [n8n]
slug: nocodb
type: external-service
upstream: https://github.com/nocodb/nocodb
---

# NocoDB

## Headline
Open-source Airtable-style spreadsheet UI that exposes any Postgres schema as editable tables, kanbans, and forms — backed by an existing relational store rather than a new datastore.

## Problem it solves
n8n workflows frequently need a lightweight CRUD surface for human-in-the-loop data (review queues, prompt libraries, ComfyUI generation logs, tagged transcripts). Today the stack has Supabase Studio (admin-only) but no end-user data editor. NocoDB mounts onto the same Supabase Postgres in a dedicated `nocodb` schema and gives non-technical users an editable view; n8n has a first-party NocoDB node so workflows can read/write rows declaratively.

## Stack wiring sketch
- nocodb → supabase via `postgresql://supabase-db:5432/<db>` with a `nocodb` schema (mirrors how n8n uses an `n8n` schema).
- n8n → nocodb via the built-in NocoDB node (`http://nocodb:8080`) for row CRUD inside workflows.
- backend → nocodb via REST for admin operations.
- kong → nocodb via a `nocodb.localhost` alias.

## Effort
small — one new manifest, one Kong alias, schema isolation in supabase-db-init. No new database engine.

## Risks & open questions
- AGPL-3.0 — fine for self-host, requires source disclosure if exposed as a SaaS.
- NocoDB writes to its own metadata tables on startup; the `nocodb` schema needs createable on first boot.
- Auth model is separate from Supabase Auth — users have to log in twice unless a future Kong-OIDC bridge is added.

## Why now (and why not sooner)
With n8n queues running real automations, users keep asking for a "spreadsheet I can edit that the workflow watches." Spinning up sheets in Supabase Studio is admin-grade; NocoDB is the lightweight end-user surface that closes the loop without adding another datastore.

## Upstream evidence
- https://github.com/nocodb/nocodb
- https://docs.nocodb.com/
- https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.nocodb/
