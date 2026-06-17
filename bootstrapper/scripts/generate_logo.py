#!/usr/bin/env python3
"""Maintainer-only generator: render assets/atlas-source.png to per-width
terminal cell-grids committed under bootstrapper/ui/textual/assets/.

Requires Pillow and chafa (NOT runtime deps):
    pip install pillow   &&   brew install chafa   # or apt-get install chafa

Run from the repo root:
    python bootstrapper/scripts/generate_logo.py
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageEnhance

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "assets" / "atlas-source.png"
OUT_DIR = REPO / "bootstrapper" / "ui" / "textual" / "assets"
BREAKPOINTS = (160, 120, 100, 80)

# Locked params.
CROP = (0.101, 0.0, 0.941, 1.0)
GAMMA, BRIGHT, SAT, CONTRAST = 1.12, 1.04, 1.22, 1.16

_SGR = re.compile(r"\x1b\[([0-9;?]*)m")
_OTHER = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_DEFAULT_FG = "#c0caf5"
_DEFAULT_BG = "#0e0f18"


def _hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def _enhanced_source() -> Image.Image:
    im = Image.open(SRC).convert("RGB")
    w, h = im.size
    box = (int(CROP[0] * w), int(CROP[1] * h), int(CROP[2] * w), int(CROP[3] * h))
    im = im.crop(box)
    lut = [min(255, int(((i / 255) ** GAMMA) * 255 * BRIGHT)) for i in range(256)]
    im = im.point(lut * 3)
    im = ImageEnhance.Color(im).enhance(SAT)
    im = ImageEnhance.Contrast(im).enhance(CONTRAST)
    return im


def _chafa(tmp_png: Path, cols: int, rows: int) -> str:
    cmd = [
        "chafa", "-f", "symbols", "-c", "full", "--symbols", "block+space",
        "--fill", "block", "--dither", "none", "-s", f"{cols}x{rows}", str(tmp_png),
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout


def _parse(ansi: str) -> list[list[list[str]]]:
    fg, bg = _DEFAULT_FG, _DEFAULT_BG
    ansi = _OTHER.sub(lambda m: m.group(0) if m.group(0).endswith("m") else "", ansi)
    rows: list[list[list[str]]] = []
    cur: list[list[str]] = []
    i = 0
    while i < len(ansi):
        m = _SGR.match(ansi, i)
        if m:
            parts = [p for p in m.group(1).split(";") if p != ""]
            j = 0
            while j < len(parts):
                c = parts[j]
                if c == "0":
                    fg, bg = _DEFAULT_FG, _DEFAULT_BG
                elif c == "38" and parts[j + 1 : j + 2] == ["2"]:
                    fg = _hex((int(parts[j + 2]), int(parts[j + 3]), int(parts[j + 4]))); j += 4
                elif c == "48" and parts[j + 1 : j + 2] == ["2"]:
                    bg = _hex((int(parts[j + 2]), int(parts[j + 3]), int(parts[j + 4]))); j += 4
                j += 1
            i = m.end(); continue
        ch = ansi[i]
        if ch == "\n":
            rows.append(cur); cur = []; i += 1; continue
        if ch in "\r\x1b":
            i += 1; continue
        cur.append([ch, fg, bg]); i += 1
    if cur:
        rows.append(cur)
    rows = [r for r in rows if r]
    width = max(len(r) for r in rows)
    for r in rows:
        while len(r) < width:
            r.append([" ", _DEFAULT_FG, _DEFAULT_BG])
    return rows


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    im = _enhanced_source()
    aspect = im.height / im.width
    tmp = OUT_DIR / "_tmp_source.png"
    im.save(tmp)
    try:
        for cols in BREAKPOINTS:
            rows = max(1, int(cols * aspect * 0.5) + 1)
            grid = _parse(_chafa(tmp, cols, rows))
            data = {"cols": len(grid[0]), "rows": len(grid), "cells": grid}
            out = OUT_DIR / f"atlas_hero_{cols}.json"
            out.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            print(f"wrote {out.relative_to(REPO)}  {data['cols']}x{data['rows']}")
    finally:
        tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
