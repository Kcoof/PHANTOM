"""AI Copilot API — /api/ai with SSE streaming (contracts/api.md)."""
from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.ai_engine import get_ai_engine
from db import database
from utils.logger import get_logger

router = APIRouter()
log = get_logger(__name__)


class ChatIn(BaseModel):
    message: str
    context_type: str | None = None  # request | finding | general
    context_id: int | None = None


class PayloadSuggestIn(BaseModel):
    url: str
    parameter: str
    vuln_type: str = "xss"
    context: str | None = None


async def _sse(generator: AsyncIterator[str]) -> StreamingResponse:
    async def event_stream():
        try:
            async for delta in generator:
                yield f"data: {json.dumps({'delta': delta})}\n\n"
        except RuntimeError as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


async def _require_runtime() -> None:
    status = await get_ai_engine().status()
    if not status["available"]:
        raise HTTPException(
            status_code=503,
            detail=f"AI runtime unavailable — start Ollama (`ollama serve`, then `ollama pull {status['model']}`). {status['detail'] or ''}".strip(),
        )


async def _load_request_context(history_id: int) -> str:
    row = await database.fetch_one("SELECT * FROM proxy_history WHERE id = ?", (history_id,))
    if not row:
        raise HTTPException(status_code=404, detail="history entry not found")
    return (
        f"Analyze this HTTP request/response for security vulnerabilities:\n\n"
        f"--- REQUEST ---\n{row['method']} {row['url']}\n{row['request_headers']}\n\n{row.get('request_body') or ''}\n"
        f"--- RESPONSE (status {row['status_code']}) ---\n{row.get('response_headers') or ''}\n\n"
        f"{(row.get('response_body') or '')[:6000]}"
    )


async def _load_finding_context(finding_id: int) -> str:
    row = await database.fetch_one("SELECT * FROM scanner_findings WHERE id = ?", (finding_id,))
    if not row:
        raise HTTPException(status_code=404, detail="finding not found")
    return (
        f"A scanner found this potential vulnerability. Assess and suggest next steps:\n\n"
        f"Type: {row['finding_type']} (severity {row['severity']}, confidence {row['confidence']})\n"
        f"Title: {row['title']}\nURL: {row['url']}\nParameter: {row.get('parameter')}\n"
        f"Evidence: {(row.get('evidence') or '')[:1500]}\n"
        f"Description: {row['description']}"
    )


@router.post("/chat")
async def chat(body: ChatIn):
    await _require_runtime()
    context_text = ""
    if body.context_type == "request" and body.context_id is not None:
        context_text = await _load_request_context(body.context_id)
    elif body.context_type == "finding" and body.context_id is not None:
        context_text = await _load_finding_context(body.context_id)

    history = await database.fetch_all(
        "SELECT role, content FROM ai_conversations ORDER BY id DESC LIMIT 10"
    )
    messages = [{"role": m["role"], "content": m["content"]} for m in reversed(history)]
    messages.append({"role": "user", "content": (context_text + "\n\n" if context_text else "") + body.message})

    await database.execute(
        "INSERT INTO ai_conversations (role, content, context_type, context_id) VALUES (?, ?, ?, ?)",
        ("user", body.message, body.context_type, body.context_id),
    )

    async def generate():
        full = []
        try:
            async for delta in get_ai_engine().stream_chat(messages):
                full.append(delta)
                yield delta
        finally:
            if full:
                await database.execute(
                    "INSERT INTO ai_conversations (role, content, context_type, context_id, model) VALUES (?, ?, ?, ?, ?)",
                    ("assistant", "".join(full), body.context_type, body.context_id, get_ai_engine().model),
                )

    return await _sse(generate())


@router.post("/analyze-request/{history_id}")
async def analyze_request(history_id: int):
    await _require_runtime()
    prompt = await _load_request_context(history_id)
    messages = [{"role": "user", "content": prompt}]

    async def generate():
        full = []
        try:
            async for delta in get_ai_engine().stream_chat(messages):
                full.append(delta)
                yield delta
        finally:
            await database.execute(
                "INSERT INTO ai_conversations (role, content, context_type, context_id, model) VALUES (?, ?, ?, ?, ?)",
                ("user", f"[analyze request #{history_id}]", "request", history_id, get_ai_engine().model),
            )
            if full:
                await database.execute(
                    "INSERT INTO ai_conversations (role, content, context_type, context_id, model) VALUES (?, ?, ?, ?, ?)",
                    ("assistant", "".join(full), "request", history_id, get_ai_engine().model),
                )

    return await _sse(generate())


@router.post("/suggest-payloads")
async def suggest_payloads(body: PayloadSuggestIn):
    await _require_runtime()
    prompt = (
        f"Generate {body.vuln_type} test payloads for the parameter '{body.parameter}' at {body.url}.\n"
        f"{'Known context: ' + body.context if body.context else ''}\n"
        "Return a numbered list of concrete payloads with one-line explanations, then a note on how to verify each."
    )
    messages = [{"role": "user", "content": prompt}]
    return await _sse(get_ai_engine().stream_chat(messages))


@router.get("/conversations")
async def conversations() -> list[dict]:
    return await database.fetch_all(
        "SELECT * FROM ai_conversations ORDER BY id DESC LIMIT 200"
    )


@router.get("/status")
async def ai_status() -> dict:
    return await get_ai_engine().status()
