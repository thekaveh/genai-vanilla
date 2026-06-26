"""Tests for build_default_model_steps (B3) — the three final wizard steps
that let the user choose the default chat/embedding/vision model.

All tests use plain dicts for selections/env_vars — no Textual app needed.
The steps' options_provider callables are invoked directly.
"""

from __future__ import annotations

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _default_env() -> dict:
    """Env that mimics a fresh stack with Ollama container-cpu enabled."""
    return {
        "LLM_PROVIDER_SOURCE": "ollama-container-cpu",
        "OLLAMA_USER_MODELS": "qwen3.6:latest,nomic-embed-text",
        "LITELLM_EMBEDDING_MODEL": "ollama/nomic-embed-text",
        # Cloud disabled
        "CLOUD_OPENAI_SOURCE": "disabled",
        "OPENAI_API_KEY": "",
        "CLOUD_ANTHROPIC_SOURCE": "disabled",
        "ANTHROPIC_API_KEY": "",
        "CLOUD_OPENROUTER_SOURCE": "disabled",
        "OPENROUTER_API_KEY": "",
    }


def _ollama_selections(models: str = "qwen3.6:latest,nomic-embed-text") -> dict:
    """Simulate wizard selections with Ollama active."""
    return {
        "LLM Engine  ·  source": "ollama-container-cpu",
        "Ollama  ·  models": models,
    }


# ── test 1: build_default_model_steps returns 3 steps with correct titles ────

def test_returns_three_steps_with_correct_titles_and_kind():
    from wizard.llm_steps import (
        build_default_model_steps,
        LLM_DEFAULT_CONTENT_TITLE,
        LLM_DEFAULT_EMBED_TITLE,
        LLM_DEFAULT_VISION_TITLE,
    )
    steps = build_default_model_steps(_default_env())
    assert len(steps) == 3, f"Expected 3 steps, got {len(steps)}"
    titles = [s.title for s in steps]
    assert LLM_DEFAULT_CONTENT_TITLE in titles
    assert LLM_DEFAULT_EMBED_TITLE in titles
    assert LLM_DEFAULT_VISION_TITLE in titles
    for s in steps:
        assert s.kind == "options", f"Step {s.title!r} has kind={s.kind!r}; expected 'options'"


# ── test 2: default config — content options include qwen3.6:latest ───────────

def test_content_step_default_config():
    from wizard.llm_steps import build_default_model_steps, LLM_DEFAULT_CONTENT_TITLE

    env = _default_env()
    steps = build_default_model_steps(env)
    content_step = next(s for s in steps if s.title == LLM_DEFAULT_CONTENT_TITLE)
    assert content_step.options_provider is not None, "content step must have options_provider"

    selections = _ollama_selections("qwen3.6:latest,nomic-embed-text")
    opts = content_step.options_provider(selections)
    values = [o.value for o in opts]
    assert "ollama/qwen3.6:latest" in values, (
        f"Expected 'ollama/qwen3.6:latest' in content options, got {values}"
    )


# ── test 3: embedding step default_value + caveat text ──────────────────────

def test_embed_step_default_value_and_caveat():
    from wizard.llm_steps import build_default_model_steps, LLM_DEFAULT_EMBED_TITLE

    env = _default_env()
    # The current saved LITELLM_EMBEDDING_MODEL is the 768-dim default
    steps = build_default_model_steps(env)
    embed_step = next(s for s in steps if s.title == LLM_DEFAULT_EMBED_TITLE)

    # default_value must be the current saved embedding model
    assert embed_step.default_value == "ollama/nomic-embed-text", (
        f"Expected default_value='ollama/nomic-embed-text', got {embed_step.default_value!r}"
    )
    # heading and subtitle must mention the dimension caveat
    combined_text = (embed_step.heading or "") + " " + (embed_step.subtitle or "")
    caveat_keywords = ["768", "pgvector"]
    for kw in caveat_keywords:
        assert kw in combined_text, (
            f"Embedding caveat keyword {kw!r} not found in heading/subtitle. "
            f"heading={embed_step.heading!r}, subtitle={embed_step.subtitle!r}"
        )


def test_embed_step_fallback_when_no_saved_value():
    from wizard.llm_steps import build_default_model_steps, LLM_DEFAULT_EMBED_TITLE

    env = _default_env()
    env["LITELLM_EMBEDDING_MODEL"] = ""  # no saved value → must fall back
    steps = build_default_model_steps(env)
    embed_step = next(s for s in steps if s.title == LLM_DEFAULT_EMBED_TITLE)
    assert embed_step.default_value == "ollama/nomic-embed-text", (
        f"Fallback default should be 'ollama/nomic-embed-text', got {embed_step.default_value!r}"
    )


# ── test 4: vision step always includes value=="" (none/skip) first ──────────

def test_vision_step_always_has_none_option_first():
    from wizard.llm_steps import build_default_model_steps, LLM_DEFAULT_VISION_TITLE

    env = _default_env()
    steps = build_default_model_steps(env)
    vision_step = next(s for s in steps if s.title == LLM_DEFAULT_VISION_TITLE)
    assert vision_step.options_provider is not None

    selections = _ollama_selections("qwen3.6:latest")
    opts = vision_step.options_provider(selections)
    assert opts, "Vision step must return at least the none/skip option"
    first = opts[0]
    assert first.value == "", (
        f"First vision option must be the none/skip sentinel (value=''), got {first.value!r}"
    )


# ── test 5: cloud-only config — content options include openai model names ────

def test_cloud_only_config_content_options():
    from wizard.llm_steps import (
        build_default_model_steps,
        LLM_DEFAULT_CONTENT_TITLE,
        cloud_models_title,
        cloud_secret_title,
    )
    from utils.llm_catalog import cloud_entries

    # Grab a real openai model name from the catalog
    openai_catalog = cloud_entries("openai")
    assert openai_catalog, "OpenAI catalog must not be empty for this test"
    openai_model_name = openai_catalog[0].name

    env = {
        "LLM_PROVIDER_SOURCE": "none",   # Ollama disabled
        "OLLAMA_USER_MODELS": "",
        "LITELLM_EMBEDDING_MODEL": "",
        "CLOUD_OPENAI_SOURCE": "enabled",
        "OPENAI_API_KEY": "sk-test",
        "OPENAI_USER_MODELS": openai_model_name,
        "CLOUD_ANTHROPIC_SOURCE": "disabled",
        "ANTHROPIC_API_KEY": "",
        "CLOUD_OPENROUTER_SOURCE": "disabled",
        "OPENROUTER_API_KEY": "",
    }
    steps = build_default_model_steps(env)
    content_step = next(s for s in steps if s.title == LLM_DEFAULT_CONTENT_TITLE)

    # Simulate wizard selections: OpenAI secret kept, models selected
    selections = {
        "LLM Engine  ·  source": "none",
        cloud_secret_title("OpenAI"): "sk-test",
        cloud_models_title("OpenAI"): openai_model_name,
    }
    opts = content_step.options_provider(selections)
    values = [o.value for o in opts]
    # Cloud model names are bare (not prefixed with "openai/")
    assert openai_model_name in values, (
        f"Expected {openai_model_name!r} in content options for cloud-only config, got {values}"
    )


# ── test 6: _litellm_id helper ───────────────────────────────────────────────

def test_litellm_id_ollama():
    from wizard.llm_steps import _litellm_id
    assert _litellm_id("ollama", "x") == "ollama/x"
    assert _litellm_id("ollama", "qwen3.6:latest") == "ollama/qwen3.6:latest"


def test_litellm_id_cloud():
    from wizard.llm_steps import _litellm_id
    assert _litellm_id("openai", "gpt-5") == "gpt-5"
    assert _litellm_id("anthropic", "claude-opus-4-5") == "claude-opus-4-5"
    assert _litellm_id("openrouter", "meta-llama/llama-3") == "meta-llama/llama-3"


# ── test 7: _selections_to_args drains answers into default_model_selections ──

def test_selections_to_args_default_model_selections():
    """_selections_to_args must drain the three default-model answers into
    stack_options['default_model_selections'] with correct sentinel semantics."""
    import sys
    import os
    sys.path.insert(0, str(
        __import__("pathlib").Path(__file__).resolve().parent.parent
    ))
    from ui.textual.integration import _selections_to_args
    from ui.textual.widgets.prompt_panel import SECRET_KEEP
    from wizard.llm_steps import (
        LLM_DEFAULT_CONTENT_TITLE,
        LLM_DEFAULT_EMBED_TITLE,
        LLM_DEFAULT_VISION_TITLE,
    )

    # Minimal services_info stub — only needs the dict access pattern
    class _SvcInfo:
        display_name = "LLM Engine"
        key = "llm_provider"
        current_value = "ollama-container-cpu"

    services_info = []  # empty — no source selections, just model defaults

    selections = {
        LLM_DEFAULT_CONTENT_TITLE: "ollama/qwen3.6:latest",
        LLM_DEFAULT_EMBED_TITLE: "ollama/nomic-embed-text",
        LLM_DEFAULT_VISION_TITLE: "",   # explicit skip
        "Base port  ·  range": "",
        "Cold start  ·  rebuild": "no",
        "Hosts setup  ·  /etc/hosts": "default",
        "Confirm  ·  launch the stack": "no",
    }
    _, stack_options = _selections_to_args(
        selections, services_info, current_base_port=63000, env_vars={},
    )
    dms = stack_options["default_model_selections"]
    assert dms.get("LITELLM_DEFAULT_MODEL") == "ollama/qwen3.6:latest"
    assert dms.get("LITELLM_EMBEDDING_MODEL") == "ollama/nomic-embed-text"
    # vision "" is a valid explicit skip — must be persisted
    assert "LITELLM_VISION_MODEL" in dms
    assert dms["LITELLM_VISION_MODEL"] == ""


def test_selections_to_args_secret_keep_content_omitted():
    """A SECRET_KEEP answer for the content step must be omitted (not written to .env)."""
    from ui.textual.integration import _selections_to_args
    from ui.textual.widgets.prompt_panel import SECRET_KEEP
    from wizard.llm_steps import (
        LLM_DEFAULT_CONTENT_TITLE,
        LLM_DEFAULT_EMBED_TITLE,
        LLM_DEFAULT_VISION_TITLE,
    )

    selections = {
        LLM_DEFAULT_CONTENT_TITLE: SECRET_KEEP,   # must be omitted
        LLM_DEFAULT_EMBED_TITLE: "ollama/nomic-embed-text",
        LLM_DEFAULT_VISION_TITLE: SECRET_KEEP,    # must be omitted
        "Base port  ·  range": "",
        "Cold start  ·  rebuild": "no",
        "Hosts setup  ·  /etc/hosts": "default",
        "Confirm  ·  launch the stack": "no",
    }
    _, stack_options = _selections_to_args(
        selections, [], current_base_port=63000, env_vars={},
    )
    dms = stack_options["default_model_selections"]
    assert "LITELLM_DEFAULT_MODEL" not in dms, (
        "SECRET_KEEP content answer must not write LITELLM_DEFAULT_MODEL"
    )
    assert "LITELLM_VISION_MODEL" not in dms, (
        "SECRET_KEEP vision answer must not write LITELLM_VISION_MODEL"
    )
    # Embed should still be present
    assert dms.get("LITELLM_EMBEDDING_MODEL") == "ollama/nomic-embed-text"


def test_selections_to_args_none_steps_omitted():
    """When the default-model steps were never visited (None in selections),
    none of the three keys should appear in default_model_selections."""
    from ui.textual.integration import _selections_to_args

    selections = {
        "Base port  ·  range": "",
        "Cold start  ·  rebuild": "no",
        "Hosts setup  ·  /etc/hosts": "default",
        "Confirm  ·  launch the stack": "no",
    }
    _, stack_options = _selections_to_args(
        selections, [], current_base_port=63000, env_vars={},
    )
    dms = stack_options["default_model_selections"]
    assert "LITELLM_DEFAULT_MODEL" not in dms
    assert "LITELLM_EMBEDDING_MODEL" not in dms
    assert "LITELLM_VISION_MODEL" not in dms


# ── test 8: skip_if_prev for content/embedding when no LLM active ────────────

def test_skip_if_prev_content_skips_when_no_llm_active():
    from wizard.llm_steps import build_default_model_steps, LLM_DEFAULT_CONTENT_TITLE

    env = {
        "LLM_PROVIDER_SOURCE": "none",
        "OLLAMA_USER_MODELS": "",
        "LITELLM_EMBEDDING_MODEL": "",
        "CLOUD_OPENAI_SOURCE": "disabled",
        "OPENAI_API_KEY": "",
        "CLOUD_ANTHROPIC_SOURCE": "disabled",
        "ANTHROPIC_API_KEY": "",
        "CLOUD_OPENROUTER_SOURCE": "disabled",
        "OPENROUTER_API_KEY": "",
    }
    steps = build_default_model_steps(env)
    content_step = next(s for s in steps if s.title == LLM_DEFAULT_CONTENT_TITLE)
    assert content_step.skip_if_prev is not None

    # No LLM active → skip_if_prev must return True
    no_llm_selections = {"LLM Engine  ·  source": "none"}
    assert content_step.skip_if_prev(no_llm_selections), (
        "content step must be skipped when no LLM provider is active"
    )


def test_skip_if_prev_embed_skips_when_no_llm_active():
    from wizard.llm_steps import build_default_model_steps, LLM_DEFAULT_EMBED_TITLE

    env = {
        "LLM_PROVIDER_SOURCE": "none",
        "OLLAMA_USER_MODELS": "",
        "LITELLM_EMBEDDING_MODEL": "",
        "CLOUD_OPENAI_SOURCE": "disabled",
        "OPENAI_API_KEY": "",
        "CLOUD_ANTHROPIC_SOURCE": "disabled",
        "ANTHROPIC_API_KEY": "",
        "CLOUD_OPENROUTER_SOURCE": "disabled",
        "OPENROUTER_API_KEY": "",
    }
    steps = build_default_model_steps(env)
    embed_step = next(s for s in steps if s.title == LLM_DEFAULT_EMBED_TITLE)
    assert embed_step.skip_if_prev is not None

    no_llm_selections = {"LLM Engine  ·  source": "none"}
    assert embed_step.skip_if_prev(no_llm_selections), (
        "embedding step must be skipped when no LLM provider is active"
    )


def test_skip_if_prev_content_not_skipped_when_ollama_active():
    from wizard.llm_steps import build_default_model_steps, LLM_DEFAULT_CONTENT_TITLE

    env = _default_env()
    steps = build_default_model_steps(env)
    content_step = next(s for s in steps if s.title == LLM_DEFAULT_CONTENT_TITLE)
    assert content_step.skip_if_prev is not None

    ollama_selections = {"LLM Engine  ·  source": "ollama-container-cpu"}
    # Must NOT skip when Ollama is active
    assert not content_step.skip_if_prev(ollama_selections), (
        "content step must NOT be skipped when Ollama is active"
    )


# ── REGRESSION TEST: _load_current_step dispatches options_provider for kind="options" ──────
#
# This test drives the ACTUAL _load_current_step dispatch code path in
# WizardScreen. Without Fix 1 (the kind="options" synchronous dispatch block),
# _load_current_step falls through to ``live_options = self._provider_cache.get(
# self._step_index, original.options)`` without ever calling the provider —
# so original.options (the placeholder []) is used and the picker is empty.
#
# We exercise this via a minimal stub of the WizardScreen state (no Textual
# app or event loop needed): we copy _load_current_step's logic onto a simple
# namespace and assert that after the call, _provider_cache[step_index] is
# non-empty for a kind="options" step with an options_provider.


def test_load_current_step_dispatches_options_provider_for_kind_options():
    """_load_current_step must populate _provider_cache for kind='options' steps
    that carry an options_provider, so the rendered options list is non-empty.

    This test FAILS without Fix 1 (the synchronous dispatch block for
    kind='options') and PASSES with it.
    """
    from wizard.llm_steps import build_default_model_steps, LLM_DEFAULT_CONTENT_TITLE
    from ui.textual.screens.wizard_screen import WizardScreen

    env = _default_env()
    steps = build_default_model_steps(env)
    content_step = next(s for s in steps if s.title == LLM_DEFAULT_CONTENT_TITLE)

    # Verify the step has the right shape for this test to be meaningful.
    assert content_step.kind == "options"
    assert content_step.options_provider is not None
    assert content_step.options == [], "placeholder options must be empty before dispatch"

    # Build a minimal namespace that satisfies _load_current_step's attribute
    # accesses without a real Textual app/event-loop.
    class _FakeScreen:
        _steps = [content_step]
        _step_index = 0
        _provider_done: dict = {}
        _provider_cache: dict = {}
        _selections: dict = {}
        _rendered_options = None   # captured by the stub below

        def _advance_past_skipped(self, direction):
            # content_step.skip_if_prev needs at least one LLM active to NOT skip;
            # inject ollama-active selection so the step isn't bypassed.
            self._selections = _ollama_selections("qwen3.6:latest,nomic-embed-text")

        def _render_step(self, original, *, options=None, is_loading=False):
            self._rendered_options = options

        def run_worker(self, *args, **kwargs):
            raise AssertionError("run_worker must NOT be called for kind='options' steps")

    fake = _FakeScreen()
    # Bind the real _load_current_step to our fake screen instance.
    WizardScreen._load_current_step(fake)

    # After the call, the provider must have been invoked and the cache populated.
    assert fake._step_index in fake._provider_cache, (
        "_provider_cache must contain the step after _load_current_step — "
        "this FAILS without the kind='options' synchronous dispatch block"
    )
    cached = fake._provider_cache[fake._step_index]
    assert len(cached) > 0, (
        "options_provider must return non-empty options for the Ollama config; "
        f"got {cached!r}"
    )
    # The rendered options must also be non-empty (not the placeholder []).
    assert fake._rendered_options is not None
    assert len(fake._rendered_options) > 0, (
        "_render_step was called with empty options — provider was not dispatched"
    )
