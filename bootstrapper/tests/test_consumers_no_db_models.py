"""
Regression guard: weaviate-init, LDR init-config.py, and backend memory_service.py
must NOT query ``public.llms`` for model selection — they now read resolved env vars
(LITELLM_EMBEDDING_MODEL / LITELLM_DEFAULT_MODEL) directly.

If any of these assertions fail it means someone re-introduced a DB query against
public.llms for model resolution inside one of these three consumers.  That is the
pattern being removed in B5 (repoint consumers off public.llms to env vars).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def test_weaviate_init_no_public_llms():
    """init-weaviate.sh must not query public.llms for the embedding model."""
    text = _read("services/weaviate/init/scripts/init-weaviate.sh")
    assert "public.llms" not in text, (
        "init-weaviate.sh still references public.llms — "
        "the embedding model must come from LITELLM_EMBEDDING_MODEL env var."
    )


def test_ldr_init_config_no_public_llms():
    """LDR init-config.py must not query public.llms for the content model."""
    text = _read("services/local-deep-researcher/build/scripts/init-config.py")
    assert "public.llms" not in text, (
        "init-config.py still references public.llms — "
        "the content model must come from LITELLM_DEFAULT_MODEL env var."
    )


def test_backend_memory_service_no_public_llms():
    """memory_service.py _get_extraction_model must not query public.llms."""
    text = _read("services/backend/app/app/memory_service.py")
    assert "public.llms" not in text, (
        "memory_service.py still references public.llms for model selection — "
        "_get_extraction_model must resolve via LITELLM_DEFAULT_MODEL env var only."
    )


def test_weaviate_compose_passes_embedding_model():
    """weaviate/compose.yml must inject LITELLM_EMBEDDING_MODEL into weaviate-init."""
    text = _read("services/weaviate/compose.yml")
    assert "LITELLM_EMBEDDING_MODEL" in text, (
        "weaviate/compose.yml does not pass LITELLM_EMBEDDING_MODEL to weaviate-init."
    )


def test_ldr_compose_passes_default_model():
    """local-deep-researcher/compose.yml must inject LITELLM_DEFAULT_MODEL."""
    text = _read("services/local-deep-researcher/compose.yml")
    assert "LITELLM_DEFAULT_MODEL" in text, (
        "local-deep-researcher/compose.yml does not pass LITELLM_DEFAULT_MODEL."
    )


def test_weaviate_init_no_double_prefix():
    """init-weaviate.sh must write the model through without re-prepending 'ollama/'."""
    text = _read("services/weaviate/init/scripts/init-weaviate.sh")
    # The old code wrote: LITELLM_EMBEDDING_MODEL=ollama/$embedding_model
    # where $embedding_model was a bare name.  The new code writes the env
    # value through unchanged.  A double-prefix write would look like
    # "ollama/ollama/" — assert that pattern is absent.
    assert "ollama/ollama/" not in text, (
        "init-weaviate.sh has a double ollama/ prefix — "
        "LITELLM_EMBEDDING_MODEL is already fully-qualified; do not re-prepend."
    )
    # And confirm the env var is used as the source (not hardcoded bare name).
    assert "LITELLM_EMBEDDING_MODEL" in text, (
        "init-weaviate.sh must read LITELLM_EMBEDDING_MODEL to source the model."
    )
