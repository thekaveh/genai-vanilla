# External Dependency Contract Ledger

Durable ledger for maintenance checks against consumed external contracts, as
required by the overnight maintenance spec's external-dependency contract
section. Each row records what was checked, the pinned or configured version,
the current/latest status observed during the pass, and the evidence source.

## 1. 2026-07-02 Maintenance Pass

| Integration point | Pinned/configured version | Latest/status check | Contract checked | Evidence / disposition |
|---|---:|---|---|---|
| Docker Compose `include:` support | Minimum v2.20.0, recommended v2.26.0 | Existing `DockerManager.check_compose_version()` parses `docker compose version --short` | Compose version floor is now enforced during startup preflight before the modular `include:` compose file is used | Guarded by `bootstrapper/tests/test_start_dependency_preflight.py` |
| scikit-learn requirement in backend | `scikit-learn>=1.9.0` | PyPI reports 1.9.0 as the latest release, released 2026-06-02 | Requirement is valid for the Python 3.12 backend image, but host Python 3.10 cannot collect it | Do not lower the requirement for host-tool compatibility; run audits with the target Python version |
| JupyterHub Python requirements | `torch==2.4.1`, `nltk` unpinned | `pip-audit 2.10.1` under host Python 3.10 collected the requirements and reported 22 known vulnerabilities across `torch 2.4.1` and `nltk 3.9.4` | Vulnerability status only; no automatic upgrade attempted because PyTorch/PyG wheels are image-coupled | Deferred for owner/process decision: add CI vulnerability scan and allowlist or plan coordinated torch/PyG bump |
| MinIO client service-account commands | `minio/mc:RELEASE.2025-08-13T08-35-41Z` | MinIO current docs center `mc admin accesskey`; legacy `mc admin user svcacct` remains a replacement-bound contract to verify before future client bumps | `services/minio/init/scripts/init-minio.sh` still uses `mc admin user svcacct` create/edit/list | Deferred pending live MinIO init validation or deliberate migration to `mc admin accesskey` |
| n8n community package install endpoint | `n8nio/n8n:2.28.2` | n8n's public REST API docs do not cover the UI-internal `/rest/community-packages` route; install path is therefore pinned to the image's observed internal API | Static REST flow trace of `/rest/community-packages` install path; init now exits nonzero if any required community-node installation fails and startup checks the one-shot exit | Guarded by `bootstrapper/tests/test_shell_script_contracts.py` and `bootstrapper/tests/test_start_post_launch_verification.py` |

## 2. Open Ledger Gaps

- Add a CI-supported dependency vulnerability audit that can run under each
  target Python version and produce an allowlisted report.
- Record exact external CLI contracts for MinIO `mc`, n8n community package
  REST endpoints, Airflow CLI commands, and Docker Compose as those paths are
  live-smoked or upgraded.
- Add image vulnerability scanning or a documented exception process for
  intentionally rolling image tags.
