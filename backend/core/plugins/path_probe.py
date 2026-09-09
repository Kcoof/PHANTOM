"""Path Probe — sensitive path discovery from a captured base URL (spec 007).

Takes a captured request, resolves the site root, and probes well-known
sensitive paths (.git/config, .env, backups, admin panels, composer files…)
flagging hits with status + evidence.
"""
from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit

from core.plugin_framework import PhantomPlugin, register, resolve_request_context
from core.scanner_checks.base import send_variant
from db import database
from utils.helpers import url_in_scope

PATHS = [
    "/.git/config", "/.git/HEAD", "/.env", "/.env.bak", "/env.bak",
    "/.DS_Store", "/server-status", "/server-info", "/actuator", "/actuator/health",
    "/admin", "/admin/login", "/administrator", "/phpmyadmin", "/adminer.php",
    "/backup", "/backup.zip", "/backup.sql", "/db.sql", "/dump.sql",
    "/composer.json", "/composer.lock", "/package.json", "/.htaccess", "/web.config",
    "/robots.txt", "/sitemap.xml", "/.svn/entries", "/wp-config.php.bak",
    "/debug", "/trace", "/console", "/swagger", "/swagger.json", "/api-docs",
    "/graphql", "/.well-known/security.txt", "/config.php.bak", "/info.php",
]

INTERESTING_CONTENT = {
    "/.git/config": "[core]",
    "/.env": "=",
    "/composer.json": '"require"',
    "/swagger.json": '"paths"',
    "/server-status": "Apache",
    "/actuator/health": '"status"',
    "/graphql": "query",
}


class PathProbePlugin(PhantomPlugin):
    id = "path-probe"
    name = "Path Probe"
    description = (
        "Probes well-known sensitive paths (.git, .env, backups, admin panels, actuator, "
        "swagger…) on the captured request's site and flags live ones with evidence. "
        "Throttled and scope-gated."
    )
    accepts = ["request"]
    parameters = []

    async def run(self, context: dict, options: dict, emit) -> None:
        req = await resolve_request_context(context)
        url = req["url"]
        if not await url_in_scope(url):
            raise RuntimeError(f"target out of scope: {url} — add an include rule in Settings → Scope")

        parts = urlsplit(url)
        root = urlunsplit((parts.scheme, parts.netloc, "", "", ""))
        headers = {k: v for k, v in req["headers"].items()
                   if k.lower() not in ("host", "content-length", "connection", "accept-encoding", "cookie")}

        await emit("info", {"message": f"probing {len(PATHS)} sensitive paths on {root}", "history_id": context.get("history_id")})

        found = 0
        done = 0
        for path in PATHS:
            done += 1
            resp = await send_variant("GET", root + path, headers, None, timeout=12.0)
            if resp is None:
                continue
            if resp.status_code != 200 or len(resp.content) < 10:
                await emit("progress", {"done": done, "total": len(PATHS)})
                continue
            body = resp.text[:4000]
            marker = INTERESTING_CONTENT.get(path)
            content_hit = marker is None or marker in body
            # generic soft-404 heuristics: identical short bodies everywhere
            if resp.status_code == 200 and content_hit and len(resp.content) > 25:
                found += 1
                evidence = f"{path} -> 200, {len(resp.content)}B" + (f", contains {marker!r}" if marker else "")
                severity = "high" if path.startswith(("/.git", "/.env", "/backup", "/db", "/dump")) else "info"
                await emit("path", {"path": path, "status": resp.status_code, "size": len(resp.content),
                                    "evidence": evidence, "severity": severity, "url": root + path})
                await self._finding(root, path, severity, evidence)
            await emit("progress", {"done": done, "total": len(PATHS)})
        await emit("summary", {"found": found})

    async def _finding(self, root, path, severity, evidence):
        url = root + path
        existing = await database.fetch_one(
            "SELECT id FROM scanner_findings WHERE finding_type = ? AND url = ? AND parameter IS NULL",
            ("sensitive_path", url),
        )
        if existing:
            return
        await database.execute(
            """INSERT INTO scanner_findings
               (scan_id, finding_type, severity, confidence, title, description, url,
                evidence, remediation)
               VALUES ('plugin', 'sensitive_path', ?, 'tentative', ?, ?, ?, ?, ?)""",
            (
                severity, f"Sensitive path exposed: {path}",
                f"The site serves {path} publicly. Verify manually — this can leak source, "
                "credentials, or admin surfaces.",
                url, evidence,
                "Block access to sensitive files/directories; keep them out of the web root.",
            ),
        )


register(PathProbePlugin())
