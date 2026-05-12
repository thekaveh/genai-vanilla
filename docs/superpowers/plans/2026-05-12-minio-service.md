# MinIO service implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add MinIO as an S3-compatible artifact-tier object-storage leaf service to the GenAI Vanilla stack, with five pre-provisioned consumer buckets and scoped service-account credentials surfaced as the public env contract — no consumer code changes in this PR.

**Architecture:** Two new container services (`minio` + one-shot `minio-init` provisioner) on `backend-network`, ten new auto-generated credentials in `.env`, full bootstrapper integration (port registration, key generation, service-config entry, CLI flag, TUI screen), and a complete documentation surface (new service page, README/ROADMAP/CHANGELOG updates).

**Tech Stack:** Docker Compose, MinIO server `RELEASE.2025-10-15T17-29-55Z` (security-floor — service-account CVE fix), `minio/mc` `RELEASE.2025-08-13T08-35-41Z`, Python 3.10+ bootstrapper (Click, Textual, PyYAML, python-dotenv), POSIX shell init script.

**Source spec:** `docs/superpowers/specs/2026-05-12-minio-service-design.md` (commit `081b141`).

**Commit convention:** terse third-person verb, no Claude `Co-Authored-By` trailer (project rule).

---

## File map

**Create (4):**
- `docs/superpowers/plans/2026-05-12-minio-service.md` — this file
- `minio-init/scripts/init-minio.sh` — idempotent bucket + service-account provisioning script
- `bootstrapper/ui/textual/screens/minio.py` — new wizard step
- `docs/services/minio.md` — service reference documentation

**Modify (12):**
- `bootstrapper/core/port_manager.py` — register `MINIO_PORT=26`, `MINIO_CONSOLE_PORT=27` in `PORT_MAPPING`
- `bootstrapper/utils/key_generator.py` — add MinIO root password + 5×(access-key, secret-key) generators, hook into `generate_missing_keys()`
- `bootstrapper/service-configs.yml` — add `source_configurable.minio` block + `service_dependencies.minio` entry
- `bootstrapper/start.py` — register `--minio-source` Click flag
- `bootstrapper/ui/state.py` — add `minio_source` field to `AppState`
- `bootstrapper/ui/state_builder.py` — plumb the new field from CLI/TUI selections
- `bootstrapper/ui/textual/integration.py` — register the new screen in the wizard step sequence
- `bootstrapper/ui/textual/screens/summary.py` — add MinIO row to the pre-launch summary
- `docker-compose.yml` — append `minio` + `minio-init` services and the `minio-data` named volume
- `.env.example` — append the MinIO env block
- `README.md` — add MinIO to service list and port allocation
- `docs/ROADMAP.md` — move MinIO from Tier 2 to Completed
- `docs/CHANGELOG.md` — replace Unreleased roadmap-addition bullet with shipped Added entry

---

## Execution principles

1. **One commit per task.** Each task ends with `git add` + `git commit`. Terse third-person verb; no Co-Authored-By trailer.
2. **No unit-test scaffolding.** The bootstrapper has no pytest suite (`bootstrapper/test_file.py` is a one-line scratch file, not a test). Verification is integration-style: run the bootstrapper, observe output, check `.env` and `docker ps`. Do NOT introduce pytest as part of this PR.
3. **Working tree must be clean before each task** (`git status` shows nothing pending). If a task touches a file that was already touched by a previous task in the same PR, that's fine — the previous task already committed.
4. **The verification phase at the end is non-optional.** Failed verification means a fix-up commit, not "ship anyway."

---

## Phase 1 — Bootstrapper Python foundation

These must land first; later tasks depend on them being in place.

### Task 1: Register MinIO ports in PORT_MAPPING

**Files:**
- Modify: `bootstrapper/core/port_manager.py:18-46`

This is the single source of truth for port offsets. Two consumers read it:
- `update_env_ports()` (same file, lines 129–179) rewrites `.env` on every `./start.sh`
- TUI wizard's `_recompute_ports` (`bootstrapper/ui/textual/integration.py:467,571`) reads it directly

Both pick up new dict entries with zero call-site changes.

- [ ] **Step 1.1: Confirm the current dict and surrounding context**

Run: `sed -n '17,46p' bootstrapper/core/port_manager.py`

Expected: prints the `PORT_MAPPING = { ... }` block currently ending with `'OPENCLAW_BRIDGE_PORT': 25,` and `'JUPYTERHUB_PORT': 48,`. Confirms offsets 0–25 and 48 are allocated; 26 and 27 are free.

- [ ] **Step 1.2: Insert the two MinIO entries after `OPENCLAW_BRIDGE_PORT`**

In `bootstrapper/core/port_manager.py`, replace this exact existing block:

```python
        'OPENCLAW_BRIDGE_PORT': 25,   # Base port + 25
        'JUPYTERHUB_PORT': 48,        # Base port + 48
```

with:

```python
        'OPENCLAW_BRIDGE_PORT': 25,   # Base port + 25
        'MINIO_PORT': 26,             # Base port + 26 (MinIO S3 API)
        'MINIO_CONSOLE_PORT': 27,     # Base port + 27 (MinIO admin console)
        'JUPYTERHUB_PORT': 48,        # Base port + 48
```

- [ ] **Step 1.3: Verify the dict via Python**

Run:
```sh
cd bootstrapper && python3 -c "
from core.port_manager import PortManager
pm = PortManager.PORT_MAPPING
assert pm['MINIO_PORT'] == 26, f'MINIO_PORT offset wrong: {pm[\"MINIO_PORT\"]}'
assert pm['MINIO_CONSOLE_PORT'] == 27, f'MINIO_CONSOLE_PORT offset wrong: {pm[\"MINIO_CONSOLE_PORT\"]}'
print('OK: MinIO ports registered at offsets 26, 27')
"
```

Expected output: `OK: MinIO ports registered at offsets 26, 27`

- [ ] **Step 1.4: Verify port assignment recomputation**

Run:
```sh
cd bootstrapper && python3 -c "
from core.port_manager import PortManager
p = PortManager(root_dir='..')
assert p.calculate_port_assignments(63000)['MINIO_PORT'] == 63026
assert p.calculate_port_assignments(63000)['MINIO_CONSOLE_PORT'] == 63027
assert p.calculate_port_assignments(64000)['MINIO_PORT'] == 64026
assert p.calculate_port_assignments(64000)['MINIO_CONSOLE_PORT'] == 64027
print('OK: BASE_PORT recomputation works for both MinIO ports')
"
```

Expected output: `OK: BASE_PORT recomputation works for both MinIO ports`

- [ ] **Step 1.5: Commit**

```sh
git add bootstrapper/core/port_manager.py
git commit -m "registers MinIO S3 API and console ports in PortManager.PORT_MAPPING"
```

---

### Task 2: Extend KeyGenerator with MinIO credentials

**Files:**
- Modify: `bootstrapper/utils/key_generator.py`

Pattern to mirror: `generate_litellm_master_key()` + `generate_and_update_litellm_master_key()` + the `generate_missing_keys()` orchestrator. Same shape: a value-producer, an "update if blank" wrapper, and registration in the orchestrator.

Credentials to generate (11 total):
- `MINIO_ROOT_PASSWORD` — 32-char URL-safe random
- `MINIO_{COMFYUI,BACKEND,N8N,JUPYTER,DOCLING}_ACCESS_KEY` — 20-char uppercase alphanumeric (S3 convention)
- `MINIO_{COMFYUI,BACKEND,N8N,JUPYTER,DOCLING}_SECRET_KEY` — 40-char URL-safe random

- [ ] **Step 2.1: Add the value-generator helpers**

Insert immediately after the existing `generate_litellm_master_key()` method (after line 54), before `get_current_env_value()`:

```python
    def generate_minio_root_password(self) -> str:
        """MinIO root password — 32-char URL-safe random."""
        return secrets.token_urlsafe(24)

    def generate_minio_access_key(self) -> str:
        """MinIO service-account access key — 20-char uppercase alphanumeric (S3 convention)."""
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(secrets.choice(alphabet) for _ in range(20))

    def generate_minio_secret_key(self) -> str:
        """MinIO service-account secret key — 40-char URL-safe random."""
        return secrets.token_urlsafe(30)
```

- [ ] **Step 2.2: Add the `MINIO_CONSUMERS` constant near the top of the class**

Insert immediately after the class docstring `"""Generates and manages encryption keys for GenAI Stack services."""` (line 15):

```python
    MINIO_CONSUMERS = ("COMFYUI", "BACKEND", "N8N", "JUPYTER", "DOCLING")
```

- [ ] **Step 2.3: Add the "update if blank" wrappers**

Insert immediately after `generate_and_update_litellm_master_key()` (after line 189), before `generate_missing_keys()`:

```python
    def generate_and_update_minio_root_password(self, force: bool = False) -> bool:
        """Generate MINIO_ROOT_PASSWORD when absent. Hand-edits stick unless force=True."""
        current_value = self.get_current_env_value('MINIO_ROOT_PASSWORD')
        if not force and current_value:
            return True
        new_value = self.generate_minio_root_password()
        return self.update_env_key('MINIO_ROOT_PASSWORD', new_value)

    def generate_and_update_minio_consumer_keys(self, force: bool = False) -> Dict[str, bool]:
        """Generate MINIO_<NAME>_ACCESS_KEY + MINIO_<NAME>_SECRET_KEY for every consumer in
        MINIO_CONSUMERS, only when blank. Returns a per-variable success map.
        """
        results: Dict[str, bool] = {}
        for consumer in self.MINIO_CONSUMERS:
            access_var = f'MINIO_{consumer}_ACCESS_KEY'
            secret_var = f'MINIO_{consumer}_SECRET_KEY'

            if force or not self.get_current_env_value(access_var):
                results[access_var] = self.update_env_key(access_var, self.generate_minio_access_key())
            else:
                results[access_var] = True

            if force or not self.get_current_env_value(secret_var):
                results[secret_var] = self.update_env_key(secret_var, self.generate_minio_secret_key())
            else:
                results[secret_var] = True

        return results
```

- [ ] **Step 2.4: Hook the new generators into `generate_missing_keys()`**

In `generate_missing_keys()` (currently ends around line 213), replace the existing body:

```python
        results = {}

        # Generate N8N encryption key
        results['N8N_ENCRYPTION_KEY'] = self.generate_and_update_n8n_key(force=force_regenerate)

        # Generate SearxNG secret
        results['SEARXNG_SECRET'] = self.generate_and_update_searxng_secret(force=force_regenerate)

        # LiteLLM master key — never force-regenerate (would invalidate virtual keys
        # and orphan spend history). Only generate when absent.
        results['LITELLM_MASTER_KEY'] = self.generate_and_update_litellm_master_key(force=False)

        return results
```

with:

```python
        results = {}

        # Generate N8N encryption key
        results['N8N_ENCRYPTION_KEY'] = self.generate_and_update_n8n_key(force=force_regenerate)

        # Generate SearxNG secret
        results['SEARXNG_SECRET'] = self.generate_and_update_searxng_secret(force=force_regenerate)

        # LiteLLM master key — never force-regenerate (would invalidate virtual keys
        # and orphan spend history). Only generate when absent.
        results['LITELLM_MASTER_KEY'] = self.generate_and_update_litellm_master_key(force=False)

        # MinIO root password — never force-regenerate (would lock out console + break
        # provisioning). Only generate when absent.
        results['MINIO_ROOT_PASSWORD'] = self.generate_and_update_minio_root_password(force=False)

        # MinIO per-consumer service-account credentials — only generate when absent.
        # Rotating these means re-running minio-init, which is a deliberate operator action.
        results.update(self.generate_and_update_minio_consumer_keys(force=False))

        return results
```

- [ ] **Step 2.5: Verify with a Python smoke test against a scratch .env**

Run:
```sh
cd bootstrapper && python3 -c "
import tempfile, pathlib
from utils.key_generator import KeyGenerator
with tempfile.TemporaryDirectory() as d:
    envp = pathlib.Path(d) / '.env'
    envp.write_text('')  # empty .env
    kg = KeyGenerator(root_dir=d)
    results = kg.generate_missing_keys()
    # All MinIO-related entries succeeded
    assert results['MINIO_ROOT_PASSWORD'] is True, results
    for c in ('COMFYUI','BACKEND','N8N','JUPYTER','DOCLING'):
        assert results[f'MINIO_{c}_ACCESS_KEY'] is True
        assert results[f'MINIO_{c}_SECRET_KEY'] is True
    contents = envp.read_text()
    # 11 lines written
    assert 'MINIO_ROOT_PASSWORD=' in contents
    for c in ('COMFYUI','BACKEND','N8N','JUPYTER','DOCLING'):
        assert f'MINIO_{c}_ACCESS_KEY=' in contents
        assert f'MINIO_{c}_SECRET_KEY=' in contents
    # Values are non-empty
    for line in contents.splitlines():
        k, _, v = line.partition('=')
        if k.startswith('MINIO_'):
            assert v.strip(), f'{k} is empty'
    # Idempotence: second call must not overwrite anything
    before = envp.read_text()
    kg.generate_missing_keys()
    assert envp.read_text() == before, 'Idempotence violated — re-run rewrote values'
    print('OK: 11 MinIO credentials generated, non-empty, idempotent')
"
```

Expected output: `OK: 11 MinIO credentials generated, non-empty, idempotent`

- [ ] **Step 2.6: Commit**

```sh
git add bootstrapper/utils/key_generator.py
git commit -m "adds MinIO root password and per-consumer service-account key generation"
```

---

### Task 3: Add MinIO entry to service-configs.yml

**Files:**
- Modify: `bootstrapper/service-configs.yml`

- [ ] **Step 3.1: Confirm the existing structure**

Run: `grep -n "^source_configurable:\|^  [a-z]\|^adaptive_services:\|^fixed_services:\|^service_dependencies:" bootstrapper/service-configs.yml | head -30`

This prints top-level sections + the names of services already under each. Confirms where to insert MinIO — alphabetically or end-of-list per the file's convention. Note which convention is used.

- [ ] **Step 3.2: Insert the `minio` entry under `source_configurable:`**

Add the following block under `source_configurable:`. Place it before `weaviate` if entries are alphabetical, otherwise at the end of `source_configurable:`. Note that `${MINIO_PORT}` is interpolated by the bootstrapper, not by Compose, because this file is consumed by the Python bootstrapper layer:

```yaml
  minio:
    container:
      scale: 1
      environment:
        MINIO_ENDPOINT: http://minio:9000
        MINIO_PUBLIC_ENDPOINT: http://localhost:${MINIO_PORT}
      deploy: {}
      extra_hosts: []
    disabled:
      scale: 0
      environment:
        MINIO_ENDPOINT: ""
        MINIO_PUBLIC_ENDPOINT: ""
      deploy: {}
      extra_hosts: []
```

- [ ] **Step 3.3: Insert the `minio` entry under `service_dependencies:`**

Add at the end of the `service_dependencies:` section (or alphabetically if that's the convention):

```yaml
  minio:
    requires: []
    optional: []
```

MinIO is a leaf service — no upstream dependencies. Consumers gain optional `minio` in their own `service_dependencies` blocks in dedicated follow-up PRs; this PR does NOT modify existing consumer entries.

- [ ] **Step 3.4: Validate YAML syntax**

Run:
```sh
python3 -c "
import yaml
with open('bootstrapper/service-configs.yml') as f:
    data = yaml.safe_load(f)
assert 'minio' in data['source_configurable'], 'minio missing under source_configurable'
assert 'container' in data['source_configurable']['minio']
assert 'disabled' in data['source_configurable']['minio']
assert data['source_configurable']['minio']['container']['scale'] == 1
assert data['source_configurable']['minio']['disabled']['scale'] == 0
assert 'minio' in data['service_dependencies']
assert data['service_dependencies']['minio'] == {'requires': [], 'optional': []}
print('OK: minio entries valid in service-configs.yml')
"
```

Expected output: `OK: minio entries valid in service-configs.yml`

- [ ] **Step 3.5: Commit**

```sh
git add bootstrapper/service-configs.yml
git commit -m "adds minio source-configurable entry and dependency block"
```

---

## Phase 2 — Docker Compose service definition

### Task 4: Create the `minio-init` provisioning script

**Files:**
- Create: `minio-init/scripts/init-minio.sh`

Idempotent shell script using `mc`. Runs every `./start.sh`. Must handle the "already exists" case for buckets, policies, and service accounts without exiting non-zero.

- [ ] **Step 4.1: Create the script directory**

Run:
```sh
mkdir -p minio-init/scripts
```

- [ ] **Step 4.2: Write `minio-init/scripts/init-minio.sh`**

Create `minio-init/scripts/init-minio.sh` with the following contents (use `printf '%s\n'` or your editor's "create" path; the `#!/bin/sh` shebang is required — the script runs in alpine/busybox-compatible sh):

```sh
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
```

- [ ] **Step 4.3: Make the script executable**

Run:
```sh
chmod +x minio-init/scripts/init-minio.sh
```

- [ ] **Step 4.4: Lint with shellcheck if available; otherwise sh -n syntax check**

Run:
```sh
sh -n minio-init/scripts/init-minio.sh && echo "OK: shell syntax valid"
```

Expected output: `OK: shell syntax valid`

If `shellcheck` is installed, also run:
```sh
shellcheck -s sh minio-init/scripts/init-minio.sh || true
```

(Warnings are acceptable; errors should be addressed.)

- [ ] **Step 4.5: Commit**

```sh
git add minio-init/scripts/init-minio.sh
git commit -m "adds idempotent MinIO bucket and service-account provisioning script"
```

---

### Task 5: Add MinIO services and named volume to docker-compose.yml

**Files:**
- Modify: `docker-compose.yml`

Two new service blocks and one new named volume. Append to existing sections; do NOT modify any existing services.

- [ ] **Step 5.1: Locate the named-volumes section**

Run: `grep -n "^volumes:\|^  [a-z][a-z0-9-]*-data:\|^  [a-z][a-z0-9-]*:$" docker-compose.yml | head -40`

This surfaces the `volumes:` block (top-level) and the list of named volumes. Identify the last entry — that's where `minio-data` gets appended.

- [ ] **Step 5.2: Append the `minio-data` named volume**

In `docker-compose.yml`, under the top-level `volumes:` section, add the following at the end (just before the `services:` block or wherever the volume list terminates):

```yaml
  minio-data:
    name: ${PROJECT_NAME}-minio-data
    driver: local
```

- [ ] **Step 5.3: Append the `minio` service**

Add the following service block to the `services:` section. Place it near the other data-layer services (after `neo4j-graph-db` or in the same neighborhood as `supabase-storage` — pick whichever produces the cleanest diff against the file's existing groupings):

```yaml
  minio:
    image: ${MINIO_IMAGE}
    container_name: ${PROJECT_NAME}-minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
      MINIO_REGION: ${MINIO_REGION}
      MINIO_BROWSER_REDIRECT_URL: ${MINIO_PUBLIC_ENDPOINT}
    ports:
      - "${MINIO_PORT}:9000"
      - "${MINIO_CONSOLE_PORT}:9001"
    volumes:
      - minio-data:/data
    deploy:
      replicas: ${MINIO_SCALE:-1}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
    networks:
      - backend-network
```

- [ ] **Step 5.4: Append the `minio-init` service immediately after `minio`**

```yaml
  minio-init:
    image: ${MINIO_INIT_IMAGE}
    container_name: ${PROJECT_NAME}-minio-init
    restart: "no"
    depends_on:
      minio:
        condition: service_healthy
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
      MINIO_BUCKET_COMFYUI: ${MINIO_BUCKET_COMFYUI}
      MINIO_COMFYUI_ACCESS_KEY: ${MINIO_COMFYUI_ACCESS_KEY}
      MINIO_COMFYUI_SECRET_KEY: ${MINIO_COMFYUI_SECRET_KEY}
      MINIO_BUCKET_BACKEND: ${MINIO_BUCKET_BACKEND}
      MINIO_BACKEND_ACCESS_KEY: ${MINIO_BACKEND_ACCESS_KEY}
      MINIO_BACKEND_SECRET_KEY: ${MINIO_BACKEND_SECRET_KEY}
      MINIO_BUCKET_N8N: ${MINIO_BUCKET_N8N}
      MINIO_N8N_ACCESS_KEY: ${MINIO_N8N_ACCESS_KEY}
      MINIO_N8N_SECRET_KEY: ${MINIO_N8N_SECRET_KEY}
      MINIO_BUCKET_JUPYTER: ${MINIO_BUCKET_JUPYTER}
      MINIO_JUPYTER_ACCESS_KEY: ${MINIO_JUPYTER_ACCESS_KEY}
      MINIO_JUPYTER_SECRET_KEY: ${MINIO_JUPYTER_SECRET_KEY}
      MINIO_BUCKET_DOCLING: ${MINIO_BUCKET_DOCLING}
      MINIO_DOCLING_ACCESS_KEY: ${MINIO_DOCLING_ACCESS_KEY}
      MINIO_DOCLING_SECRET_KEY: ${MINIO_DOCLING_SECRET_KEY}
    volumes:
      - ./minio-init/scripts:/scripts:ro
    entrypoint: ["/bin/sh", "/scripts/init-minio.sh"]
    networks:
      - backend-network
```

- [ ] **Step 5.5: Validate compose syntax (statically, without running)**

Run:
```sh
docker compose config --quiet && echo "OK: compose syntax valid"
```

This validates and resolves interpolations. It will warn if env vars referenced in compose are undefined — at this point `MINIO_IMAGE`, `MINIO_INIT_IMAGE`, etc. are NOT yet in `.env`, so the command will fail with "variable is not set" warnings/errors.

To validate compose syntax independently of env, instead run:
```sh
python3 -c "
import yaml
with open('docker-compose.yml') as f:
    data = yaml.safe_load(f)
assert 'minio' in data['services'], 'minio service missing'
assert 'minio-init' in data['services'], 'minio-init service missing'
assert data['services']['minio']['ports'] == ['\${MINIO_PORT}:9000', '\${MINIO_CONSOLE_PORT}:9001']
assert 'minio-data' in data['volumes']
assert data['volumes']['minio-data']['name'] == '\${PROJECT_NAME}-minio-data'
deps = data['services']['minio-init']['depends_on']
assert deps['minio']['condition'] == 'service_healthy'
print('OK: docker-compose.yml MinIO blocks valid')
"
```

Expected output: `OK: docker-compose.yml MinIO blocks valid`

(Full `docker compose config` validation happens after Task 6 lands the env vars.)

- [ ] **Step 5.6: Commit**

```sh
git add docker-compose.yml
git commit -m "adds MinIO and minio-init services with named data volume"
```

---

### Task 6: Append MinIO block to .env.example

**Files:**
- Modify: `.env.example`

- [ ] **Step 6.1: Append the MinIO env block at the end of the file**

Add the following block to `.env.example`, after the last existing entry. Match the file's existing comment-banner style (visible in earlier sections):

```
# =============================================================================
# MinIO (S3-compatible object storage — artifact-tier complement to Supabase Storage)
# =============================================================================
MINIO_SOURCE=container                            # Options: container, disabled
MINIO_IMAGE=minio/minio:RELEASE.2025-10-15T17-29-55Z
MINIO_INIT_IMAGE=minio/mc:RELEASE.2025-08-13T08-35-41Z
MINIO_PORT=63026                                  # S3 API
MINIO_CONSOLE_PORT=63027                          # Admin console UI
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=                              # Auto-generated on first start
MINIO_REGION=us-east-1
MINIO_ENDPOINT=                                   # AUTO-MANAGED (internal, e.g. http://minio:9000)
MINIO_PUBLIC_ENDPOINT=                            # AUTO-MANAGED (host, e.g. http://localhost:63026)
MINIO_SCALE=1                                     # AUTO-MANAGED (0 when MINIO_SOURCE=disabled)

# Per-consumer bucket names + service-account credentials
MINIO_BUCKET_COMFYUI=comfyui
MINIO_COMFYUI_ACCESS_KEY=                         # Auto-generated on first start
MINIO_COMFYUI_SECRET_KEY=                         # Auto-generated on first start

MINIO_BUCKET_BACKEND=backend
MINIO_BACKEND_ACCESS_KEY=
MINIO_BACKEND_SECRET_KEY=

MINIO_BUCKET_N8N=n8n
MINIO_N8N_ACCESS_KEY=
MINIO_N8N_SECRET_KEY=

MINIO_BUCKET_JUPYTER=jupyter
MINIO_JUPYTER_ACCESS_KEY=
MINIO_JUPYTER_SECRET_KEY=

MINIO_BUCKET_DOCLING=docling
MINIO_DOCLING_ACCESS_KEY=
MINIO_DOCLING_SECRET_KEY=
```

- [ ] **Step 6.2: Verify every var declared in the compose block is now defined in .env.example**

Run:
```sh
for v in MINIO_IMAGE MINIO_INIT_IMAGE MINIO_PORT MINIO_CONSOLE_PORT MINIO_ROOT_USER MINIO_ROOT_PASSWORD MINIO_REGION MINIO_PUBLIC_ENDPOINT MINIO_SCALE MINIO_BUCKET_COMFYUI MINIO_COMFYUI_ACCESS_KEY MINIO_COMFYUI_SECRET_KEY MINIO_BUCKET_BACKEND MINIO_BACKEND_ACCESS_KEY MINIO_BACKEND_SECRET_KEY MINIO_BUCKET_N8N MINIO_N8N_ACCESS_KEY MINIO_N8N_SECRET_KEY MINIO_BUCKET_JUPYTER MINIO_JUPYTER_ACCESS_KEY MINIO_JUPYTER_SECRET_KEY MINIO_BUCKET_DOCLING MINIO_DOCLING_ACCESS_KEY MINIO_DOCLING_SECRET_KEY; do
    grep -q "^${v}=" .env.example || echo "MISSING: $v"
done
echo "Check complete (no MISSING lines above = all present)"
```

Expected output: no `MISSING:` lines printed; only the final `Check complete...` line.

- [ ] **Step 6.3: Full compose validation now that env vars exist**

Run:
```sh
cp .env.example .env
docker compose config --quiet && echo "OK: full compose validation passes" || echo "FAIL — review output"
rm -f .env
```

Expected output: `OK: full compose validation passes`

(If FAIL, the most likely cause is `MINIO_PUBLIC_ENDPOINT=` being empty in `.env.example`, which `docker compose config` may warn about. The AUTO-MANAGED fields get populated by `./start.sh`; for this static check, temporarily set them in the copy or accept the warning if it's only a warning, not an error.)

- [ ] **Step 6.4: Commit**

```sh
git add .env.example
git commit -m "appends MinIO environment block to .env.example"
```

---

## Phase 3 — Bootstrapper CLI + TUI integration

### Task 7: Register `--minio-source` Click flag in start.py

**Files:**
- Modify: `bootstrapper/start.py`

The pattern to mirror is `--weaviate-source`. Find that flag in the file and add MinIO's directly after it.

- [ ] **Step 7.1: Locate the existing `--weaviate-source` flag and its handling**

Run:
```sh
grep -n "weaviate.source\|weaviate_source" bootstrapper/start.py
```

Note: every occurrence (decorator, main signature, override-application call site). Each is a place to add MinIO's analog.

- [ ] **Step 7.2: Add the Click decorator**

In `bootstrapper/start.py`, find the existing decorator that declares `--weaviate-source`. It looks like:

```python
@click.option('--weaviate-source', type=click.Choice(['container', 'localhost', 'disabled']), help='Override Weaviate source')
```

Add the following analogous decorator immediately AFTER the `--weaviate-source` decorator (preserving alphabetical or grouped ordering wherever that's the file's convention):

```python
@click.option('--minio-source', type=click.Choice(['container', 'disabled']), help='Override MinIO source')
```

- [ ] **Step 7.3: Add `minio_source` to the `main()` signature**

Find the `def main(...)` declaration. Add `minio_source` to the parameter list, immediately after `weaviate_source` (or wherever Weaviate sits in the signature):

```python
def main(base_port, cold, setup_hosts, skip_hosts, llm_provider_source,
         ...,  # existing parameters unchanged
         weaviate_source, minio_source, n8n_source, ...):  # insert minio_source after weaviate_source
```

- [ ] **Step 7.4: Wire `minio_source` through SourceOverrideManager (or wherever weaviate_source flows)**

Search for where `weaviate_source` is consumed inside `main()`:

```sh
grep -n "weaviate_source" bootstrapper/start.py
```

For every occurrence inside `main()` that applies a CLI override (typically via `source_override_manager.apply_overrides(...)` or by assembling a kwargs dict), add an analogous line for `minio_source`. Example: if there's a line like:

```python
if weaviate_source:
    self.source_override_manager.set_override('WEAVIATE_SOURCE', weaviate_source)
```

add immediately below:

```python
if minio_source:
    self.source_override_manager.set_override('MINIO_SOURCE', minio_source)
```

Match the exact call style used for Weaviate — do not improvise a different pattern. If Weaviate is plumbed via a dict, add MinIO to the same dict.

- [ ] **Step 7.5: Verify the flag parses**

Run:
```sh
./start.sh --help 2>&1 | grep -i minio
```

Expected: a line like `--minio-source [container|disabled]  Override MinIO source` is printed.

Also:
```sh
./start.sh --minio-source bogus 2>&1 | head -5
```

Expected: Click rejects the value with "Invalid value for '--minio-source'" or similar.

- [ ] **Step 7.6: Commit**

```sh
git add bootstrapper/start.py
git commit -m "adds --minio-source CLI flag with container/disabled choices"
```

---

### Task 8: Create the MinIO wizard screen

**Files:**
- Create: `bootstrapper/ui/textual/screens/minio.py`

Mirror `bootstrapper/ui/textual/screens/weaviate.py` exactly — it's the closest pattern. Single-select between two source values with a descriptive panel.

- [ ] **Step 8.1: Read `weaviate.py` end-to-end to capture the exact shape**

Run:
```sh
cat bootstrapper/ui/textual/screens/weaviate.py
```

Note: the class name pattern (`WeaviateScreen` etc.), the imports, the `on_mount`/`compose` methods, how options are rendered, how the result is written back to `AppState`. The new file should differ only in the per-screen specifics (title, options list, description text, target field name).

- [ ] **Step 8.2: Create `bootstrapper/ui/textual/screens/minio.py`**

Use the Weaviate screen as the template. Below is the structure — adapt to match Weaviate's actual class hierarchy and import paths verbatim (do not invent new ones):

```python
"""MinIO source selection screen for the bootstrapper TUI wizard."""

# Imports — copy from weaviate.py exactly, then adjust class/function names as needed.

# Screen class — mirror WeaviateScreen:
#   - Title: "MinIO (object storage)"
#   - Subtitle / description (verbatim text below)
#   - Options: [("container", "Run MinIO in a container (recommended)"),
#               ("disabled",  "Disable MinIO")]
#   - Result writes to AppState.minio_source

# Description panel text (verbatim):
DESCRIPTION = (
    "MinIO — artifact-tier object storage. Provides S3-compatible storage for "
    "ComfyUI outputs, Backend blobs, n8n files, JupyterHub datasets, and Doc "
    "Processor output. Buckets and scoped service-account credentials are "
    "provisioned automatically. Consumer code is unchanged in this release — "
    "Supabase Storage remains the app-tier file surface; each consumer's "
    "artifact path is wired through MinIO in its own follow-up."
)

# Live-status panel: show S3 API endpoint and console URL computed from current
# base_port + offsets 26/27 (read from PortManager.PORT_MAPPING). Match how
# weaviate.py renders its live preview.
```

The file must be a drop-in replacement for `weaviate.py`'s shape — same class hierarchy, same method overrides, same way of pushing the selected value into `AppState`. The implementor reads `weaviate.py` first, then writes `minio.py` adapting only the per-service details.

- [ ] **Step 8.3: Verify the file imports without syntax error**

Run:
```sh
cd bootstrapper && python3 -c "
import importlib, sys
sys.path.insert(0, '.')
m = importlib.import_module('ui.textual.screens.minio')
print('OK: minio screen module imports')
"
```

Expected output: `OK: minio screen module imports`

If imports fail, fix them by mirroring `weaviate.py`'s import block more closely.

- [ ] **Step 8.4: Commit**

```sh
git add bootstrapper/ui/textual/screens/minio.py
git commit -m "adds MinIO source-selection wizard screen"
```

---

### Task 9: Wire `minio_source` through AppState, state_builder, and screen sequence

**Files:**
- Modify: `bootstrapper/ui/state.py`
- Modify: `bootstrapper/ui/state_builder.py`
- Modify: `bootstrapper/ui/textual/integration.py`

Pattern to mirror in every case: how `weaviate_source` is declared, defaulted, and registered.

- [ ] **Step 9.1: Add `minio_source` field to AppState**

Find the `AppState` dataclass in `bootstrapper/ui/state.py` and the line declaring `weaviate_source`. Add an analogous field directly after it:

```python
    minio_source: str = "container"
```

Match the existing default-style (literal vs. computed) used by neighbors. `container` is the default per the spec.

- [ ] **Step 9.2: Plumb `minio_source` through state_builder**

Find `bootstrapper/ui/state_builder.py` and `grep -n weaviate_source`:

```sh
grep -n "weaviate_source" bootstrapper/ui/state_builder.py
```

For every occurrence (typically: reading the CLI kwarg, reading the TUI selection, populating `AppState`), add a parallel line for `minio_source`. The exact lines depend on what's there — do not invent new code paths; mirror Weaviate.

- [ ] **Step 9.3: Register the MinIO screen in the wizard sequence**

In `bootstrapper/ui/textual/integration.py`, locate where wizard step rows are assembled. Search for `weaviate`:

```sh
grep -n "weaviate" bootstrapper/ui/textual/integration.py
```

Identify the spot where Weaviate's row is added to the wizard step list (likely a `ServiceRow(...)` or equivalent). Add a MinIO row immediately AFTER Weaviate, BEFORE n8n. The exact constructor signature comes from looking at the Weaviate row literal — match it field-for-field.

- [ ] **Step 9.4: Verify the wizard launches and the MinIO step appears**

Run a non-interactive smoke test that does NOT require TTY:

```sh
cd bootstrapper && python3 -c "
import sys; sys.path.insert(0, '.')
from ui.state import AppState
a = AppState()
assert hasattr(a, 'minio_source'), 'AppState.minio_source missing'
assert a.minio_source == 'container', f'default wrong: {a.minio_source}'
print('OK: AppState.minio_source defaults to container')
"
```

Expected output: `OK: AppState.minio_source defaults to container`

For the full wizard-launch verification, the implementor can either:
- run `./start.sh` interactively and confirm MinIO appears as a wizard step between Weaviate and n8n, OR
- defer that confirmation to the Phase 5 verification matrix.

- [ ] **Step 9.5: Commit**

```sh
git add bootstrapper/ui/state.py bootstrapper/ui/state_builder.py bootstrapper/ui/textual/integration.py
git commit -m "plumbs minio_source through AppState, state_builder, and wizard sequence"
```

---

### Task 10: Add MinIO row to the launch summary screen

**Files:**
- Modify: `bootstrapper/ui/textual/screens/summary.py`

- [ ] **Step 10.1: Locate the existing summary-row pattern**

Run:
```sh
grep -n "weaviate\|WEAVIATE" bootstrapper/ui/textual/screens/summary.py
```

Note how Weaviate is shown — likely a row entry in a Textual `DataTable` or a formatted string with the endpoint URL.

- [ ] **Step 10.2: Add the MinIO row directly after the Weaviate row**

The shape comes from inspecting Weaviate's exact code. Conceptually, the new row shows:
- Label: `MinIO`
- Status: derived from `state.minio_source` (e.g. `container` or `disabled`)
- Endpoint: `MINIO_PUBLIC_ENDPOINT` from env (S3 API host URL)
- Console: `http://localhost:${MINIO_CONSOLE_PORT}` (computed)

Mirror Weaviate's row literally — same number of columns, same formatting helpers. Do not invent new column conventions.

- [ ] **Step 10.3: Verify the file still imports cleanly**

Run:
```sh
cd bootstrapper && python3 -c "
import sys; sys.path.insert(0, '.')
import ui.textual.screens.summary as s
print('OK: summary module imports')
"
```

Expected output: `OK: summary module imports`

- [ ] **Step 10.4: Commit**

```sh
git add bootstrapper/ui/textual/screens/summary.py
git commit -m "adds MinIO row to launch summary"
```

---

## Phase 4 — Documentation

### Task 11: Create docs/services/minio.md

**Files:**
- Create: `docs/services/minio.md`

Follow the existing service-page pattern. Reference: `docs/services/supabase.md`.

- [ ] **Step 11.1: Inspect the existing service-doc template**

Run:
```sh
ls docs/services/ && head -60 docs/services/supabase.md
```

Note the heading hierarchy, common frontmatter (if any), section ordering, code-fence style.

- [ ] **Step 11.2: Write `docs/services/minio.md`**

Create the file with the following structure. Adapt header style and section ordering to match `supabase.md` exactly.

```markdown
# MinIO

S3-compatible object storage for the artifact tier of the stack. Complements Supabase Storage rather than replacing it: Supabase Storage stays the app-tier surface (row-level-security uploads, signed URLs, ≤50 MB files); MinIO is the artifact-tier surface for high-throughput, large-blob workloads.

## Endpoints

| Surface | URL |
|---|---|
| S3 API (internal) | `http://minio:9000` |
| Admin console (internal) | `http://minio:9001` |
| S3 API (host) | `http://localhost:${MINIO_PORT}` (default `63026`) |
| Admin console (host) | `http://localhost:${MINIO_CONSOLE_PORT}` (default `63027`) |

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
- **403 AccessDenied** — confirm the consumer credential's scoped policy matches the target bucket. Use root credentials to inspect: `mc admin policy info local <consumer>-policy`.
- **Cross-path-style failures** — MinIO requires path-style addressing. In boto3 use `Config(s3={"addressing_style": "path"})`.
- **`minio` container restart-loops** — typically `MINIO_ROOT_PASSWORD` is empty. Confirm `.env` has it populated; if blank, delete the line and re-run `./start.sh` (the bootstrapper will regenerate).
```

- [ ] **Step 11.3: Verify the file renders as valid markdown (no broken fences)**

Run:
```sh
python3 -c "
import re
with open('docs/services/minio.md') as f:
    text = f.read()
# Code fences are balanced
fences = re.findall(r'^\`\`\`', text, re.MULTILINE)
assert len(fences) % 2 == 0, f'Unbalanced code fences: {len(fences)}'
# All five buckets mentioned
for b in ('comfyui','backend','n8n','jupyter','docling'):
    assert f'\`{b}\`' in text, f'bucket {b} not mentioned'
print('OK: minio.md structure valid')
"
```

Expected output: `OK: minio.md structure valid`

- [ ] **Step 11.4: Commit**

```sh
git add docs/services/minio.md
git commit -m "adds docs/services/minio.md service reference"
```

---

### Task 12: Update README.md with MinIO entries

**Files:**
- Modify: `README.md`

The root README has multiple service tables. Audit, then add MinIO consistently.

- [ ] **Step 12.1: Find every place the README lists services or ports**

Run:
```sh
grep -n "weaviate\|Weaviate\|63019\|63018\|comfyui\|ComfyUI" README.md
```

Each line is potentially a spot where MinIO needs to appear. Note the line numbers.

- [ ] **Step 12.2: Add MinIO to the services list**

For each line surfaced above that describes Weaviate in a service-list context, add a MinIO entry immediately below it (or alphabetically — match the file's existing convention). The MinIO description:

> **MinIO** — S3-compatible artifact-tier object storage (ComfyUI outputs, Backend blobs, n8n files, JupyterHub datasets, Doc Processor output). Console at `http://localhost:63027`.

- [ ] **Step 12.3: Add MinIO ports to any port-allocation table**

Look for a table or listing of `630xx` port assignments. Add two rows:

| `MINIO_PORT` | `63026` | MinIO S3 API |
| `MINIO_CONSOLE_PORT` | `63027` | MinIO admin console |

Match the existing table's column structure exactly.

- [ ] **Step 12.4: Add MinIO to the architecture/"what's included" overview if one exists**

If the README opens with a "Services" or "Components" overview list, add a one-line MinIO entry there too. Keep it short — most of the detail lives in `docs/services/minio.md`.

- [ ] **Step 12.5: Sanity-check that MinIO appears in every place Weaviate appears**

Run:
```sh
diff <(grep -c -i minio README.md) <(grep -c -i weaviate README.md) >/dev/null && echo "OK: MinIO appears as often as Weaviate" || echo "Mismatch — manual check needed"
```

(A perfect 1:1 isn't strictly required; the goal is to catch obvious omissions. A "Mismatch" result warrants visual inspection but isn't necessarily a fix-needed.)

- [ ] **Step 12.6: Commit**

```sh
git add README.md
git commit -m "documents MinIO service and ports in README"
```

---

### Task 13: Move MinIO entry in docs/ROADMAP.md from Tier 2 to Completed

**Files:**
- Modify: `docs/ROADMAP.md`

- [ ] **Step 13.1: Read the current MinIO entry and the Completed section header**

Run:
```sh
sed -n '14,56p' docs/ROADMAP.md   # Completed section
sed -n '165,181p' docs/ROADMAP.md # current MinIO entry under Tier 2
```

Note the format of Completed entries (e.g. LiteLLM gateway, LangMem) — they're typically a bold title + bullet list with concise scope-shipped notes.

- [ ] **Step 13.2: Delete the MinIO block from Tier 2**

In `docs/ROADMAP.md`, remove lines `165`–`181` (inclusive — the full MinIO block under Tier 2, starting with the bold title and ending just before the next sibling entry).

- [ ] **Step 13.3: Add a new MinIO entry at the end of Completed**

After the last existing Completed entry (e.g. LangMem persistent memory), insert:

```markdown
**MinIO object storage (artifact tier)**
- S3-compatible artifact-tier storage server (Go, AGPL-v3). Pinned to `minio/minio:RELEASE.2025-10-15T17-29-55Z` (security floor — service-account CVE fix).
- Five pre-provisioned buckets — `comfyui`, `backend`, `n8n`, `jupyter`, `docling` — each with a scoped service-account credential surfaced as `MINIO_<NAME>_ACCESS_KEY` / `MINIO_<NAME>_SECRET_KEY` in `.env`.
- Admin console at `http://localhost:63027`; S3 API at `http://localhost:63026` (host) / `http://minio:9000` (internal).
- Complements Supabase Storage rather than replacing it. Per-consumer wiring (ComfyUI, Backend, n8n, JupyterHub, Doc Processor) ships in dedicated follow-up PRs — credentials and bucket names are in `.env` from day one for opt-in by env-only change.
```

- [ ] **Step 13.4: Verify the file is still syntactically valid markdown**

Run:
```sh
python3 -c "
with open('docs/ROADMAP.md') as f:
    text = f.read()
# MinIO no longer under Tier 2
import re
tier2 = re.search(r'### Tier 2.*?### Tier 3', text, re.DOTALL).group(0)
assert '**MinIO' not in tier2, 'MinIO still appears under Tier 2'
# MinIO now under Completed
completed = re.search(r'### Completed.*?### Tier 1', text, re.DOTALL).group(0)
assert '**MinIO object storage' in completed, 'MinIO not under Completed'
print('OK: ROADMAP MinIO entry relocated')
"
```

Expected output: `OK: ROADMAP MinIO entry relocated`

- [ ] **Step 13.5: Commit**

```sh
git add docs/ROADMAP.md
git commit -m "moves MinIO from Tier 2 to Completed on ROADMAP"
```

---

### Task 14: Update docs/CHANGELOG.md

**Files:**
- Modify: `docs/CHANGELOG.md`

- [ ] **Step 14.1: Read the current [Unreleased] section**

Run:
```sh
sed -n '1,30p' docs/CHANGELOG.md
```

Identify the existing Unreleased "ROADMAP additions" line that mentions MinIO as a future plan.

- [ ] **Step 14.2: Remove the MinIO mention from the Unreleased roadmap-addition bullet**

Find the bullet (around line 9) that reads something like:

> - **ROADMAP additions**: Tier 1 — unified LLM gateway (LiteLLM, or equivalent) and per-service configuration modularization. Tier 2 — Hermes Agent (Nous Research's programmable agent runtime, with Open WebUI integration link) and MinIO (S3-compatible object storage).

Trim out the MinIO mention. The remaining bullet becomes:

> - **ROADMAP additions**: Tier 1 — unified LLM gateway (LiteLLM, or equivalent) and per-service configuration modularization. Tier 2 — Hermes Agent (Nous Research's programmable agent runtime, with Open WebUI integration link).

- [ ] **Step 14.3: Add a new Added entry under Unreleased**

Add a bullet under `[Unreleased] → Added` (create the `### Added` subsection if it doesn't exist):

```markdown
### Added
- **MinIO object storage**: S3-compatible artifact-tier storage service with five pre-provisioned buckets (`comfyui`, `backend`, `n8n`, `jupyter`, `docling`) and scoped service-account credentials surfaced as `MINIO_<NAME>_ACCESS_KEY` / `MINIO_<NAME>_SECRET_KEY` in `.env`. Admin console at `http://localhost:63027`; S3 API at `http://localhost:63026`. Consumer code is unchanged in this release; each consumer integration ships in a dedicated follow-up. Pinned to `minio/minio:RELEASE.2025-10-15T17-29-55Z` (security-floor — service-account CVE fix).
```

- [ ] **Step 14.4: Verify**

Run:
```sh
grep -n "MinIO" docs/CHANGELOG.md
```

Expected: one or two MinIO mentions total — the new Added entry, and (if the rewrite of step 14.2 didn't fully remove it) nothing under ROADMAP additions for Tier 2.

- [ ] **Step 14.5: Commit**

```sh
git add docs/CHANGELOG.md
git commit -m "logs shipped MinIO object-storage service under CHANGELOG Unreleased Added"
```

---

## Phase 5 — End-to-end verification

This phase runs the spec's full 11-step verification matrix. Each verification step is its own checklist item — execute them in order and only proceed if the previous passed. If any step fails, write a fix-up commit and re-run the failing step.

**Pre-requisite:** ensure Docker daemon is running and the working tree is clean (`git status` empty).

### Task 15: Spec verification matrix

- [ ] **Step 15.1: Fresh start, default selections**

Run:
```sh
./stop.sh --cold
./start.sh --minio-source container
```

Expected:
- `./start.sh` completes without errors
- `docker ps --format '{{.Names}}'` lists `genai-minio` (or `${PROJECT_NAME}-minio` for the configured project name)
- `docker ps -a --format '{{.Names}}: {{.Status}}' | grep minio-init` shows the init container exited with code 0
- `grep ^MINIO_ROOT_PASSWORD= .env | grep -v '^MINIO_ROOT_PASSWORD=$'` — non-empty
- `grep -cE '^MINIO_(COMFYUI|BACKEND|N8N|JUPYTER|DOCLING)_(ACCESS|SECRET)_KEY=[^[:space:]]' .env` returns `10`

- [ ] **Step 15.2: Console reachability**

Open `http://localhost:63027` in a browser. Log in with `minioadmin` and the value of `MINIO_ROOT_PASSWORD` from `.env`.

Expected:
- Login succeeds
- Five buckets visible: `comfyui`, `backend`, `n8n`, `jupyter`, `docling`
- Under Identity → Service Accounts: five accounts present, each attached to its named policy

- [ ] **Step 15.3: S3 API smoke test from host**

Run:
```sh
MINIO_ROOT_PASSWORD=$(grep ^MINIO_ROOT_PASSWORD= .env | cut -d= -f2-)
mc alias set local http://localhost:63026 minioadmin "$MINIO_ROOT_PASSWORD"
mc ls local/
```

Expected: five buckets listed (`comfyui`, `backend`, `n8n`, `jupyter`, `docling`).

If `mc` is not installed on the host, instead run from inside the minio-init image:
```sh
docker run --rm --network ${PROJECT_NAME}-network --env-file .env \
  ${MINIO_INIT_IMAGE} sh -c 'mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc ls local/'
```

- [ ] **Step 15.4: Per-consumer credential & IAM scoping smoke test**

Run:
```sh
ACCESS=$(grep ^MINIO_BACKEND_ACCESS_KEY= .env | cut -d= -f2-)
SECRET=$(grep ^MINIO_BACKEND_SECRET_KEY= .env | cut -d= -f2-)
mc alias set backend-test http://localhost:63026 "$ACCESS" "$SECRET"

echo hello | mc pipe backend-test/backend/test.txt
# Expected: succeeds with no error

echo hello | mc pipe backend-test/comfyui/test.txt
# Expected: FAILS with 'Access Denied' or 'AccessDenied'
```

The second command MUST fail. If it succeeds, the IAM policy is mis-scoped — investigate `mc admin policy info local backend-policy` and the script in `minio-init/scripts/init-minio.sh`.

- [ ] **Step 15.5: Source-variant flip to disabled**

Run:
```sh
./start.sh --minio-source disabled
docker ps --filter "name=minio" --format '{{.Names}}'
```

Expected: no `minio` or `minio-init` container is running. `grep ^MINIO_SCALE= .env` shows `MINIO_SCALE=0`.

Flip back for subsequent steps:
```sh
./start.sh --minio-source container
```

- [ ] **Step 15.6: Idempotence on re-run**

With `MINIO_SOURCE=container` and the existing data volume intact, run:
```sh
./start.sh
docker logs ${PROJECT_NAME}-minio-init --tail 50
```

Expected: `minio-init` exits 0 again; logs show "already exists, skipping" or equivalent for buckets, policies, and service accounts.

- [ ] **Step 15.7: Bootstrapper-level checks**

Run:
```sh
./start.sh --help 2>&1 | grep -- '--minio-source'
```

Expected: a line listing `--minio-source [container|disabled]` with help text.

Then launch the wizard interactively (`./start.sh` with no flags) and confirm:
- A MinIO step appears between Weaviate and n8n
- Selecting `container` and proceeding shows MinIO endpoints in the pre-launch summary screen

- [ ] **Step 15.8: Cold-start data wipe**

Run:
```sh
./stop.sh --cold
docker volume ls --format '{{.Name}}' | grep minio || echo "no minio volume — expected"
./start.sh --minio-source container
mc alias set local http://localhost:63026 minioadmin "$(grep ^MINIO_ROOT_PASSWORD= .env | cut -d= -f2-)"
mc ls local/
```

Expected:
- After `stop.sh --cold`: no `genai-minio-data` volume listed
- After `start.sh`: all five buckets re-provisioned

- [ ] **Step 15.9: Cross-runtime check (Podman, if available)**

If Podman is installed and `bootstrapper/core/docker_manager.py` detects it:
```sh
./stop.sh --cold
PODMAN_USERNS=keep-id ./start.sh --minio-source container
```

Expected: MinIO container is healthy; host-exposed ports 63026 and 63027 are reachable; `mc ls local/` works as in step 15.3.

If Podman is not available locally, skip this step and note "Podman not tested locally; relying on existing HOST_GATEWAY_IP plumbing".

- [ ] **Step 15.10: Hand-edit stickiness**

Run:
```sh
sed -i.bak 's/^MINIO_BUCKET_BACKEND=.*/MINIO_BUCKET_BACKEND=my-custom-bucket/' .env
./start.sh
mc alias set local http://localhost:63026 minioadmin "$(grep ^MINIO_ROOT_PASSWORD= .env | cut -d= -f2-)"
mc ls local/
```

Expected: bucket `my-custom-bucket` exists (in addition to or instead of `backend`, depending on whether init runs against existing state). `key_generator.py` did not overwrite the hand edit.

Restore:
```sh
mv .env.bak .env
./start.sh
```

- [ ] **Step 15.11: Base-port recomputation**

Run:
```sh
./stop.sh --cold
./start.sh --base-port 64000 --minio-source container
grep -E '^MINIO_(CONSOLE_)?PORT=' .env
docker port ${PROJECT_NAME}-minio
```

Expected:
- `.env` contains `MINIO_PORT=64026` and `MINIO_CONSOLE_PORT=64027`
- `docker port` output shows `9000/tcp -> 0.0.0.0:64026` and `9001/tcp -> 0.0.0.0:64027`

This is the test specifically tied to the user-requested guarantee that `--base-port` correctly recomputes MinIO's ports.

Restore default base port for completeness:
```sh
./stop.sh --cold
./start.sh --base-port 63000 --minio-source container
```

- [ ] **Step 15.12: Final sanity check & summary commit (if any housekeeping needed)**

After all 11 verification steps pass, run:
```sh
git status
git log --oneline -20
```

Expected:
- Clean working tree
- 14 implementation commits since `081b141` (the spec commit) — one per Task 1–14

If any verification step required a fix-up edit, ensure that fix is committed with a `fixes ...` style message. If everything passed first time, no extra commit is needed.

---

## Self-review against spec

After completing all tasks, verify spec coverage:

| Spec section | Implementing task(s) |
|---|---|
| Architecture / Position in stack | Task 5 (compose) |
| Image pin | Task 6 (.env.example) |
| Ports | Task 1 (PORT_MAPPING) + Task 5 (compose ports) + Task 6 (.env.example defaults) |
| Healthcheck | Task 5 (compose `healthcheck:` block) |
| Persistence | Task 5 (named volume) |
| Restart policy / container naming | Task 5 |
| Source variants | Task 3 (service-configs.yml) |
| Bucket layout & service accounts | Task 4 (init script) |
| Per-bucket IAM policy | Task 4 (init script JSON template) |
| Init container | Task 4 (script) + Task 5 (compose service) |
| Key generation | Task 2 (KeyGenerator extension) |
| `.env.example` block | Task 6 |
| Bootstrapper changes — service-configs.yml | Task 3 |
| Bootstrapper changes — service_config.py | (no change needed — engine is generic; verified in Task 3.4) |
| Bootstrapper changes — key_generator.py | Task 2 |
| Bootstrapper changes — start.py CLI flag | Task 7 |
| Bootstrapper changes — TUI screen | Task 8 |
| Bootstrapper changes — state.py + state_builder.py | Task 9 |
| Bootstrapper changes — integration.py screen sequence | Task 9 |
| Bootstrapper changes — summary.py | Task 10 |
| Docker Compose changes | Task 5 |
| New repo directory `minio-init/scripts/` | Task 4 |
| docs/services/minio.md | Task 11 |
| README.md updates | Task 12 |
| docs/ROADMAP.md update | Task 13 |
| docs/CHANGELOG.md entry | Task 14 |
| Verification (all 11 spec steps) | Task 15 (1–11) + Task 15.11 (base-port recomp, explicit user-requested) |
| Out-of-scope items | not implemented — by design |

Every spec section has a task. Verification step 11 (the user-requested base-port recomputation invariant) is explicitly mapped to Task 15.11.
