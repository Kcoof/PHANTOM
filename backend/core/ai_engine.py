"""AI engine — Ollama-compatible local runtime with streaming (research.md D4).

Local-first: talks to a configurable local endpoint; degrades gracefully with
a clear status when the runtime is unavailable (Constitution V + VII).
"""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

import config
from utils.logger import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """You are PHANTOM AI, an expert web application security analyst.
You analyze HTTP requests and responses to find security vulnerabilities.

When analyzing a request, you should:
1. Identify the technology stack from headers and response patterns
2. Check for common vulnerability patterns
3. Suggest specific attack vectors with example payloads
4. Rate the risk level of each finding
5. Provide remediation advice

Always be specific and actionable. Include exact payloads the user can try.
Format findings clearly with severity ratings.
Reminder: this analysis supports authorized security testing only."""


class AIEngine:
    def __init__(self) -> None:
        self.base_url = config.AI_BASE_URL
        self.model = config.AI_MODEL

    async def status(self) -> dict:
        result = {
            "available": False,
            "provider": "ollama",
            "model": self.model,
            "base_url": self.base_url,
            "detail": None,
        }
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    models = [m.get("name", "") for m in resp.json().get("models", [])]
                    result["available"] = True
                    result["models"] = models
                    if models and not any(m.startswith(self.model.split(":")[0]) for m in models):
                        result["detail"] = (
                            f"runtime up; model '{self.model}' not pulled (available: {', '.join(models[:5])})"
                        )
                else:
                    result["detail"] = f"runtime responded {resp.status_code}"
        except httpx.HTTPError as exc:
            result["detail"] = f"cannot reach {self.base_url} ({exc.__class__.__name__})"
        return result

    async def stream_chat(
        self,
        messages: list[dict],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield assistant text deltas from an Ollama-compatible /api/chat stream."""
        payload = {
            "model": model or self.model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=config.AI_TIMEOUT_S) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                if resp.status_code != 200:
                    body = (await resp.aread()).decode("utf-8", errors="replace")[:300]
                    raise RuntimeError(f"AI runtime error {resp.status_code}: {body}")
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if data.get("error"):
                        raise RuntimeError(f"AI runtime error: {data['error']}")
                    message = data.get("message") or {}
                    delta = message.get("content")
                    if delta:
                        yield delta
                    if data.get("done"):
                        return


_engine = AIEngine()


def get_ai_engine() -> AIEngine:
    return _engine
