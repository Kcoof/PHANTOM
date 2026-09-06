"""WebSocket event bus — /ws endpoint + broadcast registry (Constitution III).

Any engine can `await broadcast(event, data)`; all connected clients receive
`{"event": ..., "data": ...}` frames. Clients may send {"event":"ping"}.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from utils.logger import get_logger

log = get_logger(__name__)
router = APIRouter()

_connections: set[WebSocket] = set()
_lock = asyncio.Lock()


async def broadcast(event: str, data: Any) -> None:
    message = json.dumps({"event": event, "data": data})
    async with _lock:
        dead: list[WebSocket] = []
        for ws in _connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            _connections.discard(ws)


def connection_count() -> int:
    return len(_connections)


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    async with _lock:
        _connections.add(ws)
    log.info("ws client connected (%d total)", len(_connections))
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("event") == "ping":
                    await ws.send_text(json.dumps({"event": "pong", "data": {}}))
            except json.JSONDecodeError:
                continue
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("ws error")
    finally:
        async with _lock:
            _connections.discard(ws)
        log.info("ws client disconnected (%d total)", len(_connections))
