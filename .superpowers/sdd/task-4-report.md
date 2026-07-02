# Task 4 Report: MCP And Kong Dashboard Recommendations

## Scope completed

- Updated `docs/strategy/atlas-vnext-strategy-report.md` section 5 with:
  - current-source-checked MCP findings
  - an explicit architecture recommendation
  - the required MCP target / consumer matrix
  - clear separation between verified current support and future / inferred support
- Updated section 6 with:
  - an explicit answer on the Kong root decision
  - a minimum viable Atlas dashboard definition
  - clear scope boundaries for what the dashboard should not try to become
- Added narrowly relevant Task 4 source notes in appendix section 10.1.

## Recommendation summary

### MCP

Atlas should adopt a **phased hybrid** MCP strategy:

1. Start with a curated package of high-value MCP servers, not one server per service.
2. Let native consumers use those servers directly first.
3. Add an aggregator later, when namespacing and policy become necessary.
4. Prefer **MetaMCP** for that later aggregation step.
5. Treat **mcpo** as a translator, not as the center of the architecture.
6. Do **not** default Atlas to Docker MCP Gateway for the internal-service-first case.

Recommended early targets:

- Supabase / Postgres
- Neo4j
- SearXNG
- Docling MCP as the first specialist expansion

### Kong root

Yes: the **Kong root** should become an Atlas entrypoint.

The first version should be a lightweight:

- **service directory**
- **health dashboard**

and should not try to replace:

- Grafana
- Supabase Studio
- the setup wizard
- a full control plane

## External source coverage used

Official/current sources checked on **July 2, 2026**:

- MCP spec: `modelcontextprotocol.io`
- MetaMCP: `docs.metamcp.com`, `github.com/metatool-ai/metamcp`
- Docker MCP Gateway: `docs.docker.com`, `github.com/docker/mcp-gateway`
- mcpo: `docs.openwebui.com`, `github.com/open-webui/mcpo`
- Open WebUI MCP support: `docs.openwebui.com`
- LiteLLM MCP support: `docs.litellm.ai`
- Hermes MCP support: `hermes-agent.nousresearch.com`, `github.com/NousResearch/hermes-agent`
- Docling MCP: `github.com/docling-project/docling-mcp`, `github.com/DS4SD/docling-serve`

## Internal sources used

- `docs/ROADMAP.md`
- `docs/deployment/ports-and-routes.md`
- `docs/research/candidates/mcp-gateway.md`
- `docs/research/candidates/mcpo.md`
- `docs/research/candidates/docling-mcp.md`
- `docs/research/candidates/voicebox.md`
- `services/kong/README.md`
- `services/open-webui/README.md`
- `services/litellm/README.md`
- `services/hermes/README.md`

## Validation

Ran the required check:

```bash
rg -n "phased hybrid|service directory|health dashboard|MCP role|Kong root" docs/strategy/atlas-vnext-strategy-report.md
```

Result: all required phrases are present in the report at the expected recommendation points.

## Notes / concerns

- OpenClaw support was intentionally labeled as inferred / later-consumer territory because this pass did not re-verify its MCP path against fresh official upstream docs.
- n8n was intentionally treated as a later expansion rather than a dependency of the initial decision because Atlas does not need n8n MCP semantics to justify the starting architecture.

## Task 4 review-fix follow-up

- Corrected the Hermes MCP discussion in `docs/strategy/atlas-vnext-strategy-report.md` section 5.1 to reflect verified current **server** capability as well as client capability, based on the official Hermes CLI docs (`hermes mcp serve`) and the Codex app-server runtime docs stating Hermes registers itself as an MCP server.
- Updated the Hermes row in the MCP role matrix from `Consumer` to `Both (consumer-first)` while preserving the recommendation that Atlas should integrate Hermes primarily as an MCP consumer unless there is a concrete callback or tool-sharing reason to expose Hermes itself.
- Updated the appendix/source notes to cite the current Hermes server-capability docs and note that issue `#342` is closed rather than future work.

Validation summary:

- Ran `rg -n "phased hybrid|service directory|health dashboard|MCP role|Kong root" docs/strategy/atlas-vnext-strategy-report.md`
- Result: required Task 4 recommendation markers remain present at lines 100, 118, 159, 163, and 204 after the Hermes correction.
