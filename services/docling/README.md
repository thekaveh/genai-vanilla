# services/docling — IBM Docling document processor (GPU)

PDF / DOCX / HTML → structured Markdown + tables + formulas. One of the
engines behind `DOC_PROCESSOR_SOURCE` (the others are
`docling-localhost` and `disabled`).

## Containers

| Container | Role | Image var |
|---|---|---|
| `docling-gpu` | NVIDIA-accelerated Docling worker, OpenAI-compatible endpoint | `DOCLING_GPU_IMAGE` (used as `BASE_IMAGE` in `provider/gpu/Dockerfile`) |

Default for `DOC_PROCESSOR_SOURCE` is `disabled` — Docling is opt-in.

## Subfolders

- **`provider/`** — source-variant code, mirroring the `STT_PROVIDER_SOURCE`
  / `TTS_PROVIDER_SOURCE` pattern.
  - `provider/gpu/` — Dockerfile + `processor.py` + `requirements.txt` for
    the in-stack GPU container.
  - `provider/localhost/` — host-install path (user runs Docling directly
    on macOS / Linux without Docker). README, `processor.py`, `models.py`,
    `server.py`, `uv.lock`, `pyproject.toml`.
  - `provider/shared/` — code reused by both provider variants
    (`api_server.py`, `models.py`, `utils.py`).

## See also

- [`docs/services/doc-processor.md`](../../docs/services/doc-processor.md) — full Doc-Processor docs (Docling is the only engine; the doc covers the source matrix).
