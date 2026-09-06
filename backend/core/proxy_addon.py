"""mitmproxy addon — captures every flow into SQLite and broadcasts live events.

Capture pipeline (plan.md / research.md D1, D5):
  request → scope check → (intercept pause via asyncio.Event) → response → persist → broadcast.

Hooks are coroutines: mitmproxy awaits them on the shared event loop, so an awaited
Event pauses exactly that flow while the rest of the app keeps running.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import mitmproxy.http
from mitmproxy import ctx

from api.websocket import broadcast
from db import database
from utils.helpers import cap_body, is_text_content_type, url_in_scope
from utils.logger import get_logger

log = get_logger(__name__)

META_FLOW_ID = "phantom_flow_id"
META_START = "phantom_start"
META_INTERCEPTED = "phantom_intercepted"
META_IN_SCOPE = "phantom_in_scope"


@dataclass
class HeldFlow:
    flow_id: str
    method: str
    url: str
    headers: dict[str, str]
    body: Optional[str]
    content_type: Optional[str]
    resume: asyncio.Event = field(default_factory=asyncio.Event)
    action: str = "forward"  # or "drop"
    modified_request: Optional[str] = None


class PhantomAddon:
    """Attached to the mitmproxy master; routes flow events into PHANTOM."""

    def __init__(self) -> None:
        self.intercept_enabled = False
        self.intercept_filter = ""  # substring on "METHOD url"; empty = match all
        self.held: dict[str, HeldFlow] = {}
        self.captured_count = 0

    # --- mitmproxy hooks (coroutines — see module docstring) -----------------

    async def request(self, flow: mitmproxy.http.HTTPFlow) -> None:
        flow.metadata[META_FLOW_ID] = uuid.uuid4().hex[:12]
        flow.metadata[META_START] = time.monotonic()
        flow.metadata[META_INTERCEPTED] = False
        flow.metadata[META_IN_SCOPE] = await self._in_scope(flow)

        # Match & Replace (request side) — applied before intercept so the
        # held request shows exactly what will be sent (spec 003, FR-003).
        try:
            from core.rewrite_engine import apply_request_rules

            new_headers, new_body = await apply_request_rules(
                flow.request.method,
                flow.request.pretty_url,
                dict(flow.request.headers),
                flow.request.get_text(strict=False) or None,
            )
            if new_headers != dict(flow.request.headers):
                flow.request.headers.clear()
                for k, v in new_headers.items():
                    flow.request.headers[k] = v
            if new_body is not None:
                flow.request.text = new_body
        except Exception:
            log.exception("match&replace (request) failed")

        if self.intercept_enabled and self._matches_filter(flow):
            held = HeldFlow(
                flow_id=flow.metadata[META_FLOW_ID],
                method=flow.request.method,
                url=flow.request.pretty_url,
                headers=dict(flow.request.headers),
                body=cap_body(
                    flow.request.raw_content or b"",
                    is_text_content_type(flow.request.headers.get("content-type", "")),
                ),
                content_type=flow.request.headers.get("content-type"),
            )
            self.held[held.flow_id] = held
            flow.metadata[META_INTERCEPTED] = True
            await broadcast(
                "intercept_request",
                {"flow_id": held.flow_id, "method": held.method, "url": held.url},
            )
            await held.resume.wait()
            self.held.pop(held.flow_id, None)
            await broadcast(
                "intercept_resolved",
                {"flow_id": held.flow_id, "action": held.action},
            )
            if held.action == "drop":
                flow.kill()
                return
            if held.modified_request:
                self._apply_modified_request(flow, held.modified_request)

    async def response(self, flow: mitmproxy.http.HTTPFlow) -> None:
        # Match & Replace (response side) — rewrite before persistence so the
        # stored response matches what the client received.
        try:
            from core.rewrite_engine import apply_response_rules

            new_headers, new_body = await apply_response_rules(
                flow.response.status_code,
                dict(flow.response.headers),
                flow.response.get_text(strict=False) or None,
            )
            if new_headers != dict(flow.response.headers):
                flow.response.headers.clear()
                for k, v in new_headers.items():
                    flow.response.headers[k] = v
            if new_body is not None:
                flow.response.text = new_body
        except Exception:
            log.exception("match&replace (response) failed")
        try:
            await self._persist(flow)
        except Exception:
            log.exception("failed to persist flow %s", flow.request.pretty_url)

    def error(self, flow: mitmproxy.http.HTTPFlow) -> None:
        log.warning(
            "flow error: %s — %s",
            flow.request.pretty_url,
            getattr(flow, "error", None),
        )

    # --- helpers ------------------------------------------------------------

    async def _in_scope(self, flow: mitmproxy.http.HTTPFlow) -> bool:
        try:
            return await url_in_scope(flow.request.pretty_url)
        except Exception:
            log.exception("scope evaluation failed; treating as in-scope")
            return True

    def _matches_filter(self, flow: mitmproxy.http.HTTPFlow) -> bool:
        if not self.intercept_filter:
            return True
        needle = self.intercept_filter.lower()
        return needle in f"{flow.request.method} {flow.request.pretty_url}".lower()

    @staticmethod
    def _apply_modified_request(flow: mitmproxy.http.HTTPFlow, raw: str) -> None:
        """Apply user-edited raw HTTP request text onto the held flow."""
        try:
            head, _, body = raw.partition("\n\n")
            lines = [ln for ln in head.splitlines() if ln.strip()]
            if lines:
                parts = lines[0].split()
                if len(parts) >= 2:
                    flow.request.method = parts[0].upper()
                    flow.request.path = parts[1]
            flow.request.headers.clear()
            for line in lines[1:]:
                if ":" in line:
                    name, _, value = line.partition(":")
                    if name.strip().lower() not in ("content-length",):
                        flow.request.headers[name.strip()] = value.strip()
            flow.request.content = body.encode("utf-8") if body else b""
        except Exception:
            log.exception("failed to apply modified intercept request")

    async def _persist(self, flow: mitmproxy.http.HTTPFlow) -> None:
        started = flow.metadata.get(META_START, time.monotonic())
        req, resp = flow.request, flow.response
        req_headers = dict(req.headers)
        req_ct = req_headers.get("content-type")
        resp_headers = dict(resp.headers) if resp else None
        resp_ct = (resp_headers or {}).get("content-type")
        from urllib.parse import urlsplit

        parts = urlsplit(req.pretty_url)
        entry_id = await database.execute(
            """INSERT INTO proxy_history
               (method, scheme, host, port, path, query_string, url,
                request_headers, request_body, request_content_type,
                status_code, response_headers, response_body, response_content_type,
                response_time_ms, size_bytes, is_intercepted, is_in_scope)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                req.method,
                parts.scheme,
                parts.hostname or "",
                parts.port or (443 if parts.scheme == "https" else 80),
                parts.path or "/",
                parts.query or None,
                req.pretty_url,
                json.dumps(req_headers),
                cap_body(req.raw_content or b"", is_text_content_type(req_ct)),
                req_ct,
                resp.status_code if resp else None,
                json.dumps(resp_headers) if resp_headers else None,
                (
                    cap_body(resp.raw_content or b"", is_text_content_type(resp_ct))
                    if resp
                    else None
                ),
                resp_ct,
                int((time.monotonic() - started) * 1000),
                len(resp.raw_content or b"") if resp else 0,
                1 if flow.metadata.get(META_INTERCEPTED) else 0,
                1 if flow.metadata.get(META_IN_SCOPE, True) else 0,
            ),
        )
        self.captured_count += 1
        await broadcast(
            "new_request",
            {
                "id": entry_id,
                "method": req.method,
                "host": parts.hostname or "",
                "path": parts.path or "/",
                "query_string": parts.query or None,
                "url": req.pretty_url,
                "status_code": resp.status_code if resp else None,
                "response_time_ms": int((time.monotonic() - started) * 1000),
                "size_bytes": len(resp.raw_content or b"") if resp else 0,
                "is_in_scope": 1 if flow.metadata.get(META_IN_SCOPE, True) else 0,
            },
        )

    # --- intercept controls (called from the API layer) ----------------------

    def queue_snapshot(self) -> list[dict]:
        return [
            {
                "flow_id": h.flow_id,
                "method": h.method,
                "url": h.url,
                "headers": h.headers,
                "body": h.body,
                "content_type": h.content_type,
            }
            for h in self.held.values()
        ]

    def forward(self, flow_id: str, modified_request: Optional[str] = None) -> bool:
        held = self.held.get(flow_id)
        if not held:
            return False
        if modified_request:
            held.modified_request = modified_request
        held.action = "forward"
        held.resume.set()
        return True

    def drop(self, flow_id: str) -> bool:
        held = self.held.get(flow_id)
        if not held:
            return False
        held.action = "drop"
        held.resume.set()
        return True

    def drop_all(self) -> int:
        ids = list(self.held.keys())
        for fid in ids:
            self.drop(fid)
        return len(ids)
