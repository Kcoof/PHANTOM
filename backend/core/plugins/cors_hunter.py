"""CORS Hunter — actively probes exploitable CORS configurations (spec 007).

Sends crafted Origin headers (evil, subdomain-spoof, suffix-spoof, null,
protocol-downgrade) and reports reflected Access-Control-Allow-Origin /
Allow-Credentials combinations that are exploitable.
"""
from __future__ import annotations

from urllib.parse import urlsplit

from core.plugin_framework import PhantomPlugin, register, resolve_request_context
from core.scanner_checks.base import send_variant
from db import database
from utils.helpers import url_in_scope

PROBES = [
    ("evil origin", "https://evil-{rand}.example"),
    ("subdomain spoof", "https://{host}.evil-{rand}.example"),
    ("prefix spoof", "https://evil-{rand}-{host}"),
    ("suffix spoof", "https://{host}-evil-{rand}.example"),
    ("null origin", "null"),
    ("http downgrade", "http://{host}"),
    ("origin echo", "{origin}"),
]


class CorsHunterPlugin(PhantomPlugin):
    id = "cors-hunter"
    name = "CORS Hunter"
    description = (
        "Actively probes CORS handling with crafted Origin headers (evil, subdomain/prefix/suffix "
        "spoofs, null, protocol downgrade). Reports reflected Access-Control-Allow-Origin + "
        "credentials combinations that are exploitable."
    )
    accepts = ["request"]
    parameters = []

    async def run(self, context: dict, options: dict, emit) -> None:
        import random
        import string

        req = await resolve_request_context(context)
        url, method = req["url"], req["method"]
        if not await url_in_scope(url):
            raise RuntimeError(f"target out of scope: {url} — add an include rule in Settings → Scope")

        host = urlsplit(url).hostname or ""
        origin = f"{urlsplit(url).scheme}://{host}"
        headers = {k: v for k, v in req["headers"].items()
                   if k.lower() not in ("host", "content-length", "connection", "accept-encoding", "origin")}
        body = req.get("body")
        content = body.encode("utf-8") if body else None

        await emit("info", {"message": f"probing {len(PROBES)} crafted origins against {host}", "history_id": context.get("history_id")})

        found = 0
        for label, template in PROBES:
            rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
            test_origin = (
                template.replace("{rand}", rand)
                .replace("{host}", host)
                .replace("{origin}", origin)
            )
            resp = await send_variant(
                method, url, {**headers, "Origin": test_origin}, content, timeout=15.0
            )
            if resp is None:
                continue
            acao = resp.headers.get("access-control-allow-origin", "")
            acac = resp.headers.get("access-control-allow-credentials", "")
            reflected = acao and acao.strip() not in ("*",) and acao.strip() == test_origin
            wildcard_cred = acao.strip() == "*" and acac.lower() == "true"
            if not (reflected or wildcard_cred):
                continue
            found += 1
            severity = "high" if (reflected and acac.lower() == "true") or wildcard_cred else "medium"
            evidence = f"Origin: {test_origin} -> ACAO: {acao} | ACAC: {acac or '(absent)'}"
            await emit("cors", {"label": label, "origin": test_origin, "acao": acao, "acac": acac,
                                "severity": severity, "evidence": evidence, "url": url})
            await self._finding(url, label, severity, evidence)
        await emit("summary", {"found": found})

    async def _finding(self, url, label, severity, evidence):
        existing = await database.fetch_one(
            "SELECT id FROM scanner_findings WHERE finding_type = ? AND url = ? AND parameter IS ?",
            ("cors_active", url, label),
        )
        if existing:
            return
        await database.execute(
            """INSERT INTO scanner_findings
               (scan_id, finding_type, severity, confidence, title, description, url,
                parameter, evidence, remediation)
               VALUES ('plugin', 'cors_active', ?, 'firm', ?, ?, ?, ?, ?, ?)""",
            (
                severity,
                f"Exploitable CORS ({label})",
                f"The endpoint reflects an attacker-controlled Origin into Access-Control-Allow-Origin ({label} probe), "
                "allowing cross-origin reads of responses — potentially with credentials.",
                url, label, evidence,
                "Restrict Access-Control-Allow-Origin to an explicit allow-list; never reflect arbitrary Origins; "
                "never combine wildcards/reflection with credentials.",
            ),
        )


register(CorsHunterPlugin())
