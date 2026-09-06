"""Active: SQL injection — error-based with a small payload set (plan.md Part 6.2)."""
from __future__ import annotations

import re

from core.scanner_checks.base import headers_of, params_of, send_variant, set_query_param
from core.scanner_engine import BaseScanCheck, register_check

PAYLOADS = [
    "'\"(",
    "1' ORDER BY 1--",
    "1 OR 1=1",
    "1' AND '1'='1",
]
ERROR_PATTERNS = [
    r"you have an error in your sql syntax",
    r"warning: mysql",
    r"unclosed quotation mark after the character string",
    r"quoted string not properly terminated",
    r"pg_query\(\)|psql.*error",
    r"sqlite3?\.OperationalError|SQLITE_ERROR",
    r"ORA-\d{5}",
    r"odbc.*driver.*sql",
    r"sqlstate\[",
]


class SqliCheck(BaseScanCheck):
    name = "SQL Injection"
    check_type = "sqli"
    severity = "critical"
    cwe_id = "CWE-89"
    mode = "active"

    async def check(self, entry: dict) -> list[dict]:
        params = params_of(entry)
        if not params or not entry.get("status_code"):
            return []
        method = entry["method"]
        req_headers = headers_of(entry, "request")
        findings = []
        for param in list(params)[:6]:
            for payload in PAYLOADS:
                url = set_query_param(entry["url"], param, payload)
                content = None
                if method not in ("GET", "HEAD"):
                    from urllib.parse import parse_qsl, urlencode

                    body_pairs = [(k, payload if k == param else v) for k, v in parse_qsl(entry.get("request_body") or "", keep_blank_values=True)]
                    content = urlencode(body_pairs).encode()
                resp = await send_variant(method, url, req_headers, content)
                if resp is None:
                    continue
                text = resp.text
                for pattern in ERROR_PATTERNS:
                    match = re.search(pattern, text, re.I)
                    if match:
                        findings.append(
                            self.finding(
                                title=f"SQL injection (error-based) in parameter '{param}'",
                                description=f"Payload {payload!r} in '{param}' triggered a database error message, indicating injectable SQL.",
                                severity="critical",
                                confidence="firm",
                                cwe_id=self.cwe_id,
                                url=url,
                                parameter=param,
                                payload=payload,
                                evidence=text[max(0, match.start() - 80) : match.start() + 180],
                                remediation="Use parameterized queries/prepared statements; never concatenate user input into SQL.",
                            )
                        )
                        break
                if findings:
                    break
            if findings:
                break  # one confirmed finding per entry is enough
        return findings


register_check(SqliCheck())
