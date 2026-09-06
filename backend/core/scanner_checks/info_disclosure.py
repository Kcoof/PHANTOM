"""Passive: information disclosure (plan.md Part 6.2)."""
from __future__ import annotations

import re

from core.scanner_checks.base import body_of, headers_of
from core.scanner_engine import BaseScanCheck, register_check

STACK_PATTERNS = [
    (r"Traceback \(most recent call last\)", "Python traceback"),
    (r"at [\w$.]+\([\w$.]*\.java:\d+\)", "Java stack trace"),
    (r"\.php on line \d+", "PHP error disclosure"),
    (r"Warning:.*\[function\.", "PHP warning"),
    (r"System\.NullReferenceException", ".NET exception"),
    (r"Microsoft \[SQL Server\]|MySQLSyntaxErrorException|ORA-\d{5}|PSQLException", "Database error message"),
]
INTERNAL_IP_RE = re.compile(r"\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b")
VERSION_SERVER_RE = re.compile(r"(nginx|apache|iis|jetty|tomcat|express|gunicorn|werkzeug|uvicorn)[/\s]([\d.]+)", re.I)


class InfoDisclosureCheck(BaseScanCheck):
    name = "Information Disclosure"
    check_type = "info_disclosure"
    severity = "info"
    cwe_id = "CWE-200"
    mode = "passive"

    async def check(self, entry: dict) -> list[dict]:
        if not entry.get("status_code"):
            return []
        findings = []
        headers = headers_of(entry)
        body = body_of(entry)

        for header in ("server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version"):
            value = headers.get(header)
            if value and VERSION_SERVER_RE.search(f"{header}: {value}"):
                findings.append(
                    self.finding(
                        title=f"Version disclosure via {header} header",
                        description=f"The {header} header reveals technology/version: {value}.",
                        severity="info",
                        confidence="certain",
                        cwe_id=self.cwe_id,
                        url=entry["url"],
                        evidence=f"{header}: {value}",
                        remediation=f"Remove or sanitize the {header} response header.",
                    )
                )
            elif value and header == "x-powered-by":
                findings.append(
                    self.finding(
                        title="Technology disclosure via X-Powered-By",
                        description=f"X-Powered-By reveals the stack: {value}.",
                        severity="info",
                        confidence="certain",
                        cwe_id=self.cwe_id,
                        url=entry["url"],
                        evidence=f"x-powered-by: {value}",
                        remediation="Disable the X-Powered-By header.",
                    )
                )

        for pattern, label in STACK_PATTERNS:
            match = re.search(pattern, body)
            if match:
                snippet = body[max(0, match.start() - 60) : match.start() + 220]
                findings.append(
                    self.finding(
                        title=f"{label} in response body",
                        description=f"Response contains a {label}, disclosing internal implementation details.",
                        severity="medium",
                        confidence="firm",
                        cwe_id=self.cwe_id,
                        url=entry["url"],
                        evidence=snippet,
                        remediation="Disable detailed errors in production; return generic error pages.",
                    )
                )
                break

        ip = INTERNAL_IP_RE.search(body[:20000])
        if ip:
            findings.append(
                self.finding(
                    title=f"Internal IP address in response ({ip.group(1)})",
                    description="A private-range IP appears in the response body, hinting at internal network layout.",
                    severity="info",
                    confidence="tentative",
                    cwe_id=self.cwe_id,
                    url=entry["url"],
                    evidence=body[max(0, ip.start() - 50) : ip.start() + 80],
                    remediation="Avoid leaking internal addresses in client-visible content.",
                )
            )
        return findings


register_check(InfoDisclosureCheck())
