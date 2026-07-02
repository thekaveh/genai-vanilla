# Task 5 Report: Rank vNext Top 20 And Track Expansions

Status: DONE

## Files Changed

- `docs/strategy/atlas-vnext-strategy-report.md`

## Scope Completed

- Replaced section 7 with a ranked vNext Top 20 list.
- Replaced section 8 with the required track expansion subsections:
  - `### 8.1 3D / Game-Generation Track`
  - `### 8.2 Trading / Financial-AI Track`
  - `### 8.3 RAG And Content-Ingestion Track`
  - `### 8.4 Data / ML Platform Track`
- Replaced section 9 with the required implementation-wave subsections:
  - `### 9.1 Build Now`
  - `### 9.2 Build Next`
  - `### 9.3 Build Later`
  - `### 9.4 Reject Or Defer For Now`
- Added Task 5 source notes in appendix section 10.1.

## Ranking Summary

The top-ranked work favors Atlas operational fit over novelty:

1. Atlas root dashboard
2. Curated MCP package
3. Langfuse
4. Crawl4AI
5. Celery + Flower
6. SSO pilot: Authentik-first, Keycloak as enterprise alternative
7. Secrets manager: Infisical-first, OpenBao watchlist
8. Supavisor
9. Apache Tika
10. OpenTelemetry Collector + Tempo + Loki
11. MLflow
12. Open WebUI Pipelines
13. Neo4j LLM Knowledge Graph Builder
14. Verba
15. Label Studio
16. Graphiti
17. SigLIP 2 vectorizer upgrade path
18. Iceberg + DuckDB, with Lakekeeper evaluated as the catalog
19. OpenBB + CCXT financial research kit
20. Blender MCP + glTF-Transform asset bridge

The list intentionally ranks dashboarding, MCP, observability, ingestion, async execution, identity, secrets, and database pressure relief above 3D foundation models or live-trading systems.

## Candidate Corpus Coverage

All existing one-pagers under `docs/research/candidates/*.md` were considered. The appendix now links the full corpus explicitly and records outside sources used for current maturity and track recommendations.

Ranked or incorporated directly:

- Apache Tika
- Celery + Flower
- Crawl4AI
- Docling MCP
- Grafana Loki, via the broader OTel + Tempo + Loki observability recommendation
- Graphiti
- Iceberg + DuckDB
- Keycloak, via SSO pilot comparison against Authentik
- Label Studio
- Langfuse
- MCP Gateway / mcpo, via the curated MCP package and translator posture
- MLflow
- Neo4j LLM Knowledge Graph Builder
- Open WebUI Pipelines
- OpenLIT, via the broader OTel posture rather than as the primary UI
- SigLIP 2 Vectorizer
- Supavisor
- Verba

Deferred or watchlisted with rationale:

- Browserless
- Firecrawl
- Honcho
- imgproxy
- NeoDash
- NocoDB
- OmniVoice
- Perplexica/Vane
- Redis Stack
- RedisInsight
- Supabase Edge Functions
- Unmute
- Voicebox
- WhisperX

Prometheus was treated as already shipped in Atlas' current roadmap state rather than ranked as new vNext work.

## Outside Research Coverage

External suggestions from the brief were either ranked, folded into track plans, or explicitly deferred:

- 3D/game: Blender MCP, Unreal Engine MCP, Godot, Hunyuan3D, TRELLIS, Nerfstudio, glTF-Transform, LiveKit.
- Trading/finance: OpenBB, Hummingbot, NautilusTrader, Freqtrade, TimescaleDB, Redpanda, OpenBao, CCXT, FinRL, FinGPT.
- Platform/data: Authentik, Infisical, OpenTelemetry Collector, Loki, Tempo, Dagster, Lakekeeper, Trino, Superset.

## Self-Review Notes

- Ranking coherence: the build-now wave maps to ranks 1-9 except the high-risk identity/secrets items, which are intentionally in Build Next despite high strategic value.
- Security posture: live trading, Blender/Unreal MCP, browser automation, and heavyweight 3D generation are all disabled/deferred until guardrails exist.
- License posture: AGPL/SSPL items are not promoted ahead of permissive alternatives unless value clearly outweighs risk.
- Atlas primitive reuse: every ranked item is tied to existing primitives such as Kong, LiteLLM, Redis, Supabase, MinIO, Neo4j, Weaviate, JupyterHub, or tracks.

## Validation Run

- Required anchor check:
  - `rg -n "### 8\.1|### 8\.2|### 8\.3|### 8\.4|### 9\.1|### 9\.2|### 9\.3|### 9\.4" docs/strategy/atlas-vnext-strategy-report.md`
  - Result: all eight required headings found.
- Section/ranking structure check:
  - `section7_rank_rows=20`
  - `missing_required_headings=none`
  - `task_placeholders_in_7_9=False`
- Candidate corpus coverage check:
  - `candidate_files=34`
  - `missing_candidate_links=none`
- Whitespace check:
  - `git diff --check -- docs/strategy/atlas-vnext-strategy-report.md .superpowers/sdd/task-5-report.md`
  - Result: no output, exit 0.
- Staged whitespace check:
  - `git diff --cached --check`
  - Result: no output, exit 0.
- Internal docs link check:
  - `python scripts/check_doc_links.py`
  - Result: no output, exit 0.

## Review Fix Follow-Up

- Added explicit decision dispositions in section 9 for the three candidates the reviewer flagged: `Supabase Edge Functions`, `OpenLIT`, and `Unmute`.
- Kept the top 20 ordering unchanged; the update only clarifies where those appendix-listed candidates land in the decision flow.
- Re-checked the appendix-vs-decision coverage path while editing so the newly added one-line dispositions sit in sections 8/9 rather than only in source notes.

### Follow-Up Validation

- `rg -n "Supabase Edge Functions|Unmute|OpenLIT" docs/strategy/atlas-vnext-strategy-report.md`
  - Result: all three candidates now appear in decision sections with explicit defer dispositions.
- `rg -n "### 8\.1|### 8\.2|### 8\.3|### 8\.4|### 9\.1|### 9\.2|### 9\.3|### 9\.4" docs/strategy/atlas-vnext-strategy-report.md`
  - Result: all eight required section anchors still present.
