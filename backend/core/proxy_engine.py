"""Proxy engine — in-process mitmproxy lifecycle (research.md D1)."""
from __future__ import annotations

import asyncio

from mitmproxy import options as mp_options
from mitmproxy.tools.dump import DumpMaster

import config
from api.websocket import broadcast
from core.proxy_addon import PhantomAddon
from utils.logger import get_logger

log = get_logger(__name__)


class ProxyError(RuntimeError):
    pass


class ProxyEngine:
    def __init__(self) -> None:
        self.addon = PhantomAddon()
        self._master: DumpMaster | None = None
        self._task: asyncio.Task | None = None
        self.running = False
        self.host: str | None = None
        self.port: int | None = None

    async def start(self, host: str | None = None, port: int | None = None) -> dict:
        if self.running:
            raise ProxyError(f"proxy already running on {self.host}:{self.port}")
        host = host or config.PROXY_HOST
        port = int(port or config.PROXY_PORT)

        opts = mp_options.Options(
            listen_host=host,
            listen_port=port,
            confdir=str(config.MITMPROXY_CONFDIR),
        )
        master = DumpMaster(opts, with_termlog=False, with_dumper=False)
        master.addons.add(self.addon)
        self._master = master
        self._task = asyncio.create_task(master.run(), name="phantom-proxy")

        # Give the master a moment to bind; if it dies immediately (port in
        # use / permission error) surface an actionable error (Constitution V).
        for _ in range(30):
            await asyncio.sleep(0.05)
            if self._task.done():
                break
        if self._task.done():
            exc = self._task.exception() if not self._task.cancelled() else None
            self._master = None
            self._task = None
            detail = f" ({exc})" if exc else ""
            raise ProxyError(
                f"proxy failed to start on {host}:{port}{detail} — "
                "check the port is free and try another port"
            )

        self.running = True
        self.host, self.port = host, port
        log.info("proxy listening on %s:%s", host, port)
        await broadcast("proxy_status", {"running": True, "host": host, "port": port})
        return {"status": "running", "host": host, "port": port}

    async def stop(self) -> dict:
        if not self.running or self._master is None:
            self.running = False
            return {"status": "stopped"}
        host, port = self.host, self.port
        try:
            self._master.shutdown()
        except Exception:
            log.exception("error while shutting down proxy master")
        if self._task:
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=5)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()
            except Exception:
                log.exception("proxy run task ended with error")
        self._master = None
        self._task = None
        self.running = False
        self.addon.drop_all()
        self.host = self.port = None
        log.info("proxy stopped (was %s:%s)", host, port)
        await broadcast("proxy_status", {"running": False, "host": None, "port": None})
        return {"status": "stopped"}

    def status(self) -> dict:
        return {
            "running": self.running,
            "host": self.host,
            "port": self.port,
            "requests_captured": self.addon.captured_count,
            "intercept_enabled": self.addon.intercept_enabled,
            "intercept_queue_size": len(self.addon.held),
        }

    def ensure_ca(self) -> None:
        """Generate the CA via mitmproxy's CertStore without running the proxy."""
        from mitmproxy.certs import CertStore

        config.ensure_data_dir()
        CertStore.from_store(str(config.MITMPROXY_CONFDIR), "mitmproxy", 2048)


_engine: ProxyEngine | None = None


def get_proxy_engine() -> ProxyEngine:
    global _engine
    if _engine is None:
        _engine = ProxyEngine()
    return _engine
