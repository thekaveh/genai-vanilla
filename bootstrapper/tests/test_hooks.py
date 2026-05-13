"""Tests for the per-service hooks under bootstrapper/services/hooks/."""

from __future__ import annotations

import pytest

from services.hooks import comfyui, cloud_providers, openclaw, weaviate


# ────────────────────────────────────────────────────────────────────────────
# comfyui
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "source,expected_endpoint,expected_is_local",
    [
        ("container-cpu", "http://comfyui:18188", "false"),
        ("container-gpu", "http://comfyui:18188", "false"),
        ("localhost", "http://host.docker.internal:8000", "true"),
        ("external", "http://my-comfyui.example.com:18188", "false"),
        ("disabled", "", "false"),
    ],
)
def test_comfyui_endpoint_per_source(source, expected_endpoint, expected_is_local):
    env = {
        "COMFYUI_SOURCE": source,
        "COMFYUI_LOCALHOST_URL": "http://host.docker.internal:8000",
        "COMFYUI_EXTERNAL_URL": "http://my-comfyui.example.com:18188",
    }
    comfyui.apply(env)
    assert env["COMFYUI_ENDPOINT"] == expected_endpoint
    assert env["IS_LOCAL_COMFYUI"] == expected_is_local


def test_comfyui_gpu_emits_deploy_resources():
    env = {"COMFYUI_SOURCE": "container-gpu"}
    comfyui.apply(env)
    assert "nvidia" in env["COMFYUI_DEPLOY_RESOURCES"]
    assert "gpu" in env["COMFYUI_DEPLOY_RESOURCES"]


def test_comfyui_cpu_has_no_deploy_resources():
    env = {"COMFYUI_SOURCE": "container-cpu"}
    comfyui.apply(env)
    assert env["COMFYUI_DEPLOY_RESOURCES"] == "~"


# ────────────────────────────────────────────────────────────────────────────
# weaviate
# ────────────────────────────────────────────────────────────────────────────


def test_weaviate_mirrors_ollama_endpoint():
    env = {
        "OLLAMA_ENDPOINT": "http://host.docker.internal:11434",
        "LITELLM_MASTER_KEY": "sk-test",
        "MULTI2VEC_CLIP_SOURCE": "container-cpu",
    }
    weaviate.apply(env)
    assert env["WEAVIATE_OLLAMA_ENDPOINT"] == "http://host.docker.internal:11434"
    assert env["WEAVIATE_LITELLM_API_KEY"] == "sk-test"
    assert env["WEAVIATE_LITELLM_BASE_URL"] == "http://litellm:4000/v1"


@pytest.mark.parametrize(
    "clip_source,clip_scale,clip_cuda",
    [
        ("container-cpu", "1", "0"),
        ("container-gpu", "1", "1"),
        ("disabled", "0", "0"),
    ],
)
def test_weaviate_clip_scale_per_source(clip_source, clip_scale, clip_cuda):
    env = {"MULTI2VEC_CLIP_SOURCE": clip_source, "OLLAMA_ENDPOINT": ""}
    weaviate.apply(env)
    assert env["CLIP_SCALE"] == clip_scale
    assert env["CLIP_ENABLE_CUDA"] == clip_cuda


# ────────────────────────────────────────────────────────────────────────────
# cloud_providers
# ────────────────────────────────────────────────────────────────────────────


def test_cloud_providers_all_disabled():
    env = {
        "CLOUD_OPENAI_SOURCE": "disabled",
        "CLOUD_ANTHROPIC_SOURCE": "disabled",
        "CLOUD_OPENROUTER_SOURCE": "disabled",
    }
    cloud_providers.apply(env)
    assert env["LITELLM_OPENAI_ENABLED"] == "false"
    assert env["LITELLM_ANTHROPIC_ENABLED"] == "false"
    assert env["LITELLM_OPENROUTER_ENABLED"] == "false"
    assert env["LITELLM_ENABLED_PROVIDERS"] == ""


def test_cloud_providers_partial_enabled():
    env = {
        "CLOUD_OPENAI_SOURCE": "enabled",
        "CLOUD_ANTHROPIC_SOURCE": "disabled",
        "CLOUD_OPENROUTER_SOURCE": "enabled",
    }
    cloud_providers.apply(env)
    assert env["LITELLM_OPENAI_ENABLED"] == "true"
    assert env["LITELLM_ANTHROPIC_ENABLED"] == "false"
    assert env["LITELLM_OPENROUTER_ENABLED"] == "true"
    assert env["LITELLM_ENABLED_PROVIDERS"] == "openai,openrouter"


def test_cloud_providers_all_enabled():
    env = {
        "CLOUD_OPENAI_SOURCE": "enabled",
        "CLOUD_ANTHROPIC_SOURCE": "enabled",
        "CLOUD_OPENROUTER_SOURCE": "enabled",
    }
    cloud_providers.apply(env)
    assert env["LITELLM_ENABLED_PROVIDERS"] == "openai,anthropic,openrouter"


def test_cloud_providers_missing_keys_default_to_disabled():
    """If a CLOUD_*_SOURCE var is missing, the hook treats it as disabled."""
    env = {}
    cloud_providers.apply(env)
    assert env["LITELLM_OPENAI_ENABLED"] == "false"
    assert env["LITELLM_ENABLED_PROVIDERS"] == ""


# ────────────────────────────────────────────────────────────────────────────
# openclaw
# ────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "source,scale,init_scale,endpoint",
    [
        ("disabled", "0", "0", ""),
        ("container", "1", "1", "http://openclaw-gateway:18789"),
        ("localhost", "0", "0", "http://host.docker.internal:63024"),
    ],
)
def test_openclaw_per_source(source, scale, init_scale, endpoint):
    env = {
        "OPENCLAW_SOURCE": source,
        "OPENCLAW_LOCALHOST_URL": "http://host.docker.internal:63024",
    }
    openclaw.apply(env)
    assert env["OPENCLAW_SCALE"] == scale
    assert env["OPENCLAW_INIT_SCALE"] == init_scale
    assert env["OPENCLAW_ENDPOINT"] == endpoint
