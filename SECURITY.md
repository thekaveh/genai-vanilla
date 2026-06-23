# Security Policy

## 1. Project Posture

Atlas is a self-hosted, single-tenant engineering platform intended
to run on a developer's local machine or a private homelab network —
applicable across generative AI, ML, and data engineering workloads.
It has no public web surface, no shared deployment, and no multi-user
access model.

This posture shapes how we triage Dependabot and CVE alerts:
vulnerabilities are scored by **(severity × tier × reachability)**, not
raw CVSS alone.

## 2. Operational Tiers

| Tier | Manifest examples | Where it runs |
|------|-------------------|---------------|
| **A — Container-shipped** | `services/docling/provider/gpu/requirements.txt`, `services/parakeet/provider/gpu/requirements.txt`, `services/backend/app/app/requirements.txt`, `services/jupyterhub/build/requirements.txt`, the various `*/Dockerfile`s | Docker image; ships to every user that runs `start.sh` (when the corresponding service is enabled) |
| **A — Host CLI** | `bootstrapper/pyproject.toml` | Local Python venv on every contributor's host |
| **B — Host install (opt-in)** | `services/docling/provider/localhost/pyproject.toml`, `services/parakeet/provider/mlx/requirements.txt` | Only installed when user picks the localhost/mlx provider variant and runs `uv sync` / `pip install -r` themselves |

Tier-A vulnerabilities are fast-tracked. Tier-B vulnerabilities are
documented; users who pick the localhost path own the deployment risk
on their host.

## 3. Reachability Triage Examples

- `transformers.Trainer` RCE (CVE-2026-1839, medium): **unreachable**.
  We use `transformers` transitively via easyocr for inference only and
  never instantiate `Trainer`. Dismissed as `tolerable_risk` with this
  rationale captured in the active remediation report.
- `urllib3` decompression-bomb (CVE-2026-44431/44432, high): **reachable**.
  The bootstrapper makes outbound HTTPS calls (Docker registry, Hugging Face,
  Ollama catalog). Floor-bumped immediately to clear.
- `torch.load` deserialization RCE (CVE-2025-32434, critical) in
  `torch==2.4.1` (Tier A, jupyterhub image): **unreachable**. No
  `torch.load` / `torch.jit.script` / `weights_only` callsite exists
  anywhere in `services/**`; notebooks load models through library APIs,
  not attacker-supplied checkpoints. The pin is held back deliberately —
  torch + PyTorch-Geometric must migrate in lockstep with the matching
  `--find-links` wheel index (see the `dependabot.yml` ignore list), so
  the fixed `torch>=2.6` is not a drop-in bump.

## 4. Reporting a Vulnerability

This is a personal-project repository. Please open a private security
advisory via the GitHub repository's **Security** tab → **Report a
vulnerability**. Do not file public issues for security-sensitive
findings.

## 5. Remediation Reports

Historical Dependabot remediation reports were retired from the working
tree in commit `ebdc9d4` (the `docs/security/` folder used to host them).
The reports are accessible only through `git log` / `git show`:

```bash
git log --oneline -- docs/security/                   # list the reports' history
git show ebdc9d4^:docs/security/2026-05-14-dependabot-remediation-report.md
git show ebdc9d4^:docs/security/2026-05-06-dependabot-remediation-report.md
```

- 2026-05-14 report — 77 alerts triaged, 62 phantom, 15 actionable
- 2026-05-06 report — 102 alerts triaged, Phases 1.1/1.2/1.3 landed
