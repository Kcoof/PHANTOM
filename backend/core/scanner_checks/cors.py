"""Passive: CORS misconfiguration (plan.md Part 6.2)."""
from __future__ import annotations

from core.scanner_checks.base import headers_of
from core.scanner_engine import BaseScanCheck, register_check


class CorsCheck(BaseScanCheck):
    name = "CORS Misconfiguration"
    check_type = "cors"
    severity = "medium"
    cwe_id = "CWE-942"
    mode = "passive"

    async def check(self, entry: dict) -> list[dict]:
        headers = headers_of(entry)
        acao = headers.get("access-control-allow-origin", "")
        acac = headers.get("access-control-allow-credentials", "")
        if not acao:
            return []
        findings = []
        if acao.strip() == "*":
            sev, desc = (
                ("high", "Wildcard CORS origin combined with credentials mode is browser-blocked, but reflects a permissive policy.")
                if acac.lower() == "true"
                else ("medium", "Any origin can read responses from this endpoint (Access-Control-Allow-Origin: *).")
            )
            findings.append(
                self.finding(
                    title="Wildcard CORS origin (ACAO: *)",
                    description=desc,
                    severity=sev,
                    confidence="firm",
                    cwe_id=self.cwe_id,
                    url=entry["url"],
                    evidence=f"access-control-allow-origin: {acao}\naccess-control-allow-credentials: {acac or '(absent)'}",
                    remediation="Restrict Access-Control-Allow-Origin to trusted origins; never combine '*' with credentials.",
                )
            )
        elif "null" == acao.strip().lower():
            findings.append(
                self.finding(
                    title="CORS allows null origin",
                    description="Access-Control-Allow-Origin reflects 'null', exploitable from sandboxed iframes.",
                    severity="medium",
                    confidence="firm",
                    cwe_id=self.cwe_id,
                    url=entry["url"],
                    evidence=f"access-control-allow-origin: {acao}",
                    remediation="Do not allow the null origin; whitelist concrete trusted origins.",
                )
            )
        return findings


register_check(CorsCheck())
