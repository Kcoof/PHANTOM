"""Proxy control API — /api/proxy (contracts/api.md)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from core.proxy_engine import ProxyError, get_proxy_engine
from utils import cert_manager

router = APIRouter()


class ProxyStartIn(BaseModel):
    host: str | None = None
    port: int | None = None


class InterceptToggleIn(BaseModel):
    enabled: bool
    filter: str | None = None


class ForwardIn(BaseModel):
    modified_request: str | None = None


@router.post("/start")
async def start_proxy(body: ProxyStartIn | None = None) -> dict:
    engine = get_proxy_engine()
    body = body or ProxyStartIn()
    try:
        return await engine.start(host=body.host, port=body.port)
    except ProxyError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/stop")
async def stop_proxy() -> dict:
    return await get_proxy_engine().stop()


@router.get("/status")
async def proxy_status() -> dict:
    return get_proxy_engine().status()


@router.post("/intercept/toggle")
async def intercept_toggle(body: InterceptToggleIn) -> dict:
    addon = get_proxy_engine().addon
    addon.intercept_enabled = body.enabled
    addon.intercept_filter = body.filter or ""
    if not body.enabled:
        addon.drop_all()
    return {"intercept": body.enabled, "filter": addon.intercept_filter}


@router.get("/intercept/queue")
async def intercept_queue() -> list[dict]:
    return get_proxy_engine().addon.queue_snapshot()


@router.post("/intercept/{flow_id}/forward")
async def intercept_forward(flow_id: str, body: ForwardIn | None = None) -> dict:
    ok = get_proxy_engine().addon.forward(
        flow_id, body.modified_request if body else None
    )
    if not ok:
        raise HTTPException(status_code=404, detail="flow not in intercept queue")
    return {"forwarded": True}


@router.post("/intercept/{flow_id}/drop")
async def intercept_drop(flow_id: str) -> dict:
    ok = get_proxy_engine().addon.drop(flow_id)
    if not ok:
        raise HTTPException(status_code=404, detail="flow not in intercept queue")
    return {"dropped": True}


@router.get("/ca-cert", response_class=PlainTextResponse)
async def ca_cert() -> PlainTextResponse:
    try:
        pem = cert_manager.get_ca_pem()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"CA unavailable: {exc}")
    return PlainTextResponse(pem, media_type="application/x-pem-file")
