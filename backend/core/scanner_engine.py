"""Scanner engine — async orchestrator + check registry (research.md D9).

Active checks are scope-gated: an active scan requires an explicit include
scope rule matching every target (Constitution I; contracts/api.md).
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

from api.websocket import broadcast
from core.scanner_checks.base import configure_throttle
from db import database
from utils.helpers import url_in_scope
from utils.logger import get_logger

log = get_logger(__name__)


class BaseScanCheck:
    """Interface for scan checks (plan.md Part 6.2)."""

    name: str = "base"
    check_type: str = "base"
    severity: str = "info"
    cwe_id: str | None = None
    mode: str = "passive"  # or "active"

    async def check(self, entry: dict) -> list[dict]:
        raise NotImplementedError

    @staticmethod
    def finding(**kwargs: Any) -> dict:
        base = {
            "finding_type": "",
            "severity": "info",
            "confidence": "tentative",
            "title": "",
            "description": "",
            "url": "",
            "parameter": None,
            "payload": None,
            "evidence": None,
            "request_dump": None,
            "response_dump": None,
            "remediation": None,
            "cwe_id": None,
        }
        base.update(kwargs)
        return base


_REGISTRY: list[BaseScanCheck] = []


def register_check(check: BaseScanCheck) -> None:
    _REGISTRY.append(check)


def available_checks() -> list[dict]:
    return [
        {
            "check_type": c.check_type,
            "name": c.name,
            "severity": c.severity,
            "mode": c.mode,
            "cwe_id": c.cwe_id,
        }
        for c in _REGISTRY
    ]


def get_checks(selected: list[str] | None = None) -> list[BaseScanCheck]:
    if not selected:
        return list(_REGISTRY)
    return [c for c in _REGISTRY if c.check_type in selected]


# Import check modules for their registration side effects.
from core.scanner_checks import (  # noqa: E402,F401
    cors,
    csrf,
    headers,
    idor,
    info_disclosure,
    jwt,
    open_redirect,
    secrets,
    sqli,
    ssrf,
    xss,
)


class ScanSession:
    def __init__(self, scan_id: str, checks: list[BaseScanCheck], entries: list[dict]):
        self.scan_id = scan_id
        self.checks = checks
        self.entries = entries
        self.paused = asyncio.Event()
        self.stopped = False
        self.done = 0
        self.total = 0
        self.findings = 0
        self.duplicates = 0
        self.task: asyncio.Task | None = None

    async def gate(self) -> None:
        """Pause point between work items."""
        while self.paused.is_set() and not self.stopped:
            await asyncio.sleep(0.2)


class ScannerEngine:
    def __init__(self) -> None:
        self.sessions: dict[str, ScanSession] = {}

    async def start_scan(
        self,
        target_url: str | None,
        history_ids: list[int] | None,
        scan_type: str,
        selected_checks: list[str] | None,
        in_scope_only: bool = False,
    ) -> str:
        # Load candidate entries: explicit ids, or recent history for the target
        if history_ids:
            marks = ",".join("?" * len(history_ids))
            entries = await database.fetch_all(
                f"SELECT * FROM proxy_history WHERE id IN ({marks})", tuple(history_ids)
            )
        else:
            where = "WHERE host LIKE ?" if target_url else ""
            params: tuple = (f"%{target_url}%",) if target_url else ()
            entries = await database.fetch_all(
                f"SELECT * FROM proxy_history {where} ORDER BY id DESC LIMIT 500", params
            )
        if in_scope_only and not history_ids:
            # focus the scan on the current scope rules (live evaluation)
            entries = [e for e in entries if await url_in_scope(e["url"])]

        checks = get_checks(selected_checks)
        if scan_type in ("active", "full"):
            checks = [c for c in checks if c.mode in ("passive", "active")] if scan_type == "full" else [c for c in checks if c.mode == "active"]
        else:
            checks = [c for c in checks if c.mode == "passive"]

        # Scope gate for active scanning (Constitution I)
        if scan_type in ("active", "full"):
            scope = await _load_include_rules()
            if not scope:
                raise PermissionError(
                    "active scanning requires an explicit include scope rule — "
                    "add one in Settings → Scope (e.g. *.your-lab.example)"
                )
            for entry in entries:
                if not await url_in_scope(entry["url"]):
                    raise PermissionError(
                        f"target out of scope for active scanning: {entry['url']}"
                    )

        scan_id = uuid.uuid4().hex[:12]
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        # Load politeness settings (spec 002, FR-004) before any probe can fire
        delay_row = await database.fetch_one("SELECT value FROM settings WHERE key = 'scanner_delay_ms'")
        conc_row = await database.fetch_one("SELECT value FROM settings WHERE key = 'scanner_concurrency'")
        try:
            configure_throttle(int(conc_row["value"]) if conc_row else 4, (int(delay_row["value"]) if delay_row else 250) / 1000)
        except (TypeError, ValueError):
            configure_throttle(4, 0.25)
        await database.execute(
            """INSERT INTO scans (id, target_url, scan_type, status, config, started_at)
               VALUES (?, ?, ?, 'running', ?, ?)""",
            (scan_id, "in-scope hosts" if in_scope_only else (target_url or "(history)"), scan_type, json.dumps({"checks": [c.check_type for c in checks]}), now),
        )
        session = ScanSession(scan_id, checks, entries)
        self.sessions[scan_id] = session
        session.task = asyncio.create_task(self._run(session), name=f"scan-{scan_id}")
        log.info("scan %s started (%s, %d entries, %d checks)", scan_id, scan_type, len(entries), len(checks))
        return scan_id

    async def _run(self, session: ScanSession) -> None:
        session.total = len(session.entries) * len(session.checks)
        try:
            for entry in session.entries:
                for check in session.checks:
                    if session.stopped:
                        break
                    await session.gate()
                    try:
                        for finding in await check.check(entry):
                            finding.setdefault("url", entry["url"])
                            # checks start from a template with empty-string
                            # defaults, so use explicit fill-ins, not setdefault
                            if not finding.get("finding_type"):
                                finding["finding_type"] = check.check_type
                            if not finding.get("severity"):
                                finding["severity"] = check.severity
                            if not finding.get("cwe_id"):
                                finding["cwe_id"] = check.cwe_id
                            await self._save_finding(session, entry, finding)
                    except Exception:
                        log.exception("check %s failed on %s", check.check_type, entry.get("url"))
                    session.done += 1
                    await broadcast(
                        "scan_progress",
                        {
                            "scan_id": session.scan_id,
                            "status": "paused" if session.paused.is_set() else "running",
                            "done": session.done,
                            "total": session.total,
                        },
                    )
                if session.stopped:
                    break
            status = "stopped" if session.stopped else "completed"
        except Exception:
            log.exception("scan %s crashed", session.scan_id)
            status = "failed"
        await database.execute(
            "UPDATE scans SET status = ?, completed_at = ?, findings_count = ? WHERE id = ?",
            (status, time.strftime("%Y-%m-%dT%H:%M:%S"), session.findings, session.scan_id),
        )
        await broadcast(
            "scan_progress",
            {
                "scan_id": session.scan_id,
                "status": status,
                "done": session.done,
                "total": session.total,
                "new_findings": session.findings,
                "duplicates": session.duplicates,
            },
        )
        self.sessions.pop(session.scan_id, None)

    async def _save_finding(self, session: ScanSession, entry: dict, finding: dict) -> None:
        # Dedupe on (finding_type, url, parameter): an existing finding — including
        # one the user marked false positive — suppresses the repeat (spec FR-001).
        existing = await database.fetch_one(
            "SELECT id FROM scanner_findings WHERE finding_type = ? AND url = ? AND parameter IS ?",
            (finding["finding_type"], finding["url"], finding.get("parameter")),
        )
        if existing:
            session.duplicates += 1
            return
        row_id = await database.execute(
            """INSERT INTO scanner_findings
               (scan_id, history_id, finding_type, severity, confidence, title, description,
                url, parameter, payload, evidence, request_dump, response_dump, remediation, cwe_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session.scan_id,
                entry.get("id"),
                finding["finding_type"],
                finding["severity"],
                finding.get("confidence", "tentative"),
                finding["title"],
                finding.get("description", ""),
                finding["url"],
                finding.get("parameter"),
                finding.get("payload"),
                finding.get("evidence"),
                finding.get("request_dump") or _dump_request(entry),
                finding.get("response_dump") or (entry.get("response_body") or "")[:2000],
                finding.get("remediation"),
                finding.get("cwe_id"),
            ),
        )
        session.findings += 1
        await database.execute(
            "UPDATE scans SET findings_count = ? WHERE id = ?", (session.findings, session.scan_id)
        )
        finding["id"] = row_id
        finding["scan_id"] = session.scan_id
        finding.setdefault("status", "open")
        finding.setdefault("timestamp", None)
        await broadcast("scan_finding", finding)

    # --- lifecycle controls ---------------------------------------------------

    def control(self, scan_id: str, action: str) -> str:
        session = self.sessions.get(scan_id)
        if not session:
            raise KeyError("scan not running")
        if action == "pause":
            session.paused.set()
        elif action == "resume":
            session.paused.clear()
        elif action == "stop":
            session.stopped = True
            session.paused.clear()
        else:
            raise ValueError(f"unknown action: {action}")
        return "paused" if session.paused.is_set() and not session.stopped else ("stopped" if session.stopped else "running")


def _dump_request(entry: dict) -> str:
    try:
        headers = json.loads(entry.get("request_headers") or "{}")
    except json.JSONDecodeError:
        headers = {}
    head = f"{entry['method']} {entry['url']}\n" + "\n".join(f"{k}: {v}" for k, v in headers.items())
    body = entry.get("request_body")
    return head + (f"\n\n{body}" if body else "")


async def _load_include_rules() -> list[dict]:
    rows = await database.fetch_all(
        "SELECT * FROM scope_rules WHERE is_active = 1 AND rule_type = 'include'"
    )
    return rows


_engine = ScannerEngine()


def get_scanner_engine() -> ScannerEngine:
    return _engine
