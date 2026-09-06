"""Intruder API — /api/intruder (spec 003, FR-101)."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.intruder_engine import WORDLISTS, get_intruder_engine
from db import database

router = APIRouter()


class AttackStartIn(BaseModel):
    raw_request: str
    payloads: list[str]
    grep_patterns: list[str] | None = None
    name: str | None = None


@router.get("/wordlists")
async def wordlists() -> dict[str, int]:
    return {name: len(items) for name, items in WORDLISTS.items()}


@router.get("/wordlists/{name}")
async def wordlist_items(name: str) -> list[str]:
    if name not in WORDLISTS:
        raise HTTPException(status_code=404, detail="unknown wordlist")
    return WORDLISTS[name]


@router.post("/attacks", status_code=201)
async def start_attack(body: AttackStartIn) -> dict:
    try:
        attack_id = await get_intruder_engine().start(
            body.raw_request, body.payloads, body.grep_patterns, body.name
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"attack_id": attack_id, "status": "running"}


@router.get("/attacks")
async def list_attacks() -> list[dict]:
    return await database.fetch_all(
        "SELECT id, name, status, total, done, created_at, baseline_status, baseline_length "
        "FROM intruder_attacks ORDER BY created_at DESC LIMIT 100"
    )


@router.get("/attacks/{attack_id}")
async def get_attack(attack_id: str) -> dict:
    row = await database.fetch_one(
        "SELECT * FROM intruder_attacks WHERE id = ?", (attack_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="attack not found")
    row["payloads"] = json.loads(row["payloads"]) if row["payloads"] else []
    row["grep_patterns"] = json.loads(row["grep_patterns"]) if row["grep_patterns"] else []
    return row


@router.get("/attacks/{attack_id}/results")
async def attack_results(attack_id: str, only_deviations: bool = False) -> list[dict]:
    row = await database.fetch_one(
        "SELECT baseline_status, baseline_length FROM intruder_attacks WHERE id = ?",
        (attack_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="attack not found")
    rows = await database.fetch_all(
        "SELECT id, idx, payload, status, length, time_ms, matched, is_baseline, url "
        "FROM intruder_results WHERE attack_id = ? ORDER BY idx LIMIT 5000",
        (attack_id,),
    )
    for r in rows:
        try:
            r["matched"] = json.loads(r["matched"]) if r["matched"] else []
        except json.JSONDecodeError:
            r["matched"] = []
        r["deviates"] = (
            not r["is_baseline"]
            and (r["status"] != row["baseline_status"] or r["length"] != row["baseline_length"])
        )
    if only_deviations:
        rows = [r for r in rows if r["deviates"]]
    return rows


@router.get("/results/{result_id}")
async def result_detail(result_id: int) -> dict:
    row = await database.fetch_one(
        "SELECT * FROM intruder_results WHERE id = ?", (result_id,)
    )
    if not row:
        raise HTTPException(status_code=404, detail="result not found")
    return row


@router.post("/attacks/{attack_id}/stop")
async def stop_attack(attack_id: str) -> dict:
    try:
        get_intruder_engine().stop(attack_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="attack not running")
    return {"stopped": True}


@router.delete("/attacks/{attack_id}")
async def delete_attack(attack_id: str) -> dict:
    await database.execute("DELETE FROM intruder_results WHERE attack_id = ?", (attack_id,))
    await database.execute("DELETE FROM intruder_attacks WHERE id = ?", (attack_id,))
    return {"deleted": True}
