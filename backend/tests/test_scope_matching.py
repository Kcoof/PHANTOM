"""Scope matching semantics — domain covers itself + all subdomains (Burp-style)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.helpers import _host_pattern_matches as m


def test_bare_domain_covers_apex_and_subdomains():
    assert m("example.com", "example.com")
    assert m("example.com", "www.example.com")
    assert m("example.com", "deep.api.example.com")


def test_wildcard_covers_subdomains_and_apex():
    assert m("*.example.com", "example.com")
    assert m("*.example.com", "api.example.com")
    assert m("*.example.com", "x.y.example.com")


def test_suffix_safety():
    assert not m("example.com", "notexample.com")
    assert not m("example.com", "example.com.evil.io")
    assert not m("*.example.com", "notexample.com")


def test_exact_subdomain_rule_covers_its_own_children_only():
    assert m("api.example.com", "api.example.com")
    assert m("api.example.com", "v2.api.example.com")
    assert not m("api.example.com", "example.com")
    assert not m("api.example.com", "other.example.com")


def test_case_and_spacing_insensitive():
    assert m("Example.COM", "  WWW.example.com  ".strip())


def test_no_accidental_cross_domain():
    assert not m("microsoft.com", "microsoft.com.attacker.net")
    assert not m("*.microsoft.com", "microsoft.com.evil.io")
