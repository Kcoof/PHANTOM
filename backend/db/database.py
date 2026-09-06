"""Async SQLite access layer — single local database, WAL mode (data-model.md)."""
from __future__ import annotations

import aiosqlite

from config import DB_PATH
from utils.logger import get_logger

log = get_logger(__name__)

_connection: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    """Return the shared connection, opening it (WAL) on first use."""
    global _connection
    if _connection is None:
        _connection = await aiosqlite.connect(DB_PATH)
        _connection.row_factory = aiosqlite.Row
        await _connection.execute("PRAGMA journal_mode=WAL")
        await _connection.execute("PRAGMA foreign_keys=ON")
        await _connection.execute("PRAGMA synchronous=NORMAL")
    return _connection


async def init_db() -> None:
    """Create schema and seed defaults (idempotent)."""
    from db import migrations  # local import to avoid cycle

    db = await get_db()
    await migrations.apply(db)
    log.info("database ready at %s", DB_PATH)


async def close_db() -> None:
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None
        log.info("database closed")


async def fetch_all(query: str, params: tuple = ()) -> list[dict]:
    db = await get_db()
    async with db.execute(query, params) as cur:
        rows = await cur.fetchall()
    return [dict(r) for r in rows]


async def fetch_one(query: str, params: tuple = ()) -> dict | None:
    db = await get_db()
    async with db.execute(query, params) as cur:
        row = await cur.fetchone()
    return dict(row) if row else None


async def execute(query: str, params: tuple = ()) -> int:
    """Run a write; returns lastrowid."""
    db = await get_db()
    cur = await db.execute(query, params)
    await db.commit()
    return cur.lastrowid or 0


async def execute_many(query: str, params: list[tuple]) -> None:
    db = await get_db()
    await db.executemany(query, params)
    await db.commit()
