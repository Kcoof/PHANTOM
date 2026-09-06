"""PHANTOM backend integration tests — pytest + TestClient (plan.md T061).

Run: backend/.venv/Scripts/python -m pytest tests/ -v
"""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# isolated data dir per test run (Constitution VII: nothing touches user data)
_tmp = tempfile.mkdtemp(prefix="phantom-test-")
os.environ["PHANTOM_DATA_DIR"] = str(Path(_tmp))

import config

config.DATA_DIR = Path(_tmp)
config.DB_PATH = config.DATA_DIR / "phantom.db"
config.MITMPROXY_CONFDIR = config.DATA_DIR / "mitmproxy"
config.ensure_data_dir()

from fastapi.testclient import TestClient

import pytest

import main as app_module
importlib.reload(app_module)


@pytest.fixture(scope="module")
def client():
    # context-managed → lifespan runs init_db on the app's own event loop
    # (the shared aiosqlite connection must live on that loop, not a throwaway one)
    with TestClient(app_module.app) as c:
        yield c


# --- health & settings -------------------------------------------------------

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_settings_seeded(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    cats = r.json()["categories"]
    assert cats["proxy"]["proxy_port"] == "8080"
    assert cats["ai"]["ai_provider"] == "ollama"


def test_settings_update_and_reject_unknown(client):
    r = client.put("/api/settings", json={"values": {"font_size": "14"}})
    assert r.status_code == 200
    assert r.json()["categories"]["ui"]["font_size"] == "14"
    r = client.put("/api/settings", json={"values": {"nope": "1"}})
    assert r.status_code == 422


# --- decoder ------------------------------------------------------------------

def test_decoder_roundtrip(client):
    enc = client.post("/api/decoder/encode", json={"input": "Hello", "codec": "base64"}).json()
    assert enc["output"] == "SGVsbG8="
    dec = client.post("/api/decoder/decode", json={"input": enc["output"], "codec": "base64"}).json()
    assert dec["output"] == "Hello"


def test_decoder_hash_known_vector(client):
    r = client.post("/api/decoder/hash", json={"input": "Hello", "algorithm": "sha256"})
    assert r.json()["digest"].startswith("185f8db32271fe25f561a6fc938b2e26")


def test_decoder_jwt_and_bad_input(client):
    jwt = "eyJhbGciOiJub25lIn0.eyJzdWIiOiIxIn0."
    r = client.post("/api/decoder/decode", json={"input": jwt, "codec": "jwt"})
    assert r.status_code == 200
    assert r.json()["output"].count("none") >= 1
    r = client.post("/api/decoder/decode", json={"input": "zzz", "codec": "hex"})
    assert r.status_code == 422


def test_decoder_auto_detect(client):
    r = client.post("/api/decoder/auto-detect", json={"input": "SGVsbG8gd29ybGQ="})
    assert r.status_code == 200
    assert any(x["codec"] == "base64" for x in r.json()["results"])


# --- history + repeater -------------------------------------------------------

def _seed_history_entry() -> int:
    import sqlite3

    db = sqlite3.connect(config.DB_PATH)
    cur = db.execute(
        """INSERT INTO proxy_history (method, scheme, host, port, path, url,
             request_headers, request_body, status_code, response_headers, response_body)
           VALUES ('GET', 'https', 'example.test', 443, '/x', 'https://example.test/x',
             '{}', NULL, 200, '{}', 'ok')"""
    )
    db.commit()
    entry_id = cur.lastrowid
    db.close()
    return entry_id


def test_history_list_and_detail(client):
    entry_id = _seed_history_entry()
    r = client.get("/api/history", params={"search": "example.test"})
    assert any(e["id"] == entry_id for e in r.json()["items"])
    r = client.get(f"/api/history/{entry_id}")
    assert r.status_code == 200
    assert r.json()["url"] == "https://example.test/x"
    r = client.get("/api/history/999999")
    assert r.status_code == 404


def test_history_annotations_and_repeater_send(client):
    entry_id = _seed_history_entry()
    assert client.post(f"/api/history/{entry_id}/tag", json={"tag": "interesting"}).json()["tags"] == ["interesting"]
    assert client.post(f"/api/history/{entry_id}/note", json={"note": "check"}).status_code == 200
    assert client.post(f"/api/history/{entry_id}/highlight", json={"color": "red"}).status_code == 200
    r = client.post(f"/api/history/{entry_id}/send-to-repeater")
    assert r.status_code == 200
    tab_id = r.json()["repeater_tab_id"]
    tabs = client.get("/api/repeater/tabs").json()
    assert any(t["id"] == tab_id for t in tabs)
    assert client.delete(f"/api/repeater/tabs/{tab_id}").json()["deleted"] is True


def test_repeater_raw_parse_errors_cleanly(client):
    tab = client.post(
        "/api/repeater/tabs",
        json={"method": "GET", "url": "https://example.test/", "request_headers": {}},
    ).json()
    r = client.post(f"/api/repeater/tabs/{tab['id']}/send", json={"raw_request": "not a request"})
    assert r.status_code in (422, 502)  # parse failure or fetch failure — never a 500 crash
    client.delete(f"/api/repeater/tabs/{tab['id']}")


def test_clear_history_with_referencing_findings(client):
    """Clearing history must survive the findings FK (findings kept, unlinked)."""
    import sqlite3

    entry_id = _seed_history_entry()
    db = sqlite3.connect(config.DB_PATH)
    db.execute(
        "INSERT OR IGNORE INTO scans (id, target_url, scan_type) VALUES ('s-clear', 't', 'passive')"
    )
    db.execute(
        """INSERT INTO scanner_findings
           (scan_id, history_id, finding_type, severity, confidence, title, description, url)
           VALUES ('s-clear', ?, 'headers', 'low', 'firm', 't', 'd', 'u')""",
        (entry_id,),
    )
    db.commit()
    db.close()
    r = client.delete("/api/history")
    assert r.status_code == 200
    assert r.json()["deleted"] >= 1
    assert client.get("/api/history").json()["total"] == 0


# --- scanner -------------------------------------------------------------------

def test_scanner_registry_and_passive_scan(client):
    checks = client.get("/api/scanner/checks").json()
    types = {c["check_type"] for c in checks}
    assert {"xss", "sqli", "headers", "cors", "jwt"} <= types
    r = client.post("/api/scanner/scan", json={"scan_type": "passive"})
    assert r.status_code == 201
    scan_id = r.json()["scan_id"]
    # TestClient runs the app loop; give the scan task a beat
    import time

    time.sleep(1.0)
    scan = client.get(f"/api/scanner/scans/{scan_id}").json()
    assert scan["status"] in ("running", "completed", "paused")


def test_active_scan_requires_scope(client):
    entry_id = _seed_history_entry()
    r = client.post("/api/scanner/scan", json={"scan_type": "active", "history_ids": [entry_id]})
    assert r.status_code == 403
    assert "scope" in r.json()["detail"].lower()


def test_scope_rule_crud(client):
    r = client.post("/api/settings/scope", json={"rule_type": "include", "host_pattern": "*.example.test"})
    assert r.status_code == 201
    rule_id = r.json()["id"]
    rules = client.get("/api/settings/scope").json()
    assert any(x["id"] == rule_id for x in rules)
    assert client.delete(f"/api/settings/scope/{rule_id}").json()["deleted"] is True


# --- dashboard & ai -------------------------------------------------------------

def test_dashboard_stats_shape(client):
    r = client.get("/api/dashboard/stats")
    body = r.json()
    assert {"total_requests", "findings_by_severity", "top_hosts", "avg_response_time_ms"} <= set(body)


def test_ai_status_graceful_offline(client):
    r = client.get("/api/ai/status")
    assert r.status_code == 200
    # no runtime in CI: must report unavailable, not crash
    assert isinstance(r.json()["available"], bool)
    r = client.post("/api/ai/chat", json={"message": "hi"})
    assert r.status_code in (200, 503)


# --- spec 002: hunting upgrade ------------------------------------------------

def _seed_body(body: str, url: str, path: str) -> int:
    import sqlite3

    db = sqlite3.connect(config.DB_PATH)
    cur = db.execute(
        """INSERT INTO proxy_history (method, scheme, host, port, path, url,
             request_headers, status_code, response_headers, response_body)
           VALUES ('GET', 'https', ?, 443, ?, ?, '{}', 200, '{}', ?)""",
        (url.split("/")[2], path, url, body),
    )
    db.commit()
    entry_id = cur.lastrowid
    db.close()
    return entry_id


def test_rescan_adds_no_duplicates(client):
    _seed_body("<html>plain</html>", "https://dedupe.test/a", "/a")
    client.post("/api/scanner/scan", json={"scan_type": "passive", "target_url": "dedupe.test"})
    time.sleep(1.5)
    before = len(client.get("/api/scanner/findings").json())
    assert before > 0, "first scan should produce findings"
    client.post("/api/scanner/scan", json={"scan_type": "passive", "target_url": "dedupe.test"})
    time.sleep(1.5)
    after = len(client.get("/api/scanner/findings").json())
    assert after == before, "rescan must not add duplicate findings"


def test_secret_detection_patterns():
    from core.scanner_checks.secrets import detect_secrets

    assert any(h["label"] == "AWS access key ID" for h in detect_secrets('aws: "AKIAIOSFODNN7EXAMPLE"'))
    assert not any(
        h["label"] == "AWS access key ID"
        for h in detect_secrets('your_api_key = "AKIAIOSFODNN7EXAMPLE"')  # placeholder-suppressed
    )
    assert any(
        h["label"] == "Private key block"
        for h in detect_secrets("-----BEGIN RSA PRIVATE KEY-----\nMIIE\n-----END RSA PRIVATE KEY-----")
    )
    generic = detect_secrets('api_key = "supersecretvalue12345"')
    assert any(h["confidence"] == "tentative" for h in generic)
    assert detect_secrets("nothing to see here") == []


def test_secrets_finding_via_scan(client):
    _seed_body('{"cfg": "AKIAIOSFODNN7EXAMPLE"}', "https://leak.test/k", "/k")
    client.post("/api/scanner/scan", json={"scan_type": "passive", "target_url": "leak.test"})
    time.sleep(1.5)
    leak = [f for f in client.get("/api/scanner/findings").json() if f["finding_type"] == "secrets"]
    assert leak and leak[0]["severity"] == "critical" and leak[0]["cwe_id"] == "CWE-798"


def test_report_markdown_and_html(client):
    r = client.get("/api/scanner/report?format=markdown")
    assert r.status_code == 200
    assert "PHANTOM Security Report" in r.text
    assert "AKIAIOSFODNN7EXAMPLE" in r.text  # secrets evidence included
    r2 = client.get("/api/scanner/report?format=html")
    assert r2.status_code == 200 and "<!doctype html" in r2.text.lower()
    assert client.get("/api/scanner/report?format=docx").status_code == 422


def test_throttle_spacing():
    import asyncio

    from core.scanner_checks.base import _respect_throttle, configure_throttle

    configure_throttle(1, 0.25)

    async def run():
        t0 = time.perf_counter()
        for _ in range(5):
            await _respect_throttle()
        elapsed = time.perf_counter() - t0
        assert elapsed >= 4 * 0.2, f"5 spaced probes took {elapsed:.2f}s"

    asyncio.run(run())


# --- spec 003: tier-2 power tools ----------------------------------------------

def test_match_replace_rules_crud_and_apply(client):
    r = client.post(
        "/api/match-replace",
        json={"enabled": True, "location": "request", "match_type": "literal",
              "match_value": "X-Old-Header", "replace_value": "X-New-Header"},
    )
    assert r.status_code == 201
    rule_id = r.json()["id"]
    rules = client.get("/api/match-replace").json()
    assert any(x["id"] == rule_id for x in rules)
    # regex validation
    bad = client.post("/api/match-replace", json={"location": "response", "match_type": "regex", "match_value": "("})
    assert bad.status_code == 422
    # rewrite engine applies literal rules
    from core.rewrite_engine import _apply_text

    text, _ = _apply_text("X-Old-Header: yes", [{"id": 1, "location": "request", "match_type": "literal",
                                                 "match_value": "X-Old-Header", "replace_value": "X-New"}], "request")
    assert text == "X-New: yes"
    text2, _ = _apply_text("v1/api", [{"id": 2, "location": "request", "match_type": "regex",
                                       "match_value": r"^v1/", "replace_value": "v2/"}], "request")
    assert text2 == "v2/api"
    assert client.delete(f"/api/match-replace/{rule_id}").json()["deleted"] is True


def test_global_search_literal_and_regex(client):
    _seed_body("the magic token ABC-123 lives here", "https://search.test/a", "/a")
    hits = client.get("/api/search", params={"q": "ABC-123"}).json()
    assert any(h["id"] and "ABC-123" in h["snippet"] for h in hits)
    rx = client.get("/api/search", params={"q": r"ABC-\d+", "regex": "true"}).json()
    assert any("ABC-123" in h["snippet"] for h in rx)
    assert client.get("/api/search", params={"q": "(", "regex": "true"}).status_code == 422


def test_intruder_end_to_end(client):
    # attack our own backend (localhost, no position left unmarked)
    raw = "GET /api/health?probe=§orig§ HTTP/1.1\nHost: 127.0.0.1:8899"
    r = client.post(
        "/api/intruder/attacks",
        json={"raw_request": raw, "payloads": ["alpha", "beta"], "grep_patterns": ["ok"], "name": "t"},
    )
    assert r.status_code == 201
    attack_id = r.json()["attack_id"]
    for _ in range(40):
        time.sleep(0.25)
        row = client.get(f"/api/intruder/attacks/{attack_id}").json()
        if row["status"] in ("completed", "failed", "stopped"):
            break
    assert row["status"] == "completed"
    results = client.get(f"/api/intruder/attacks/{attack_id}/results").json()
    assert len(results) == 3  # baseline + 2 payloads
    assert results[0]["is_baseline"] in (0, 1, True)
    statuses = {r["status"] for r in results}
    assert 200 in statuses  # our health endpoint answered
    # no positions -> 422
    bad = client.post("/api/intruder/attacks", json={"raw_request": "GET / HTTP/1.1", "payloads": ["x"]})
    assert bad.status_code == 422
    # wordlists available
    wl = client.get("/api/intruder/wordlists").json()
    assert "sqli-basic" in wl and wl["sqli-basic"] >= 5
