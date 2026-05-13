# services/

Per-service manifest folders. Each subfolder corresponds to one **service family** (a logical grouping of co-lifecycled containers — e.g. `supabase/` owns all eight `supabase-*` containers, `n8n/` owns `n8n` + `n8n-worker` + `n8n-init`).

**Phase progress:**

- ✅ **Phase A** landed the scaffolding (schemas, loader, validator, env assembler, CI lint).
- ✅ **Phase B** carved out `services/redis/` as the template — manifest + compose fragment, with byte-equivalence to the monolithic rendering proven by `bootstrapper/tests/test_fragment_equivalence.py`.
- ⏳ **Phase C** migrates the remaining ~18 services in dependency order.
- ⏳ **Phase D** swaps the root `docker-compose.yml` for a thin `include:`-shell, deletes `bootstrapper/service-configs.yml`, and wires the manifests into `bootstrapper/start.py`.
- ⏳ **Phase E** runs the full verification matrix.

## Phase B scaffolding (temporary)

While we carve services out one at a time, the monolithic `docker-compose.yml` at the repo root remains the **live** compose file. The fragments under `services/<name>/compose.yml` are NOT yet wired into the active stack — they're parallel definitions used to prove the pattern works.

The file `docker-compose.modular.yml` at the repo root is a tiny parent shell that includes the carved fragments plus stub definitions for not-yet-carved dependencies. Its purpose is local verification:

```bash
docker compose --env-file .env -f docker-compose.modular.yml config -q     # validates merge
docker compose --env-file .env -f docker-compose.modular.yml config         # prints merged shape
```

This file disappears in Phase D when it becomes the actual `docker-compose.yml`.

## Layout (forward-looking)

```
services/
├── _order.yml          # NEW (Phase D): canonical service order for stable .env.example diffs
├── supabase/
│   ├── service.yml     # manifest: env vars, sources, deps, image refs
│   └── compose.yml     # Docker Compose fragment for the family's containers
├── redis/
│   ├── service.yml
│   └── compose.yml
└── … (≈17 more service folders)
```

## Adding or changing a service

1. Edit `services/<name>/service.yml` (the manifest) and/or `services/<name>/compose.yml` (the fragment).
2. The schema lives at `bootstrapper/schemas/service.schema.json`.
3. Run the lint locally:
   ```bash
   cd bootstrapper && uv run python -m tools.validate_fragments --check-env-example
   ```
4. If you changed any env-affecting field, regenerate `.env.example`:
   ```bash
   cd bootstrapper && uv run python -m services.env_assembler > ../.env.example
   ```
   (Wiring into `./start.sh` lands in Phase D; in Phase A this is a manual step for development of the modular layout itself.)

## Folder-name rules

- Lowercase kebab-case (matches `name:` field in the manifest)
- Names starting with `_` are reserved (e.g. `_order.yml`, future `_user/` overlay)
- Names starting with `.` are ignored by the loader

See the design spec at the plan path (`please-do-a-comprehensive-lovely-pelican.md`) for the full set of decisions and edge cases.
