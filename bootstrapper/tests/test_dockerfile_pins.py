"""Every `services/**/Dockerfile` must pin its FROM image to a digest or
patch-versioned tag — never to a floating tag like `latest`, `slim`,
`stable`, or `edge`.

A floating tag means rebuilds can pick up a future supply-chain-compromised
or behaviorally-changed base image without lockstep visibility. Today the
stack uses patch-version tags everywhere (e.g. `python:3.12.7-slim`,
`apache/airflow:3.2.2`, `pytorch/pytorch:2.5.1-cuda12.4-cudnn9-runtime`).
This test locks that posture in CI so a future contributor can't
re-introduce a floating tag silently.

ARG-defaulted FROMs (e.g. `FROM ${BASE_IMAGE}`) are exempt because the
ARG itself is overridden by compose at build time and resolves to a
fully-qualified tag from `.env.example` / `services/<svc>/service.yml`.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]

# Floating tags that admit a moving target. `latest` is the worst offender;
# `slim` / `stable` / `edge` / `bookworm` (Debian codename, no version) all
# track a moving point without operator visibility.
FORBIDDEN_TAGS = {"latest", "slim", "stable", "edge", "bookworm", "bullseye"}

FROM_RE = re.compile(r"^\s*FROM\s+(\S+)", re.MULTILINE)


def _discover_dockerfiles() -> list[Path]:
    return sorted(REPO_ROOT.glob("services/**/Dockerfile"))


@pytest.mark.parametrize(
    "dockerfile",
    _discover_dockerfiles(),
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_dockerfile_from_is_pinned(dockerfile: Path) -> None:
    """Every `FROM <image>:<tag>` must use a digest or a tag NOT in the
    floating-tag denylist. `FROM ${ARG}` is exempt (ARG is compose-driven).
    """
    text = dockerfile.read_text(encoding="utf-8")
    images = FROM_RE.findall(text)
    assert images, f"{dockerfile.relative_to(REPO_ROOT)} has no FROM directive"
    for image in images:
        # ARG-driven references are compose-controlled; skip.
        if image.startswith("$") or image.startswith("${"):
            continue
        # Digest-pinned (image@sha256:...) is acceptable.
        if "@sha256:" in image:
            continue
        # Otherwise, image must be `name:tag`. Reject untagged or floating-tag.
        assert ":" in image, (
            f"{dockerfile.relative_to(REPO_ROOT)} FROM {image!r}: untagged "
            f"image (rebuilds resolve to :latest). Pin to a patch-version tag."
        )
        tag = image.rsplit(":", 1)[1].lower()
        # Accept tag-with-suffix like "3.12.7-slim" — only fail when the WHOLE
        # tag is a known floating marker (slim alone, latest alone, etc.).
        if tag in FORBIDDEN_TAGS:
            pytest.fail(
                f"{dockerfile.relative_to(REPO_ROOT)} FROM {image!r}: "
                f"floating tag {tag!r}. Pin to a patch-version tag "
                f"(e.g. python:3.12.7-slim, alpine:3.20)."
            )


def test_at_least_one_dockerfile_discovered() -> None:
    """Belt-and-suspenders: if the glob returns zero, fail loudly."""
    files = _discover_dockerfiles()
    assert files, "No Dockerfiles discovered under services/**/Dockerfile"
