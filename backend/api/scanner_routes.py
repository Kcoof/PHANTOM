"""Scanner API — /api/scanner (contracts/api.md + spec 002 report export)."""
from __future__ import annotations

import html as html_lib
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, field_validator

from core.scanner_engine import available_checks, get_scanner_engine
from db import database

router = APIRouter()

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
SEVERITY_COLORS = {
    "critical": "#ff3838",
    "high": "#ff6b35",
    "medium": "#ffc107",
    "low": "#00b894",
    "info": "#74b9ff",
}


class ScanStartIn(BaseModel):
    target_url: str | None = None
    history_ids: list[int] | None = None
    scan_type: str = "passive"
    checks: list[str] | None = None

    @field_validator("scan_type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        if v not in ("active", "passive", "full"):
            raise ValueError("scan_type must be active, passive, or full")
        return v


@router.post("/scan", status_code=201)
async def start_scan(body: ScanStartIn) -> dict:
    engine = get_scanner_engine()
    try:
        scan_id = await engine.start_scan(
            target_url=body.target_url,
            history_ids=body.history_ids,
            scan_type=body.scan_type,
            selected_checks=body.checks,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except Exception as exc:  # noqa: BLE001 — surface actionable errors (Constitution V)
        raise HTTPException(status_code=500, detail=f"scan failed to start: {exc}")
    return {"scan_id": scan_id, "status": "running"}


@router.get("/checks")
async def list_checks() -> list[dict]:
    return available_checks()


@router.get("/targets")
async def list_targets() -> list[dict]:
    """Distinct hosts seen in proxy history — pick a scan target from these."""
    return await database.fetch_all(
        "SELECT host, COUNT(*) AS count, MAX(timestamp) AS last_seen "
        "FROM proxy_history GROUP BY host ORDER BY count DESC LIMIT 200"
    )


@router.get("/scans")
async def list_scans() -> list[dict]:
    return await database.fetch_all("SELECT * FROM scans ORDER BY timestamp DESC LIMIT 100")


@router.get("/scans/{scan_id}")
async def get_scan(scan_id: str) -> dict:
    row = await database.fetch_one("SELECT * FROM scans WHERE id = ?", (scan_id,))
    if not row:
        raise HTTPException(status_code=404, detail="scan not found")
    return row


@router.post("/scans/{scan_id}/{action}")
async def control_scan(scan_id: str, action: str) -> dict:
    if action not in ("pause", "resume", "stop"):
        raise HTTPException(status_code=422, detail="action must be pause, resume, or stop")
    engine = get_scanner_engine()
    try:
        status = engine.control(scan_id, action)
    except KeyError:
        raise HTTPException(status_code=404, detail="scan not running")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"scan_id": scan_id, "status": status}


@router.get("/findings")
async def list_findings(
    severity: str | None = None,
    type: str | None = None,  # noqa: A002 — API param name per contract
    scan_id: str | None = None,
    status: str | None = None,
) -> list[dict]:
    where, params = [], []
    if severity:
        where.append("severity = ?")
        params.append(severity)
    if type:
        where.append("finding_type = ?")
        params.append(type)
    if scan_id:
        where.append("scan_id = ?")
        params.append(scan_id)
    if status:
        where.append("status = ?")
        params.append(status)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    return await database.fetch_all(
        f"SELECT * FROM scanner_findings {clause} ORDER BY id DESC LIMIT 500", tuple(params)
    )


@router.get("/findings/{finding_id}")
async def get_finding(finding_id: int) -> dict:
    row = await database.fetch_one("SELECT * FROM scanner_findings WHERE id = ?", (finding_id,))
    if not row:
        raise HTTPException(status_code=404, detail="finding not found")
    return row


class StatusIn(BaseModel):
    status: str


# --- report export (spec 002, FR-003) ----------------------------------------


async def _report_findings(severity: str | None) -> list[dict]:
    where, params = "status != 'false_positive'", []
    if severity:
        where += " AND severity = ?"
        params.append(severity)
    rows = await database.fetch_all(
        f"SELECT * FROM scanner_findings WHERE {where} ORDER BY id DESC", tuple(params)
    )
    return sorted(rows, key=lambda r: (SEVERITY_RANK.get(r["severity"], 9), r["finding_type"], r["url"]))


def _markdown_report(findings: list[dict]) -> str:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    lines = [
        "# PHANTOM Security Report",
        "",
        f"**Generated**: {time.strftime('%Y-%m-%d %H:%M')}  ",
        f"**Findings**: {len(findings)} ("
        + ", ".join(f"{counts.get(s, 0)} {s}" for s in SEVERITY_RANK if counts.get(s))
        + ")",
        "",
        "> Authorized-testing engagement output — verify every finding before reporting.",
        "",
        "---",
        "",
    ]
    for i, f in enumerate(findings, 1):
        lines += [
            f"## {i}. [{f['severity'].upper()}] {f['title']}",
            "",
            f"- **Type**: {f['finding_type']}" + (f" ({f['cwe_id']})" if f.get("cwe_id") else ""),
            f"- **Confidence**: {f['confidence']}",
            f"- **URL**: `{f['url']}`",
        ]
        if f.get("parameter"):
            lines.append(f"- **Parameter**: `{f['parameter']}`")
        if f.get("payload"):
            lines.append(f"- **Payload**: `{str(f['payload'])[:200]}`")
        lines += ["", f"**Description**: {f['description']}", ""]
        if f.get("evidence"):
            lines += ["**Evidence**:", "", "```", str(f["evidence"])[:1500], "```", ""]
        if f.get("remediation"):
            lines += [f"**Remediation**: {f['remediation']}", ""]
        lines += ["---", ""]
    return "\n".join(lines)


def _html_report(findings: list[dict]) -> str:
    counts: dict[str, int] = {}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1
    chips = " ".join(
        f'<span style="background:{SEVERITY_COLORS[s]}22;color:{SEVERITY_COLORS[s]};'
        f'border:1px solid {SEVERITY_COLORS[s]}66;border-radius:99px;padding:2px 10px;'
        f'font:600 11px/1.6 sans-serif">{counts.get(s, 0)} {s.upper()}</span>'
        for s in SEVERITY_RANK
        if counts.get(s)
    )
    cards = []
    for i, f in enumerate(findings, 1):
        color = SEVERITY_COLORS.get(f["severity"], "#888")
        evidence = (
            f'<pre style="background:#f4f4f6;border:1px solid #ddd;border-radius:6px;'
            f'padding:10px;font:11px/1.5 monospace;overflow:auto;white-space:pre-wrap">{html_lib.escape(str(f["evidence"])[:1500])}</pre>'
            if f.get("evidence")
            else ""
        )
        cards.append(
            f'<section style="border:1px solid #ddd;border-left:4px solid {color};'
            f'border-radius:8px;padding:14px 18px;margin:14px 0;page-break-inside:avoid">'
            f'<h3 style="margin:0 0 6px;font:600 15px sans-serif">'
            f'<span style="color:{color}">[{f["severity"].upper()}]</span> '
            f'{html_lib.escape(f["title"])}</h3>'
            f'<div style="font:12px sans-serif;color:#555;margin-bottom:8px">'
            f'{html_lib.escape(f["finding_type"])}'
            + (f' &middot; {html_lib.escape(f["cwe_id"])}' if f.get("cwe_id") else "")
            + f' &middot; confidence: {html_lib.escape(f["confidence"])}'
            + (f' &middot; param: <code>{html_lib.escape(str(f["parameter"]))}</code>' if f.get("parameter") else "")
            + '</div>'
            f'<div style="font:12px sans-serif;margin-bottom:6px"><b>URL:</b> '
            f'<code style="word-break:break-all">{html_lib.escape(f["url"])}</code></div>'
            f'<p style="font:13px/1.6 sans-serif;margin:8px 0">{html_lib.escape(f["description"])}</p>'
            f'{evidence}'
            + (f'<p style="font:13px/1.6 sans-serif;margin:8px 0"><b>Fix:</b> {html_lib.escape(f["remediation"])}</p>' if f.get("remediation") else "")
            + "</section>"
        )
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>PHANTOM Security Report</title></head>
<body style="font:14px/1.6 sans-serif;color:#1a1a1a;background:#fff;margin:0;padding:40px;max-width:900px">
<h1 style="font:700 24px sans-serif;border-bottom:2px solid #6c5ce7;padding-bottom:8px">PHANTOM Security Report</h1>
<div style="font:12px sans-serif;color:#666;margin:6px 0 14px">Generated {time.strftime('%Y-%m-%d %H:%M')}
 &middot; {len(findings)} findings &middot; authorized-testing engagement output</div>
<div style="margin-bottom:10px">{chips}</div>
{''.join(cards) or '<p style="color:#666">No findings match the filter.</p>'}
</body></html>"""


@router.get("/report")
async def export_report(format: str = "markdown", severity: str | None = None):
    if format not in ("markdown", "html"):
        raise HTTPException(status_code=422, detail="format must be markdown or html")
    findings = await _report_findings(severity)
    if format == "html":
        return Response(
            content=_html_report(findings),
            media_type="text/html",
            headers={"Content-Disposition": 'attachment; filename="phantom-report.html"'},
        )
    return Response(
        content=_markdown_report(findings),
        media_type="text/markdown",
        headers={"Content-Disposition": 'attachment; filename="phantom-report.md"'},
    )


@router.put("/findings/{finding_id}/status")
async def update_finding_status(finding_id: int, body: StatusIn) -> dict:
    valid = {"open", "confirmed", "fixed", "false_positive"}
    if body.status not in valid:
        raise HTTPException(status_code=422, detail=f"status must be one of {', '.join(sorted(valid))}")
    row = await database.fetch_one("SELECT id FROM scanner_findings WHERE id = ?", (finding_id,))
    if not row:
        raise HTTPException(status_code=404, detail="finding not found")
    await database.execute(
        "UPDATE scanner_findings SET status = ?, is_false_positive = ? WHERE id = ?",
        (body.status, 1 if body.status == "false_positive" else 0, finding_id),
    )
    row = await database.fetch_one("SELECT * FROM scanner_findings WHERE id = ?", (finding_id,))
    return row
