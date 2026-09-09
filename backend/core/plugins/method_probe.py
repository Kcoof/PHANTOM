"""Method Probe — HTTP verb tampering detection (spec 007).

Tries alternative HTTP methods on an endpoint and flags dangerous behavior:
unexpected allowed methods, TRACE/XST reflection, PUT/DELETE acceptance,
DEBUG-style information leaks, and method override headers.
"""
from __future__ import annotations

from core.plugin_framework import PhantomPlugin, register, resolve_request_context
from core.scanner_checks.base import send_variant
from db import database
from utils.helpers import url_in_scope

METHODS = ["OPTIONS", "TRACE", "PUT", "DELETE", "PATCH", "HEAD", "DEBUG", "CONNECT"]
BASELINE_TIMEOUT = 15.0


class MethodProbePlugin(PhantomPlugin):
    id = "method-probe"
    name = "Method Probe"
    description = (
        "Probes alternative HTTP methods (OPTIONS, TRACE, PUT, DELETE, PATCH, DEBUG, …) on an "
        "endpoint and flags verb tampering: unexpected allows, TRACE reflection (XST), "
        "state-changing methods on read endpoints, and verbose method errors."
    )
    accepts = ["request"]
    parameters = []

    async def run(self, context: dict, options: dict, emit) -> None:
        req = await resolve_request_context(context)
        url = req["url"]
        if not await url_in_scope(url):
            raise RuntimeError(f"target out of scope: {url} — add an include rule in Settings → Scope")

        headers = {k: v for k, v in req["headers"].items()
                   if k.lower() not in ("host", "content-length", "connection", "accept-encoding")}
        body = req.get("body")
        content = body.encode("utf-8") if body else None
        base_method = req["method"].upper()

        await emit("info", {"message": f"probing {len(METHODS)} methods on {base_method} {url}", "history_id": context.get("history_id")})

        found = 0
        for m in METHODS:
            resp = await send_variant(m, url, headers, content, timeout=BASELINE_TIMEOUT)
            if resp is None:
                continue
            issues = self._assess(m, resp, base_method)
            if not issues:
                continue
            for severity, title, evidence in issues:
                found += 1
                await emit("method", {"method": m, "title": title, "severity": severity,
                                      "evidence": evidence, "status": resp.status_code, "url": url})
                await self._finding(url, m, severity, title, evidence)
        await emit("summary", {"found": found})

    def _assess(self, method, resp, base_method):
        issues = []
        allow = resp.headers.get("allow", "")
        text = resp.text or ""
        if method == "TRACE" and resp.status_code == 200 and ("TRACE /" in text or "X-" in text[:200]):
            issues.append(("medium", "TRACE enabled (Cross-Site Tracing)", f"TRACE reflected: {text[:120]}"))
        if method in ("PUT", "DELETE", "PATCH") and resp.status_code in (200, 201, 204) and base_method == "GET":
            issues.append(("high", f"{method} accepted on a read endpoint",
                           f"{method} returned {resp.status_code} (no auth challenge) — possible state change / upload"))
        if method == "DEBUG" and resp.status_code == 200 and len(text) > 200:
            issues.append(("medium", "DEBUG method leaks details", f"DEBUG returned {len(text)}B of diagnostics"))
        if method == "OPTIONS":
            unexpected = [m for m in ("PUT", "DELETE", "TRACE", "PATCH", "DEBUG") if m in allow.upper()]
            if unexpected:
                issues.append(("low", f"OPTIONS advertises risky methods: {', '.join(unexpected)}", f"Allow: {allow}"))
        if resp.status_code == 405 and allow:
            return issues  # clean rejection with allow info — fine
        if resp.status_code >= 500:
            issues.append(("low", f"{method} causes server error", f"{method} -> {resp.status_code}"))
        return issues

    async def _finding(self, url, method, severity, title, evidence):
        existing = await database.fetch_one(
            "SELECT id FROM scanner_findings WHERE finding_type = ? AND url = ? AND parameter IS ?",
            ("verb_tamper", url, method),
        )
        if existing:
            return
        await database.execute(
            """INSERT INTO scanner_findings
               (scan_id, finding_type, severity, confidence, title, description, url,
                parameter, evidence, remediation)
               VALUES ('plugin', 'verb_tamper', ?, 'firm', ?, ?, ?, ?, ?, ?)""",
            (
                severity, title,
                f"HTTP verb tampering: {title}. The endpoint behaves differently under {method}.",
                url, method, evidence,
                "Restrict allowed methods per endpoint; disable TRACE/DEBUG in production; "
                "require authorization for state-changing methods.",
            ),
        )


register(MethodProbePlugin())
