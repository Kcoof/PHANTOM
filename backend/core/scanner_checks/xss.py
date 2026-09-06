"""Active: reflected XSS (plan.md Part 6.2). Sends canary payloads, checks reflection."""
from __future__ import annotations

import html as html_lib

from core.scanner_checks.base import headers_of, params_of, send_variant, set_query_param
from core.scanner_engine import BaseScanCheck, register_check

CANARY = "ph4nt0m"
PAYLOAD = "<svG/onload=alert(1)>"


class XssCheck(BaseScanCheck):
    name = "Reflected XSS"
    check_type = "xss"
    severity = "high"
    cwe_id = "CWE-79"
    mode = "active"

    async def check(self, entry: dict) -> list[dict]:
        params = params_of(entry)
        if not params or not entry.get("status_code"):
            return []
        method = entry["method"]
        req_headers = headers_of(entry, "request")
        findings = []
        for param in list(params)[:8]:  # bound the work per entry
            probe = f"{CANARY}{len(param)}x"
            url = set_query_param(entry["url"], param, probe + PAYLOAD)
            content = None
            if method not in ("GET", "HEAD"):
                from urllib.parse import parse_qsl, urlencode

                body_pairs = [(k, probe + PAYLOAD if k == param else v) for k, v in parse_qsl(entry.get("request_body") or "", keep_blank_values=True)]
                content = urlencode(body_pairs).encode()
            resp = await send_variant(method, url, req_headers, content)
            if resp is None:
                continue
            text = resp.text
            escaped = html_lib.escape(probe + PAYLOAD)
            if probe + PAYLOAD in text:
                # raw, unescaped reflection of an HTML-bearing payload
                idx = text.find(probe + PAYLOAD)
                findings.append(
                    self.finding(
                        title=f"Reflected XSS in parameter '{param}'",
                        description=f"The value of '{param}' is reflected unescaped into the response, allowing HTML/script injection.",
                        severity="high",
                        confidence="firm",
                        cwe_id=self.cwe_id,
                        url=url,
                        parameter=param,
                        payload=probe + PAYLOAD,
                        evidence=text[max(0, idx - 80) : idx + 120],
                        remediation="Context-aware output encoding; prefer a strict CSP as a second line of defense.",
                    )
                )
            elif probe in text and escaped not in text and "&lt;" not in text[max(0, text.find(probe) - 40): text.find(probe) + len(probe) + 40]:
                idx = text.find(probe)
                findings.append(
                    self.finding(
                        title=f"Unescaped reflection in parameter '{param}' (verify manually)",
                        description=f"Value of '{param}' reflects without visible encoding; manual verification recommended.",
                        severity="medium",
                        confidence="tentative",
                        cwe_id=self.cwe_id,
                        url=url,
                        parameter=param,
                        payload=probe,
                        evidence=text[max(0, idx - 60) : idx + 100],
                        remediation="Encode reflected values per output context (HTML, attribute, JS).",
                    )
                )
        return findings


register_check(XssCheck())
