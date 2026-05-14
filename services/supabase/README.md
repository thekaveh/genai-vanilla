# services/supabase — Supabase family

This folder houses the **entire Supabase stack** as a single co-lifecycled family. Eight containers + two named volumes share one manifest (`service.yml`) and one compose fragment (`compose.yml`).

## Containers

| Container | Role | Image var |
|---|---|---|
| `supabase-db` | PostgreSQL 16 + pgvector + postgis | `SUPABASE_DB_IMAGE` |
| `supabase-db-init` | One-shot SQL bootstrap (alpine `psql`) — runs every script in `./db/scripts/` in alpha order, idempotent | (alpine, no var) |
| `supabase-meta` | Metadata REST API (table editor backing) | `SUPABASE_META_IMAGE` |
| `supabase-storage` | Object storage backend (file-system or S3 driver) | `SUPABASE_STORAGE_IMAGE` |
| `supabase-auth` | GoTrue auth (JWT, email/password, OAuth) | `SUPABASE_AUTH_IMAGE` |
| `supabase-api` | PostgREST — auto-generated REST over public schema | `SUPABASE_API_IMAGE` |
| `supabase-realtime` | Realtime — Postgres WAL → WebSocket | `SUPABASE_REALTIME_IMAGE` |
| `supabase-studio` | Web dashboard (port `SUPABASE_STUDIO_PORT`) | `SUPABASE_STUDIO_IMAGE` |

## Subfolders

- `db/scripts/` — bind-mounted into `supabase-db-init` at `/scripts`; the runner executes every `.sql` here on every boot (each script uses `IF NOT EXISTS` for safety).
- `db/snapshot/` — optional pre-built database snapshot, bind-mounted into `supabase-db-init` at `/snapshot`. Drop a Postgres dump in here to seed the DB on first boot; empty by default.

## Files

- `service.yml` — the family manifest (all 8 containers' env vars, the `SUPABASE_*` source variants if any, runtime_sc data).
- `compose.yml` — the fragment defining all 8 services + the `supabase-db-data` and `supabase-storage-data` named volumes.

## See also

- [`docs/services/supabase.md`](../../docs/services/supabase.md) — full service docs.
- The `supabase-db-init` runner shell: `services/supabase/db/scripts/db-init-runner.sh`
