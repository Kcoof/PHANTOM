"""AI engine — local Ollama or any OpenAI-compatible provider (spec: D4 + user request).

Local-first default (Constitution VII): provider 'ollama' talks to a local
runtime. Provider 'openai' enables optional cloud/local OpenAI-compatible
endpoints (Groq, OpenRouter, LM Studio, Gemini compat, ...) — opt-in, with the
operator's API key stored locally. All settings are read live from the DB so
switching provider/model never needs a restart.
"""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

import config
from db import database
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


async def _settings() -> dict:
    rows = await database.fetch_all("SELECT key, value FROM settings WHERE category = 'ai'")
    s = {r["key"]: r["value"] for r in rows}
    return {
        "provider": s.get("ai_provider", config.AI_BASE_URL and "ollama" or "ollama"),
        "model": s.get("ai_model", config.AI_MODEL),
        "base_url": s.get("ai_base_url", config.AI_BASE_URL).rstrip("/"),
        "api_key": s.get("ai_api_key", ""),
    }


class AIEngine:
    @property
    def model(self) -> str:
        return config.AI_MODEL

    async def current_config(self) -> dict:
        return await _settings()

    async def status(self) -> dict:
        s = await _settings()
        result = {
            "available": False,
            "provider": s["provider"],
            "model": s["model"],
            "base_url": s["base_url"],
            "detail": None,
        }
        try:
            if s["provider"] == "openai":
                if not s["api_key"]:
                    result["detail"] = "provider is OpenAI-compatible but no API key set (Settings → AI → ai_api_key)"
                    return result
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        f"{s['base_url']}/models",
                        headers={"Authorization": f"Bearer {s['api_key']}"},
                    )
                if resp.status_code == 200:
                    result["available"] = True
                    try:
                        models = [m.get("id", "") for m in resp.json().get("data", [])][:20]
                        result["models"] = models
                    except (json.JSONDecodeError, AttributeError):
                        pass
                else:
                    result["detail"] = f"provider responded {resp.status_code} (check base_url / api_key)"
            else:  # ollama (local default)
                async with httpx.AsyncClient(timeout=3.0) as client:
                    resp = await client.get(f"{s['base_url']}/api/tags")
                if resp.status_code == 200:
                    models = [m.get("name", "") for m in resp.json().get("models", [])]
                    result["available"] = True
                    result["models"] = models
                    if models and not any(m.startswith(s["model"].split(":")[0]) for m in models):
                        result["detail"] = f"runtime up; model '{s['model']}' not pulled (available: {', '.join(models[:5])})"
                else:
                    result["detail"] = f"runtime responded {resp.status_code}"
        except httpx.HTTPError as exc:
            result["detail"] = f"cannot reach {s['base_url']} ({exc.__class__.__name__})"
        return result

    async def stream_chat(
        self,
        messages: list[dict],
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """Yield assistant text deltas; dispatches on the configured provider."""
        s = await _settings()
        model = model or s["model"]
        if s["provider"] == "openai":
            async for delta in self._stream_openai(s, model, messages):
                yield delta
        else:
            async for delta in self._stream_ollama(s, model, messages):
                yield delta

    async def _stream_ollama(self, s: dict, model: str, messages: list[dict]) -> AsyncIterator[str]:
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=config.AI_TIMEOUT_S) as client:
            async with client.stream("POST", f"{s['base_url']}/api/chat", json=payload) as resp:
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
                    delta = (data.get("message") or {}).get("content")
                    if delta:
                        yield delta
                    if data.get("done"):
                        return

    async def _stream_openai(self, s: dict, model: str, messages: list[dict]) -> AsyncIterator[str]:
        if not s["api_key"]:
            raise RuntimeError("no API key configured (Settings → AI → ai_api_key)")
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, *messages],
            "stream": True,
        }
        headers = {"Authorization": f"Bearer {s['api_key']}"}
        async with httpx.AsyncClient(timeout=config.AI_TIMEOUT_S) as client:
            async with client.stream(
                "POST", f"{s['base_url']}/chat/completions", json=payload, headers=headers
            ) as resp:
                if resp.status_code != 200:
                    raw = (await resp.aread()).decode("utf-8", errors="replace")
                    try:
                        msg = json.loads(raw)["error"]["message"][:220]
                    except (json.JSONDecodeError, KeyError, TypeError):
                        msg = raw[:220]
                    hint = ""
                    if resp.status_code in (413, 429):
                        hint = " — free-tier rate/size limit; retry in a minute or switch to a lighter model (Settings → AI)"
                    raise RuntimeError(f"AI provider error {resp.status_code}: {msg}{hint}")
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        return
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    choices = data.get("choices") or []
                    if choices:
                        delta = choices[0].get("delta", {}).get("content")
                        if delta:
                            yield delta


_engine = AIEngine()


def get_ai_engine() -> AIEngine:
    return _engine
