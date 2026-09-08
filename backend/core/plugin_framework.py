"""Plugin framework — runnable action plugins with live results (spec 005).

A plugin is a class with a small contract; the engine runs it as a background
task, persists runs/results, and streams everything over WebSocket.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, Awaitable, Callable

from api.websocket import broadcast
from db import database
from utils.logger import get_logger

log = get_logger(__name__)

Emit = Callable[[str, dict], Awaitable[None]]  # emit(kind, data)


class PhantomPlugin:
    """Contract for plugins — subclass and register()."""

    id: str = "base"
    name: str = "Base Plugin"
    description: str = ""
    accepts: list[str] = []  # context kinds: "request"
    parameters: list[dict] = []  # declarative options -> auto-rendered UI

    async def run(self, context: dict, options: dict, emit: Emit) -> None:
        raise NotImplementedError


_REGISTRY: dict[str, PhantomPlugin] = {}


def register(plugin: PhantomPlugin) -> None:
    _REGISTRY[plugin.id] = plugin


def available() -> list[dict]:
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "accepts": p.accepts,
            "parameters": p.parameters,
        }
        for p in _REGISTRY.values()
    ]


def get_plugin(plugin_id: str) -> PhantomPlugin | None:
    return _REGISTRY.get(plugin_id)


async def resolve_request_context(context: dict) -> dict:
    """Context {'kind':'request','history_id':N} -> request dict (method/url/headers/body)."""
    if context.get("kind") == "raw":
        from api.repeater_routes import parse_raw_request

        parsed = parse_raw_request(context["raw_request"], fallback_url=None)
        return {
            "method": parsed.method,
            "url": parsed.url,
            "headers": parsed.headers,
            "body": parsed.body,
        }
    entry = await database.fetch_one(
        "SELECT * FROM proxy_history WHERE id = ?", (context.get("history_id"),)
    )
    if not entry:
        raise ValueError(f"history entry #{context.get('history_id')} not found")
    try:
        headers = json.loads(entry["request_headers"] or "{}")
    except json.JSONDecodeError:
        headers = {}
    return {
        "method": entry["method"],
        "url": entry["url"],
        "headers": headers,
        "body": entry.get("request_body"),
    }


class PluginEngine:
    def __init__(self) -> None:
        self.runs: dict[str, dict] = {}

    async def start(self, plugin_id: str, context: dict, options: dict) -> str:
        plugin = get_plugin(plugin_id)
        if not plugin:
            raise ValueError(f"unknown plugin: {plugin_id}")
        run_id = uuid.uuid4().hex[:12]
        target = str(context.get("history_id") or context.get("url") or "custom request")
        await database.execute(
            """INSERT INTO plugin_runs (id, plugin_id, target, status, options)
               VALUES (?, ?, ?, 'running', ?)""",
            (run_id, plugin_id, target, json.dumps(options)),
        )
        self.runs[run_id] = {"plugin_id": plugin_id, "stopped": False}
        context = {**context, "_run_id": run_id}  # plugins check engine.is_stopped(_run_id)
        task = asyncio.create_task(self._run(run_id, plugin, context, options), name=f"plugin-{run_id}")
        self.runs[run_id]["task"] = task
        return run_id

    def stop(self, run_id: str) -> None:
        run = self.runs.get(run_id)
        if not run:
            raise KeyError("run not active")
        run["stopped"] = True

    def is_stopped(self, run_id: str) -> bool:
        return self.runs.get(run_id, {}).get("stopped", False)

    async def _run(self, run_id: str, plugin: PhantomPlugin, context: dict, options: dict) -> None:
        status = "completed"

        async def emit(kind: str, data: dict) -> None:
            await self._emit(run_id, kind, data)

        try:
            await plugin.run(context, options, emit)
        except Exception as exc:
            log.exception("plugin run %s (%s) failed", run_id, plugin.id)
            status = "failed"
            await database.execute(
                "UPDATE plugin_runs SET error = ? WHERE id = ?", (str(exc)[:500], run_id)
            )
        if self.is_stopped(run_id):
            status = "stopped"
        await database.execute(
            "UPDATE plugin_runs SET status = ? WHERE id = ?", (status, run_id)
        )
        self.runs.pop(run_id, None)
        await broadcast(
            "plugin_done",
            {"run_id": run_id, "plugin_id": plugin.id, "status": status},
        )

    async def _emit(self, run_id: str, kind: str, data: dict) -> None:
        if kind == "progress":
            await database.execute(
                "UPDATE plugin_runs SET done = ?, total = ? WHERE id = ?",
                (data.get("done", 0), data.get("total", 0), run_id),
            )
            await broadcast("plugin_progress", {"run_id": run_id, **data})
            return
        # any other kind is a persisted result row
        row_id = await database.execute(
            "INSERT INTO plugin_results (run_id, kind, data) VALUES (?, ?, ?)",
            (run_id, kind, json.dumps(data)),
        )
        await broadcast("plugin_result", {"run_id": run_id, "id": row_id, "kind": kind, "data": data})


_engine = PluginEngine()


def get_plugin_engine() -> PluginEngine:
    return _engine


# register built-ins (import side effects)
from core.plugins import hpere  # noqa: E402,F401
