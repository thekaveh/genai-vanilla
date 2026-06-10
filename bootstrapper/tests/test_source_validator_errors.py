"""SourceValidator error accumulation across multiple invalid SOURCEs.

Regression guard: validate_source_value() used to reset the shared
validation_errors list on every call, so a .env with two invalid SOURCE
values (followed by valid ones) failed validation while reporting zero
errors — start.py then printed "✅ All SOURCE values are valid"
immediately before sys.exit(1).
"""
from __future__ import annotations

import shutil
from pathlib import Path
from core.config_parser import ConfigParser
from services.source_validator import SourceValidator


REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = REPO_ROOT / ".env.example"


def _validator(tmp_path: Path, overrides: dict) -> SourceValidator:
    env_path = tmp_path / ".env"
    shutil.copy(ENV_EXAMPLE, env_path)
    text = env_path.read_text(encoding="utf-8")
    out = []
    for line in text.splitlines():
        key = line.split("=", 1)[0] if "=" in line else None
        out.append(f"{key}={overrides[key]}" if key in overrides else line)
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    cp = ConfigParser(str(REPO_ROOT))
    cp.env_file_path = env_path
    return SourceValidator(config_parser=cp)


def test_multiple_invalid_sources_all_reported(tmp_path):
    v = _validator(tmp_path, {
        "COMFYUI_SOURCE": "bogus-value",
        "WEAVIATE_SOURCE": "also-bogus",
    })
    assert v.validate_all_sources() is False
    errors = v.get_validation_errors()
    joined = "\n".join(errors)
    assert "COMFYUI_SOURCE" in joined
    assert "WEAVIATE_SOURCE" in joined


def test_single_invalid_source_not_wiped_by_later_valid_ones(tmp_path):
    """An early invalid SOURCE must survive validation of later valid vars."""
    v = _validator(tmp_path, {"COMFYUI_SOURCE": "bogus-value"})
    assert v.validate_all_sources() is False
    assert any("COMFYUI_SOURCE" in e for e in v.get_validation_errors())


def test_default_env_example_is_valid(tmp_path):
    v = _validator(tmp_path, {})
    assert v.validate_all_sources() is True
    assert v.get_validation_errors() == []
