"""Shared helpers for scan checks."""
from __future__ import annotations

import json
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from utils.helpers import url_in_scope


def headers_of(entry: dict, side: str = "response") -> dict[str, str]:
    try:
        raw = entry.get(f"{side}_headers") or "{}"
        return {k.lower(): v for k, v in json.loads(raw).items()}
    except json.JSONDecodeError:
        return {}


def body_of(entry: dict, side: str = "response") -> str:
    return entry.get(f"{side}_body") or ""


def params_of(entry: dict) -> dict[str, str]:
    """Query params + urlencoded body params (single-valued)."""
    result: dict[str, str] = {}
    qs = entry.get("query_string") or urlsplit(entry["url"]).query
    result.update(dict(parse_qsl(qs, keep_blank_values=True)))
    req_ct = headers_of(entry, "request").get("content-type", "")
    body = body_of(entry, "request")
    if "urlencoded" in req_ct and body:
        result.update(dict(parse_qsl(body, keep_blank_values=True)))
    return result


def set_query_param(url: str, param: str, value: str) -> str:
    parts = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != param]
    q.append((param, value))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


async def send_variant(
    method: str,
    url: str,
    headers: dict[str, str],
    content: bytes | None,
    timeout: float = 15.0,
) -> httpx.Response | None:
    """Send a modified request if the URL is in scope; None if out of scope/failed."""
    if not await url_in_scope(url):
        return None
    clean = {k: v for k, v in headers.items() if k.lower() not in ("host", "content-length", "connection", "accept-encoding")}
    try:
        async with httpx.AsyncClient(follow_redirects=False, verify=False, timeout=timeout) as client:
            return await client.request(method, url, headers=clean, content=content)
    except httpx.HTTPError:
        return None
