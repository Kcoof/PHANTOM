"""Shared helpers for scan checks."""
from __future__ import annotations

import asyncio
import json
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

from utils.helpers import url_in_scope

# Politeness throttle for active probes (spec 002, FR-004): a semaphore caps
# concurrent sends and every send waits `delay_s` — configured by the engine
# from scanner settings before each scan.
_probe_semaphore = asyncio.Semaphore(4)
_probe_delay_s = 0.25
_last_probe_at: float = 0.0
_throttle_lock = asyncio.Lock()


def configure_throttle(concurrency: int, delay_s: float) -> None:
    """Set the global probe throttle (called at scan start)."""
    global _probe_semaphore, _probe_delay_s
    _probe_delay_s = max(0.0, delay_s)
    try:
        _probe_semaphore = asyncio.Semaphore(max(1, int(concurrency)))
    except (TypeError, ValueError):
        pass


async def _respect_throttle() -> None:
    global _last_probe_at
    async with _throttle_lock:
        now = asyncio.get_event_loop().time()
        wait = _last_probe_at + _probe_delay_s - now
        if wait > 0:
            await asyncio.sleep(wait)
        _last_probe_at = asyncio.get_event_loop().time()


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
    """Send a modified request if the URL is in scope; None if out of scope/failed.

    Every send passes the global throttle (concurrency cap + delay).
    """
    if not await url_in_scope(url):
        return None
    clean = {k: v for k, v in headers.items() if k.lower() not in ("host", "content-length", "connection", "accept-encoding")}
    async with _probe_semaphore:
        await _respect_throttle()
        try:
            async with httpx.AsyncClient(follow_redirects=False, verify=False, timeout=timeout) as client:
                return await client.request(method, url, headers=clean, content=content)
        except httpx.HTTPError:
            return None
