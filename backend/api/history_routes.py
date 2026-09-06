"""Proxy history API — /api/history (contracts/api.md)."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from db import database
from utils.helpers import parse_tags

router = APIRouter()

_LIST_COLUMNS = (
    "id, timestamp, method, scheme, host, port, path, query_string, url, "
    "request_content_type, status_code, response_content_type, response_time_ms, "
    "size_bytes, is_intercepted, is_in_scope, tags, notes, highlight_color"
)


def _decode_row(row: dict) -> dict:
    row["tags"] = parse_tags(row.get("tags"))
    return row


def _decode_full(row: dict) -> dict:
    row = _decode_row(row)
    for key in ("request_headers", "response_headers"):
        try:
            row[key] = json.loads(row[key]) if row.get(key) else {}
        except (json.JSONDecodeError, TypeError):
            row[key] = {}
    return row


@router.get("")
async def list_history(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    method: str | None = None,
    host: str | None = None,
    status: int | None = None,
    search: str | None = None,
    in_scope: bool | None = None,
) -> dict:
    where: list[str] = []
    params: list = []
    if method:
        where.append("method = ?")
        params.append(method.upper())
    if host:
        where.append("host LIKE ?")
        params.append(f"%{host}%")
    if status is not None:
        where.append("status_code = ?")
        params.append(status)
    if search:
        where.append("(url LIKE ? OR host LIKE ? OR path LIKE ?)")
        params += [f"%{search}%"] * 3
    if in_scope is not None:
        where.append("is_in_scope = ?")
        params.append(1 if in_scope else 0)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    total_row = await database.fetch_one(f"SELECT COUNT(*) AS n FROM proxy_history {clause}", tuple(params))
    offset = (page - 1) * limit
    rows = await database.fetch_all(
        f"SELECT {_LIST_COLUMNS} FROM proxy_history {clause} ORDER BY id DESC LIMIT ? OFFSET ?",
        tuple(params) + (limit, offset),
    )
    return {
        "items": [_decode_row(r) for r in rows],
        "total": total_row["n"],
        "page": page,
        "limit": limit,
    }


@router.get("/{entry_id}")
async def get_history(entry_id: int) -> dict:
    row = await database.fetch_one("SELECT * FROM proxy_history WHERE id = ?", (entry_id,))
    if not row:
        raise HTTPException(status_code=404, detail="history entry not found")
    return _decode_full(row)


@router.delete("")
async def clear_history() -> dict:
    row = await database.fetch_one("SELECT COUNT(*) AS n FROM proxy_history")
    await database.execute("DELETE FROM proxy_history")
    return {"deleted": row["n"]}


@router.delete("/{entry_id}")
async def delete_history(entry_id: int) -> dict:
    row = await database.fetch_one("SELECT id FROM proxy_history WHERE id = ?", (entry_id,))
    if not row:
        raise HTTPException(status_code=404, detail="history entry not found")
    await database.execute("DELETE FROM proxy_history WHERE id = ?", (entry_id,))
    return {"deleted": True}


class TagIn(BaseModel):
    tag: str


class NoteIn(BaseModel):
    note: str


class HighlightIn(BaseModel):
    color: str | None = None  # None clears


@router.post("/{entry_id}/tag")
async def tag_history(entry_id: int, body: TagIn) -> dict:
    row = await database.fetch_one("SELECT tags FROM proxy_history WHERE id = ?", (entry_id,))
    if not row:
        raise HTTPException(status_code=404, detail="history entry not found")
    tags = parse_tags(row["tags"])
    tag = body.tag.strip()
    if tag and tag not in tags:
        tags.append(tag)
    await database.execute(
        "UPDATE proxy_history SET tags = ? WHERE id = ?", (json.dumps(tags), entry_id)
    )
    return {"tags": tags}


@router.post("/{entry_id}/note")
async def note_history(entry_id: int, body: NoteIn) -> dict:
    row = await database.fetch_one("SELECT id FROM proxy_history WHERE id = ?", (entry_id,))
    if not row:
        raise HTTPException(status_code=404, detail="history entry not found")
    await database.execute(
        "UPDATE proxy_history SET notes = ? WHERE id = ?", (body.note, entry_id)
    )
    return {"note": body.note}


@router.post("/{entry_id}/highlight")
async def highlight_history(entry_id: int, body: HighlightIn) -> dict:
    row = await database.fetch_one("SELECT id FROM proxy_history WHERE id = ?", (entry_id,))
    if not row:
        raise HTTPException(status_code=404, detail="history entry not found")
    await database.execute(
        "UPDATE proxy_history SET highlight_color = ? WHERE id = ?", (body.color, entry_id)
    )
    return {"color": body.color}


@router.post("/{entry_id}/send-to-repeater")
async def send_to_repeater(entry_id: int) -> dict:
    row = await database.fetch_one("SELECT * FROM proxy_history WHERE id = ?", (entry_id,))
    if not row:
        raise HTTPException(status_code=404, detail="history entry not found")
    name = f"{row['method']} {row['host']}{row['path'][:40]}"
    tab_id = await database.execute(
        """INSERT INTO repeater_tabs (name, method, url, request_headers, request_body, history)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            name,
            row["method"],
            row["url"],
            row["request_headers"],
            row["request_body"],
            json.dumps([]),
        ),
    )
    return {"repeater_tab_id": tab_id}
