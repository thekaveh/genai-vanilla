---
slug: siglip2-vectorizer
name: SigLIP 2 Vectorizer
type: external-service
category-fit: data
generated: 2026-05-19
upstream: https://github.com/weaviate/multi2vec-clip-inference
license: Apache-2.0
referenced-by: [multi2vec-clip]
---

# SigLIP 2 Vectorizer

## Headline
Swap the pinned `sentence-transformers-clip-ViT-B-32` image for a Weaviate-published SigLIP 2 multi2vec image (e.g. `multi2vec-clip-google-siglip2-base-patch16-512`) to get sharper, multilingual, higher-resolution multimodal embeddings while reusing the existing container slot.

## Problem it solves
The current CLIP ViT-B-32 model is English-only, capped at 224x224 image input, and trails newer encoders by a wide margin on retrieval benchmarks. SigLIP 2 (released 2025 by Google) handles 100+ languages, accepts 512x512 inputs, and uses sigmoid pairwise loss for sharper retrieval — directly improving every consumer of Weaviate's `multi2vec-clip` module without changing the API surface. Because the inference container's HTTP contract (`/vectorize`, `/meta`, `/.well-known/ready`) is identical, this is a zero-code swap at the manifest level.

## Stack wiring sketch
- weaviate → siglip2-vectorizer via `CLIP_INFERENCE_API=http://multi2vec-clip:8080` (unchanged)
- backend → siglip2-vectorizer via `POST /vectorize` (same endpoint, same payload)
- jupyterhub → siglip2-vectorizer via `POST /vectorize` for notebook experiments

(Every bullet names a real service in the current topology.)

## Effort
small — a one-line `MULTI2VEC_CLIP_IMAGE` default change in `services/weaviate/service.yml`, plus an embedding-dimension audit on existing Weaviate collections (SigLIP 2 base is 768-d vs ViT-B-32's 512-d; existing vector spaces are incompatible and require re-vectorization).

## Risks & open questions
- Vector dimension changes from 512 → 768 (or higher for `large` variants). Existing Weaviate collections vectorized with ViT-B-32 cannot be queried with the new model — a re-index migration script is required.
- Larger image size (224 → 512) increases CPU latency materially; recommend pairing with `MULTI2VEC_CLIP_SOURCE=container-gpu` for production.
- Container image sizes are larger; pull time on first start increases.
- SigLIP 2 license: published by Google under Apache 2.0 but verify the specific Hugging Face weights' license at adoption time.

## Why now (and why not sooner)
SigLIP 2 weights and Weaviate-published inference images shipped in 2025; the upstream `multi2vec-clip-inference` repo lists them as official variants. Sooner would have meant building a custom inference container; with the official image now available, the swap is a manifest edit.

## Upstream evidence
- https://github.com/weaviate/multi2vec-clip-inference (lists SigLIP 2 prebuilt images under `multi2vec-clip-google-siglip2-*`)
- https://docs.weaviate.io/weaviate/model-providers/transformers/embeddings-multimodal (documents SigLIP 2 as a supported model family)
