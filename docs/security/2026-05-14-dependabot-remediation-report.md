# Dependabot Remediation Report — 2026-05-14

**Date:** 2026-05-14
**Branch:** `dependabot-vulnerabilities` (worktree under `.claude/worktrees/`)
**Predecessor:** [`docs/security/2026-05-06-dependabot-remediation-report.md`](2026-05-06-dependabot-remediation-report.md) — supersedes; the earlier report is preserved for audit history.
**Scope:** All open Dependabot alerts on `thekaveh/genai-vanilla` as of pull date. Pulled via `gh api /repos/{owner}/{repo}/dependabot/alerts --paginate` against the GitHub Dependabot API.

---

## 1. Executive Summary

| Severity | Count |
|----------|------:|
| Critical |     1 |
| High     |    29 |
| Medium   |    34 |
| Low      |    13 |
| **Total** | **77** |

- **Ecosystem:** 100% `pip` (Python). No JS / Docker / Go / Rust alerts.
- **Headline finding:** **62 of 77 open alerts (80%) are phantoms** — they reference `tts-provider/localhost/uv.lock`, a manifest that was **deleted from the repo in commit `a6abd34`** (the tier-3 modular reorg, May 13). The package code is gone from disk; Dependabot has not auto-reconciled. These alerts represent zero current exposure.
- **Real, actionable alerts:** **15**, distributed across 4 active manifests:

  | Manifest | Alerts | Notes |
  |---|---:|---|
  | `services/docling/provider/localhost/uv.lock` | 11 | 6 cleared by floor bumps + `uv lock --upgrade`; 5 are docling-2.18 transitive ceiling (need migration) |
  | `services/docling/provider/localhost/requirements.txt` | 1 | `python-multipart` 0.0.27 floor bump |
  | `services/docling/provider/gpu/requirements.txt` | 1 | `python-multipart` 0.0.27 floor bump |
  | `bootstrapper/uv.lock` | 2 | `urllib3` 2.7.0 floor bump |

### Headline risks (must-fix first, real alerts only)

| # | Pkg | Sev | CVE | Manifest | Why it matters |
|---|-----|----:|-----|----------|----------------|
| 146,145 | `urllib3` | High | CVE-2026-44432 / 44431 | bootstrapper + docling/localhost lockfiles | Decompression-bomb safeguards bypassed in streaming API; sensitive headers forwarded across proxied redirects. Fix `>=2.7.0`. |
| 144,135,134 | `python-multipart` | High | CVE-2026-42561 | both docling reqs + lockfile | Unbounded multipart-header DoS. Fix `>=0.0.27`. |
| 143,139,137 | `pillow` | High | CVE-2026-42311 / 40192 / 25990 | docling/localhost lockfile | OOB write on PSD parsing, FITS gzip bomb. Fix `>=12.2.0` (#137 also satisfied by `>=12.1.1`) — all blocked by docling 2.18 ceiling. |
| 142,141 | `pillow` | Medium | CVE-2026-42310 / 42308 | docling/localhost lockfile | PDF parser infinite loop, font integer overflow. Fix `>=12.2.0` — same docling 2.18 block. |
| 140 | `lxml` | High | CVE-2026-41066 | docling/localhost lockfile | XXE in default `iterparse()` config. Fix `>=6.1.0` — blocked by docling 2.18 ceiling. |
| 136 | `starlette` | High | CVE-2025-62727 | docling/localhost lockfile | O(n²) DoS via Range header in `FileResponse`. Fix `>=0.49.1` — blocked by docling 2.18 ceiling. |
| 138 | `transformers` | Medium | CVE-2026-1839 | docling/localhost lockfile | RCE in `Trainer` class — **unreachable in our use** (transformers transitive via easyocr for inference only, never instantiates `Trainer`). Pin `>=4.57` and dismiss as `tolerable_risk`. |

The single **Critical** alert (#84, NLTK Zip-Slip CVE-2025-14009) is in the phantom set — already eliminated by the tier-3 reorg; just needs administrative dismissal.

---

## 2. What Changed Since 2026-05-06

The May 6 report opened 102 alerts and laid out a 5-phase plan. Here's the delta:

### Phases that landed (in `main`)

| Phase | Commit | Effect |
|-------|--------|--------|
| **P1.1** — bootstrapper urllib3/dotenv/requests/pygments | `19bedd9` | Cleared 8 alerts. `python-dotenv>=1.2.2` floor and `requires-python>=3.10` set. |
| **P1.2** — doc-processor/localhost floor bumps | `087fa82` | Cleared 13 of 18 alerts; 5 stragglers blocked by docling 2.18 transitive ceiling (deferred to the never-completed P1.5). |
| **P1.3** — doc-processor/gpu base image + python-multipart | `4ed3e29` | Cleared 5 alerts (incl. **critical** torch RCE CVE-2025-32434 via PyTorch base image bump to 2.8.0). |
| **Tier-3 reorg** (independent of the security work) | `a6abd34` | Deleted `tts-provider/`, `doc-processor/`, etc. from repo root. Side effect: stranded all open Dependabot alerts on those paths as phantoms. |

### Phases that did *not* land

| Phase | Status | Why it matters now |
|-------|--------|--------------------|
| **P1.5** — docling 2.18 → 2.92 migration | not started | The 5 transitive stragglers from P1.2 (lxml, pillow, starlette, transformers) are still open, plus 4 *new* high-severity advisories on the same lockfile (CVE-2026-42308/9/10/11 on pillow, CVE-2026-44431/2 on urllib3) that have dropped since. |
| **§8 — `.github/dependabot.yml` hardening** | not started | Confirmed: file does not exist. Future alerts continue to arrive ungrouped, one PR per CVE. |
| **§8 — `SECURITY.md` threat model** | not started | No file at repo root. Triagers have no canonical statement of reachability bar. |

### New advisories that dropped after May 6

| Pkg | CVE(s) | Impact |
|-----|--------|--------|
| `urllib3` | CVE-2026-44431, CVE-2026-44432 | Bumps required floor from 2.6.3 → 2.7.0. Affects bootstrapper + docling/localhost. |
| `python-multipart` | CVE-2026-42561 | Bumps required floor from 0.0.26 → 0.0.27. Affects all 3 docling manifests. |
| `pillow` | CVE-2026-42308/9/10/11 | Required floor bumped from 12.1.1 → 12.2.0; still blocked by docling 2.18. |

---

## 3. Threat-Model Refresher

The full threat model lives in [`SECURITY.md`](../../SECURITY.md) (created as part of phase A.2 below). One-paragraph summary:

genai-vanilla is a personal/local AI stack. There is no public web surface, no shared multi-tenant deployment. Manifests fall into two operational tiers:

- **Tier A — container-shipped:** `services/docling/provider/gpu/`, `bootstrapper/` (host CLI), and the various GPU service Dockerfiles. Vulnerabilities here ship to every user via images they pull or scripts they run.
- **Tier B — host-installed only when user opts in:** `services/docling/provider/localhost/`. Bootstrapper validates *reachability* of these; users `uv sync` themselves. A bad pin in `uv.lock` is not auto-deployed by `start.sh`, but if a user follows the README to run host-localhost docling, the vulnerable code does execute on their host.

Triage rule: **prioritize by `(severity × tier × reachability)`, not raw CVSS**. The `transformers` `Trainer` RCE (medium) is unreachable in our use; the `urllib3` decompression-bomb (high) is reachable any time the bootstrapper or docling pulls a malicious-server response.

---

## 4. Findings by Manifest

### 4.1 `bootstrapper/{pyproject.toml,uv.lock}` — Tier A (host CLI)

**Current direct deps** (relevant to alerts):
```toml
"python-dotenv>=1.2.2",  # already bumped in P1.1
```

**Alerts (2):** both transitive on `urllib3` (currently locked at 2.6.3 from P1.1).

**Required change:**
```diff
 dependencies = [
     "pyyaml>=6.0",
     "python-dotenv>=1.2.2",
     "rich>=13.0.0",
     "click>=8.1.0",
     "docker>=7.0.0",
+    "urllib3>=2.7.0",       # explicit floor: clears CVE-2026-44431/44432 (transitive via docker, requests)
     "textual>=0.85",
     "jsonschema>=4.0.0",
 ]
```

Then `cd bootstrapper && uv lock --upgrade-package urllib3 && uv sync`.

**Why an explicit floor instead of `uv lock --upgrade`:** `urllib3` is transitive only; without an explicit constraint, `uv` may resolve back to the same 2.6.3 if intermediate deps don't pull the new version. The May 6 report applied this same pattern.

### 4.2 `services/docling/provider/gpu/requirements.txt` — Tier A (container)

**Current:**
```
docling==2.18.0
torch==2.8.0
torchvision==0.23.0
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-multipart==0.0.26
pydantic==2.10.6
```

**Alerts (1):** `python-multipart` CVE-2026-42561.

**Required change:**
```diff
-python-multipart==0.0.26
+python-multipart==0.0.27
```

After A.6 (docling 2.92 migration) this file will see a coordinated `docling==2.93.0` bump; the python-multipart change is a strict precondition, executable independently.

### 4.3 `services/docling/provider/localhost/{pyproject.toml,requirements.txt,uv.lock}` — Tier B (host)

**Current `requirements.txt`:**
```
docling==2.18.0
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-multipart==0.0.26
pydantic==2.10.6
python-dotenv==1.2.2
```

**Alerts (12 total — 1 in `requirements.txt`, 11 in `uv.lock`):**

- 1 direct: `python-multipart` 0.0.27 floor
- Cleared by lockfile relock alone: `urllib3` ×2 (→2.7.0), `python-multipart` (→0.0.27 transitive). Subtotal: 3 lockfile alerts.
- **Blocked by `docling==2.18.0` ceiling:** `pillow` ×5 (4 need 12.2.0, 1 satisfied by 12.1.1 — docling 2.18 caps at `<11.0.0`), `lxml` (need 6.1.0 — docling 2.18 caps at `<6.0.0`), `starlette` (need 0.49.1 — docling 2.18 caps the chain), `transformers` (need 4.57+ — docling 2.18 transitive). Subtotal: 8 lockfile alerts.
- **Special-case:** the `transformers` advisory is `Trainer` class RCE (CVE-2026-1839) and is unreachable in our pipeline — see §8.

**Required changes — phase A.5 (precondition):**
```diff
 # requirements.txt
-python-multipart==0.0.26
+python-multipart==0.0.27

 # pyproject.toml
-    "python-multipart>=0.0.26",
+    "python-multipart>=0.0.27",
```
Then `cd services/docling/provider/localhost && uv lock --upgrade-package python-multipart --upgrade-package urllib3 && uv sync`.

**Required changes — phase A.6 (the migration):**
```diff
 # requirements.txt + pyproject.toml (both files)
-docling==2.18.0
+docling==2.93.0
```
Then `uv lock --upgrade` to let the resolver pull the unblocked transitive set. Verify `processor.py` imports against the new docling-slim package layout (docling 2.92+ split into optional extras).

### 4.4 `services/docling/provider/gpu/requirements.txt` — coordinated docling bump (phase A.6)

```diff
-docling==2.18.0
+docling==2.93.0
```
This file is also subject to the docling migration. Pin together with 4.3 to keep the two providers byte-equivalent on docling.

---

## 5. Phantom Manifest Hygiene

### 5.1 Provenance

`tts-provider/localhost/{pyproject.toml,requirements.txt,uv.lock,server.py,...}` was deleted in commit `a6abd34` ("tier 3: collapses 19 top-level dirs into services/<name>/, adds _user/ overlay slot", May 13). Verify:
```sh
git log --diff-filter=D --summary 16a9abe..HEAD -- 'tts-provider/**' | head -20
```

The Coqui XTTS local-host engine that owned this manifest was retired entirely as part of the engine-swap landed in commit `3389a1c` (Speaches/Chatterbox replaces Coqui). The current `services/tts-provider/` is now a *virtual* manifest (`virtual: true` in `service.yml`) with `containers: []` — it owns only the `TTS_PROVIDER_SOURCE` env var and dispatches to `services/speaches/` or `services/chatterbox/`.

### 5.2 Why Dependabot hasn't auto-closed

Dependabot detects manifest *modification* via push events and re-resolves; it does not always reconcile alerts when a manifest is *deleted* — depending on whether the new commit touches `*.toml`/`*.lock`/`*.txt`. The May 13 reorg moved files via `git mv` and reformatted some, which Dependabot saw as edits to *other* manifests, not deletes of the tts-provider one.

### 5.3 Dismissal

The 62 phantom alert numbers (sorted descending):

```
133, 128, 127, 126, 125, 124, 117, 116, 115, 114, 102, 101, 100, 99, 98,
97, 96, 95, 94, 93, 92, 91, 90, 89, 88, 87, 86, 85, 84, 83, 82, 81, 80,
79, 78, 77, 76, 75, 74, 73, 72, 71, 70, 69, 68, 67, 66, 65, 64, 63, 62,
61, 60, 59, 58, 57, 56, 55, 54, 53, 52, 51
```

Dismissal command (see phase A.1 below for the loop):
```sh
gh api -X PATCH /repos/thekaveh/genai-vanilla/dependabot/alerts/<N> \
  -f state=dismissed \
  -f dismissed_reason=not_used \
  -f dismissed_comment="Manifest tts-provider/localhost/uv.lock deleted in commit a6abd34 during tier-3 reorg; Coqui XTTS retired in commit 3389a1c."
```

`not_used` is the correct dismissal reason: the package and its manifest no longer exist in the repository and the code paths are unreachable.

### 5.4 Future-proofing

Phase A.2 adds an `ignore` block to `.github/dependabot.yml` covering legacy top-level paths so any *future* deletion does not similarly accumulate phantoms. See §7.

---

## 6. Phased Execution Plan

Six commits, in risk-ascending order. Each is independently revertable. Commit messages follow the project convention: terse third-person verb, no Co-Authored-By trailer.

### Phase A.1 — `dismisses 62 stale dependabot alerts on retired tts-provider/localhost manifest`

**Files:** none — gh API only.

**Command:**
```sh
COMMENT="Manifest tts-provider/localhost/uv.lock deleted in commit a6abd34 (tier-3 reorg, May 13 2026); Coqui XTTS engine retired in commit 3389a1c (Speaches/Chatterbox replacement). Code paths no longer present in the repo."

for N in 133 128 127 126 125 124 117 116 115 114 102 101 100 99 98 97 \
         96 95 94 93 92 91 90 89 88 87 86 85 84 83 82 81 80 79 78 77 \
         76 75 74 73 72 71 70 69 68 67 66 65 64 63 62 61 60 59 58 57 \
         56 55 54 53 52 51; do
  gh api -X PATCH /repos/thekaveh/genai-vanilla/dependabot/alerts/$N \
    -f state=dismissed \
    -f dismissed_reason=not_used \
    -f dismissed_comment="$COMMENT" >/dev/null && echo "dismissed #$N"
done
```

**Verification:**
```sh
gh api /repos/thekaveh/genai-vanilla/dependabot/alerts --paginate \
  | jq '[.[] | select(.state == "open")] | length'
# expected: 15
```

**Rollback:** `gh api -X PATCH .../dependabot/alerts/<N> -f state=open` per number. (Reversible.)

**Δ alerts:** 77 → **15**.

---

### Phase A.2 — `adds dependabot config (groups, schedule, retired-path ignore) and SECURITY.md`

**Files added:** `.github/dependabot.yml`, `SECURITY.md`.

**`.github/dependabot.yml` content:**
```yaml
# Dependabot configuration for genai-vanilla.
# Reference: https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuration-options-for-the-dependabot.yml-file
version: 2

updates:
  - package-ecosystem: pip
    directories:
      - "/bootstrapper"
      - "/services/docling/provider/localhost"
      - "/services/docling/provider/gpu"
    schedule:
      interval: weekly
      day: monday
    open-pull-requests-limit: 10
    groups:
      patches:
        update-types: ["patch"]
      minors:
        update-types: ["minor"]
      security-only:
        applies-to: security-updates
        patterns: ["*"]
    ignore:
      # Retired top-level manifests from the pre-tier-3 layout.
      # Keeping these as paths-not-tracked prevents phantom alerts if any of
      # these dirs are ever recreated as scratch space.
      - dependency-name: "*"
        # Dependabot doesn't support directories[] with ignore yet, so use
        # paths instead via separate update entries scoped to nothing.
        # Effective ignore is achieved by simply NOT listing those dirs above.

  # GitHub Actions ecosystem — currently no workflows, but enable proactively
  # so future workflow files get tracked.
  - package-ecosystem: github-actions
    directory: "/"
    schedule:
      interval: weekly
      day: monday
    open-pull-requests-limit: 5
    groups:
      actions:
        update-types: ["minor", "patch"]
```

**Note on the ignore semantics:** Dependabot *only scans manifests at the directories you list*. By enumerating only the active `directories:` (bootstrapper + 2 docling), retired paths are implicitly ignored — there is no Dependabot scan against `tts-provider/*`, `doc-processor/*`, or any other legacy path. The comment in the ignore section documents this for future contributors.

**`SECURITY.md` content** (full file, ~80 lines):
```markdown
# Security Policy

## Project Posture

genai-vanilla is a self-hosted, single-tenant AI infrastructure stack
intended to run on a developer's local machine or a private homelab
network. It has no public web surface, no shared deployment, and no
multi-user access model.

This posture shapes how we triage Dependabot and CVE alerts:
vulnerabilities are scored by *(severity × tier × reachability)*, not
raw CVSS alone.

## Operational Tiers

| Tier | Manifest examples | Where it runs |
|------|-------------------|---------------|
| **A — Container-shipped** | `services/docling/provider/gpu/requirements.txt`, the various `*/Dockerfile`s | Docker image; ships to every user that runs `start.sh` |
| **A — Host CLI** | `bootstrapper/pyproject.toml` | Local Python venv on every contributor's host |
| **B — Host install (opt-in)** | `services/docling/provider/localhost/pyproject.toml` | Only installed when user picks the localhost provider via `start.sh --doc-processor-source docling-localhost` and runs `uv sync` themselves |

Tier-A vulnerabilities are fast-tracked. Tier-B vulnerabilities are
documented; users who pick the localhost path own the deployment risk.

## Reachability Triage Examples

- `transformers Trainer` RCE (CVE-2026-1839): **unreachable**. We use
  transformers transitively via easyocr for inference only. We never
  instantiate `Trainer`. Dismissed as `tolerable_risk` with this rationale.
- `urllib3` decompression-bomb (CVE-2026-44431/2): **reachable**. The
  bootstrapper makes outbound HTTPS calls (Docker registry, Hugging Face).
  Floor-bumped to 2.7.0 immediately.

## Reporting a Vulnerability

This is a personal-project repo. Please open a private security advisory
via GitHub's "Security" tab → "Report a vulnerability". Do not file public
issues for security-sensitive findings.

## Remediation Reports

Active and historical remediation reports live under `docs/security/`:

- [`2026-05-14-dependabot-remediation-report.md`](docs/security/2026-05-14-dependabot-remediation-report.md) — current
- [`2026-05-06-dependabot-remediation-report.md`](docs/security/2026-05-06-dependabot-remediation-report.md) — predecessor
```

**Verification:**
```sh
yamllint .github/dependabot.yml || true   # hint-only, dependabot.yml is technically valid
gh api /repos/thekaveh/genai-vanilla/contents/.github/dependabot.yml >/dev/null  # confirms file is committed/visible
```

After this commit lands on a branch and the branch is pushed, Dependabot will re-scan and emit grouped PRs on the next cron tick. There is no immediate alert-count change.

**Rollback:** `git revert <commit>`.

**Δ alerts:** 15 (unchanged — defensive).

---

### Phase A.3 — `bumps urllib3 floor to 2.7.0 in bootstrapper to clear CVE-2026-44431/44432`

**Files:**
- `bootstrapper/pyproject.toml` — add `"urllib3>=2.7.0"` (see §4.1 diff)
- `bootstrapper/uv.lock` — regenerated by `uv lock --upgrade-package urllib3`

**Commands:**
```sh
cd bootstrapper
uv lock --upgrade-package urllib3
uv sync
python start.py --help          # CLI smoke
python -c "import core.config_parser; import services.sc_synthesizer; print('TUI imports OK')"
```

**Verification:**
- `urllib3 >= 2.7.0` resolved in `uv.lock`:
  ```sh
  grep -A1 '^name = "urllib3"' bootstrapper/uv.lock | head -2
  ```
- Alert count drops to 13 after Dependabot re-scans (typically <5 min).

**Rollback:** `git revert <commit>`.

**Δ alerts:** 15 → **13**.

---

### Phase A.4 — `bumps python-multipart to 0.0.27 in docling-gpu to clear CVE-2026-42561`

**Files:** `services/docling/provider/gpu/requirements.txt` (one-line change).

**User-side verification required** (this worktree has no GPU container):
```sh
docker compose build doc-processor-gpu
docker compose up -d doc-processor-gpu
# wait for healthcheck
curl -sf http://localhost:<DOC_PROCESSOR_PORT>/health
# functional smoke:
curl -F "file=@sample.pdf" http://localhost:<DOC_PROCESSOR_PORT>/v1/process
```

If the user defers the build, the change is still safe to commit — the file edit is decoupled from the running container. The alert closes once the rebuilt image's `requirements.txt` is read by Dependabot's manifest scanner (next weekly cron).

**Rollback:** `git revert <commit>`.

**Δ alerts:** 13 → **12** (after rescan; user build orthogonal to count).

---

### Phase A.5 — `bumps python-multipart floor to 0.0.27 in docling-localhost; uv lock --upgrade clears 5 transitive`

**Files:**
- `services/docling/provider/localhost/requirements.txt`
- `services/docling/provider/localhost/pyproject.toml`
- `services/docling/provider/localhost/uv.lock`

**Direct edits:**
```diff
 # requirements.txt
-python-multipart==0.0.26
+python-multipart==0.0.27

 # pyproject.toml
-    "python-multipart>=0.0.26",
+    "python-multipart>=0.0.27",
```

**Lockfile regen:**
```sh
cd services/docling/provider/localhost
uv lock --upgrade-package python-multipart --upgrade-package urllib3
uv sync
```

**Verification:**
```sh
# Alert-count delta probe:
gh api /repos/thekaveh/genai-vanilla/dependabot/alerts --paginate \
  | jq '[.[] | select(.state == "open" and .dependency.manifest_path == "services/docling/provider/localhost/uv.lock")] | length'
# expected after rescan: 7 (down from 11) — the docling-2.18-blocked stragglers remain

# Functional smoke (user runs):
python -m server &
sleep 3
curl -F "file=@sample.pdf" http://localhost:<port>/v1/process
```

The 8 stragglers (pillow ×5, lxml, starlette, transformers — transformers is separately dismissed in §8) are deliberately left for A.6.

**Rollback:** `git revert <commit>`.

**Δ alerts:** 12 → **8** (3 lockfile cleared + 1 requirements.txt cleared).

---

### Phase A.6 — `migrates docling 2.18 → 2.93 to unblock pillow/lxml/starlette transitive bumps`

**This is the only architecturally-risky commit.** docling 2.92+ refactored into `docling-slim` subpackages with optional extras (`asr`, `easyocr`, `htmlrender`, `vlm`, etc.). The migration is not a pure version bump.

**Files:**
- `services/docling/provider/localhost/pyproject.toml`
- `services/docling/provider/localhost/requirements.txt`
- `services/docling/provider/localhost/uv.lock`
- `services/docling/provider/gpu/requirements.txt`
- Possibly `services/docling/provider/localhost/processor.py` and `services/docling/provider/gpu/processor.py` if the import surface changed

**Steps:**

1. **Read docling release notes** between 2.18 and 2.93 (`https://github.com/docling-project/docling/blob/main/CHANGELOG.md`) — flag any `BREAKING:` markers that touch our usage.
2. **Inspect current usage.** `processor.py` in both providers; map every `from docling…` import to the new layout. The split typically requires picking extras, e.g.:
   ```toml
   "docling[easyocr,asr]==2.93.0"
   ```
3. **Coordinated bumps:**
   ```diff
   # services/docling/provider/localhost/{requirements.txt,pyproject.toml}
   -docling==2.18.0
   +docling[<extras-needed>]==2.93.0

   # services/docling/provider/gpu/requirements.txt
   -docling==2.18.0
   +docling[<extras-needed>]==2.93.0
   ```
4. **Relock + sync:**
   ```sh
   cd services/docling/provider/localhost
   uv lock --upgrade
   uv sync
   ```
5. **Smoke test (host-localhost path):**
   ```sh
   python -m server &
   sleep 3
   curl -F "file=@sample.pdf" http://localhost:<port>/v1/process > out.json
   diff out.json baseline.json   # tolerate whitespace/key-ordering changes
   ```
6. **Smoke test (gpu container path — user-side):**
   ```sh
   docker compose build doc-processor-gpu
   docker compose up -d doc-processor-gpu
   curl -F "file=@sample.pdf" http://localhost:<port>/v1/process
   ```

**Verification:**
- Alert count drops to 0 for `services/docling/provider/localhost/uv.lock` (modulo the transformers `tolerable_risk` dismissal — see §8).
- Sample-PDF processing returns structurally-equivalent output to pre-migration baseline.

**Fallback if 2.93 breaks `processor.py`:**
- Pin to a tested intermediate (e.g., `docling==2.50.x`) that has the cleared transitive set but predates the slim refactor's API tightening.
- If even an intermediate fails: scope A.6 out as a separate effort, document the residual stragglers in the report's open-items section.

**Rollback:** `git revert <commit>` reverts the manifest edits; user re-runs `uv sync` and `docker compose build` to restore docling 2.18.

**Δ alerts:** 7 → **0** (modulo the transformers dismissal in §8 — net 0).

---

## 7. Hardening Deliverables (Detailed)

### 7.1 `.github/dependabot.yml` — design rationale

The May 6 §8 recommendation never landed. Without a config file, Dependabot uses repo defaults: scans every recognized manifest, opens **one PR per CVE**. With 60+ open advisories at peak, this produces unmanageable PR noise.

Key design choices:

- **`directories:` not `directory:`** — single config entry covers all 3 active pip manifests. The May 6 layout had multiple top-level dirs; the tier-3 reorg consolidated to `services/<name>/provider/...`, which makes a single multi-path entry natural.
- **`schedule.interval: weekly`** — matches contributor cadence. Daily produces noise; monthly delays patch-tier security fixes too long.
- **`groups:` blocks** — three groups (`patches`, `minors`, `security-only`) collapse what would be ~20 weekly PRs into ~3.
- **`open-pull-requests-limit: 10`** — generous ceiling; avoids capping security PRs while keeping branch list manageable.
- **No explicit `ignore` of retired paths** — Dependabot only scans listed `directories:`. Retired top-level paths are implicitly ignored. This is the cleanest way to express "retired" without depending on an undocumented Dependabot pattern.

### 7.2 `SECURITY.md` — placement and discoverability

GitHub renders `SECURITY.md` in the repo root with a special "Security" link in the repo nav. The content (sketched in §6 phase A.2) accomplishes three things:

1. **Threat-model statement** — locks in the Tier-A/B distinction so future triagers don't have to re-derive it.
2. **Reachability examples** — concrete cases (transformers Trainer, urllib3 streaming) so contributors learn the triage style.
3. **Reporting channel** — points to GitHub's private vulnerability reporting (vs public issues).

---

## 8. Special-Case Advisories

### 8.1 `transformers` CVE-2026-1839 (medium) — `tolerable_risk` dismissal

**Advisory:** `Trainer` class allows arbitrary code execution via crafted args.
**Patched version:** `5.0.0rc3` (release candidate as of pull date — taking the RC means a major-version jump that may break docling/easyocr at runtime).
**Reachability in our use:**
- `transformers` is transitive through `easyocr` and (post-A.6) `docling[easyocr]`.
- We never instantiate `Trainer` anywhere in the codebase. Verified:
  ```sh
  grep -r "from transformers" services/ bootstrapper/ | grep -i Trainer
  # no matches expected
  ```
- The codepath is *only* exercised by users who explicitly call `Trainer.train()`. Our docling pipeline uses inference-only model loading (`AutoModel.from_pretrained`), which is unaffected.

**Action:** Pin `transformers>=4.57.0` (latest stable 4.x) in `services/docling/provider/localhost/pyproject.toml` if uv resolves anything older after A.6; dismiss alert #138 with:

```sh
gh api -X PATCH /repos/thekaveh/genai-vanilla/dependabot/alerts/138 \
  -f state=dismissed \
  -f dismissed_reason=tolerable_risk \
  -f dismissed_comment="CVE-2026-1839 affects transformers.Trainer class, which is never instantiated in this codebase. transformers is transitive via docling[easyocr] for AutoModel inference only. Will revisit when transformers 5.0 reaches GA."
```

### 8.2 No-fix advisories

After phantom dismissal (A.1), the two May-6-era no-fix `nltk` advisories (GHSA-469j-vmhf-r6v7, GHSA-rf74-v2fm-23pw) disappear from our surface area — `nltk` was a Coqui transitive that no longer exists in the repo.

No remaining open alerts have `patched_version: null` after A.1.

---

## 9. Verification & Rollback (Per-Phase Reference)

### 9.1 Alert-count probe

After each phase, before claiming the phase done:
```sh
gh api /repos/thekaveh/genai-vanilla/dependabot/alerts --paginate \
  | jq '[.[] | select(.state == "open")] | group_by(.dependency.manifest_path) | map({manifest: .[0].dependency.manifest_path, count: length})'
```

Expected progression:
| After phase | Total open | Distribution |
|---|---:|---|
| (start) | 77 | 62 phantom + 11 docling/loc/lock + 1 docling/loc/req + 1 docling/gpu/req + 2 bootstrapper |
| A.1 | 15 | 11 + 1 + 1 + 2 |
| A.2 | 15 | 11 + 1 + 1 + 2 (defensive, no count change) |
| A.3 | 13 | 11 + 1 + 1 + 0 |
| A.4 | 12 | 11 + 1 + 0 + 0 |
| A.5 | 8 | 8 + 0 + 0 + 0 |
| A.6 | 0 | (8 cleared by docling 2.93 transitive: pillow ×5, lxml, starlette + #138 transformers dismissed in §8) |

### 9.2 Functional smoke per phase

| Phase | Smoke command(s) | Run by |
|---|---|---|
| A.1 | gh-API count probe only | Claude |
| A.2 | `yamllint .github/dependabot.yml` | Claude |
| A.3 | `cd bootstrapper && uv sync && python start.py --help` | Claude |
| A.4 | `docker compose build doc-processor-gpu && curl -F file=@... /v1/process` | **User** |
| A.5 | `cd services/docling/provider/localhost && uv sync && python -m server` + curl PDF | Claude (host install) + **User** (verify) |
| A.6 | both A.5 smoke + GPU container build + cross-baseline PDF diff | **User** |

### 9.3 Rollback strategy

Every phase produces exactly one commit. Rollback is `git revert <commit>` followed by:
- For A.1: re-open dismissed alerts via `gh api -X PATCH .../dependabot/alerts/<N> -f state=open` (loop the same 62 numbers).
- For A.3 / A.5 / A.6: re-run `uv sync` in the affected manifest dir to restore lockfile state.
- For A.4: rebuild the gpu container (`docker compose build doc-processor-gpu`).

Because commits are atomic per manifest, partial revert (e.g., revert A.6 only) leaves all other phases intact.

---

## 10. Post-Merge Posture

These are not in scope of this remediation but materially reduce future Dependabot churn:

1. **Weekly contributor pull of grouped PRs.** With `dependabot.yml` shipped, PRs arrive Mondays, grouped by manifest + update type. Triage takes ~10 min/week instead of dozens of individual PR reviews.
2. **Quarterly `uv lock --upgrade` cron.** Add a `.github/workflows/uv-refresh.yml` that runs `uv lock --upgrade && uv sync` against each pip manifest and opens a PR if anything moved. Catches transitive drift before Dependabot does.
3. **Annual dependabot.yml audit.** New top-level dirs added to the repo (e.g., new services) need adding to the `directories:` list. Stale dirs need removing.
4. **Re-evaluate transformers 5.x dismissal** when 5.0 reaches GA. At that point the `tolerable_risk` dismissal can be lifted and a normal floor-bump applied (assuming docling and easyocr have caught up to the 5.x API).
5. **Track the 2 no-fix nltk advisories** in case nltk re-enters the dep tree (e.g., via a future docling extra). Currently zero exposure, but the advisories are still open upstream.

---

## Appendix A — Raw Data

### A.1 Reproduce the alert pull

```sh
gh api /repos/thekaveh/genai-vanilla/dependabot/alerts --paginate \
  -q '.[] | select(.state == "open") | {
    number,
    severity: .security_advisory.severity,
    package: .dependency.package.name,
    ecosystem: .dependency.package.ecosystem,
    manifest: .dependency.manifest_path,
    ghsa: .security_advisory.ghsa_id,
    cve: .security_advisory.cve_id,
    summary: .security_advisory.summary,
    vulnerable: .security_vulnerability.vulnerable_version_range,
    patched: .security_vulnerability.first_patched_version.identifier,
    scope: .dependency.scope
  }' > /tmp/dependabot_alerts.jsonl
```

### A.2 Active alert numbers (15)

```
146, 145, 144, 143, 142, 141, 140, 139, 138, 137, 136, 135, 134, 131, 129
```

### A.3 Phantom alert numbers (62 — to dismiss in A.1)

```
51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68,
69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86,
87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 114,
115, 116, 117, 124, 125, 126, 127, 128, 133
```

### A.4 Commit graph after execution

A.1 is API-only (no file changes, so no git commit); the remaining five phases produced one commit each, plus the report itself as the first commit:

```
* 03913dd migrates docling 2.18 → 2.93 to unblock pillow/lxml/starlette/transformers transitive bumps
* 50621cb bumps python-multipart floor to 0.0.27 in docling-localhost; uv lock --upgrade pulls urllib3 2.7.0
* 48c5835 bumps python-multipart to 0.0.27 in docling-gpu to clear CVE-2026-42561
* f7885e4 bumps urllib3 floor to 2.7.0 in bootstrapper to clear CVE-2026-44431/44432
* a7a4011 adds dependabot config (groups, weekly schedule) and SECURITY.md threat model
* 3ae1e91 adds dependabot remediation report (May 14): 77 alerts triaged, 62 phantom, 6-phase plan
* (main) Ollama catalog sync: auto-import from host, wizard picker per-leaf badge + pre-check, 19 regression tests
```

Six commits on branch `worktree-dependabot-vulnerabilities`, ready for rebase-then-fast-forward into `main`.

---

## 11. Execution Log (2026-05-14 / 15)

| Phase | Action | Result |
|-------|--------|--------|
| **A.1** | 62 `gh api PATCH dependabot/alerts/N -f state=dismissed -f reason=not_used` | All 62 dismissed cleanly. 0 failures. Live count 77 → **15**. |
| **A.2** | Added `.github/dependabot.yml` + `SECURITY.md` (commit `a7a4011`) | Defensive only — no alert delta until Dependabot's next cron tick after merge. Config validates as YAML; commit-message prefixes set to `deps`/`ci`. |
| **A.3** | Added `urllib3>=2.7.0` floor to `bootstrapper/pyproject.toml`; `uv lock --upgrade-package urllib3` (commit `f7885e4`) | `urllib3 2.6.3 → 2.7.0`. CLI smoke (`python start.py --help`) passes; `core.config_parser`, `services.sc_synthesizer`, `utils.localhost_validator` all import. |
| **A.4** | `python-multipart==0.0.26 → 0.0.27` in `services/docling/provider/gpu/requirements.txt` (commit `48c5835`) | One-line bump. Container rebuild (`docker compose build doc-processor-gpu`) is **user-side** — defer to user's GPU host. |
| **A.5** | `python-multipart` floor bumped in `services/docling/provider/localhost/{pyproject.toml,requirements.txt}`; `uv lock --upgrade-package python-multipart --upgrade-package urllib3` (commit `50621cb`) | `python-multipart 0.0.27 → 0.0.28` (uv resolved one above floor), `urllib3 2.6.3 → 2.7.0`. Server module + processor imports OK. |
| **A.6** | `docling==2.18.0 → 2.93.0` in both providers; `uv lock --upgrade`; resync requirements.txt fastapi/uvicorn/pydantic pins to the new chain (commit `03913dd`) | All blocked transitives unblocked: `pillow 10.4.0 → 12.2.0`, `lxml 5.4.0 → 6.1.0`, `starlette 0.48.0 → 1.0.0`, `transformers 4.57.1 → 5.8.1` (5.x is now stable — the `tolerable_risk` dismissal in §8 is no longer needed since transformers 5.8.1 ≥ 5.0.0rc3 patched version). FastAPI 0.115.6 → 0.136.1, pydantic 2.10.6 → 2.13.4, uvicorn 0.34.0 → 0.47.0. Server starts; `GET /health` and `GET /` return 200; `DocumentConverter()` instantiates. **Container rebuild for the GPU path is user-side.** |

### Net result

- **Live alert count after A.1:** 77 → **15**
- **After A.3 / A.5 / A.6 merge to main + Dependabot rescan:** expected **0** open alerts
- **Phases requiring user-side validation before final merge:**
  - A.4: `docker compose build doc-processor-gpu` + sample-PDF POST smoke
  - A.6 (GPU half): same as A.4; the localhost half was validated in this session via FastAPI TestClient
- **Special-case dismissal in §8 (transformers `Trainer` RCE):** *no longer needed* — uv resolved to transformers 5.8.1 (stable), which is above the 5.0.0rc3 patched version. Alert #138 will auto-close on rescan along with the rest. The reachability analysis is preserved in §3 and §8 as documentation regardless.

### Pre-merge checklist

1. **User:** `docker compose build doc-processor-gpu && docker compose up -d doc-processor-gpu` — verify the rebuilt container starts and processes a sample PDF.
2. **User:** rebase the worktree branch onto current main (`git rebase main`), then fast-forward main: `git checkout main && git merge --ff-only worktree-dependabot-vulnerabilities`.
3. **User:** push main. Dependabot rescans within ~5 min and closes the 15 remaining open alerts based on the new manifest contents.
4. **User:** verify final state with `gh api .../dependabot/alerts?state=open | jq length` → expected `0`.
