# 🛠️ PHANTOM

**PHANTOM** is an open-core, AI-native web application security testing platform — a local-first alternative to Burp Suite built with Python (FastAPI + mitmproxy) and React (TypeScript + Electron).

> ⚠️ **Authorized testing only.** PHANTOM is intended for use against applications you own or have explicit written permission to test (your own lab, DVWA, OWASP Juice Shop, or an engagement with a signed scope). Active scanning is scope-gated by design: it refuses to run until you define an include rule for your authorized targets. Always respect the rules of engagement of any program you test.

## Modules

| Module | What it does |
|---|---|
| **Proxy** | Intercepting HTTP(S) proxy (mitmproxy) with live traffic history, filters, annotations, and full request/response inspection |
| **Repeater** | Replay and edit captured requests in a Monaco editor with response views (raw / headers / body / hex) and per-tab history |
| **Scanner** | Passive + active vulnerability checks with live-streamed findings: reflected XSS, SQLi, SSRF, open redirect, IDOR, CORS, security headers, cookies, CSRF, JWT issues |
| **AI Copilot** | Local LLM assistant (Ollama-compatible) that streams request analysis, answers security questions, and generates contextual payloads |
| **Dashboard** | Traffic-over-time charts, findings by severity, top hosts, detected technologies |
| **Decoder** | Chainable encode/decode (Base64, URL, HTML, hex, unicode, gzip, JWT) + hashes + auto-detect |

All captured data stays on your machine (local SQLite; AI defaults to a local model runtime). No telemetry.

## Quick start (development)

Prerequisites: Python 3.11+, Node.js 18+.

```bash
# 1. Backend
cd backend
python -m venv .venv
source .venv/Scripts/activate    # Windows Git Bash  (macOS/Linux: .venv/bin/activate)
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8899 --reload

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

Or use the helpers: `scripts/dev.ps1` (Windows) / `scripts/dev.sh` (macOS/Linux).

## Using the proxy

1. In the app, open **Proxy** → press **Start** (listens on `127.0.0.1:8080`).
2. Configure your browser/client to use `http://127.0.0.1:8080` as proxy.
3. For HTTPS, trust the CA: download it from the Proxy view (or `http://127.0.0.1:8899/api/proxy/ca-cert`) and import it into your browser/OS trust store.
4. Browse — traffic appears live in the history table.

CLI smoke test:

```bash
curl -x http://127.0.0.1:8080 http://example.com
# HTTPS with the PHANTOM CA:
curl -x http://127.0.0.1:8080 --cacert <(curl -s http://127.0.0.1:8899/api/proxy/ca-cert) https://example.com
# On Windows curl (schannel) add: --ssl-no-revoke
```

## Scanning safely

- **Passive scans** analyze already-captured traffic — no requests are sent.
- **Active scans** send modified requests and are **blocked until you add an include scope rule** in **Settings → Scope** (e.g. `*.your-lab.example`). Point them only at systems you're authorized to test.

## AI Copilot (optional)

PHANTOM talks to any Ollama-compatible runtime:

```bash
ollama serve
ollama pull mistral   # or another model; adjust in Settings → AI
```

The Copilot degrades gracefully when the runtime is down — everything else keeps working.

## Desktop app (Electron)

```bash
cd frontend
npm run electron:dev    # launches the shell in dev mode (backend + UI)
npm run electron:build  # packaged build via electron-builder
```

## Tests

```bash
cd backend && ./.venv/Scripts/python -m pytest tests/ -v   # (macOS/Linux: .venv/bin/python)
```

## Spec-driven development

This repo is built with [GitHub Spec Kit](https://github.com/github/spec-kit). The constitution, feature spec, technical plan, API contracts, data model, and the task checklist live in [`specs/001-phantom-mvp/`](specs/001-phantom-mvp/) with workflow commands in [`.agents/commands/`](.agents/commands/).

## Architecture

```
Electron shell ── React/TS UI (Vite; Zustand, Monaco, Recharts)
      │                │  REST /api/*  +  WebSocket /ws (live events)
      │                ▼
      └────▶ FastAPI backend (127.0.0.1:8899)
                ├─ Proxy engine: in-process mitmproxy (127.0.0.1:8080)
                ├─ Scanner engine: 11 passive/active checks
                ├─ AI engine: Ollama-compatible, SSE streaming
                └─ SQLite (aiosqlite, WAL) — all data local
```

## License

MIT — see [LICENSE](LICENSE).
