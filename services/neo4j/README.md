# services/neo4j — Neo4j graph database

Long-term memory / graph store. Used by the backend's LangMem-equivalent
service and surfaced through JupyterHub for ad-hoc Cypher.

## Containers

| Container | Role | Image var |
|---|---|---|
| `neo4j-graph-db` | Neo4j 5.x with bundled snapshot-restore wrapper | `NEO4J_GRAPH_DB_IMAGE` (used as `BASE_IMAGE` in `build/Dockerfile`) |

## Subfolders

- **`build/`** — Dockerfile + scripts that wrap the upstream Neo4j
  entrypoint:
  - `scripts/backup.sh`, `scripts/restore.sh` — snapshot/restore helpers.
  - `scripts/auto_restore.sh` — restores `build/snapshot/` on first boot.
  - `scripts/docker-entrypoint-wrapper.sh` — composes the above before
    chaining to the stock Neo4j entrypoint.
  - `snapshot/` — seed-data snapshot bind-mounted at `/snapshot`.

## Sources

`NEO4J_GRAPH_DB_SOURCE` picks between `container` (default),
`localhost` (use the user's existing host install — `NEO4J_URI` flips to
`bolt://host.docker.internal:7687`), and `disabled`.

## See also

- [`docs/services/neo4j.md`](../../docs/services/neo4j.md) — full service docs.
