"""Global search API — regex/literal across history (spec 003, FR-102)."""
from __future__ import annotations

import re

from fastapi import APIRouter, Query

from db import database

router = APIRouter()

SCAN_ROWS = 5000
SNIPPET = 90


@router.get("")
async def search(
    q: str = Query(..., min_length=1),
    regex: bool = False,
    side: str = Query("both", pattern="^(request|response|both)$"),
    limit: int = Query(200, ge=1, le=500),
) -> list[dict]:
    pattern = None
    if regex:
        try:
            pattern = re.compile(q, re.IGNORECASE)
        except re.error as exc:
            from fastapi import HTTPException

            raise HTTPException(status_code=422, detail=f"invalid regex: {exc}")
        matcher = lambda text: pattern.search(text or "")  # noqa: E731
    else:
        needle = q.lower()
        matcher = lambda text: needle in (text or "").lower()  # noqa: E731

    rows = await database.fetch_all(
        "SELECT id, method, url, request_headers, request_body, "
        "response_headers, response_body, status_code "
        "FROM proxy_history ORDER BY id DESC LIMIT ?",
        (SCAN_ROWS,),
    )
    hits: list[dict] = []
    for row in rows:
        where = None
        snippet = ""
        for where_name, text in _texts(row, side):
            m = matcher(text)
            if m:
                where, snippet = where_name, _around(text, m if regex else None, q)
                break
        if where:
            hits.append(
                {
                    "id": row["id"],
                    "method": row["method"],
                    "url": row["url"],
                    "status_code": row["status_code"],
                    "where": where,
                    "snippet": snippet,
                }
            )
            if len(hits) >= limit:
                break
    return hits


def _texts(row: dict, side: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if side in ("request", "both"):
        out.append(("request", (row.get("request_headers") or "") + "\n" + (row.get("request_body") or "")))
    if side in ("response", "both"):
        out.append(("response", (row.get("response_headers") or "") + "\n" + (row.get("response_body") or "")))
    return out


def _around(text: str, match: re.Match | None, needle: str) -> str:
    start = match.start() if match else text.lower().find(needle.lower())
    if start < 0:
        start = 0
    begin = max(0, start - SNIPPET // 2)
    end = min(len(text), start + SNIPPET)
    prefix = "…" if begin > 0 else ""
    suffix = "…" if end < len(text) else ""
    return (prefix + text[begin:end].replace("\n", " ") + suffix).strip()
