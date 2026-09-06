"""Settings & scope rules API — /api/settings (contracts/api.md)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from db import database
from db.models import ScopeRule

router = APIRouter()

VALID_CATEGORIES = {"proxy", "scanner", "ai", "ui", "general"}


class SettingsUpdate(BaseModel):
    values: dict[str, str]


@router.get("")
async def get_settings() -> dict:
    rows = await database.fetch_all("SELECT key, value, category FROM settings ORDER BY category, key")
    grouped: dict[str, dict[str, str]] = {}
    for row in rows:
        grouped.setdefault(row["category"], {})[row["key"]] = row["value"]
    return {"categories": grouped}


@router.put("")
async def update_settings(body: SettingsUpdate) -> dict:
    if not body.values:
        raise HTTPException(status_code=422, detail="no settings provided")
    existing = await database.fetch_all("SELECT key FROM settings")
    known = {r["key"] for r in existing}
    unknown = set(body.values) - known
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"unknown setting key(s): {', '.join(sorted(unknown))}",
        )
    await database.execute_many(
        "UPDATE settings SET value = ? WHERE key = ?",
        [(v, k) for k, v in body.values.items()],
    )
    return await get_settings()


# --- Scope rules -----------------------------------------------------------

class ScopeRuleIn(BaseModel):
    rule_type: str
    protocol: str | None = None
    host_pattern: str
    port: str | None = None
    path_pattern: str = ".*"
    is_active: bool = True

    @field_validator("rule_type")
    @classmethod
    def _valid_type(cls, v: str) -> str:
        if v not in ("include", "exclude"):
            raise ValueError("rule_type must be 'include' or 'exclude'")
        return v

    @field_validator("protocol")
    @classmethod
    def _valid_protocol(cls, v: str | None) -> str | None:
        if v and v not in ("http", "https", "any"):
            raise ValueError("protocol must be http, https, or any")
        return v


@router.get("/scope")
async def get_scope() -> list[dict]:
    return await database.fetch_all("SELECT * FROM scope_rules ORDER BY id")


@router.post("/scope", status_code=201)
async def add_scope_rule(rule: ScopeRuleIn) -> dict:
    # validate regex up front (data-model: invalid patterns rejected)
    import re

    try:
        re.compile(rule.path_pattern)
    except re.error as exc:
        raise HTTPException(status_code=422, detail=f"invalid path_pattern: {exc}")
    rule_id = await database.execute(
        """INSERT INTO scope_rules (rule_type, protocol, host_pattern, port, path_pattern, is_active)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (rule.rule_type, rule.protocol, rule.host_pattern, rule.port, rule.path_pattern, int(rule.is_active)),
    )
    row = await database.fetch_one("SELECT * FROM scope_rules WHERE id = ?", (rule_id,))
    return row


@router.delete("/scope/{rule_id}")
async def delete_scope_rule(rule_id: int) -> dict:
    row = await database.fetch_one("SELECT id FROM scope_rules WHERE id = ?", (rule_id,))
    if not row:
        raise HTTPException(status_code=404, detail="scope rule not found")
    await database.execute("DELETE FROM scope_rules WHERE id = ?", (rule_id,))
    return {"deleted": True}
