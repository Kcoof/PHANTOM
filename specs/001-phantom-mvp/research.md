# Research: PHANTOM MVP

**Phase 0 output of `/speckit.plan`** — resolves design decisions before implementation.
All "NEEDS CLARIFICATION" items from the source planning document were pre-resolved by the
project's decision log; this file records the choices with rationale and alternatives.

## D1: Proxy engine — in-process mitmproxy vs subprocess

- **Decision**: Run mitmproxy **in-process** (asyncio `ProxyServer`/`DumpMaster`-style setup)
  with a custom addon.
- **Rationale**: The addon must pause flows for intercept (asyncio `Event` keyed by flow id),
  write to SQLite, and broadcast WebSocket events — all naturally async and same-loop with
  FastAPI. No IPC serialization layer needed.
- **Alternatives considered**: mitmproxy as a subprocess with a dump file (simpler capture but
  intercept/pause and live events become awkward); writing a proxy from scratch (rejected —
  TLS interception is battle-tested in mitmproxy; Constitution II favors reliability).

## D2: Storage — aiosqlite single-file SQLite, WAL

- **Decision**: `aiosqlite` against one local `phantom.db` in WAL mode; migrations create all
  tables idempotently at startup (`CREATE TABLE IF NOT EXISTS`).
- **Rationale**: Zero-config, local-first (Constitution VII), adequate for tens of thousands of
  rows with the defined indexes; WAL allows concurrent reads during proxy writes.
- **Alternatives considered**: Postgres (overkill, violates local-first simplicity); raw files
  (no querying for filters/dashboard).

## D3: Real-time delivery — FastAPI WebSocket `/ws` event bus

- **Decision**: One WebSocket endpoint `/ws`; a connection registry broadcasts JSON events
  (`new_request`, `intercept_request`, `scan_progress`, `scan_finding`, `proxy_status`,
  `ai_status`); the frontend `useWebSocket` hook auto-reconnects and re-syncs state.
- **Rationale**: Constitution III forbids polling; a single event bus keeps modules decoupled
  (any engine can `await broadcast(event, data)`).
- **Alternatives considered**: SSE (fine for one-way but WebSocket also covers future two-way
  needs and is already required by the stack).

## D4: AI runtime — Ollama-compatible local endpoint, streaming

- **Decision**: `ai_engine` talks to an Ollama-compatible HTTP API (`/api/chat`) at a
  configurable local base URL; chat responses stream to the frontend via SSE passthrough;
  `/api/ai/status` probes availability; all AI features degrade gracefully.
- **Rationale**: Local-first default (Constitution VII), streaming requirement (Constitution
  III), Ollama is the de-facto standard local runtime with a stable API.
- **Alternatives considered**: Cloud LLM APIs (rejected as default — privacy/local-first;
  could be added later as an optional provider).

## D5: Intercept queue — asyncio.Event keyed by flow id

- **Decision**: When intercept is ON and a request matches the intercept filter, the addon
  stores the flow, creates an `asyncio.Event`, broadcasts `intercept_request`, and awaits the
  event. Forward (optionally mutated) or Drop sets the event and disposes the flow.
- **Rationale**: Direct implementation of the source plan's pattern; no polling, no threads.
- **Alternatives considered**: Thread-based blocking (mitmproxy also supports sync addons, but
  the rest of the backend is async).

## D6: Frontend architecture — Vite + React 18 + TS, Zustand, services layer

- **Decision**: Vite dev server (proxying `/api` and `/ws` to :8899), one Zustand store per
  module, one axios service file per backend router, shared component library hand-rolled to
  the design tokens (no heavyweight UI framework).
- **Rationale**: The premium dark theme demands full styling control (Constitution IV); the
  source plan's design tokens and components are fully specified — a framework would fight them.
- **Alternatives considered**: MUI/Chakra (theming overhead, generic look — violates IV).

## D7: Desktop shell — Electron wrapping backend process

- **Decision**: Electron main process spawns the Python backend (bundled venv/pyinstaller or
  system python in dev), loads the built frontend, and manages lifecycle (kill backend on
  quit). Dev mode runs uvicorn + Vite separately.
- **Rationale**: Largest ecosystem, automatic cross-platform (source plan decision).
- **Alternatives considered**: Tauri (lighter but Rust toolchain not in stack); none (plain
  web app loses desktop integration).

## D8: Development platform — Windows first, cross-platform scripts

- **Decision**: Development happens on Windows (Git Bash); scripts ship as both `.ps1` and
  `.sh`; Python virtual environment under `backend/.venv`.
- **Rationale**: Matches the actual dev machine; constitution requires cross-platform behavior.
- **Alternatives considered**: WSL-only development (adds friction for Electron/Windows).

## D9: Scanner architecture — async orchestrator + check registry

- **Decision**: `ScannerEngine` runs a scan session; each check is a class with
  `name/check_type/severity/cwe_id` and an async `check(request_data) -> list[Finding]`;
  active checks send via httpx with per-check timeouts and rate limiting; scope rules gate
  active checks (Constitution I).
- **Rationale**: Mirrors the source plan's BaseScanCheck interface; registry makes checks
  independently testable and selectable per scan.
- **Alternatives considered**: Monolithic scanner (untestable, violates VI).

## D10: Large/binary body handling

- **Decision**: Bodies stored up to a configurable cap (default 512 KiB) with a truncation
  marker `...[truncated N bytes]`; content-type aware text extraction (binary bodies stored
  as hex preview).
- **Rationale**: Keeps SQLite rows and the live table responsive (spec edge case).
- **Alternatives considered**: Unlimited storage (history degrades at high rates).
