# Contributing — adding or modifying a service

The stack uses a **per-service folder layout** under `services/<name>/`. Each service family (one or more co-lifecycled containers) owns:

- `service.yml` — manifest: env vars, source variants, image refs, dependencies, optional Python hook
- `compose.yml` — Docker Compose fragment for that family's containers

The thin top-level `docker-compose.yml` merges fragments via Compose's native `include:` directive (requires Compose ≥ v2.20; v2.26+ recommended).

## Adding a new service

1. Create the folder: `mkdir services/myservice`
2. Write `services/myservice/service.yml`. Schema: `bootstrapper/schemas/service.schema.json`.
   - `name:` must equal the folder name (kebab-case).
   - `category:` one of `data | llm | ai | app | infra`.
   - `containers:` lists every container name in your compose.yml.
   - `env:` declares every env var the service owns. Use `auto_managed: true` for vars computed by source effects or a Python hook; use `secret: true` for credentials (default never echoed into `.env.example`).
   - `sources:` (optional) declares source variants and their declarative `effects:` (env var assignments). Source effects may write to any env var the manifest declares — including `auto_managed` ones.
   - `images:` lists each container's `${X_IMAGE}` env var so version bumps happen in one place.
3. Write `services/myservice/compose.yml`. Use `${VAR}` interpolation; never inline literal images. Conventions:
   - `services:` lists only this family's containers
   - `volumes:` lists only this family's named volumes (`name: ${PROJECT_NAME}-<service>-<purpose>`, plus `driver: local` for byte-equivalence with the legacy monolithic shape)
   - `networks:` references `backend-network`; never redefines it
   - Bind-mount paths are **relative to the fragment file** (e.g., `../../myservice/scripts:/scripts`)
4. Add the fragment to the `include:` list in `docker-compose.yml`.
5. Add an entry to `services/_order.yml` (controls wizard display order and `.env.example` ordering).
6. (Optional) If declarative source effects can't express your computation, add a hook:
   - Create `bootstrapper/services/hooks/myservice.py` exporting an `apply(env: dict[str, str]) -> dict[str, str]` callable.
   - Reference it from the manifest: `hook: services.hooks.myservice`.
   - Add tests at `bootstrapper/tests/test_hooks.py`.
7. Run the lint locally:
   ```bash
   cd bootstrapper && uv run python -m tools.validate_fragments
   ```
8. Run the test suite:
   ```bash
   cd bootstrapper && uv run pytest tests/ -q
   ```

## Modifying an existing service

- Env var default change → edit the manifest's `env:` block. Re-run the lint.
- Image version bump → edit the manifest's `images[].default`. The compose fragment references the var, so no compose change is needed.
- New container in the family → add to `containers:` in the manifest AND to `services:` in the fragment.
- New source variant → add to `sources.options[]` in the manifest.

## Schema cheatsheet

```yaml
name: myservice
label: "My service (human-readable)"
category: app                           # data | llm | ai | app | infra
docs: docs/services/myservice.md        # optional
virtual: false                          # true for env-only manifests like cloud-providers

containers:                             # may be [] when virtual: true
  - myservice

images:
  - var: MYSERVICE_IMAGE
    default: "myorg/myservice:1.0.0"
    container: myservice

sources:                                # OPTIONAL; omit for single-source services
  var: MYSERVICE_SOURCE
  default: container
  options:
    - id: container
      label: "Container"
      effects:
        MYSERVICE_SCALE: 1
        MYSERVICE_ENDPOINT: "http://myservice:8080"
    - id: disabled
      label: "Disabled"
      effects:
        MYSERVICE_SCALE: 0
        MYSERVICE_ENDPOINT: ""

env:
  - name: MYSERVICE_SOURCE
    default: container
  - name: MYSERVICE_PORT
    default: 63099
  - name: MYSERVICE_API_KEY
    default: ""
    secret: true                        # default never echoed into .env.example
  - name: MYSERVICE_SCALE
    auto_managed: true                  # computed by source effects/hook
  - name: MYSERVICE_ENDPOINT
    auto_managed: true

depends_on:                             # logical deps (compose-level lives in compose.yml)
  required: []
  optional: []

exports:                                # documents the cross-service env-var contract
  - name: MYSERVICE_ENDPOINT
    consumers: [backend, n8n]

hook: services.hooks.myservice          # optional; Python entry point
```

## Validator rules (what the lint catches)

1. **schema check** — every `service.yml` matches `bootstrapper/schemas/service.schema.json`
2. **duplicate_env_var** — exactly one manifest owns each env-var name
3. **duplicate_container** — exactly one manifest owns each container name
4. **unknown_dependency** — `depends_on.required/optional` references a known manifest
5. **undeclared_export** — every `exports[].name` is in this manifest's `env:` or produced by source effects
6. **undeclared_effect** — every `sources.options[].effects` key is declared somewhere
7. **undeclared_source_var** — the SOURCE var itself is declared in `env:`
8. **unknown_consumer** — every `exports[].consumers` entry is a known manifest

## Byte-equivalence

`bootstrapper/tests/test_fragment_equivalence.py` asserts that
`docker compose -f docker-compose.yml config` matches the golden baseline at
`bootstrapper/tests/fixtures/rendered_config_baseline.yml`. If you change a
fragment's compose shape, you'll either need to update the baseline (after
confirming the change is intentional) or restore byte-equivalence.

```bash
# Inspect drift
docker compose --env-file .env -f docker-compose.yml config > /tmp/actual.yml
diff bootstrapper/tests/fixtures/rendered_config_baseline.yml /tmp/actual.yml

# Refresh baseline (only when the drift is intentional)
docker compose --env-file .env -f docker-compose.yml config > \
    bootstrapper/tests/fixtures/rendered_config_baseline.yml
```
