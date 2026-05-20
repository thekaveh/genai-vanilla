---
slug: supabase-edge-functions
name: Supabase Edge Functions (Deno runtime)
type: external-service
category-fit: apps
generated: 2026-05-19
upstream: https://supabase.com/docs/guides/functions
license: Apache-2.0
referenced-by: [supabase]
---

# Supabase Edge Functions (Deno runtime)

## Headline
Self-hosted Deno-based serverless runtime (`supabase/edge-runtime`) that runs short TypeScript functions next to the rest of the Supabase family and can be triggered by HTTP, database webhooks, or pg_net.

## Problem it solves
The stack today has no lightweight glue layer for "when X happens in Postgres, call Y service". Workflows that need a single HTTP handler (a webhook receiver, a model-routing shim, a Storage post-upload hook) currently force the user into n8n (heavy) or into editing the FastAPI backend (rebuild, restart). Edge Functions give a third option: drop a `.ts` file, invoke at `http://supabase-edge-functions:9000/<name>` or via `pg_net.http_post` from a Postgres trigger.

## Stack wiring sketch
- supabase-db (pg_net / database webhook) -> supabase-edge-functions via HTTP POST
- kong -> supabase-edge-functions via `/functions/v1/*` route (mirrors hosted Supabase URL shape)
- supabase-edge-functions -> litellm via `http://litellm:4000/v1/chat/completions`
- supabase-edge-functions -> supabase-storage via `http://supabase-storage:5000` (signed-URL workflows)
- supabase-edge-functions -> n8n via `http://n8n:5678/webhook/*` (handoff for long-running flows)

## Effort
medium — single new container (`supabase/edge-runtime:latest`) plus a `functions/` bind-mount and one Kong route; the bigger cost is documenting JWT/CORS conventions and authoring the first few example functions.

## Risks & open questions
- Deno runtime image is ~150 MB; meaningful idle footprint on minimal stacks.
- Hot-reload story for bind-mounted functions is acceptable in dev but not battle-tested for prod.
- Overlaps with n8n for trigger-style use cases — guidance needed on when to reach for which.
- Auth surface: functions accept the same `SUPABASE_JWT_SECRET`, so a leaked key gives execution rights — must stay behind Kong.

## Why now (and why not sooner)
Until pg_net / pg_cron / database webhooks land as feature gaps (see supabase row Section 3), the trigger surface for Edge Functions was thin. With those extensions enabled, Edge Functions become the natural in-stack target — closing the loop between "row inserted" and "call an LLM / write to Storage / notify Hermes" without dragging in n8n.

## Upstream evidence
- https://supabase.com/docs/guides/functions
- https://github.com/supabase/edge-runtime
