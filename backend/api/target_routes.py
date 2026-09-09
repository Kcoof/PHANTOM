"""Target site-map API — /api/target (Burp-style site tree, spec 006)."""
from __future__ import annotations

from fastapi import APIRouter, Query

from db import database

router = APIRouter()


@router.get("/tree")
async def site_tree(search: str | None = None) -> list[dict]:
    """Flat host+path rows — the frontend assembles the expandable tree."""
    where, params = "", ()
    if search:
        where = "WHERE host LIKE ? OR path LIKE ?"
        params = (f"%{search}%", f"%{search}%")
    return await database.fetch_all(
        f"""SELECT host, scheme, path,
                   MAX(CASE WHEN scheme='https' THEN 1 ELSE 0 END) AS has_https,
                   COUNT(*) AS count,
                   GROUP_CONCAT(DISTINCT method) AS methods,
                   MAX(id) AS last_id,
                   (SELECT status_code FROM proxy_history p2
                     WHERE p2.host = proxy_history.host AND p2.path = proxy_history.path
                     ORDER BY p2.id DESC LIMIT 1) AS last_status
            FROM proxy_history {where}
            GROUP BY host, path
            ORDER BY host, count(*) DESC
            LIMIT 4000""",
        params,
    )


@router.get("/entries")
async def path_entries(
    host: str = Query(...),
    path: str = Query(...),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    """Captured entries for one exact host+path (the right-hand panel)."""
    return await database.fetch_all(
        """SELECT id, timestamp, method, url, status_code, response_time_ms, size_bytes,
                  is_intercepted, is_in_scope
           FROM proxy_history WHERE host = ? AND path = ?
           ORDER BY id DESC LIMIT ?""",
        (host, path, limit),
    )
