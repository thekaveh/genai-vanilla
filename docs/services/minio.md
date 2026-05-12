# MinIO

S3-compatible object storage for the artifact tier of the stack. Complements Supabase Storage rather than replacing it: Supabase Storage stays the app-tier surface (row-level-security uploads, signed URLs, ≤50 MB files); MinIO is the artifact-tier surface for high-throughput, large-blob workloads.

## Endpoints

| Surface | URL |
|---|---|
| S3 API (internal) | `http://minio:9000` |
| Admin console (internal) | `http://minio:9001` |
| S3 API (host) | `http://localhost:${MINIO_PORT}` (default `63030`) |
| Admin console (host) | `http://localhost:${MINIO_CONSOLE_PORT}` (default `63031`) |

## Default credentials

- **Root user:** `MINIO_ROOT_USER` (default `minioadmin`)
- **Root password:** `MINIO_ROOT_PASSWORD` — auto-generated to `.env` on first `./start.sh`. Retrieve with `grep ^MINIO_ROOT_PASSWORD= .env`. Use these credentials to log into the admin console.

Root credentials are NEVER surfaced to consumers — see Service accounts below.

## Bucket layout

Five buckets are pre-provisioned by `minio-init`. Bucket names are the bare service identifier:

| Bucket | Intended consumer |
|---|---|
| `comfyui` | ComfyUI generated outputs |
| `backend` | Backend (FastAPI) large blobs / embeddings / model checkpoints |
| `n8n` | n8n workflow file inputs and outputs |
| `jupyter` | JupyterHub datasets and model artifacts |
| `docling` | Doc Processor parsed-document persistence |

Bucket names are overridable via `MINIO_BUCKET_<NAME>` env vars; hand-edits stick.

## Service accounts

Each consumer has its own MinIO service account with an inline IAM policy scoped to a single bucket:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": ["arn:aws:s3:::<bucket>/*"] },
    { "Effect": "Allow", "Action": ["s3:ListBucket"],
      "Resource": ["arn:aws:s3:::<bucket>"] }
  ]
}
```

Credentials are auto-generated to `.env` and exposed as `MINIO_<NAME>_ACCESS_KEY` and `MINIO_<NAME>_SECRET_KEY` where `<NAME>` ∈ `{COMFYUI, BACKEND, N8N, JUPYTER, DOCLING}`. A cross-bucket access attempt with a consumer credential returns `403 AccessDenied`.

## Consumer integration recipe (for follow-up PRs)

Python (boto3):

```python
import boto3
from botocore.client import Config
import os

s3 = boto3.client(
    "s3",
    endpoint_url=os.environ["MINIO_ENDPOINT"],
    aws_access_key_id=os.environ["MINIO_BACKEND_ACCESS_KEY"],
    aws_secret_access_key=os.environ["MINIO_BACKEND_SECRET_KEY"],
    region_name=os.environ["MINIO_REGION"],
    config=Config(s3={"addressing_style": "path"}),
)
s3.put_object(Bucket=os.environ["MINIO_BUCKET_BACKEND"], Key="hello.txt", Body=b"hello")
```

Shell (`mc`):

```sh
mc alias set local http://localhost:${MINIO_PORT} "$MINIO_BACKEND_ACCESS_KEY" "$MINIO_BACKEND_SECRET_KEY"
mc cp ./somefile local/backend/somefile
```

## Source variants

`MINIO_SOURCE` may be:

- `container` (default) — run MinIO in a Docker Compose container
- `disabled` — turn MinIO off (`MINIO_SCALE=0`); the service is not scheduled

`localhost` and `external` variants are not provided in this release.

## Data persistence

MinIO data lives in the `${PROJECT_NAME}-minio-data` named Docker volume mounted at `/data`. `./stop.sh --cold` removes this volume.

## Operations

- **Add a bucket manually:** `mc mb local/<bucket>` from a host with `mc` and the root alias configured.
- **Rotate a service-account key:** edit `MINIO_<NAME>_ACCESS_KEY` and `MINIO_<NAME>_SECRET_KEY` in `.env`, then run `docker compose up --force-recreate minio-init` to re-provision.
- **Logs:** `docker logs ${PROJECT_NAME}-minio` and `docker logs ${PROJECT_NAME}-minio-init`.

## Troubleshooting

- **`SignatureDoesNotMatch`** — most often clock skew between host and container. Sync your host clock.
- **Browser-based S3 client fails with CORS** — MinIO's default CORS config rejects unrecognized origins. Configure via `mc admin config` if browser uploads are required.
- **`403 AccessDenied`** — confirm the consumer credential's scoped policy matches the target bucket. Use root credentials to inspect: `mc admin policy info local <consumer>-policy`.
- **Cross-path-style failures** — MinIO requires path-style addressing. In boto3 use `Config(s3={"addressing_style": "path"})`.
- **`minio` container restart-loops** — typically `MINIO_ROOT_PASSWORD` is empty. Confirm `.env` has it populated; if blank, delete the line and re-run `./start.sh` (the bootstrapper will regenerate).
