"""TLS CA management — mitmproxy CA lives in the local data dir (Constitution VII)."""
from __future__ import annotations

from pathlib import Path

import config
from utils.logger import get_logger

log = get_logger(__name__)


def confdir() -> Path:
    config.ensure_data_dir()
    return config.MITMPROXY_CONFDIR


def ca_cert_path() -> Path:
    return confdir() / "mitmproxy-ca-cert.pem"


def get_ca_pem() -> str:
    """Return the CA certificate PEM text, generating the CA on first use.

    mitmproxy creates its CA lazily when the proxy first starts; if it does not
    exist yet we start a throwaway in-process master once to trigger generation.
    """
    path = ca_cert_path()
    if not path.exists():
        log.info("mitmproxy CA not found — generating via engine bootstrap")
        from core.proxy_engine import get_proxy_engine  # deferred import

        engine = get_proxy_engine()
        engine.ensure_ca()
    if not path.exists():
        raise RuntimeError("failed to generate mitmproxy CA certificate")
    return path.read_text(encoding="utf-8")
