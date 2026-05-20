---
service: example-service
category: data
generated: 2026-05-18
generator: phase-b-hand-edit
sources_consulted:
  - https://github.com/example/example-service
  - services/example-service/service.yml
---

# example-service — Integration Research

## 1. Missing-pair integrations

- **example-service ↔ hermes**
  - Why valuable: persistent agent memory across sessions
  - Mechanism sketch: Hermes skill writing session graphs via Bolt protocol on port 7687
  - Effort: medium
  - Risks / open questions: schema design; write-amplification on tool-call loops
  - Confidence: medium

## 2. Candidate new services

- **Example Candidate** → `../candidates/example-candidate.md`
  - Headline: synthetic example one-pager paired with this row fixture
  - Other consumers in stack: backend, n8n (illustrative only)

## 3. Per-service feature gaps

- **example-service's foo-mode** — bundled but not wired through the stack
  - Why pursue: enables walkie-talkie agent UX
  - Effort: small
