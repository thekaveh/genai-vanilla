"""Tests for bootstrapper.utils.model_resolver.

All tests are pure unit tests — no DB, no network, no running containers.
Ollama tags are passed explicitly where needed; env dicts are synthetic.

Test matrix:
  1. Default config  — ollama-container-cpu, no cloud keys
  2. Ollama disabled — LLM_PROVIDER_SOURCE=none
  3. Cloud enabled   — openai enabled+keyed, ollama also active → ordering
  4. User override   — OPENAI_USER_MODELS=gpt-5 activates exactly that model
  5. Cloud no key    — enabled but no API key → no actives for that provider
  6. Custom ollama   — OLLAMA_CUSTOM_MODELS synthesized entry
  7. ollama_tags     — host-side auto-import unions into active set
  8. best('vision')  — picks vision-capable model; None when none active
  9. Embedding carve-out — resolved_defaults never contains LITELLM_EMBEDDING_MODEL
"""

from __future__ import annotations

import pytest

from utils.model_resolver import active_models, best, resolved_defaults


# ── helpers ──────────────────────────────────────────────────────────────────

def _names(entries) -> list[str]:
    return [e.name for e in entries]


# ── 1. Default config ────────────────────────────────────────────────────────

class TestDefaultConfig:
    """Empty env (or just ollama-container-cpu) → default ollama actives."""

    def test_active_models_includes_default_active_ollama(self):
        models = active_models({})
        names = _names(models)
        # qwen3.6:latest is the default content+vision model
        assert "qwen3.6:latest" in names

    def test_active_models_includes_embedding_model(self):
        models = active_models({})
        names = _names(models)
        # nomic-embed-text is default_active for embeddings
        assert "nomic-embed-text" in names

    def test_active_models_has_three_default_ollama_entries(self):
        # The catalog has 3 default_active ollama entries:
        # qwen3.6:latest (content+vision), qwen3-embedding:0.6b (embeddings),
        # nomic-embed-text (embeddings)
        models = active_models({})
        ollama_models = [e for e in models if e.provider == "ollama"]
        assert len(ollama_models) >= 3

    def test_best_content_is_qwen(self):
        result = best("content", {})
        assert result == "ollama/qwen3.6:latest"

    def test_best_embeddings_is_ollama(self):
        result = best("embeddings", {})
        assert result is not None
        assert result.startswith("ollama/")

    def test_resolved_defaults_has_exactly_two_keys(self):
        defaults = resolved_defaults({})
        assert set(defaults.keys()) == {"LITELLM_DEFAULT_MODEL", "LITELLM_VISION_MODEL"}

    def test_resolved_defaults_default_model_is_qwen(self):
        defaults = resolved_defaults({})
        assert defaults["LITELLM_DEFAULT_MODEL"] == "ollama/qwen3.6:latest"

    def test_resolved_defaults_vision_model_is_qwen(self):
        defaults = resolved_defaults({})
        assert defaults["LITELLM_VISION_MODEL"] == "ollama/qwen3.6:latest"

    def test_explicit_ollama_container_cpu_same_as_empty(self):
        env = {"LLM_PROVIDER_SOURCE": "ollama-container-cpu"}
        assert active_models(env) == active_models({})


# ── 2. Ollama disabled ────────────────────────────────────────────────────────

class TestOllamaDisabled:
    """LLM_PROVIDER_SOURCE=none → no ollama actives."""

    def test_no_ollama_actives_when_source_none(self):
        env = {"LLM_PROVIDER_SOURCE": "none"}
        models = active_models(env)
        ollama = [e for e in models if e.provider == "ollama"]
        assert ollama == []

    def test_no_ollama_actives_when_source_disabled(self):
        env = {"LLM_PROVIDER_SOURCE": "disabled"}
        models = active_models(env)
        ollama = [e for e in models if e.provider == "ollama"]
        assert ollama == []

    def test_best_content_is_none_when_no_cloud(self):
        env = {"LLM_PROVIDER_SOURCE": "none"}
        assert best("content", env) is None

    def test_best_content_falls_to_cloud_when_enabled(self):
        env = {
            "LLM_PROVIDER_SOURCE": "none",
            "LITELLM_OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "sk-test",
        }
        result = best("content", env)
        # Should be a cloud model (not ollama/)
        assert result is not None
        assert not result.startswith("ollama/")


# ── 3. Cloud enabled + ollama active → ordering ──────────────────────────────

class TestCloudEnabledOrderingWithOllama:
    """Ollama precedes cloud in active_models → ollama wins best()."""

    def setup_method(self):
        self.env = {
            "LLM_PROVIDER_SOURCE": "ollama-container-cpu",
            "LITELLM_OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "sk-test",
        }

    def test_active_models_has_both_ollama_and_openai(self):
        models = active_models(self.env)
        providers = {e.provider for e in models}
        assert "ollama" in providers
        assert "openai" in providers

    def test_ollama_comes_before_openai_in_active_list(self):
        models = active_models(self.env)
        providers_ordered = [e.provider for e in models]
        first_ollama = next(i for i, p in enumerate(providers_ordered) if p == "ollama")
        first_openai = next(i for i, p in enumerate(providers_ordered) if p == "openai")
        assert first_ollama < first_openai, (
            "Ollama entries must precede cloud entries (ollama is higher priority)"
        )

    def test_best_content_is_ollama_not_openai(self):
        result = best("content", self.env)
        assert result is not None
        assert result.startswith("ollama/"), (
            f"Expected ollama/ prefix (ollama has higher priority), got {result!r}"
        )


# ── 4. User override ──────────────────────────────────────────────────────────

class TestUserModelOverride:
    """OPENAI_USER_MODELS=gpt-5 activates exactly gpt-5 for openai."""

    def test_user_models_activates_exactly_named_model(self):
        env = {
            "LLM_PROVIDER_SOURCE": "none",
            "LITELLM_OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_USER_MODELS": "gpt-5",
        }
        models = active_models(env)
        openai_models = [e for e in models if e.provider == "openai"]
        assert len(openai_models) == 1
        assert openai_models[0].name == "gpt-5"

    def test_user_models_csv_activates_multiple(self):
        env = {
            "LLM_PROVIDER_SOURCE": "none",
            "LITELLM_OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_USER_MODELS": "gpt-5,gpt-4o",
        }
        models = active_models(env)
        openai_names = [e.name for e in models if e.provider == "openai"]
        assert set(openai_names) == {"gpt-5", "gpt-4o"}

    def test_user_models_overrides_defaults(self):
        env = {
            "LLM_PROVIDER_SOURCE": "none",
            "LITELLM_OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_USER_MODELS": "gpt-5",
        }
        models = active_models(env)
        openai_names = [e.name for e in models if e.provider == "openai"]
        # gpt-5-mini is a default_active, but OPENAI_USER_MODELS overrides that
        assert "gpt-5-mini" not in openai_names


# ── 5. Cloud enabled but no key ───────────────────────────────────────────────

class TestCloudNoKey:
    """Enabled flag set but no API key → no actives for that provider."""

    def test_no_actives_when_enabled_but_no_key(self):
        env = {
            "LLM_PROVIDER_SOURCE": "none",
            "LITELLM_OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "",
        }
        models = active_models(env)
        openai = [e for e in models if e.provider == "openai"]
        assert openai == []

    def test_no_actives_when_key_only_whitespace(self):
        env = {
            "LLM_PROVIDER_SOURCE": "none",
            "LITELLM_OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "   ",
        }
        models = active_models(env)
        openai = [e for e in models if e.provider == "openai"]
        assert openai == []

    def test_no_actives_when_not_enabled(self):
        env = {
            "LLM_PROVIDER_SOURCE": "none",
            "LITELLM_OPENAI_ENABLED": "false",
            "OPENAI_API_KEY": "sk-test",
        }
        models = active_models(env)
        openai = [e for e in models if e.provider == "openai"]
        assert openai == []

    def test_no_actives_when_key_missing_entirely(self):
        env = {
            "LLM_PROVIDER_SOURCE": "none",
            "LITELLM_OPENAI_ENABLED": "true",
            # OPENAI_API_KEY not set
        }
        models = active_models(env)
        openai = [e for e in models if e.provider == "openai"]
        assert openai == []


# ── 6. Custom/live-only ollama ────────────────────────────────────────────────

class TestCustomOllamaModels:
    """OLLAMA_CUSTOM_MODELS=mymodel:7b appears in active_models as synthesized."""

    def test_custom_model_appears_in_active_models(self):
        env = {
            "LLM_PROVIDER_SOURCE": "ollama-container-cpu",
            "OLLAMA_CUSTOM_MODELS": "mymodel:7b",
        }
        models = active_models(env)
        names = _names(models)
        assert "mymodel:7b" in names

    def test_custom_model_is_synthesized_not_from_catalog(self):
        env = {
            "LLM_PROVIDER_SOURCE": "ollama-container-cpu",
            "OLLAMA_CUSTOM_MODELS": "totally-custom:99b",
        }
        models = active_models(env)
        custom = next((e for e in models if e.name == "totally-custom:99b"), None)
        assert custom is not None
        assert custom.provider == "ollama"
        # Synthesized entries have content=8 (the live-only default)
        assert custom.content == 8

    def test_custom_model_combined_with_catalog_defaults(self):
        env = {
            "LLM_PROVIDER_SOURCE": "ollama-container-cpu",
            "OLLAMA_CUSTOM_MODELS": "mymodel:7b",
        }
        models = active_models(env)
        names = _names(models)
        # Both catalog default and custom should be present
        assert "qwen3.6:latest" in names
        assert "mymodel:7b" in names

    def test_custom_models_csv(self):
        env = {
            "LLM_PROVIDER_SOURCE": "ollama-container-cpu",
            "OLLAMA_CUSTOM_MODELS": "model-a:1b,model-b:3b",
        }
        models = active_models(env)
        names = _names(models)
        assert "model-a:1b" in names
        assert "model-b:3b" in names


# ── 7. ollama_tags auto-import ────────────────────────────────────────────────

class TestOllamaTagsAutoImport:
    """Passing ollama_tags= unions extra model names into the active set."""

    def test_tags_union_into_active_set(self):
        env = {"LLM_PROVIDER_SOURCE": "ollama-localhost"}
        models = active_models(env, ollama_tags=["extra:1b"])
        names = _names(models)
        assert "extra:1b" in names

    def test_tags_combined_with_defaults(self):
        env = {"LLM_PROVIDER_SOURCE": "ollama-localhost"}
        models = active_models(env, ollama_tags=["extra:1b"])
        names = _names(models)
        assert "qwen3.6:latest" in names
        assert "extra:1b" in names

    def test_tags_none_does_not_add_anything(self):
        env = {"LLM_PROVIDER_SOURCE": "ollama-container-cpu"}
        models_without = active_models(env)
        models_with_none = active_models(env, ollama_tags=None)
        assert _names(models_without) == _names(models_with_none)

    def test_tags_empty_list_adds_nothing(self):
        env = {"LLM_PROVIDER_SOURCE": "ollama-container-cpu"}
        models_no_tags = active_models(env, ollama_tags=None)
        models_empty_tags = active_models(env, ollama_tags=[])
        # Empty list should not add any new entries
        assert set(_names(models_empty_tags)) == set(_names(models_no_tags))

    def test_tags_are_synthesized_when_not_in_catalog(self):
        env = {"LLM_PROVIDER_SOURCE": "ollama-localhost"}
        models = active_models(env, ollama_tags=["unknown-model:2b"])
        custom = next((e for e in models if e.name == "unknown-model:2b"), None)
        assert custom is not None
        assert custom.provider == "ollama"
        assert custom.content == 8  # synthesized default

    def test_tags_already_in_catalog_uses_catalog_entry(self):
        env = {"LLM_PROVIDER_SOURCE": "ollama-localhost"}
        # qwen3.6:latest is already in the catalog with real capability values
        models = active_models(env, ollama_tags=["qwen3.6:latest"])
        qwen = next((e for e in models if e.name == "qwen3.6:latest"), None)
        assert qwen is not None
        # Should be the catalog entry, not a synthesized one (vision > 0 in catalog)
        assert qwen.content > 0


# ── 8. best('vision') ─────────────────────────────────────────────────────────

class TestBestVision:
    """best('vision') picks a vision-capable active model; None when none active."""

    def test_best_vision_default_config(self):
        # qwen3.6:latest appears in the vision section of ollama/models.yaml
        result = best("vision", {})
        assert result == "ollama/qwen3.6:latest"

    def test_best_vision_none_when_no_vision_capable_active(self):
        # Force ollama off and no cloud → no vision model
        env = {"LLM_PROVIDER_SOURCE": "none"}
        result = best("vision", env)
        assert result is None

    def test_best_vision_cloud_when_ollama_off(self):
        env = {
            "LLM_PROVIDER_SOURCE": "none",
            "LITELLM_OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "sk-test",
        }
        result = best("vision", env)
        # gpt-5 and gpt-5-mini are vision-capable in the openai catalog
        assert result is not None
        assert not result.startswith("ollama/")

    def test_best_vision_with_custom_only_model_is_none(self):
        # A pure-custom model with no vision capability should not win vision
        env = {
            "LLM_PROVIDER_SOURCE": "ollama-container-cpu",
            "OLLAMA_USER_MODELS": "mynotvision:1b",
        }
        # OLLAMA_USER_MODELS overrides defaults, so only custom is active
        # Synthesized entries have vision=0
        result = best("vision", env)
        assert result is None


# ── 9. Embedding carve-out ────────────────────────────────────────────────────

class TestEmbeddingCarveOut:
    """resolved_defaults NEVER contains LITELLM_EMBEDDING_MODEL."""

    def test_resolved_defaults_never_has_embedding_key_default_env(self):
        defaults = resolved_defaults({})
        assert "LITELLM_EMBEDDING_MODEL" not in defaults

    def test_resolved_defaults_never_has_embedding_key_cloud_env(self):
        env = {
            "LLM_PROVIDER_SOURCE": "none",
            "LITELLM_OPENAI_ENABLED": "true",
            "OPENAI_API_KEY": "sk-test",
        }
        defaults = resolved_defaults(env)
        assert "LITELLM_EMBEDDING_MODEL" not in defaults

    def test_resolved_defaults_never_has_embedding_key_all_disabled(self):
        env = {"LLM_PROVIDER_SOURCE": "none"}
        defaults = resolved_defaults(env)
        assert "LITELLM_EMBEDDING_MODEL" not in defaults

    def test_resolved_defaults_exactly_two_keys(self):
        defaults = resolved_defaults({})
        assert len(defaults) == 2
        assert set(defaults.keys()) == {"LITELLM_DEFAULT_MODEL", "LITELLM_VISION_MODEL"}

    def test_resolved_defaults_exactly_two_keys_various_envs(self):
        for env in [
            {},
            {"LLM_PROVIDER_SOURCE": "none"},
            {"LLM_PROVIDER_SOURCE": "ollama-container-gpu"},
            {
                "LITELLM_OPENAI_ENABLED": "true",
                "OPENAI_API_KEY": "sk-x",
            },
        ]:
            defaults = resolved_defaults(env)
            assert set(defaults.keys()) == {"LITELLM_DEFAULT_MODEL", "LITELLM_VISION_MODEL"}, (
                f"resolved_defaults returned wrong keys for env={env!r}: {set(defaults.keys())!r}"
            )

    def test_best_embeddings_still_exists_and_works(self):
        # best('embeddings') is NOT wired into resolved_defaults, but it
        # should still function (used by B3 wizard step, B4 picker).
        result = best("embeddings", {})
        assert result is not None
        assert result.startswith("ollama/")
