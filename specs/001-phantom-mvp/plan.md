# Implementation Plan: PHANTOM MVP

**Branch**: `001-phantom-mvp` | **Date**: 2026-09-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-phantom-mvp/spec.md`

## Summary

Build PHANTOM, an AI-native web security testing platform for authorized pentesting and bug
bounty work. A local desktop application: an intercepting HTTP(S) proxy captures all traffic
into a local store and live-streams it to a premium dark-themed UI; a Repeater replays/edits
requests; a Scanner runs 10 passive/active vulnerability checks; an AI Copilot (local LLM
runtime by default) streams request analysis and payload suggestions; a Dashboard aggregates
traffic/severity/technology analytics; a Decoder chains encode/decode/hash transforms.

Technical approach: Python 3.11+ backend (FastAPI REST + WebSocket on localhost:8899, mitmproxy
as in-process proxy engine on localhost:8080, SQLite via aiosqlite, httpx for outbound sends),
React 18 + TypeScript frontend (Vite dev server / static bundle, Zustand state, Monaco editor,
Recharts), Electron shell packaging both. All data stays local.

## Technical Context

**Language/Version**: Python 3.11+ (backend); TypeScript 5.x, Node 18+ (frontend)

**Primary Dependencies**:
- Backend: `fastapi`, `uvicorn[standard]`, `mitmproxy>=10`, `aiosqlite`, `httpx`, `websockets`,
  `python-multipart`, `pydantic>=2`, `cryptography`, `beautifulsoup4`
- Frontend: `react`, `react-dom`, `react-router-dom`, `@monaco-editor/react`, `recharts`,
  `zustand`, `axios`, `lucide-react`, `react-hot-toast`, `react-markdown`, `highlight.js`
- Shell: `electron`, `electron-builder`

**Storage**: SQLite (single local file via aiosqlite; WAL mode). No external DB.

**Testing**: `pytest` + `httpx`/`fastapi.TestClient` for backend API integration tests; manual
end-to-end proxy verification (curl through the proxy) at each proxy-touching change; frontend
verified in browser during development.

**Target Platform**: Windows, macOS, Linux (desktop app via Electron; dev mode = uvicorn + Vite).

**Project Type**: Desktop application (web-service backend + SPA frontend in Electron shell).

**Performance Goals**: Live history update within 1s at 100 req/min sustained; passive scan of
1,000 entries within 2 minutes; UI views render < 1s; AI first token < 3s when runtime is up.

**Constraints**: Backend binds localhost only by default; no telemetry; all artifacts local;
dark theme mandated by constitution; premium UI bar (Monaco, split panes, micro-animations).

**Scale/Scope**: Single operator, single project database; tens of thousands of history rows;
hundreds of findings per scan session.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | How the plan complies |
|---|---|---|
| I. Authorized Testing Only | PASS | Active scan requires scope rules; out-of-scope targets refused; README + UI carry the restriction. |
| II. Proxy-First Reliability | PASS | Proxy engine is scheduled first after foundations; every proxy change gets an end-to-end curl test; US1 checkpoint blocks later stories. |
| III. Real-Time by Default | PASS | WebSocket `/ws` event stream for traffic/intercept/scan/AI events; AI chat streams via SSE. No polling anywhere in the UI. |
| IV. Premium Dark UI | PASS | Exact design tokens in `frontend/src/index.css`; Monaco in Repeater; resizable SplitPane; method/status color coding; Inter + JetBrains Mono. |
| V. Never Fail Silently | PASS | Structured logging; every fetch wrapped with toast-on-error; AI runtime unavailability surfaced as status, not failure. |
| VI. Incremental Delivery | PASS | tasks.md orders work by user story with checkpoints; commit per verified increment. |
| VII. Local-First by Default | PASS | SQLite on disk; AI defaults to local Ollama endpoint; zero cloud calls in core modules. |

Re-check after Phase 1: data model keeps everything in local SQLite; contracts expose only
localhost-bound HTTP/WS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-phantom-mvp/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
backend/                          # Python FastAPI backend
├── requirements.txt
├── main.py                       # FastAPI app entry, lifespan, router registration
├── config.py                     # defaults & env configuration
├── core/                         # engines
│   ├── proxy_engine.py           # mitmproxy lifecycle management
│   ├── proxy_addon.py            # traffic capture/intercept addon
│   ├── scanner_engine.py         # async scan orchestrator
│   ├── scanner_checks/           # xss, sqli, ssrf, idor, auth_bypass, cors,
│   │                             # headers, info_disclosure, open_redirect, csrf, jwt
│   ├── ai_engine.py              # local LLM runtime client + prompts (streaming)
│   └── decoder_engine.py         # encode/decode/hash transforms
├── api/                          # route modules (proxy, history, repeater, scanner,
│   │                             # ai, decoder, dashboard, settings, websocket)
├── db/                           # database.py (aiosqlite), models.py, migrations.py
└── utils/                        # cert_manager.py, helpers.py, logger.py

frontend/                         # React + TypeScript frontend
├── package.json / vite.config.ts / tsconfig.json / index.html
└── src/
    ├── main.tsx / App.tsx / index.css (design tokens)
    ├── components/
    │   ├── layout/               # Sidebar, TopBar, StatusBar, MainLayout
    │   ├── proxy/                # ProxyView, RequestTable, RequestDetail,
    │   │                         # InterceptPanel, FilterBar
    │   ├── repeater/             # RepeaterView, RequestEditor, ResponseViewer, Tabs
    │   ├── scanner/              # ScannerView, ScanConfig, FindingsList,
    │   │                         # FindingDetail, ScanProgress
    │   ├── dashboard/            # DashboardView, StatsCards, TrafficChart,
    │   │                         # VulnChart, TechStack
    │   ├── decoder/              # DecoderView, CodecChain, CodecPanel
    │   ├── copilot/              # CopilotView, ChatMessage, ChatInput, ContextPanel
    │   └── shared/               # Button, Badge, Modal, Tabs, Table, Tooltip,
│   │                             # Dropdown, SearchInput, CodeBlock, SplitPane,
│   │                             # LoadingSpinner
    ├── hooks/                    # useWebSocket, useApi, useProxyHistory, useTheme
    ├── stores/                   # zustand: proxy, scanner, repeater, copilot, settings
    ├── services/                 # axios API clients per module
    ├── types/                    # TypeScript types per module + common
    └── utils/                    # formatters, constants, colors

electron/                         # main.ts, preload.ts, electron-builder.yml
scripts/                          # dev.ps1/dev.sh, build.sh, setup-certs.py
```

**Structure Decision**: Web-application structure (`backend/` + `frontend/`) wrapped by an
`electron/` shell, exactly as above — matches the "web app + desktop wrapper" project type.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations — table intentionally empty.
