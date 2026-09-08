"""PHANTOM Security Platform — backend entry point.

Run: uvicorn main:app --host 127.0.0.1 --port 8899 --reload  (from backend/)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from api import (
    ai_routes,
    dashboard_routes,
    decoder_routes,
    history_routes,
    intruder_routes,
    match_replace_routes,
    plugin_routes,
    proxy_routes,
    repeater_routes,
    scanner_routes,
    search_routes,
    settings_routes,
    websocket,
)
from core.proxy_engine import get_proxy_engine
from db.database import close_db, init_db
from utils.logger import get_logger, setup_logging

log = get_logger("phantom")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    config.ensure_data_dir()
    await init_db()
    log.info("PHANTOM backend starting on %s:%s", config.BACKEND_HOST, config.BACKEND_PORT)
    yield
    engine = get_proxy_engine()
    await engine.stop()
    await close_db()
    log.info("PHANTOM backend stopped")


app = FastAPI(
    title="PHANTOM Security Platform",
    version="1.0.0",
    description="Local-first web security testing platform — authorized testing only.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(proxy_routes.router, prefix="/api/proxy", tags=["Proxy"])
app.include_router(history_routes.router, prefix="/api/history", tags=["History"])
app.include_router(repeater_routes.router, prefix="/api/repeater", tags=["Repeater"])
app.include_router(scanner_routes.router, prefix="/api/scanner", tags=["Scanner"])
app.include_router(ai_routes.router, prefix="/api/ai", tags=["AI Copilot"])
app.include_router(decoder_routes.router, prefix="/api/decoder", tags=["Decoder"])
app.include_router(dashboard_routes.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(settings_routes.router, prefix="/api/settings", tags=["Settings"])
app.include_router(intruder_routes.router, prefix="/api/intruder", tags=["Intruder"])
app.include_router(search_routes.router, prefix="/api/search", tags=["Search"])
app.include_router(match_replace_routes.router, prefix="/api/match-replace", tags=["Match & Replace"])
app.include_router(plugin_routes.router, prefix="/api/plugins", tags=["Plugins"])
app.include_router(websocket.router, tags=["WebSocket"])


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "app": "phantom", "version": "1.0.0"}
