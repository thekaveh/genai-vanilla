#!/bin/sh
# MinIO bucket + service-account provisioning. Idempotent: re-running is a no-op.
set -eu

echo "minio-init: starting MinIO provisioning..."

# Required env vars
: "${MINIO_ROOT_USER:?MINIO_ROOT_USER is required}"
: "${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD is required}"

# Wait for MinIO server (depends_on healthcheck should already guarantee this, but be defensive)
echo "minio-init: waiting for MinIO at http://minio:9000..."
i=0
until mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null 2>&1; do
    i=$((i + 1))
    if [ "$i" -gt 30 ]; then
        echo "minio-init: ERROR — could not reach MinIO after 30 attempts; aborting" >&2
        exit 1
    fi
    sleep 2
done
echo "minio-init: alias 'local' configured"

# Each consumer: bucket name var, access-key var, secret-key var
# Format: CONSUMER:BUCKET_VAR:ACCESS_VAR:SECRET_VAR
for entry in \
    "comfyui:MINIO_BUCKET_COMFYUI:MINIO_COMFYUI_ACCESS_KEY:MINIO_COMFYUI_SECRET_KEY" \
    "backend:MINIO_BUCKET_BACKEND:MINIO_BACKEND_ACCESS_KEY:MINIO_BACKEND_SECRET_KEY" \
    "n8n:MINIO_BUCKET_N8N:MINIO_N8N_ACCESS_KEY:MINIO_N8N_SECRET_KEY" \
    "jupyter:MINIO_BUCKET_JUPYTER:MINIO_JUPYTER_ACCESS_KEY:MINIO_JUPYTER_SECRET_KEY" \
    "docling:MINIO_BUCKET_DOCLING:MINIO_DOCLING_ACCESS_KEY:MINIO_DOCLING_SECRET_KEY" \
; do
    consumer=$(echo "$entry" | cut -d: -f1)
    bucket_var=$(echo "$entry" | cut -d: -f2)
    access_var=$(echo "$entry" | cut -d: -f3)
    secret_var=$(echo "$entry" | cut -d: -f4)

    # Resolve variable values via indirection
    eval "bucket=\${$bucket_var:-}"
    eval "access=\${$access_var:-}"
    eval "secret=\${$secret_var:-}"

    if [ -z "$bucket" ] || [ -z "$access" ] || [ -z "$secret" ]; then
        echo "minio-init: ERROR — missing env for consumer '$consumer' ($bucket_var/$access_var/$secret_var)" >&2
        exit 1
    fi

    # 1. Create bucket (idempotent)
    echo "minio-init: ensuring bucket 'local/$bucket'..."
    mc mb --ignore-existing "local/$bucket"

    # 2. Write the scoped policy to a tmp file
    policy_file="/tmp/${consumer}-policy.json"
    cat > "$policy_file" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": ["arn:aws:s3:::${bucket}/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": ["arn:aws:s3:::${bucket}"]
    }
  ]
}
EOF

    # 3. Create or update the named policy (idempotent)
    policy_name="${consumer}-policy"
    if mc admin policy info local "$policy_name" >/dev/null 2>&1; then
        echo "minio-init: updating existing policy '$policy_name'..."
        # `mc admin policy create` overwrites if the name exists in recent mc versions;
        # older versions require remove+create. Try create; if it errors, do the dance.
        if ! mc admin policy create local "$policy_name" "$policy_file" 2>/dev/null; then
            mc admin policy remove local "$policy_name" || true
            mc admin policy create local "$policy_name" "$policy_file"
        fi
    else
        echo "minio-init: creating policy '$policy_name'..."
        mc admin policy create local "$policy_name" "$policy_file"
    fi

    # 4. Create the service account (idempotent — skip if access key already exists)
    if mc admin user svcacct info local "$access" >/dev/null 2>&1; then
        echo "minio-init: service account '$access' already exists, skipping"
    else
        echo "minio-init: creating service account '$access' for bucket '$bucket'..."
        mc admin user svcacct add local "$MINIO_ROOT_USER" \
            --access-key "$access" \
            --secret-key "$secret" \
            --policy "$policy_file"
    fi

    rm -f "$policy_file"
done

echo "minio-init: provisioning complete"
