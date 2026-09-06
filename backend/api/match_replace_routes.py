"""Match & Replace API — /api/match-replace (spec 003, FR-003)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from db import database

router = APIRouter()


class RuleIn(BaseModel):
    enabled: bool = True
    location: str  # request | response
    match_type: str  # literal | regex
    match_value: str
    replace_value: str = ""
    comment: str | None = None

    @field_validator("location")
    @classmethod
    def _loc(cls, v: str) -> str:
        if v not in ("request", "response"):
            raise ValueError("location must be request or response")
        return v

    @field_validator("match_type")
    @classmethod
    def _mt(cls, v: str) -> str:
        if v not in ("literal", "regex"):
            raise ValueError("match_type must be literal or regex")
        return v


@router.get("")
async def list_rules() -> list[dict]:
    return await database.fetch_all("SELECT * FROM match_replace_rules ORDER BY id")


@router.post("", status_code=201)
async def add_rule(rule: RuleIn) -> dict:
    if rule.match_type == "regex":
        import re

        try:
            re.compile(rule.match_value)
        except re.error as exc:
            raise HTTPException(status_code=422, detail=f"invalid regex: {exc}")
    rule_id = await database.execute(
        """INSERT INTO match_replace_rules (enabled, location, match_type, match_value, replace_value, comment)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (1 if rule.enabled else 0, rule.location, rule.match_type, rule.match_value, rule.replace_value, rule.comment),
    )
    row = await database.fetch_one("SELECT * FROM match_replace_rules WHERE id = ?", (rule_id,))
    return row


@router.put("/{rule_id}")
async def update_rule(rule_id: int, rule: RuleIn) -> dict:
    existing = await database.fetch_one("SELECT id FROM match_replace_rules WHERE id = ?", (rule_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="rule not found")
    await database.execute(
        "UPDATE match_replace_rules SET enabled = ?, location = ?, match_type = ?, match_value = ?, replace_value = ?, comment = ? WHERE id = ?",
        (1 if rule.enabled else 0, rule.location, rule.match_type, rule.match_value, rule.replace_value, rule.comment, rule_id),
    )
    row = await database.fetch_one("SELECT * FROM match_replace_rules WHERE id = ?", (rule_id,))
    return row


@router.delete("/{rule_id}")
async def delete_rule(rule_id: int) -> dict:
    await database.execute("DELETE FROM match_replace_rules WHERE id = ?", (rule_id,))
    return {"deleted": True}
