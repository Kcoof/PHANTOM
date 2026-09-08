"""AI Copilot API — /api/ai with SSE streaming (contracts/api.md + spec 004 triage)."""
from __future__ import annotations

import asyncio
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


# --- AI auto-triage (spec 004) -------------------------------------------------

SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
VALID_VERDICTS = {"likely-real", "likely-fp", "needs-manual"}


def parse_triage_json(text: str) -> list[dict]:
    """Tolerantly extract the JSON verdict array from a model response."""
    import re as _re

    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        return []
    candidate = text[start : end + 1]
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        candidate2 = _re.sub(r",\s*]", "]", candidate)  # trailing commas
        try:
            data = json.loads(candidate2)
        except json.JSONDecodeError:
            return []
    out = []
    if not isinstance(data, list):
        return []
    for item in data:
        if not isinstance(item, dict):
            continue
        verdict = str(item.get("verdict", "")).strip().lower()
        if verdict not in VALID_VERDICTS:
            continue
        try:
            fid = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        try:
            priority = max(1, min(5, int(item.get("priority", 3))))
        except (TypeError, ValueError):
            priority = 3
        out.append(
            {
                "id": fid,
                "verdict": verdict,
                "reason": str(item.get("reason", ""))[:200],
                "priority": priority,
            }
        )
    return out


def _triage_prompt(batch: list[dict]) -> str:
    lines = []
    for f in batch:
        evidence = (f.get("evidence") or "")[:140].replace("\n", " ")
        lines.append(
            f"#{f['id']} [{f['severity']}/{f['finding_type']}/{f['confidence']}] "
            f"{f['title']} — {f['url']} | evidence: {evidence or '(none)'}"
        )
    return (
        "You are triaging automated security-scanner findings. Judge each one: is it a real, "
        "reportable security issue, or scanner noise / false positive / informational-only?\n"
        "Context heuristics: missing CSP/header findings on static assets are usually low value; "
        "cookie-flag and CSRF findings on API/CORS endpoints are often false positives; "
        "secret/credential findings and reflected payloads are high value if evidence matches.\n"
        "Respond ONLY with a JSON array, one object per finding, exactly:\n"
        '[{"id": <finding id>, "verdict": "likely-real"|"likely-fp"|"needs-manual", '
        '"reason": "<=20 words", "priority": 1-5}]\n'
        "priority: 5 = report immediately, 1 = ignore.\n\nFindings:\n" + "\n".join(lines)
    )


_triage_task: asyncio.Task | None = None


class TriageIn(BaseModel):
    severity: str | None = None
    scan_id: str | None = None
    limit: int = 100


@router.post("/triage")
async def start_triage(body: TriageIn | None = None):
    global _triage_task
    await _require_runtime()
    if _triage_task is not None and not _triage_task.done():
        raise HTTPException(status_code=409, detail="a triage run is already in progress")
    body = body or TriageIn()

    where, params = "status != 'false_positive' AND ai_verdict IS NULL", []
    if body.severity:
        where += " AND severity = ?"
        params.append(body.severity)
    if body.scan_id:
        where += " AND scan_id = ?"
        params.append(body.scan_id)
    findings = await database.fetch_all(
        f"SELECT * FROM scanner_findings WHERE {where} ORDER BY id DESC LIMIT 500", tuple(params)
    )
    findings.sort(key=lambda f: (SEVERITY_RANK.get(f["severity"], 9), -f["id"]))
    findings = findings[: max(1, min(body.limit, 100))]
    if not findings:
        raise HTTPException(status_code=422, detail="no findings to triage")

    engine = get_ai_engine()
    model_name = (await engine.current_config())["model"]

    async def run():
        global _triage_task
        done = 0
        tagged = 0
        batches = [findings[i : i + 10] for i in range(0, len(findings), 10)]
        for batch in batches:
            chunks: list[str] = []
            for attempt in range(3):  # free-tier rate limits recover in ~a minute
                try:
                    async for delta in engine.stream_chat(
                        [{"role": "user", "content": _triage_prompt(batch)}]
                    ):
                        chunks.append(delta)
                    break
                except Exception as exc:
                    log.warning("triage batch attempt %s failed: %s", attempt + 1, exc)
                    chunks = []
                    if attempt < 2:
                        await asyncio.sleep(60)  # let the rate-limit window reset
            try:
                verdicts = parse_triage_json("".join(chunks))
                for v in verdicts:
                    if not any(f["id"] == v["id"] for f in batch):
                        continue
                    await database.execute(
                        "UPDATE scanner_findings SET ai_verdict = ? WHERE id = ?",
                        (
                            json.dumps(
                                {
                                    "verdict": v["verdict"],
                                    "reason": v["reason"],
                                    "priority": v["priority"],
                                    "model": model_name,
                                }
                            ),
                            v["id"],
                        ),
                    )
                    tagged += 1
            except Exception:
                log.exception("triage verdict write failed")
            done += len(batch)
            await broadcast(
                "ai_triage_progress",
                {"done": done, "total": len(findings), "tagged": tagged},
            )
            if batch is not batches[-1]:
                await asyncio.sleep(2.5)  # be gentle with free-tier rate limits
        await broadcast(
            "ai_triage_done",
            {"done": done, "total": len(findings), "tagged": tagged},
        )
        _triage_task = None

    _triage_task = asyncio.create_task(run(), name="ai-triage")
    return {"started": True, "count": len(findings), "batches": (len(findings) + 9) // 10}
