"""PHANTOM backend configuration — defaults with environment overrides."""
import os
from pathlib import Path

BACKEND_HOST = os.environ.get("PHANTOM_BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.environ.get("PHANTOM_BACKEND_PORT", "8899"))

PROXY_HOST = os.environ.get("PHANTOM_PROXY_HOST", "127.0.0.1")
PROXY_PORT = int(os.environ.get("PHANTOM_PROXY_PORT", "8080"))

# Data directory: database, mitmproxy CA material — kept local (Constitution VII).
DATA_DIR = Path(os.environ.get("PHANTOM_DATA_DIR", Path.home() / ".phantom"))
DB_PATH = DATA_DIR / "phantom.db"
MITMPROXY_CONFDIR = DATA_DIR / "mitmproxy"

# Response/request body persistence cap (spec edge case: large bodies).
MAX_BODY_BYTES = int(os.environ.get("PHANTOM_MAX_BODY_BYTES", str(512 * 1024)))
TRUNCATION_MARKER = "...[truncated {n} bytes]"

# Local AI runtime (Ollama-compatible). Local-first default (Constitution VII).
AI_BASE_URL = os.environ.get("PHANTOM_AI_BASE_URL", "http://localhost:11434")
AI_MODEL = os.environ.get("PHANTOM_AI_MODEL", "mistral")
AI_TIMEOUT_S = float(os.environ.get("PHANTOM_AI_TIMEOUT_S", "120"))

SCANNER_THREADS = int(os.environ.get("PHANTOM_SCANNER_THREADS", "10"))
SCANNER_TIMEOUT_S = float(os.environ.get("PHANTOM_SCANNER_TIMEOUT_S", "30"))

CORS_ORIGINS = os.environ.get("PHANTOM_CORS_ORIGINS", "*").split(",")


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MITMPROXY_CONFDIR.mkdir(parents=True, exist_ok=True)
