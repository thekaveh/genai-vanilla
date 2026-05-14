# services/comfyui — ComfyUI image-generation family

Two containers, four named volumes.

## Containers

| Container | Role | Image var |
|---|---|---|
| `comfyui` | ComfyUI server (port `COMFYUI_PORT`, internal `18188`) | `COMFYUI_IMAGE` |
| `comfyui-init` | One-shot init — downloads ComfyUI models declared via env vars, installs custom nodes | `COMFYUI_INIT_IMAGE` (alpine) |

## Subfolders

- `init/scripts/` — bind-mounted into `comfyui-init` at `/scripts`. Entrypoint is `/scripts/download_models.sh`.

## Named volumes (4)

Models, generated output, user-uploaded input, and custom nodes are each persisted in their own volume:
- `comfyui-models` — checkpoints, VAEs, ControlNets, LoRAs (multi-GB)
- `comfyui-output` — generated images
- `comfyui-input` — user-uploaded reference images
- `comfyui-custom-nodes` — installed extension nodes

Cold-restart (`./start.sh --cold`) wipes these — re-downloads can take 10-30 minutes depending on `COMFYUI_DOWNLOAD_MODELS`.

## See also

- [`docs/services/comfyui.md`](../../docs/services/comfyui.md) — full service docs.
