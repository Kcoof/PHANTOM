"""Passive: security headers & cookie flags (plan.md Part 6.2)."""
from __future__ import annotations

from core.scanner_engine import BaseScanCheck, register_check
from core.scanner_checks.base import body_of, headers_of

RECOMMENDED = {
    "strict-transport-security": ("Strict-transport-security (HSTS)", "CWE-319", "medium",
        "Force HTTPS with Strict-Transport-Security on HTTPS responses."),
    "content-security-policy": ("Content-Security-Policy", "CWE-693", "medium",
        "Add a Content-Security-Policy to mitigate XSS and injection vectors."),
    "x-frame-options": ("X-Frame-Options / frame-ancestors", "CWE-1021", "low",
        "Prevent clickjacking with X-Frame-Options: DENY/SAMEORIGIN (or CSP frame-ancestors)."),
    "x-content-type-options": ("X-Content-Type-Options", "CWE-430", "low",
        "Add X-Content-Type-Options: nosniff to stop MIME-type sniffing."),
}


class SecurityHeadersCheck(BaseScanCheck):
    name = "Missing Security Headers"
    check_type = "headers"
    severity = "low"
    cwe_id = "CWE-693"
    mode = "passive"

    async def check(self, entry: dict) -> list[dict]:
        if not entry.get("status_code"):
            return []
        headers = headers_of(entry)
        findings = []
        for key, (title, cwe, severity, remediation) in RECOMMENDED.items():
            if key == "strict-transport-security" and entry.get("scheme") != "https":
                continue
            csp = headers.get("content-security-policy", "")
            if key == "x-frame-options" and "frame-ancestors" in csp:
                continue
            if key not in headers:
                findings.append(
                    self.finding(
                        title=f"Missing {title}",
                        description=f"The response does not include the {key} header.",
                        severity=severity,
                        confidence="firm",
                        cwe_id=cwe,
                        url=entry["url"],
                        evidence=f"(header absent; {len(headers)} headers present)",
                        remediation=remediation,
                    )
                )
        return findings


class CookieFlagsCheck(BaseScanCheck):
    name = "Insecure Cookie Flags"
    check_type = "cookies"
    severity = "low"
    cwe_id = "CWE-1004"
    mode = "passive"

    async def check(self, entry: dict) -> list[dict]:
        if not entry.get("status_code"):
            return []
        headers = headers_of(entry)
        raw_cookies = headers.get("set-cookie", "")
        if not raw_cookies:
            return []
        import re

        cookies = re.split(r",(?=[^;]+?=)", raw_cookies)
        findings = []
        for cookie in cookies:
            name = cookie.split("=", 1)[0].strip()
            lower = cookie.lower()
            missing = []
            if "secure" not in lower:
                missing.append("Secure")
            if "httponly" not in lower:
                missing.append("HttpOnly")
            if "samesite" not in lower:
                missing.append("SameSite")
            if missing and name and not name.lower().startswith(("csrf", "xsrf")):
                findings.append(
                    self.finding(
                        title=f"Cookie '{name}' missing {', '.join(missing)}",
                        description=f"Set-Cookie for '{name}' lacks {', '.join(missing)} flag(s).",
                        severity="medium" if "Secure" in missing and entry.get("scheme") == "https" else "low",
                        confidence="firm",
                        cwe_id="CWE-1004",
                        url=entry["url"],
                        evidence=cookie[:300],
                        remediation="Set Secure; HttpOnly; SameSite=Lax (or Strict) on session cookies.",
                    )
                )
        return findings


register_check(SecurityHeadersCheck())
register_check(CookieFlagsCheck())
