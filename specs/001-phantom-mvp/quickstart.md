# Quickstart: PHANTOM MVP Validation Guide

**Phase 1 output of `/speckit.plan`.** Runnable scenarios that prove the feature works
end-to-end. Each user story checkpoint maps to a section below. Prerequisites: Python 3.11+,
Node 18+, a Git shell.

## Setup (once)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash (macOS/Linux: .venv/bin/activate)
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

## Run (dev mode)

Terminal 1 — backend:

```bash
cd backend && source .venv/Scripts/activate
uvicorn main:app --host 127.0.0.1 --port 8899 --reload
```

Terminal 2 — frontend:

```bash
cd frontend && npm run dev     # Vite on :5173, proxies /api and /ws to :8899
```

Open http://localhost:5173. Expected: PHANTOM dark-themed shell with sidebar navigation
(Dashboard, Proxy, Repeater, Scanner, Decoder, AI Copilot, Settings) and a status bar.

## Scenario A — Proxy capture (US1 checkpoint)

1. `POST http://127.0.0.1:8899/api/proxy/start` (or Proxy view → Start).
2. Send traffic through the proxy:
   `curl -x http://127.0.0.1:8080 http://example.com -s -o /dev/null -w "%{http_code}\n"`
3. **Pass**: within 1 second the Proxy view history table shows the request; selecting it
   shows full request and response panes. `GET /api/history` returns the entry.
4. HTTPS: `curl -x http://127.0.0.1:8080 --cacert <downloaded CA> https://example.com` —
   the CA downloads from the Proxy view (or `GET /api/proxy/ca-cert`); entry appears decrypted.
5. Filters: set method/status/search filters; table narrows correctly.

## Scenario B — Intercept (US1 checkpoint)

1. Enable Intercept in the Proxy view.
2. `curl -x http://127.0.0.1:8080 http://example.com &` — the request stalls.
3. **Pass**: the Intercept panel shows the held request; Forward completes the curl with a
   response; Drop makes curl fail fast; the history row is flagged as intercepted.

## Scenario C — Repeater (US2 checkpoint)

1. In Proxy history, context-menu a request → **Send to Repeater**.
2. Edit a header in the Monaco editor, press **Ctrl+Enter**.
3. **Pass**: response (status, headers, body, time) appears right of the editor; the tab keeps
   send history; closing/reopening the app restores tabs.

## Scenario D — Scanner (US3 checkpoint)

1. Settings → Scope: add include rule `*.example.com` (or the lab host).
2. Scanner view → Passive scan over captured history → **Pass**: findings (if any) stream in
   with severity/evidence; e.g. security-header findings on most live sites.
3. Active scan against an authorized lab target (e.g. local DVWA/Juice Shop) with selected
   checks → findings appear with payload + evidence; pause/stop work; marking a finding
   false-positive updates counts.

## Scenario E — AI Copilot (US4 checkpoint)

1. With a local Ollama running (`ollama serve`, model pulled): Copilot shows available.
2. Proxy history → context-menu → **AI Analyze**; **Pass**: streamed analysis text appears
   progressively; follow-up question keeps conversation context.
3. Stop Ollama → **Pass**: Copilot shows an unavailable status with guidance; all other
   modules unaffected (`GET /api/ai/status` → `{available: false}`).

## Scenario F — Dashboard (US5 checkpoint)

With traffic and findings present: Dashboard shows stat cards, traffic chart (minute/hour/day
toggle), severity donut, and detected technologies matching the browsed hosts.

## Scenario G — Decoder (US6 checkpoint)

1. Input `SGVsbG8=` → Decode Base64 → `Hello`.
2. Chain: encode result as URL → decode back.
3. Paste a JWT (`eyJ…`) → auto-detect identifies and decodes header/payload.
4. Hash `Hello` (SHA-256) → correct digest `185f8db32271fe25f561a6fc938b2e26…`.

## Scenario H — Real-time & resilience (cross-cutting)

1. With the UI open, generate proxy traffic → rows appear without refresh (no polling).
2. Kill and restart the backend → UI shows disconnected then reconnects and restores state.
3. Kill the backend port conflict scenario → start proxy on occupied port returns a clear
   error toast; app remains usable.

## Scenario I — Desktop shell (polish checkpoint)

`npm run electron` (after `npm run build`) → app window opens with backend spawned; quitting
the app terminates the backend process.
