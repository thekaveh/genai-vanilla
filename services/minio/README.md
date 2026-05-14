# services/minio — MinIO object-storage family

Two containers, one named volume.

## Containers

| Container | Role | Image var |
|---|---|---|
| `minio` | MinIO S3-compatible object store (S3 API on `MINIO_PORT`, console on `MINIO_CONSOLE_PORT`) | `MINIO_IMAGE` |
| `minio-init` | One-shot mc sidecar — provisions buckets + service-account credentials | `MINIO_INIT_IMAGE` (`minio/mc`) |

## Subfolders

- `init/scripts/` — bind-mounted into `minio-init` at `/scripts`. Entrypoint is `/scripts/init-minio.sh`. Creates the five pre-provisioned consumer buckets and the per-consumer scoped credentials surfaced as the public env contract.

## Roles vs Supabase Storage

MinIO is the **artifact-tier** surface (high-throughput, large-blob: ComfyUI outputs, doc-processor binaries, dataset versioning, n8n/backend handoff). Supabase Storage remains the **app-tier** surface (row-level-security uploads, signed URLs, ~50 MB ceiling). They coexist; pick by workload, not by preference.

## Access

| Surface | URL |
|---|---|
| Admin console (Kong alias) | `http://minio.localhost:${KONG_HTTP_PORT}` — requires `./start.sh --setup-hosts`. Login `minioadmin` / `${MINIO_ROOT_PASSWORD}`. |
| Admin console (direct port) | `http://localhost:${MINIO_CONSOLE_PORT}` (default `:63031`) — equivalent, no hosts setup needed. |
| S3 API (host) | `http://localhost:${MINIO_PORT}` (default `:63030`) — NOT Kong-aliased; S3 clients use the direct port. |
| S3 API (internal) | `http://minio:9000` — sibling containers (backend, n8n, ComfyUI, JupyterHub) call this with their per-bucket service-account credentials. |

The Kong route is gated on `MINIO_SOURCE != disabled`. Defined in
`bootstrapper/utils/kong_config_generator.py::generate_minio_service()`
with `preserve_host: True` so the console SPA constructs URLs
against the browser's real hostname.

## See also

- [`docs/services/minio.md`](../../docs/services/minio.md) — full service docs.
