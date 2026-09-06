"""Passive: JWT issues (plan.md Part 6.2)."""
from __future__ import annotations

import base64
import binascii
import json
import re
import time

from core.scanner_checks.base import body_of, headers_of
from core.scanner_engine import BaseScanCheck, register_check

JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]*)?")


def _b64decode(part: str) -> dict | None:
    padded = part + "=" * (-len(part) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(padded))
    except (binascii.Error, json.JSONDecodeError, ValueError):
        return None


class JwtCheck(BaseScanCheck):
    name = "JWT Issues"
    check_type = "jwt"
    severity = "high"
    cwe_id = "CWE-347"
    mode = "passive"

    async def check(self, entry: dict) -> list[dict]:
        haystack = " ".join(
            [
                headers_of(entry, "request").get("authorization", ""),
                headers_of(entry, "request").get("cookie", ""),
                body_of(entry, "request") or "",
                body_of(entry) or "",
            ]
        )
        findings = []
        for match in JWT_RE.finditer(haystack):
            token = match.group(0)
            parts = token.split(".")
            header = _b64decode(parts[0]) if len(parts) >= 2 else None
            payload = _b64decode(parts[1]) if len(parts) >= 2 else None
            if not header:
                continue
            alg = str(header.get("alg", "")).lower()
            if alg in ("none", ""):
                findings.append(
                    self.finding(
                        title="JWT uses 'none' algorithm",
                        description="A JWT is signed with (or requests) the 'none' algorithm, allowing unsigned tokens.",
                        severity="critical",
                        confidence="firm",
                        cwe_id=self.cwe_id,
                        url=entry["url"],
                        payload=token[:80] + "…",
                        evidence=f"header: {json.dumps(header)}",
                        remediation="Reject 'none' algorithm tokens; enforce an allow-list of asymmetric/HMAC algorithms server-side.",
                    )
                )
            elif alg.startswith("hs") and entry.get("scheme") != "https":
                findings.append(
                    self.finding(
                        title="HMAC JWT transmitted over plain HTTP",
                        description="An HS-signed JWT travels unencrypted; it can be sniffed and replayed.",
                        severity="high",
                        confidence="firm",
                        cwe_id=self.cwe_id,
                        url=entry["url"],
                        evidence=f"alg={alg}, scheme={entry.get('scheme')}",
                        remediation="Serve authenticated traffic over HTTPS only.",
                    )
                )
            if isinstance(payload, dict) and "exp" in payload and isinstance(payload["exp"], (int, float)):
                if payload["exp"] < time.time():
                    findings.append(
                        self.finding(
                            title="Expired JWT accepted",
                            description="The request carries a JWT whose exp is in the past but the server still processed it.",
                            severity="high",
                            confidence="firm",
                            cwe_id=self.cwe_id,
                            url=entry["url"],
                            evidence=f"exp={payload['exp']} (now={int(time.time())})",
                            remediation="Enforce exp validation on every authenticated request.",
                        )
                    )
            if isinstance(payload, dict) and "exp" not in payload:
                findings.append(
                    self.finding(
                        title="JWT without expiration claim",
                        description="The JWT payload has no exp claim, so stolen tokens never expire.",
                        severity="medium",
                        confidence="firm",
                        cwe_id=self.cwe_id,
                        url=entry["url"],
                        evidence=f"payload keys: {', '.join(payload.keys())[:200]}",
                        remediation="Issue short-lived JWTs with an exp claim and rotate refresh tokens.",
                    )
                )
            break  # first token per entry is enough
        return findings


register_check(JwtCheck())
