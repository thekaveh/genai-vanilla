"""BRAND_* fallback contract for the linear --no-tui banner.

``BannerDisplay._brand_credits`` / ``_brand_tagline`` read BRAND_* from
.env so a fork can rebrand the linear banner the same way the Textual
wizard's brand panel does, and must fall back to the upstream defaults
when .env is absent/unreadable — without ever throwing (a banner crash
must not abort startup). Only the Textual ``AppState`` path was covered;
the banner's fallback contract was not.
"""

from __future__ import annotations

from utils.banner import BannerDisplay

_DEFAULT_AUTHOR = "Developed by Kaveh Razavi"
_DEFAULT_REPO = "https://github.com/thekaveh/atlas"
_DEFAULT_LICENSE = "Apache License 2.0"
_DEFAULT_TAGLINE = (
    "A self-hosted, source-configurable multi-disciplinary engineering platform"
)


def _patch_env(monkeypatch, value):
    """Make ``ConfigParser().parse_env_file()`` return (or raise) ``value``.

    Also no-ops ``__init__`` so construction can't touch the real .env.
    """
    from core.config_parser import ConfigParser

    monkeypatch.setattr(ConfigParser, "__init__", lambda self, *a, **k: None)
    if isinstance(value, Exception):

        def boom(self):
            raise value

        monkeypatch.setattr(ConfigParser, "parse_env_file", boom)
    else:
        monkeypatch.setattr(ConfigParser, "parse_env_file", lambda self: value)


def test_brand_credits_honor_brand_env(monkeypatch):
    _patch_env(
        monkeypatch,
        {
            "BRAND_AUTHOR": "Acme Corp",
            "BRAND_REPO_URL": "https://example.com/acme/fork",
            "BRAND_LICENSE": "MIT",
        },
    )
    author, repo, lic = BannerDisplay()._brand_credits()
    assert author == "Developed by Acme Corp"
    assert repo == "https://example.com/acme/fork"
    assert lic == "MIT"


def test_brand_tagline_honors_brand_env(monkeypatch):
    _patch_env(monkeypatch, {"BRAND_TAGLINE": "Custom tagline"})
    assert BannerDisplay()._brand_tagline() == "Custom tagline"


def test_brand_credits_fall_back_to_upstream_defaults(monkeypatch):
    _patch_env(monkeypatch, {})  # no BRAND_* keys present
    assert BannerDisplay()._brand_credits() == (
        _DEFAULT_AUTHOR,
        _DEFAULT_REPO,
        _DEFAULT_LICENSE,
    )


def test_brand_tagline_falls_back_to_default(monkeypatch):
    _patch_env(monkeypatch, {})
    assert BannerDisplay()._brand_tagline() == _DEFAULT_TAGLINE


def test_brand_credits_survive_unreadable_env(monkeypatch):
    _patch_env(monkeypatch, RuntimeError("unreadable .env"))
    # Must not raise; returns upstream defaults.
    assert BannerDisplay()._brand_credits() == (
        _DEFAULT_AUTHOR,
        _DEFAULT_REPO,
        _DEFAULT_LICENSE,
    )


def test_brand_tagline_survives_unreadable_env(monkeypatch):
    _patch_env(monkeypatch, RuntimeError("unreadable .env"))
    assert BannerDisplay()._brand_tagline() == _DEFAULT_TAGLINE
