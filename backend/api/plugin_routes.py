"""Plugins API — /api/plugins (spec 005, FR-301)."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.plugin_framework import available, get_plugin_engine
from db import database

router = APIRouter()


class PluginRunIn(BaseModel):
    context: dict  # {"kind": "request", "history_id": N} | {"kind": "raw", "raw_request": str}
    options: dict = {}


@router.get("")
async def list_plugins() -> list[dict]:
    return available()


@router.post("/{plugin_id}/run", status_code=201)
async def run_plugin(plugin_id: str, body: PluginRunIn):
    try:
        run_id = await get_plugin_engine().start(plugin_id, body.context, body.options)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "unknown plugin" in str(exc) else 422, detail=str(exc))
    return {"run_id": run_id, "status": "running"}


@router.get("/runs")
async def list_runs() -> list[dict]:
    return await database.fetch_all(
        "SELECT * FROM plugin_runs ORDER BY created_at DESC LIMIT 100"
    )


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    row = await database.fetch_one("SELECT * FROM plugin_runs WHERE id = ?", (run_id,))
    if not row:
        raise HTTPException(status_code=404, detail="run not found")
    return row


@router.get("/runs/{run_id}/results")
async def run_results(run_id: str) -> list[dict]:
    rows = await database.fetch_all(
        "SELECT * FROM plugin_results WHERE run_id = ? ORDER BY id", (run_id,)
    )
    for r in rows:
        try:
            r["data"] = json.loads(r["data"])
        except json.JSONDecodeError:
            r["data"] = {}
    return rows


@router.post("/runs/{run_id}/stop")
async def stop_run(run_id: str) -> dict:
    try:
        get_plugin_engine().stop(run_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="run not active")
    return {"stopped": True}


@router.delete("/runs/{run_id}")
async def delete_run(run_id: str) -> dict:
    await database.execute("DELETE FROM plugin_results WHERE run_id = ?", (run_id,))
    await database.execute("DELETE FROM plugin_runs WHERE id = ?", (run_id,))
    return {"deleted": True}
