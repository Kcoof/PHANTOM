"""Active: open redirect (plan.md Part 6.2)."""
from __future__ import annotations

from urllib.parse import urlsplit

from core.scanner_checks.base import headers_of, params_of, send_variant, set_query_param
from core.scanner_engine import BaseScanCheck, register_check

REDIRECT_PARAMS = ("url", "redirect", "redirect_uri", "next", "return", "returnurl", "return_to", "goto", "dest", "destination", "continue", "target", "r")
EVIL_HOST = "phantom-oob-test.example"


class OpenRedirectCheck(BaseScanCheck):
    name = "Open Redirect"
    check_type = "open_redirect"
    severity = "medium"
    cwe_id = "CWE-601"
    mode = "active"

    async def check(self, entry: dict) -> list[dict]:
        params = params_of(entry)
        if not params:
            return []
        candidates = [k for k in params if k.lower() in REDIRECT_PARAMS or any(h in k.lower() for h in ("redirect", "url", "next", "goto", "return"))]
        if not candidates:
            return []
        method = entry["method"]
        req_headers = headers_of(entry, "request")
        findings = []
        for param in candidates[:4]:
            for payload in (f"https://{EVIL_HOST}/probe", f"//{EVIL_HOST}/probe", f"https://{EVIL_HOST}\\@{urlsplit(entry['url']).netloc}"):
                url = set_query_param(entry["url"], param, payload)
                content = None
                if method not in ("GET", "HEAD"):
                    from urllib.parse import parse_qsl, urlencode

                    body_pairs = [(k, payload if k == param else v) for k, v in parse_qsl(entry.get("request_body") or "", keep_blank_values=True)]
                    content = urlencode(body_pairs).encode()
                resp = await send_variant(method, url, req_headers, content)
                if resp is None:
                    continue
                location = ""
                for k, v in resp.headers.items():
                    if k.lower() == "location":
                        location = v
                        break
                if resp.status_code in (301, 302, 303, 307, 308) and EVIL_HOST in location:
                    findings.append(
                        self.finding(
                            title=f"Open redirect in parameter '{param}'",
                            description=f"Parameter '{param}' redirects to an arbitrary external host ({location}).",
                            severity="medium",
                            confidence="certain",
                            cwe_id=self.cwe_id,
                            url=url,
                            parameter=param,
                            payload=payload,
                            evidence=f"{resp.status_code} Location: {location}",
                            remediation="Validate redirect targets against an allow-list of hosts; prefer server-side mapped redirects.",
                        )
                    )
                    break
        return findings


register_check(OpenRedirectCheck())
