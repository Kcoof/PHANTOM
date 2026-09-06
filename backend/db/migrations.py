"""Schema creation & seed data — full DDL per specs/001-phantom-mvp/data-model.md."""
from __future__ import annotations

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS proxy_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    method TEXT NOT NULL,
    scheme TEXT NOT NULL DEFAULT 'https',
    host TEXT NOT NULL,
    port INTEGER NOT NULL DEFAULT 443,
    path TEXT NOT NULL,
    query_string TEXT,
    url TEXT NOT NULL,
    request_headers TEXT NOT NULL,
    request_body TEXT,
    request_content_type TEXT,
    status_code INTEGER,
    response_headers TEXT,
    response_body TEXT,
    response_content_type TEXT,
    response_time_ms INTEGER,
    size_bytes INTEGER,
    is_intercepted BOOLEAN DEFAULT 0,
    is_in_scope BOOLEAN DEFAULT 1,
    tags TEXT,
    notes TEXT,
    ai_analysis TEXT,
    highlight_color TEXT
);

CREATE TABLE IF NOT EXISTS scanner_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id TEXT NOT NULL,
    history_id INTEGER,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    finding_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    confidence TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    url TEXT NOT NULL,
    parameter TEXT,
    payload TEXT,
    evidence TEXT,
    request_dump TEXT,
    response_dump TEXT,
    remediation TEXT,
    cwe_id TEXT,
    cvss_score REAL,
    is_false_positive BOOLEAN DEFAULT 0,
    status TEXT DEFAULT 'open',
    FOREIGN KEY (history_id) REFERENCES proxy_history(id)
);

CREATE TABLE IF NOT EXISTS scans (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    target_url TEXT NOT NULL,
    scan_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    total_requests INTEGER DEFAULT 0,
    findings_count INTEGER DEFAULT 0,
    config TEXT,
    started_at TEXT,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS repeater_tabs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    method TEXT NOT NULL,
    url TEXT NOT NULL,
    request_headers TEXT NOT NULL,
    request_body TEXT,
    last_response_status INTEGER,
    last_response_headers TEXT,
    last_response_body TEXT,
    last_response_time_ms INTEGER,
    history TEXT
);

CREATE TABLE IF NOT EXISTS ai_conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now')),
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    context_type TEXT,
    context_id INTEGER,
    model TEXT
);

CREATE TABLE IF NOT EXISTS scope_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_type TEXT NOT NULL,
    protocol TEXT,
    host_pattern TEXT NOT NULL,
    port TEXT,
    path_pattern TEXT DEFAULT '.*',
    is_active BOOLEAN DEFAULT 1
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    db_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    category TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_history_host ON proxy_history(host);
CREATE INDEX IF NOT EXISTS idx_history_method ON proxy_history(method);
CREATE INDEX IF NOT EXISTS idx_history_status ON proxy_history(status_code);
CREATE INDEX IF NOT EXISTS idx_history_timestamp ON proxy_history(timestamp);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON scanner_findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_scan ON scanner_findings(scan_id);
CREATE INDEX IF NOT EXISTS idx_findings_type ON scanner_findings(finding_type);
"""

SEED_SETTINGS = [
    ("proxy_port", "8080", "proxy"),
    ("proxy_host", "127.0.0.1", "proxy"),
    ("intercept_enabled", "false", "proxy"),
    ("intercept_filter", "", "proxy"),
    ("scanner_threads", "10", "scanner"),
    ("scanner_timeout", "30", "scanner"),
    ("scanner_delay_ms", "250", "scanner"),
    ("scanner_concurrency", "4", "scanner"),
    ("ai_provider", "ollama", "ai"),
    ("ai_model", "mistral", "ai"),
    ("ai_base_url", "http://localhost:11434", "ai"),
    ("theme", "dark", "ui"),
    ("font_size", "13", "ui"),
]


async def apply(db: aiosqlite.Connection) -> None:
    await db.executescript(SCHEMA)
    await db.executemany(
        "INSERT OR IGNORE INTO settings (key, value, category) VALUES (?, ?, ?)",
        SEED_SETTINGS,
    )
    await db.commit()
