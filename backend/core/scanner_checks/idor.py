"""Active: IDOR probing — numeric identifier tampering (plan.md Part 6.2, tentative)."""
from __future__ import annotations

import re

from core.scanner_checks.base import headers_of, params_of, send_variant, set_query_param
from core.scanner_engine import BaseScanCheck, register_check

ID_RE = re.compile(r"^(?:id|uid|user|user_id|uid|account|doc|order|ref|no|num)$", re.I)


class IdorCheck(BaseScanCheck):
    name = "IDOR / Object Reference"
    check_type = "idor"
    severity = "high"
    cwe_id = "CWE-639"
    mode = "active"

    async def check(self, entry: dict) -> list[dict]:
        if not entry.get("status_code"):
            return []
        params = params_of(entry)
        id_params = [
            (k, v)
            for k, v in params.items()
            if (ID_RE.match(k) or k.endswith(("_id", "id"))) and v.strip().isdigit()
        ]
        if not id_params:
            # path-based numeric ids: /users/123
            m = re.search(r"/(\d{2,})(?:/|$|\?)", entry["url"])
            if not m:
                return []
        method = entry["method"]
        if method not in ("GET",):
            return []
        req_headers = headers_of(entry, "request")
        baseline = await send_variant(method, entry["url"], req_headers, None)
        if baseline is None or baseline.status_code >= 400:
            return []

        findings = []
        probes: list[tuple[str, str, str]] = []  # (param, new_url, note)
        for k, v in id_params[:3]:
            n = int(v)
            for cand in (n + 1, max(1, n - 1)):
                probes.append((k, set_query_param(entry["url"], k, str(cand)), f"{k}={v}→{cand}"))
                break  # one neighbor per param
        if not probes:
            m = re.search(r"/(\d{2,})", entry["url"])
            n = int(m.group(1))
            probes.append(("-", entry["url"][: m.start(1)] + str(n + 1) + entry["url"][m.end(1):], f"path id {n}→{n+1}"))

        for param, url, note in probes[:3]:
            resp = await send_variant(method, url, req_headers, None)
            if resp is None:
                continue
            same_ok = resp.status_code == 200
            body_shift = abs(len(resp.content) - len(baseline.content))
            totally_different = body_shift > max(200, 0.3 * len(baseline.content))
            if same_ok and totally_different:
                findings.append(
                    self.finding(
                        title=f"Possible IDOR ({note})",
                        description=(
                            "Changing the object identifier returned 200 with substantially different content "
                            "while the original request was also 200 — the endpoint may not enforce ownership."
                        ),
                        severity="high",
                        confidence="tentative",
                        cwe_id=self.cwe_id,
                        url=url,
                        parameter=param if param != "-" else None,
                        payload=note,
                        evidence=f"original: 200/{len(baseline.content)}B; tampered: {resp.status_code}/{len(resp.content)}B",
                        remediation="Enforce per-object authorization checks server-side; use non-sequential identifiers.",
                    )
                )
                break
        return findings


register_check(IdorCheck())
