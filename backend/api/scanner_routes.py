"""Scanner API — /api/scanner (contracts/api.md)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from core.scanner_engine import available_checks, get_scanner_engine
from db import database

router = APIRouter()


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
