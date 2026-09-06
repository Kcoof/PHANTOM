"""Shared helpers: body extraction with caps, scope evaluation, content typing."""
from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlsplit

import config
from db import database

_TEXT_RE = re.compile(r"(text/|json|xml|javascript|x-www-form-urlencoded|urlencoded)", re.I)


def is_text_content_type(content_type: Optional[str]) -> bool:
    if not content_type:
        return True  # assume text when unspecified
    return bool(_TEXT_RE.search(content_type))


def cap_body(data: bytes, is_text: bool) -> str:
    """Return a persisted, size-capped string form of a body (data-model D10)."""
    if data is None:
        return None  # type: ignore[return-value]
    truncated = len(data) > config.MAX_BODY_BYTES
    blob = data[: config.MAX_BODY_BYTES]
    if is_text:
        text = blob.decode("utf-8", errors="replace")
    else:
        text = blob.hex()
    if truncated:
        text += config.TRUNCATION_MARKER.format(n=len(data) - config.MAX_BODY_BYTES)
    return text


def parse_bool(value: str) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class CompiledScope:
    includes: list[dict]
    excludes: list[dict]


async def load_scope() -> CompiledScope:
    rows = await database.fetch_all(
        "SELECT * FROM scope_rules WHERE is_active = 1 ORDER BY id"
    )
    return CompiledScope(
        includes=[r for r in rows if r["rule_type"] == "include"],
        excludes=[r for r in rows if r["rule_type"] == "exclude"],
    )


def _host_pattern_matches(pattern: str, host: str) -> bool:
    """Subdomain-aware host matching (Burp-style 'include all subdomains').

    - `example.com` matches example.com AND any subdomain (a.example.com)
    - `*.example.com` matches subdomains AND the apex example.com
    - `api.example.com` matches itself and anything under it
    - suffix-safe: `notexample.com` does NOT match `example.com`
    """
    p = pattern.lower().strip()
    h = host.lower().strip()
    if h == p or fnmatch.fnmatch(h, p):
        return True
    base = p[2:] if p.startswith("*.") else p
    return h == base or h.endswith("." + base)


def _rule_matches(rule: dict, scheme: str, host: str, port: int, path: str) -> bool:
    protocol = rule.get("protocol")
    if protocol and protocol not in ("any", None, "", scheme):
        return False
    if not _host_pattern_matches(rule["host_pattern"], host):
        return False
    rport = rule.get("port")
    if rport and str(rport).lower() not in ("any", "", str(port)):
        return False
    path_pattern = rule.get("path_pattern") or ".*"
    try:
        if not re.fullmatch(path_pattern, path or "/"):
            return False
    except re.error:
        return False
    return True


async def url_in_scope(url: str) -> bool:
    """include/exclude evaluation per data-model.md; no rules → everything in scope."""
    parts = urlsplit(url)
    scope = await load_scope()
    scheme, host = parts.scheme, (parts.hostname or "")
    port = parts.port or (443 if scheme == "https" else 80)
    path = parts.path or "/"
    if any(_rule_matches(r, scheme, host, port, path) for r in scope.excludes):
        return False
    if not scope.includes:
        return True
    return any(_rule_matches(r, scheme, host, port, path) for r in scope.includes)


def parse_tags(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else []
    except (json.JSONDecodeError, TypeError):
        return []
