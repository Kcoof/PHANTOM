"""Repeater API — /api/repeater (contracts/api.md). Sends via httpx (research D7)."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db import database

router = APIRouter()


@dataclass
class ParsedRaw:
    method: str
    url: str
    headers: dict[str, str]
    body: str | None


_RAW_START = re.compile(r"^([A-Z]+)\s+(\S+)(?:\s+HTTP/[\d.]+)?\s*$", re.IGNORECASE)


def parse_raw_request(raw: str, fallback_url: str | None = None) -> ParsedRaw:
    """Parse raw HTTP request text: METHOD path [HTTP/1.1] + headers + body."""
    head, _, body = raw.partition("\n\n")
    lines = [ln.rstrip("\r") for ln in head.split("\n")]
    method, target = "GET", fallback_url or "http://example.com/"
    headers: dict[str, str] = {}
    for line in lines:
        if not line.strip():
            continue
        if _RAW_START.match(line):
            parts = line.split()
            method, target = parts[0].upper(), parts[1]
        elif ":" in line:
            name, _, value = line.partition(":")
            headers[name.strip()] = value.strip()
    if target.startswith("http://") or target.startswith("https://"):
        url = target
    else:
        # path-only target: resolve against fallback host or Host header
        if fallback_url:
            parts = urlsplit(fallback_url)
            url = f"{parts.scheme}://{parts.netloc}{target}"
        elif "host" in {k.lower() for k in headers}:
            host = next(v for k, v in headers.items() if k.lower() == "host")
            url = f"http://{host}{target}"
        else:
            raise HTTPException(status_code=422, detail="cannot resolve target host from raw request")
    return ParsedRaw(method=method, url=url, headers=headers, body=body or None)


def _row_to_tab(row: dict) -> dict:
    for key, default in (
        ("request_headers", {}),
        ("last_response_headers", None),
        ("history", []),
    ):
        try:
            row[key] = json.loads(row[key]) if row.get(key) else ({} if default == {} else default)
        except (json.JSONDecodeError, TypeError):
            row[key] = {} if default == {} else default
    return row


class TabCreate(BaseModel):
    name: str | None = None
    method: str = "GET"
    url: str = ""
    request_headers: dict[str, str] = {}
    request_body: str | None = None


class TabUpdate(BaseModel):
    name: str | None = None
    method: str | None = None
    url: str | None = None
    request_headers: dict[str, str] | None = None
    request_body: str | None = None


class SendIn(BaseModel):
    raw_request: str | None = None  # if omitted, stored request is used


def _stored_raw(row: dict) -> str:
    """Render the stored tab as canonical raw HTTP (Burp-style start line)."""
    parts = urlsplit(row["url"])
    target = parts.path or "/"
    if parts.query:
        target += f"?{parts.query}"
    headers = json.loads(row["request_headers"]) if row["request_headers"] else {}
    lines = [f"{row['method']} {target} HTTP/1.1"]
    if not any(k.lower() == "host" for k in headers):
        lines.append(f"Host: {parts.netloc}")
    lines.extend(f"{k}: {v}" for k, v in headers.items())
    raw = "\n".join(lines)
    if row.get("request_body"):
        raw += f"\n\n{row['request_body']}"
    return raw


@router.get("/tabs")
async def list_tabs() -> list[dict]:
    rows = await database.fetch_all("SELECT * FROM repeater_tabs ORDER BY id")
    return [_row_to_tab(r) for r in rows]


@router.post("/tabs", status_code=201)
async def create_tab(body: TabCreate) -> dict:
    name = body.name or f"{body.method} {urlsplit(body.url).netloc or 'new'}"
    tab_id = await database.execute(
        """INSERT INTO repeater_tabs (name, method, url, request_headers, request_body, history)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (name, body.method, body.url, json.dumps(body.request_headers), body.request_body, json.dumps([])),
    )
    row = await database.fetch_one("SELECT * FROM repeater_tabs WHERE id = ?", (tab_id,))
    return _row_to_tab(row)


@router.get("/tabs/{tab_id}")
async def get_tab(tab_id: int) -> dict:
    row = await database.fetch_one("SELECT * FROM repeater_tabs WHERE id = ?", (tab_id,))
    if not row:
        raise HTTPException(status_code=404, detail="repeater tab not found")
    return _row_to_tab(row)


@router.put("/tabs/{tab_id}")
async def update_tab(tab_id: int, body: TabUpdate) -> dict:
    row = await database.fetch_one("SELECT * FROM repeater_tabs WHERE id = ?", (tab_id,))
    if not row:
        raise HTTPException(status_code=404, detail="repeater tab not found")
    await database.execute(
        """UPDATE repeater_tabs SET
             name = ?, method = ?, url = ?, request_headers = ?, request_body = ?
           WHERE id = ?""",
        (
            body.name or row["name"],
            body.method or row["method"],
            body.url or row["url"],
            json.dumps(body.request_headers) if body.request_headers is not None else row["request_headers"],
            body.request_body if body.request_body is not None else row["request_body"],
            tab_id,
        ),
    )
    row = await database.fetch_one("SELECT * FROM repeater_tabs WHERE id = ?", (tab_id,))
    return _row_to_tab(row)


@router.delete("/tabs/{tab_id}")
async def delete_tab(tab_id: int) -> dict:
    row = await database.fetch_one("SELECT id FROM repeater_tabs WHERE id = ?", (tab_id,))
    if not row:
        raise HTTPException(status_code=404, detail="repeater tab not found")
    await database.execute("DELETE FROM repeater_tabs WHERE id = ?", (tab_id,))
    return {"deleted": True}


@router.post("/tabs/{tab_id}/send")
async def send_tab(tab_id: int, body: SendIn | None = None) -> dict:
    row = await database.fetch_one("SELECT * FROM repeater_tabs WHERE id = ?", (tab_id,))
    if not row:
        raise HTTPException(status_code=404, detail="repeater tab not found")

    raw = (body.raw_request if body and body.raw_request else _stored_raw(row)).strip()
    parsed = parse_raw_request(raw, fallback_url=row["url"])

    # update stored tab from the edited raw request
    await database.execute(
        "UPDATE repeater_tabs SET method = ?, url = ?, request_headers = ?, request_body = ? WHERE id = ?",
        (parsed.method, parsed.url, json.dumps(parsed.headers), parsed.body, tab_id),
    )

    send_headers = {
        k: v for k, v in parsed.headers.items()
        if k.lower() not in ("host", "content-length", "connection", "accept-encoding")
    }
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(
            follow_redirects=False,
            verify=False,  # lab targets commonly use self-signed certs
            timeout=30.0,
        ) as client:
            resp = await client.request(
                parsed.method,
                parsed.url,
                headers=send_headers,
                content=parsed.body.encode("utf-8") if parsed.body else None,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"request failed: {exc}")

    elapsed = int((time.monotonic() - started) * 1000)
    resp_body = resp.text
    resp_headers = dict(resp.headers)

    history = json.loads(row["history"]) if row["history"] else []
    history.append(
        {
            "sent_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "method": parsed.method,
            "url": parsed.url,
            "status": resp.status_code,
            "time_ms": elapsed,
        }
    )
    await database.execute(
        """UPDATE repeater_tabs SET last_response_status = ?, last_response_headers = ?,
             last_response_body = ?, last_response_time_ms = ?, history = ? WHERE id = ?""",
        (resp.status_code, json.dumps(resp_headers), resp_body, elapsed, json.dumps(history[-20:]), tab_id),
    )
    return {
        "status": resp.status_code,
        "headers": resp_headers,
        "body": resp_body,
        "time_ms": elapsed,
        "size": len(resp.content),
    }
