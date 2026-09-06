"""Dashboard API — /api/dashboard aggregation queries (contracts/api.md)."""
from __future__ import annotations

from fastapi import APIRouter, Query

from db import database

router = APIRouter()

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]


@router.get("/stats")
async def stats() -> dict:
    total_req = await database.fetch_one("SELECT COUNT(*) AS n, AVG(response_time_ms) AS avg_ms FROM proxy_history")
    by_severity = await database.fetch_all(
        """SELECT severity, COUNT(*) AS n FROM scanner_findings
           WHERE status != 'false_positive' GROUP BY severity"""
    )
    top_hosts = await database.fetch_all(
        "SELECT host, COUNT(*) AS n FROM proxy_history GROUP BY host ORDER BY n DESC LIMIT 10"
    )
    severity_map = {r["severity"]: r["n"] for r in by_severity}
    return {
        "total_requests": total_req["n"],
        "avg_response_time_ms": round(total_req["avg_ms"] or 0),
        "total_findings": sum(severity_map.values()),
        "findings_by_severity": {s: severity_map.get(s, 0) for s in SEVERITY_ORDER},
        "top_hosts": [{"host": r["host"], "count": r["n"]} for r in top_hosts],
    }


@router.get("/traffic")
async def traffic(
    interval: str = Query("minute", pattern="^(minute|hour|day)$"),
) -> list[dict]:
    fmt = {"minute": "%Y-%m-%d %H:%M", "hour": "%Y-%m-%d %H:00", "day": "%Y-%m-%d"}[interval]
    rows = await database.fetch_all(
        f"""SELECT strftime('{fmt}', timestamp) AS bucket, COUNT(*) AS count
            FROM proxy_history GROUP BY bucket ORDER BY bucket DESC LIMIT 500"""
    )
    return list(reversed(rows))


@router.get("/technologies")
async def technologies() -> list[dict]:
    """Detect technologies from Server/X-Powered-By response headers."""
    rows = await database.fetch_all(
        "SELECT host, response_headers FROM proxy_history WHERE response_headers IS NOT NULL"
    )
    seen: dict[str, dict] = {}
    import json as _json

    for row in rows:
        try:
            headers = _json.loads(row["response_headers"])
        except (_json.JSONDecodeError, TypeError):
            continue
        for header in ("Server", "server", "X-Powered-By", "x-powered-by"):
            value = headers.get(header)
            if value:
                tech = str(value).strip()
                entry = seen.setdefault(tech, {"technology": tech, "hosts": set(), "source": header.lower()})
                entry["hosts"].add(row["host"])
    return [
        {"technology": v["technology"], "hosts": sorted(v["hosts"])[:5], "source": v["source"]}
        for v in sorted(seen.values(), key=lambda x: x["technology"].lower())
    ][:50]


@router.get("/top-findings")
async def top_findings() -> list[dict]:
    rows = await database.fetch_all(
        """SELECT finding_type, COUNT(*) AS count,
                  MIN(severity) AS sample_severity
           FROM scanner_findings WHERE status != 'false_positive'
           GROUP BY finding_type ORDER BY count DESC LIMIT 20"""
    )
    # rank severities properly
    rank = {s: i for i, s in enumerate(reversed(SEVERITY_ORDER))}
    all_sev = await database.fetch_all(
        "SELECT finding_type, severity FROM scanner_findings WHERE status != 'false_positive'"
    )
    max_sev: dict[str, str] = {}
    for r in all_sev:
        cur = max_sev.get(r["finding_type"])
        if cur is None or rank.get(r["severity"], -1) > rank.get(cur, -1):
            max_sev[r["finding_type"]] = r["severity"]
    return [
        {"finding_type": r["finding_type"], "count": r["count"], "max_severity": max_sev.get(r["finding_type"], "info")}
        for r in rows
    ]
