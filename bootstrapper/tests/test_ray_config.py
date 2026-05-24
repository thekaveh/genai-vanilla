"""Unit tests for _generate_ray_config() — derives RAY_IMAGE, RAY_WORKER_SCALE,
RAY_ADDRESS, RAY_HEAD_SCALE from RAY_SOURCE + RAY_WORKER_COUNT.

The hook is the only adaptive piece in the ray manifest — its correctness
is load-bearing for the entire compose substitution chain (image tag,
worker replicas, RAY_ADDRESS pushed into Backend / JupyterHub).
"""

from __future__ import annotations


def _service_config_instance():
    """Build a ServiceConfig instance with no real env file — we only
    test the pure hook function. Lazy-import to avoid module-load deps."""
    from services.service_config import ServiceConfig
    sc = ServiceConfig.__new__(ServiceConfig)
    # Minimal fields the hook reads; everything else stays uninitialized.
    sc.service_sources = {}
    return sc


def test_disabled_returns_empty_address_and_zero_scales():
    sc = _service_config_instance()
    out = sc._generate_ray_config(
        source_value="disabled",
        shared_env={"RAY_WORKER_COUNT": "2"},
    )
    assert out["RAY_HEAD_SCALE"] == "0"
    assert out["RAY_WORKER_SCALE"] == "0"
    assert out["RAY_ADDRESS"] == ""
    # Image is irrelevant when disabled but must be set to a valid default
    # (compose won't pull a missing image with replicas: 0, but tests for
    # env-example consistency need *some* value).
    assert out["RAY_IMAGE"].startswith("rayproject/ray:")


def test_container_cpu_returns_cpu_image_and_resolved_scales():
    sc = _service_config_instance()
    out = sc._generate_ray_config(
        source_value="ray-container-cpu",
        shared_env={"RAY_WORKER_COUNT": "3", "RAY_IMAGE": "rayproject/ray:2.55.1",
                    "RAY_GPU_IMAGE": "rayproject/ray:2.55.1-gpu"},
    )
    assert out["RAY_IMAGE"] == "rayproject/ray:2.55.1"
    assert out["RAY_HEAD_SCALE"] == "1"
    assert out["RAY_WORKER_SCALE"] == "3"
    assert out["RAY_ADDRESS"] == "ray://ray-head:10001"


def test_container_gpu_returns_gpu_image_and_resolved_scales():
    sc = _service_config_instance()
    out = sc._generate_ray_config(
        source_value="ray-container-gpu",
        shared_env={"RAY_WORKER_COUNT": "2", "RAY_IMAGE": "rayproject/ray:2.55.1",
                    "RAY_GPU_IMAGE": "rayproject/ray:2.55.1-gpu"},
    )
    assert out["RAY_IMAGE"] == "rayproject/ray:2.55.1-gpu"
    assert out["RAY_HEAD_SCALE"] == "1"
    assert out["RAY_WORKER_SCALE"] == "2"
    assert out["RAY_ADDRESS"] == "ray://ray-head:10001"


def test_external_uses_external_address_and_zero_scales():
    sc = _service_config_instance()
    out = sc._generate_ray_config(
        source_value="ray-external",
        shared_env={"RAY_EXTERNAL_ADDRESS": "ray://my-cluster.anyscale.com:10001",
                    "RAY_WORKER_COUNT": "5"},
    )
    assert out["RAY_HEAD_SCALE"] == "0"
    assert out["RAY_WORKER_SCALE"] == "0"
    assert out["RAY_ADDRESS"] == "ray://my-cluster.anyscale.com:10001"


def test_external_with_empty_address_falls_back_safely():
    """If user sets RAY_SOURCE=ray-external but forgets RAY_EXTERNAL_ADDRESS,
    we don't crash — emit an empty RAY_ADDRESS so consumers know Ray is
    unavailable. The source-validator should have caught this upstream
    via the `requires: [RAY_EXTERNAL_ADDRESS]` block, but the hook must
    still degrade gracefully."""
    sc = _service_config_instance()
    out = sc._generate_ray_config(
        source_value="ray-external",
        shared_env={"RAY_EXTERNAL_ADDRESS": "", "RAY_WORKER_COUNT": "0"},
    )
    assert out["RAY_ADDRESS"] == ""


def test_worker_count_zero_means_head_only():
    sc = _service_config_instance()
    out = sc._generate_ray_config(
        source_value="ray-container-cpu",
        shared_env={"RAY_WORKER_COUNT": "0", "RAY_IMAGE": "rayproject/ray:2.55.1",
                    "RAY_GPU_IMAGE": "rayproject/ray:2.55.1-gpu"},
    )
    assert out["RAY_HEAD_SCALE"] == "1"  # head still on
    assert out["RAY_WORKER_SCALE"] == "0"  # head-only single-node Ray


def test_invalid_worker_count_falls_back_to_default():
    """A malformed RAY_WORKER_COUNT (non-integer, negative) should fall
    back to the manifest's stated default `2` rather than crash."""
    sc = _service_config_instance()
    out = sc._generate_ray_config(
        source_value="ray-container-cpu",
        shared_env={"RAY_WORKER_COUNT": "not-a-number",
                    "RAY_IMAGE": "rayproject/ray:2.55.1",
                    "RAY_GPU_IMAGE": "rayproject/ray:2.55.1-gpu"},
    )
    assert out["RAY_WORKER_SCALE"] == "2"
