# Reusing Atlas as Infrastructure

How to use Atlas as the backing infrastructure / platform for another project — for example a RAG-showcase app that needs Weaviate + Neo4j + an LLM gateway + object storage without standing those up itself.

This page is the **overview and decision guide**. It answers: *can I reuse Atlas, which method should I pick, is it ready, how do I wire my project to it, and how do I customize it?* For the full step-by-step of the Git-submodule method specifically, see [submodule-usage.md](submodule-usage.md).

---

## 1. TL;DR

- **Yes, Atlas is designed to be reused** as shared infra for other projects. The whole stack is namespaced by `PROJECT_NAME`, its ports move as a block via `BASE_PORT`, every service is toggleable via `*_SOURCE`, and all containers share one Docker network (`${PROJECT_NAME}-network`) that your project can join.
- **Two methods are ready today:**
  - **A — Standalone + shared network** (recommended when one Atlas instance backs *several* of your projects): run Atlas on its own; your project is a *separate* repo / Compose project that joins `${PROJECT_NAME}-network` and calls services by their Docker DNS name (or through Kong).
  - **B — Git submodule** (recommended when your project *ships and deploys Atlas together with it*): vendor Atlas into your repo under `infra/` and run it from there. Fully documented in [submodule-usage.md](submodule-usage.md).
- **Customization needs no fork:** `PROJECT_NAME`, `BASE_PORT`, `BRAND_*`, per-service `*_SOURCE`, and `--track` cover the common cases.
- **Honest status:** the consumer paths above work today. Two reuse niceties are not finished yet — auto-launching services you drop into the `services/_user/` overlay, and published semver release tags for pinning. See [§7 Readiness & known gaps](#7-readiness--known-gaps).

---

## 2. Choose your reuse method

| Method | Use it when… | Ready? | Detail |
|--------|--------------|--------|--------|
| **A. Standalone + shared network** | One Atlas instance is shared infra across one or more *separate* project repos; you want your app decoupled from Atlas internals. | **Yes** | [§3](#3-method-a--standalone--shared-network-the-rag-showcase-walkthrough) |
| **B. Git submodule** | Your project should clone/deploy *with* a pinned copy of Atlas (single repo, single deploy unit, reproducible version). | **Yes** | [submodule-usage.md](submodule-usage.md) + [§4](#4-method-b--git-submodule) |
| **C. Template / fork** | You need to diverge structurally from upstream Atlas. | Works, but you own the merge cost | [§5](#5-method-c--template--fork-and-why-not-published-images) |
| **D. Published images / pip package** | You want `docker pull atlas/...` or `pip install atlas` without the repo. | **Not supported** | [§5](#5-method-c--template--fork-and-why-not-published-images) |

**Rule of thumb:** building a showcase / app that *talks to* infra → **Method A**. Shipping a product that *bundles* the infra → **Method B**.

---

## 3. Method A — Standalone + shared network (the RAG-showcase walkthrough)

Atlas runs as its own stack. Your RAG project is a separate Compose project that attaches to Atlas's network and addresses services by container DNS name. Nothing in your app repo needs to know Atlas's internals beyond the service hostnames.

### 3.1 Step 1 — Run Atlas with a known `PROJECT_NAME`

```bash
# In your Atlas checkout
./start.sh --llm-provider-source none --cloud-openai-source enabled --openai-api-key sk-...   # cloud LLMs, no local GPU
# (or any track/source combination your showcase needs, e.g. --track gen-ai-rag)
```

`PROJECT_NAME` (default `atlas`) determines the shared network name: **`${PROJECT_NAME}-network`** (e.g. `atlas-network`). Set it in Atlas's `.env` if you want a non-default name.

### 3.2 Step 2 — Join Atlas's network from your project

In your RAG project's `docker-compose.yml`, declare Atlas's network as **external** and attach your service to it:

```yaml
# your-rag-project/docker-compose.yml
services:
  rag-app:
    build: .
    environment:
      # Address Atlas services by their in-network DNS name (see §3.3)
      WEAVIATE_URL: "http://weaviate:8080"
      NEO4J_URI: "bolt://neo4j-graph-db:7687"
      OPENAI_BASE_URL: "http://litellm:4000/v1"   # LiteLLM gateway (OpenAI-compatible)
      S3_ENDPOINT: "http://minio:9000"
    networks:
      - atlas

networks:
  atlas:
    external: true
    name: atlas-network        # = ${PROJECT_NAME}-network from your Atlas .env
```

Start Atlas first, then your project:

```bash
(cd /path/to/atlas && ./start.sh)      # infra up
docker compose up -d                    # your RAG app joins atlas-network
```

### 3.3 Service addresses (inside the shared network)

Within `${PROJECT_NAME}-network`, reach each service by its **compose service name** on its **container port** (these are stable and independent of `BASE_PORT`, which only affects host-published ports):

| Service | In-network address | Notes |
|---------|--------------------|-------|
| **Kong** (API gateway / single entry) | `kong-api-gateway:8000` (HTTPS `:8443`) | Route everything through here if you prefer one entry point |
| **LiteLLM** (LLM gateway, OpenAI-compatible) | `litellm:4000` | `POST http://litellm:4000/v1/chat/completions`; auth with `LITELLM_MASTER_KEY` |
| **Weaviate** (vector DB) | `weaviate:8080` (gRPC `weaviate:50051`) | |
| **Neo4j** (graph DB) | `neo4j-graph-db:7687` (Bolt), `:7474` (HTTP) | auth from `GRAPH_DB_AUTH` |
| **Supabase Postgres** | `supabase-db:5432` | REST/Auth/Storage are exposed via Kong — see [submodule-usage.md §6.2](submodule-usage.md) |
| **MinIO** (S3-compatible) | `minio:9000` (console `:9001`) | creds `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` |
| **Redis** | `redis:6379` | auth `REDIS_PASSWORD` |
| **n8n** (workflows) | `n8n:5678` | |
| **Open WebUI** (chat UI) | `open-web-ui:8080` | |
| **Backend** (FastAPI orchestrator) | `backend:8000` | |

The authoritative, always-current port list (host-published ports + Kong hostnames) is [ports-and-routes.md](ports-and-routes.md) and the generated `.env.example`.

### 3.4 Going through Kong instead (single entry point)

If you'd rather not depend on individual service hostnames, route through Kong — Atlas's gateway — at `kong-api-gateway:8000`. Supabase REST is path-routed (`/rest/v1/...`); browser-facing services are host-routed (`<service>.localhost`). The Kong patterns, including the auth headers, are documented in [submodule-usage.md §6.2](submodule-usage.md).

---

## 4. Method B — Git submodule

Vendor Atlas into your repo and run it from a subdirectory — best when your project and its infra ship as one versioned, reproducible unit.

```bash
git submodule add https://github.com/thekaveh/atlas infra
cd infra && cp .env.example .env      # set PROJECT_NAME to your project
./start.sh
```

This is the same shared-network model as Method A (your app joins `${PROJECT_NAME}-network`), with the difference that Atlas's source lives inside your repo at a pinned commit. The **complete** guide — directory layout, `.gitignore`, custom env-file location, integration patterns, contributing upstream, CI/CD, multiple stacks, troubleshooting — is [submodule-usage.md](submodule-usage.md).

---

## 5. Method C — Template / fork (and why not published images)

- **Template / fork:** Clone Atlas, rip out what you don't need, and own it. Full control, but you inherit the cost of merging upstream changes by hand. Reasonable only if you need to diverge structurally.
- **Published images / pip package (not supported):** There is no `atlas/...` image set or `pip install atlas` artifact. The bootstrapper assumes the repo layout (it reads `services/<name>/service.yml` manifests and generates compose from them), so Atlas is consumed *as a repo*, not as a dependency. If a packaged distribution is ever needed it would be new work; today, use Method A or B.

---

## 6. Customizing Atlas for your project (no fork required)

| Knob | What it does | Where |
|------|--------------|-------|
| **`PROJECT_NAME`** | Prefixes every container, volume, and the network (`${PROJECT_NAME}-network`). The key to running it as *your* stack and to isolation between stacks. | `.env` |
| **`BASE_PORT`** | Moves the entire host-published port block (default `63000`). `./start.sh --base-port 64000`. Does not affect in-network addresses. | `.env` / flag |
| **`BRAND_*`** | Rebrands the wizard/banner (name, tagline, author, repo URL, license) — make Atlas present as your platform. | `.env` (`BRAND_*` block) |
| **`*_SOURCE`** | Enable/disable each service or pick its backend (`container` / `container-gpu` / `localhost` / `disabled`, plus `api` for LLMs). Disable what your showcase doesn't use. | `.env` / `--<svc>-source` |
| **`--track`** | Start a curated subset (`gen-ai-rag`, `gen-ai-eng`, `gen-ai-creative`, `ml-eng`, `data-eng`, `all`). `--track gen-ai-rag` is the natural fit for a RAG showcase. | flag |
| **`services/_user/` overlay** | Drop your own co-located service manifests here (gitignored upstream, so they never leak into Atlas PRs). | `services/_user/<name>/` — see limitation in §7 |

Full source/customization matrix: [source-configuration.md](source-configuration.md).

---

## 7. Readiness & known gaps

| Capability | Status |
|------------|--------|
| Standalone + shared-network consumer (Method A) | **Ready** |
| Git submodule (Method B) | **Ready** ([submodule-usage.md](submodule-usage.md)) |
| Customization: `PROJECT_NAME` / `BASE_PORT` / `BRAND_*` / `*_SOURCE` / `--track` | **Ready** |
| Multiple isolated Atlas stacks on one host | **Ready** (distinct `PROJECT_NAME` + `BASE_PORT`) |
| `services/_user/` overlay **auto-launch** | **Partial** — manifests dropped in `services/_user/` are parsed by the bootstrapper, but the top-level `docker-compose.yml` `include:` list is hand-maintained, so those services are **not started automatically** yet. Until this is wired, add a co-located service from *your own* Compose project on the shared network (Method A) instead. |
| Published images / pip package | **Not supported** (see §5) |
| Semver release tags for submodule pinning | **Not yet** — pin to a commit SHA for now |

The two gaps above are tracked as Phase 1 of the production-readiness & reuse roadmap: [`docs/superpowers/specs/2026-06-20-production-readiness-and-reuse-roadmap-design.md`](../superpowers/specs/2026-06-20-production-readiness-and-reuse-roadmap-design.md) (Part 3).

---

## 8. See also

- [submodule-usage.md](submodule-usage.md) — complete Git-submodule guide (layout, integration patterns, CI/CD, troubleshooting)
- [source-configuration.md](source-configuration.md) — every `*_SOURCE` variable and what it does
- [ports-and-routes.md](ports-and-routes.md) — authoritative port + Kong-hostname mapping
- [Production readiness & reuse roadmap](../superpowers/specs/2026-06-20-production-readiness-and-reuse-roadmap-design.md) — the strategy/assessment behind this guide
