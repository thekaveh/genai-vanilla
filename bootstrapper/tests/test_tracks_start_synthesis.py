"""Tests for the start.py-level override-set + force-disable synthesis
(the no-wizard / --no-tui code path that mirrors _selections_to_args).
"""

from __future__ import annotations

import pytest

from tracks import load_tracks, is_in_track


def test_off_track_flag_in_overridden_set():
    """When --track gen-ai-rag --comfyui-source container is passed
    via CLI, the synthesis block must:
      - add 'comfyui' to overridden_services
      - leave source_args['comfyui_source'] = 'container' (user choice)
      - NOT write 'disabled' for it
    """
    # Simulate the synthesis logic directly (mirrors start.py block).
    source_args = {
        "comfyui_source": "container",
        "weaviate_source": None,   # off-track, no user override
    }
    overridden_services: set = set()
    reg = load_tracks()
    track_obj = reg.by_key["gen-ai-rag"]
    always_on = reg.always_on
    # gen-ai-rag includes weaviate, excludes comfyui
    for cli_key in list(source_args.keys()):
        svc_key = cli_key.removesuffix("_source").replace("_", "-")
        if is_in_track(track_obj, svc_key, always_on=always_on):
            continue
        if source_args.get(cli_key) is not None:
            overridden_services.add(svc_key)
        else:
            source_args[cli_key] = "disabled"
    assert "comfyui" in overridden_services
    assert source_args["comfyui_source"] == "container"   # user choice preserved
    # weaviate is in-track → not touched
    assert source_args["weaviate_source"] is None


def test_off_track_no_flag_force_disabled():
    """When --track gen-ai-rag is passed alone, comfyui_source goes to
    'disabled' (and is NOT added to overridden_services)."""
    source_args = {"comfyui_source": None, "weaviate_source": None}
    overridden_services: set = set()
    reg = load_tracks()
    track_obj = reg.by_key["gen-ai-rag"]
    always_on = reg.always_on
    for cli_key in list(source_args.keys()):
        svc_key = cli_key.removesuffix("_source").replace("_", "-")
        if is_in_track(track_obj, svc_key, always_on=always_on):
            continue
        if source_args.get(cli_key) is not None:
            overridden_services.add(svc_key)
        else:
            source_args[cli_key] = "disabled"
    assert source_args["comfyui_source"] == "disabled"
    assert "comfyui" not in overridden_services
