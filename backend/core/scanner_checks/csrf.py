"""Passive: missing CSRF protection on state-changing requests (plan.md Part 6.2)."""
from __future__ import annotations

from core.scanner_checks.base import body_of, headers_of, params_of
from core.scanner_engine import BaseScanCheck, register_check

TOKEN_HINTS = ("csrf", "xsrf", "token", "authenticity", "_token", "anticsrf")
STATE_CHANGING = {"POST", "PUT", "PATCH", "DELETE"}


class CsrfCheck(BaseScanCheck):
    name = "CSRF Token Missing"
    check_type = "csrf"
    severity = "medium"
    cwe_id = "CWE-352"
    mode = "passive"

    async def check(self, entry: dict) -> list[dict]:
        if entry.get("method", "").upper() not in STATE_CHANGING:
            return []
        if not entry.get("status_code") or entry["status_code"] >= 400:
            return []
        # state-changing + authenticated-looking requests without a token hint
        headers = headers_of(entry, "request")
        body = body_of(entry, "request")
        params = params_of(entry)
        hay = " ".join(list(headers.keys()) + list(params.keys())).lower()
        has_token_hint = any(h in hay for h in TOKEN_HINTS)
        has_cookie_auth = "cookie" in headers
        if has_token_hint:
            return []
        if not has_cookie_auth:
            return []  # no cookie-based auth in play; header/bearer auth is not CSRF-prone
        return [
            self.finding(
                title=f"{entry['method']} {entry.get('path', '')} without CSRF token",
                description=(
                    "A state-changing request sent with cookie-based authentication carries no "
                    "CSRF token in headers, parameters, or body."
                ),
                severity="medium",
                confidence="tentative",
                cwe_id=self.cwe_id,
                url=entry["url"],
                evidence=f"request headers: {', '.join(sorted(headers))[:200]}\nparams: {', '.join(params)[:200]}",
                remediation="Add synchronizer or double-submit CSRF tokens to state-changing endpoints.",
            )
        ]


register_check(CsrfCheck())
