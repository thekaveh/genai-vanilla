---
slug: mcpo
name: mcpo (MCP-to-OpenAPI Proxy)
type: external-service
category-fit: agents
generated: 2026-05-19
upstream: https://github.com/open-webui/mcpo
license: MIT
referenced-by: [open-webui]
---

# mcpo (MCP-to-OpenAPI Proxy)

## Headline
Lightweight proxy from the Open WebUI org that exposes any Model Context Protocol server (stdio, SSE, or Streamable HTTP) as an OpenAPI-compatible REST endpoint with auto-generated docs and optional auth.

## Problem it solves
The MCP ecosystem is exploding (filesystem, git, GitHub, Postgres, browser, Slack MCP servers exist today) but raw MCP speaks stdio, which is unsafe to expose between containers and is not consumable by Open WebUI's OpenAPI tool-server feature, n8n's HTTP node, or LiteLLM's custom-tool path. mcpo bridges that gap so the whole stack can adopt MCP tools without bespoke glue per service.

## Stack wiring sketch
- open-webui → mcpo via "OpenAPI tool server" admin setting pointing at `http://mcpo:8000/<server>/openapi.json`
- hermes → mcpo via HTTP tool-call (Hermes already speaks REST tool servers)
- n8n → mcpo via HTTP Request node for workflow tools
- litellm → mcpo as a custom tool-server upstream
- kong → mcpo via an `mcp.localhost` alias for the auto-generated `/docs` UI

## Effort
small — single container image (`ghcr.io/open-webui/mcpo:main`), one config file enumerating which MCP servers to mount, a new SOURCE variant, an admin step in Open WebUI's init to register the endpoints.

## Risks & open questions
- Choice of bundled MCP servers (filesystem? git? Postgres?) — needs a curated default list.
- Auth: a single API key vs per-server token; how secrets reach the proxy.
- Some MCP servers want a writable working directory — volume layout matters.

## Why now (and why not sooner)
MCP became the de-facto agent-tool protocol in 2025; Open WebUI shipped native MCP/OpenAPI tool-server support, and Hermes already accepts external tool servers. The stack now has three natural consumers, so a shared adapter is more valuable than per-service integration.

## Upstream evidence
- https://github.com/open-webui/mcpo — "Expose any MCP tool as an OpenAPI-compatible HTTP server—instantly."
- https://docs.openwebui.com/features/ — "MCP Support: Native integration with Model Context Protocol servers."
