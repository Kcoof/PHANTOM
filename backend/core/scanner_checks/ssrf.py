"""Active: SSRF probing via internal URL injection (plan.md Part 6.2, tentative)."""
from __future__ import annotations

from urllib.parse import urlsplit

from core.scanner_checks.base import headers_of, params_of, send_variant, set_query_param
from core.scanner_engine import BaseScanCheck, register_check

URLISH_HINTS = ("url", "link", "path", "site", "host", "source", "dest", "redirect", "next", "fetch", "load", "img", "callback", "domain", "reference", "return")
INTERNAL_TARGETS = ["http://127.0.0.1:8899/api/health", "http://localhost:8899/api/health"]


class SsrfCheck(BaseScanCheck):
    name = "SSRF"
    check_type = "ssrf"
    severity = "high"
    cwe_id = "CWE-918"
    mode = "active"

    async def check(self, entry: dict) -> list[dict]:
        params = params_of(entry)
        if not params or not entry.get("status_code"):
            return []
        # only probe parameters whose name or value hints at URL handling
        candidates = [
            (k, v)
            for k, v in params.items()
            if any(h in k.lower() for h in URLISH_HINTS) or v.startswith(("http://", "https://", "//"))
        ]
        if not candidates:
            return []
        method = entry["method"]
        req_headers = headers_of(entry, "request")
        baseline = await send_variant(method, entry["url"], req_headers, None)
        if baseline is None:
            return []
        findings = []
        for param, original in candidates[:4]:
            for internal in INTERNAL_TARGETS:
                url = set_query_param(entry["url"], param, internal)
                content = None
                if method not in ("GET", "HEAD"):
                    from urllib.parse import parse_qsl, urlencode

                    body_pairs = [(k, internal if k == param else v) for k, v in parse_qsl(entry.get("request_body") or "", keep_blank_values=True)]
                    content = urlencode(body_pairs).encode()
                resp = await send_variant(method, url, req_headers, content)
                if resp is None:
                    continue
                # Differential signals: internal fetch often changes status/length materially
                len_delta = abs(len(resp.content) - len(baseline.content))
                status_changed = resp.status_code != baseline.status_code
                echoed = "phantom" in resp.text.lower() and "health" in resp.text.lower()
                if echoed or (status_changed and len_delta > 200):
                    findings.append(
                        self.finding(
                            title=f"Possible SSRF in parameter '{param}' (verify manually)",
                            description=(
                                f"Replacing '{param}' with an internal URL ({internal}) produced a "
                                f"materially different response ({baseline.status_code}→{resp.status_code}, "
                                f"Δ{len_delta}B){' and echoed our marker' if echoed else ''}."
                            ),
                            severity="high",
                            confidence="tentative",
                            cwe_id=self.cwe_id,
                            url=url,
                            parameter=param,
                            payload=internal,
                            evidence=f"baseline: {baseline.status_code}/{len(baseline.content)}B; probe: {resp.status_code}/{len(resp.content)}B",
                            remediation="Allow-list outbound destinations; never fetch user-supplied internal URLs; block link-local/metadata addresses.",
                        )
                    )
                    break
        return findings


register_check(SsrfCheck())
