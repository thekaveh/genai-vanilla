# Security Policy

## Project Posture

genai-vanilla is a self-hosted, single-tenant AI infrastructure stack
intended to run on a developer's local machine or a private homelab
network. It has no public web surface, no shared deployment, and no
multi-user access model.

This posture shapes how we triage Dependabot and CVE alerts:
vulnerabilities are scored by **(severity × tier × reachability)**, not
raw CVSS alone.

## Operational Tiers

| Tier | Manifest examples | Where it runs |
|------|-------------------|---------------|
| **A — Container-shipped** | `services/docling/provider/gpu/requirements.txt`, the various `*/Dockerfile`s | Docker image; ships to every user that runs `start.sh` |
| **A — Host CLI** | `bootstrapper/pyproject.toml` | Local Python venv on every contributor's host |
| **B — Host install (opt-in)** | `services/docling/provider/localhost/pyproject.toml` | Only installed when user picks the localhost provider via `start.sh --doc-processor-source docling-localhost` and runs `uv sync` themselves |

Tier-A vulnerabilities are fast-tracked. Tier-B vulnerabilities are
documented; users who pick the localhost path own the deployment risk
on their host.

## Reachability Triage Examples

- `transformers.Trainer` RCE (CVE-2026-1839, medium): **unreachable**.
  We use `transformers` transitively via easyocr for inference only and
  never instantiate `Trainer`. Dismissed as `tolerable_risk` with this
  rationale captured in the active remediation report.
- `urllib3` decompression-bomb (CVE-2026-44431/44432, high): **reachable**.
  The bootstrapper makes outbound HTTPS calls (Docker registry, Hugging Face,
  Ollama catalog). Floor-bumped immediately to clear.

## Reporting a Vulnerability

This is a personal-project repository. Please open a private security
advisory via the GitHub repository's **Security** tab → **Report a
vulnerability**. Do not file public issues for security-sensitive
findings.

## Remediation Reports

Active and historical Dependabot remediation reports live under
[`docs/security/`](docs/security/):

- `2026-05-14-dependabot-remediation-report.md` — current (77 alerts triaged, 62 phantom, 15 actionable)
- `2026-05-06-dependabot-remediation-report.md` — predecessor (102 alerts triaged, Phases 1.1/1.2/1.3 landed)
