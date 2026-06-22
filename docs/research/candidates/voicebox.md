---
category-fit: media
generated: 2026-06-22
license: MIT
name: Voicebox (jamiepine)
referenced-by: [hermes, tts-provider, stt-provider]
slug: voicebox
type: external-service
upstream: https://github.com/jamiepine/voicebox
---

# Voicebox (jamiepine)

## Headline

A local-first AI voice studio — a Tauri (Rust) **desktop GUI app**, MIT, ~32k stars, active (v0.5.0, Apr 2026). One process bundles **7 TTS engines** (Qwen3-TTS, Qwen CustomVoice, LuxTTS, Chatterbox Multilingual, Chatterbox Turbo, HumeAI TADA, Kokoro), **Whisper STT** (incl. Turbo), a **bundled local Qwen3 LLM** for dictation refinement and per-voice personalities, global-hotkey dictation, a native REST API, and a **built-in MCP server** mounted at `/mcp` (Streamable HTTP) on `127.0.0.1:17493`.

## Problem it solves

The genuinely novel capability is **agent voice over MCP**: `voicebox.speak` lets any MCP-aware agent talk in a cloned voice, with `voicebox.transcribe`, `voicebox.list_captures`, `voicebox.list_profiles` alongside. That maps cleanly onto the stack's MCP-client tier — Hermes ("MCP-native"), LiteLLM's `mcp_servers`, Open WebUI's native MCP client, n8n's `n8n-nodes-mcp`, and OpenClaw's MCP CLI — and would be the first concrete MCP server in the ROADMAP §3.10 architecture.

Everything else is **redundant**: Voicebox bundles Chatterbox + Kokoro + Whisper, exactly the engines the stack already runs via Speaches and Chatterbox. As a TTS/STT engine it adds weight and a GUI dependency, not capability.

## Stack wiring sketch

If pursued, the realistic shape is **MCP-only** (the OpenAI-provider path is a non-starter — see Risks):

- A **virtual manifest** `services/voicebox/` owning `VOICEBOX_SOURCE` (`localhost` / `disabled`, default **disabled**) + `VOICEBOX_MCP_PORT` (17493). No container, no compose fragment — it's a host-resident endpoint, like the `tts-provider` / `cloud-providers` virtual manifests.
- When enabled, the bootstrapper auto-injects the Voicebox MCP server into every native MCP-client consumer: Hermes `config.yaml` gets an `mcp_servers.voicebox` block (`http://host.docker.internal:17493/mcp`, header `X-Voicebox-Client-Id: atlas-hermes`), with the existing `init-hermes.sh` envsubst + strip-block render path; similar registration for LiteLLM / Open WebUI / n8n / OpenClaw, each with a distinct client-id so the user can pin a voice per consumer in the Voicebox UI.
- Host reach via `extra_hosts: host.docker.internal:host-gateway`, mirroring the `*-localhost` source variants.

## Effort

**~2–4 focused days** for the Hermes-first path (new virtual manifest + 4-seam source plumbing + adaptive injection into `init-hermes.sh` + docs regen + tests). Fan-out to Open WebUI / n8n / OpenClaw is larger and more brittle because their MCP-client config is largely UI/runtime-driven rather than env-injectable. Low *engine* maintenance debt (we own no shim), but the integration is only exercisable on a developer's local machine.

## Risks & open questions

- **No OpenAI-compatible endpoint.** This is the blocker. The native API is `POST /generate` (requires a stateful `profile_id`), `POST /speak`, `POST /transcribe` (field `audio`, not OpenAI's `file`). OpenAI compat is **planned but unshipped** — `docs/plans/OPENAI_SUPPORT.md` is marked "Status: Planned for v0.2.0," tracked in **issue #10 (still open)**, with **no `backend/openai_compat.py` in `main` despite the project being at v0.5.0** — it slipped three minor versions. Without it, Voicebox cannot serve the stack's OpenAI-protocol voice consumers (Open WebUI mic/speak buttons via `AUDIO_*_OPENAI_API_BASE_URL`, backend `/synthesize`+`/transcribe`, JupyterHub helpers), all of which would go dark if Voicebox were the chosen source.
- **Host desktop app, single-machine only.** `voicebox.speak` plays audio on the host's physical speakers with an on-screen pill. It is meaningless on a remote/headless server — so the integration is inherently local-dev-only and must default to disabled.
- **Redundancy + statefulness.** Engines overlap with Speaches/Chatterbox; TTS requires pre-created voice profiles living in the app's SQLite, awkward for a stateless provider model.

## Recommendation

**Shelve — re-evaluate when issue #10 (OpenAI compatibility) ships.** At that point a `voicebox-localhost` source variant becomes feasible through the existing OpenAI-protocol layer, and the MCP auto-wiring (Hermes-first, optionally fanning out to all native MCP clients) can be designed on top. Until then it is a desktop app that duplicates engines the stack already has, with its one novel surface (agent voice over MCP) reachable only on a single local machine.

## Upstream evidence

- https://github.com/jamiepine/voicebox — MIT source (Tauri + FastAPI), v0.5.0
- https://github.com/jamiepine/voicebox/issues/10 — OpenAI API compatibility (open)
- https://docs.voicebox.sh — product + MCP server docs
- https://voicebox.sh — landing / downloads
