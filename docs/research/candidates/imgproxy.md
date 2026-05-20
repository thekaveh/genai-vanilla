---
slug: imgproxy
name: imgproxy
type: external-service
category-fit: media
generated: 2026-05-19
upstream: https://github.com/imgproxy/imgproxy
license: MIT
referenced-by: [supabase]
---

# imgproxy

## Headline
The exact image-transformation sidecar Supabase Storage upstream is designed to talk to — resizes, re-encodes, and signs image URLs on the fly so ComfyUI outputs and user uploads can be served at multiple sizes from one source object.

## Problem it solves
Today `supabase-storage` and `minio` hold raw images (ComfyUI generations, user uploads, OpenWebUI attachments) and serve them at their original dimensions. Anything consuming them (Open WebUI thumbnails, future frontend galleries, JupyterHub previews) has to download the full file. imgproxy is the canonical companion the Supabase Storage `IMGPROXY_URL` env var was built for; turning it on unlocks transform URLs like `/render/image/resize/width/256/...` without touching the source bytes.

## Stack wiring sketch
- supabase-storage -> imgproxy via `IMGPROXY_URL=http://imgproxy:8080`
- imgproxy -> supabase-storage (or minio) over S3 for source reads
- open-webui -> kong -> imgproxy (for chat-message thumbnails)
- backend -> imgproxy (for any image-list endpoints it exposes)
- comfyui -> supabase-storage (writes original) -> imgproxy (serves derivatives)

## Effort
small — one stateless container, one env var on `supabase-storage`, one Kong route. No DB schema changes.

## Risks & open questions
- imgproxy's signing-key model needs a new secret in `.env` (`IMGPROXY_KEY`, `IMGPROXY_SALT`) — bootstrapper would need to auto-generate them.
- CPU-bound on large images; resource limits matter on small hosts.
- Format support: JPEG/PNG/WebP/AVIF out of the box; HEIC/RAW need the Pro build.

## Why now (and why not sooner)
With ComfyUI producing 1024x1024+ images and Open WebUI displaying them inline, the bandwidth cost of un-resized serving is now visible. imgproxy is also a prerequisite for any future "image gallery" or "asset browser" UI that wants snappy thumbnails.

## Upstream evidence
- https://github.com/imgproxy/imgproxy
- https://supabase.com/docs/guides/storage/serving/image-transformations
