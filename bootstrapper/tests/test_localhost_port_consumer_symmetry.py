"""Regression test for the asymmetric-override class documented in
`feedback_localhost_url_override_symmetry.md`.

The wizard writes each localhost-source port override to a
`<SERVICE>_LOCALHOST_PORT` variable in `.env`
(`test_localhost_port_override.py` already covers that direction).
But the consumer side — `bootstrapper/services/service_config.py`,
which assembles the in-container `<SERVICE>_ENDPOINT` values used by
LiteLLM, OpenClaw, Open-WebUI, etc. — must read THE SAME `_LOCALHOST_PORT`
var when the source is `localhost`. Reading the container's
host-bound port var (e.g. `HERMES_API_PORT`, `OPENCLAW_GATEWAY_PORT`,
`DOC_PROCESSOR_PORT`) silently strands every wizard-supplied port
override — the user's stack works but every consumer points at the
default container port.

This bug shipped to main three times (docling, hermes, openclaw) before
the Pass 2 audit caught it. This test prevents the next instance by
asserting that EVERY `<X>_LOCALHOST_PORT` declared in `.env.example`
appears as a literal string somewhere in `service_config.py`. The
literal-string check is intentionally crude — it doesn't validate that
the reference is structurally correct (e.g. consumed in a `localhost`
branch), only that the consumer knows the name exists. Combined with
`test_localhost_port_override.py` (wizard side) it forces both sides of
the symmetry to stay in sync.

Exclusions are explicit: `BASE_PORT` and any LOCALHOST_PORT for which the
consumer pipeline genuinely doesn't exist yet (e.g. provider-only
variants that don't have a downstream `_ENDPOINT` emit step) are listed
in `_KNOWN_NO_CONSUMER`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_EXAMPLE = REPO_ROOT / ".env.example"
SERVICE_CONFIG = REPO_ROOT / "bootstrapper" / "services" / "service_config.py"
SERVICES_ROOT = REPO_ROOT / "services"


_LOCALHOST_PORT_PATTERN = re.compile(r"^([A-Z][A-Z0-9_]*_LOCALHOST_PORT)=", re.MULTILINE)


def _consumer_source_text() -> str:
    """All the places a `<X>_LOCALHOST_PORT` var can legitimately be read
    to build an in-container endpoint:

    - `bootstrapper/services/service_config.py` — where Python code
      assembles `<X>_ENDPOINT` for consumers (used when the localhost
      source has `scale: 0` and there's no container env block to
      interpolate into).
    - `services/<X>/service.yml` runtime_sc — where Compose-level
      `${...}` interpolation injects the var into the producer
      container's runtime env block.

    Either path is correct. The asymmetric-override bug only fires when
    NEITHER path references the localhost port var.
    """
    parts = [SERVICE_CONFIG.read_text(encoding="utf-8")]
    for sy in sorted(SERVICES_ROOT.glob("*/service.yml")):
        parts.append(sy.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


# LOCALHOST_PORTs that intentionally have no in-container consumer yet.
# The wizard still writes them (so users can override the host port), but
# no `<X>_ENDPOINT` is emitted downstream because nothing in the stack
# calls them in-container with that hostname. When a consumer lands, the
# matching name moves OUT of this set and the test below enforces the
# symmetry.
_KNOWN_NO_CONSUMER: set[str] = {
    # Provider-internal services — Open-WebUI talks to the *engine*
    # directly via AUDIO_*_OPENAI_API_BASE_URL, not via a generic
    # *_ENDPOINT plumbed through service_config.
    "PARAKEET_LOCALHOST_PORT",
    "WHISPER_CPP_LOCALHOST_PORT",
    "CHATTERBOX_LOCALHOST_PORT",
    # Direct Bolt-protocol connection from a few clients; no
    # auto-generated NEO4J_BOLT_ENDPOINT today.
    "NEO4J_LOCALHOST_BOLT_PORT",
}


def _localhost_port_vars() -> list[str]:
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    names = sorted(set(_LOCALHOST_PORT_PATTERN.findall(text)))
    return [n for n in names if n not in _KNOWN_NO_CONSUMER]


@pytest.mark.parametrize("var_name", _localhost_port_vars())
def test_localhost_port_var_referenced_by_consumer(var_name: str) -> None:
    """`var_name` (a `<X>_LOCALHOST_PORT` env var) must be CONSUMED
    either by `service_config.py` (Python-built endpoint) OR by a
    `services/*/service.yml` runtime_sc block (Compose `${...}`
    interpolation). Either path correctly plumbs the wizard's port
    override into the in-container endpoint.

    "Consumed" means a real READ pattern — `${VAR...}` interpolation
    or a Python string literal like `'VAR'`. Bare declarations on env:
    or row metadata lines don't count, because those are how the var is
    SURFACED but not how it's READ. The bug we're guarding against is
    exactly the case where the var is declared everywhere but read
    nowhere on the consumer side.

    See module docstring for the full asymmetric-override failure mode.
    """
    text = _consumer_source_text()
    compose_interp = f"${{{var_name}"           # ${VAR or ${VAR:-default}
    python_literal_single = f"'{var_name}'"     # 'VAR' as a string literal
    python_literal_double = f'"{var_name}"'     # "VAR" as a string literal

    consumed = (
        compose_interp in text
        or python_literal_single in text
        or python_literal_double in text
    )

    assert consumed, (
        f"{var_name} is declared in .env.example but is NOT consumed by "
        f"any of:\n"
        f"  - `${{{var_name}:-...}}` interpolation in a "
        f"services/*/service.yml runtime_sc block\n"
        f"  - `current_env.get('{var_name}', ...)` in "
        f"bootstrapper/services/service_config.py\n\n"
        f"The wizard writes the user's host port to this var, but no "
        f"in-container ENDPOINT generator reads it — so the override "
        f"silently dies. This is the asymmetric-override class "
        f"documented in feedback_localhost_url_override_symmetry.md.\n\n"
        f"Either:\n"
        f"  1. Add a `${{{var_name}:-...}}` interpolation in the "
        f"     service's runtime_sc.environment block (preferred when "
        f"     the localhost variant runs a container), OR\n"
        f"  2. Add a `_LOCALHOST` branch in service_config.py that "
        f"     reads `{var_name}` to build the corresponding ENDPOINT "
        f"     (when the container is disabled), OR\n"
        f"  3. If this service genuinely has no in-container consumer, "
        f"     add `{var_name}` to _KNOWN_NO_CONSUMER in this test file "
        f"     with a comment explaining why."
    )


def test_known_no_consumer_set_doesnt_grow_silently() -> None:
    """Sanity check: _KNOWN_NO_CONSUMER should be deliberate. If a future
    contributor moves something INTO this set, they must justify it in
    the docstring comment above. If they REMOVE one (because a consumer
    landed), the parametrised test above starts enforcing the read.
    """
    assert len(_KNOWN_NO_CONSUMER) <= 6, (
        "_KNOWN_NO_CONSUMER has grown past the expected size. Each entry "
        "should be justified inline — silent growth means the symmetry "
        "test is losing coverage."
    )
