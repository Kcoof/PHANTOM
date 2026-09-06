---
description: "Task list for PHANTOM MVP implementation"
---

# Tasks: PHANTOM MVP

**Input**: Design documents from `/specs/001-phantom-mvp/`

**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/api.md, quickstart.md

**Tests**: Backend API integration tests are included in the Polish phase (T061); per-story
verification follows the quickstart.md scenarios at each checkpoint (Constitution VI).

**Organization**: Tasks grouped by user story; US1 (Proxy) is the MVP. Sequential execution in
priority order; [P] tasks are parallelizable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US6)
- File paths are relative to repository root

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per plan.md (backend/, frontend/, electron/, scripts/ dirs)
- [ ] T002 Initialize backend Python project: backend/requirements.txt (per plan.md), venv at backend/.venv, install deps
- [ ] T003 Initialize frontend with Vite react-ts template in frontend/ and install runtime deps (react-router-dom, @monaco-editor/react, recharts, zustand, axios, lucide-react, react-hot-toast, react-markdown, highlight.js)
- [ ] T004 [P] Configure frontend/vite.config.ts dev proxy (/api, /ws → 127.0.0.1:8899) and tsconfig paths

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core backend infrastructure every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Implement backend/config.py — defaults + env overrides (ports, paths, caps)
- [ ] T006 [P] Implement backend/utils/logger.py — structured logging setup
- [ ] T007 [P] Implement backend/db/database.py — aiosqlite connection, WAL mode, init_db()
- [ ] T008 Implement backend/db/migrations.py — full schema per data-model.md (8 tables, indexes, seeded settings)
- [ ] T009 [P] Implement backend/db/models.py — Pydantic models for all entities + enums
- [ ] T010 [P] Implement backend/api/websocket.py — /ws endpoint, connection registry, broadcast()
- [ ] T011 Implement backend/main.py — FastAPI app, CORS, lifespan (init DB, stop proxy), router registration
- [ ] T012 Verify foundation: uvicorn boots on :8899, GET /api/settings returns seeded defaults

**Checkpoint**: Foundation ready — user story implementation can begin

---

## Phase 3: User Story 1 - Intercept & Inspect Traffic (Priority: P1) 🎯 MVP

**Goal**: Working intercepting proxy with live, filterable, annotatable history UI — the heart of PHANTOM

**Independent Test**: Quickstart Scenarios A + B (curl through proxy → live history; intercept forward/drop)

### Implementation for User Story 1

- [ ] T013 [P] [US1] Implement backend/utils/cert_manager.py — mitmproxy CA location/ensure + PEM export
- [ ] T014 [US1] Implement backend/core/proxy_addon.py — capture every flow, scope check, size-capped body extraction, SQLite persistence, new_request broadcast, intercept queue via asyncio.Event + intercept_request broadcast
- [ ] T015 [US1] Implement backend/core/proxy_engine.py — in-process mitmproxy start/stop, status, intercept toggle/queue/forward/drop, per-flow state
- [ ] T016 [US1] Implement backend/api/proxy_routes.py — start/stop/status, intercept toggle/queue/forward/drop, ca-cert download
- [ ] T017 [US1] Implement backend/api/history_routes.py — filtered paginated list, detail, delete (one/all), tag/note/highlight, send-to-repeater/scanner/copilot
- [ ] T018 [P] [US1] Build frontend/src/index.css — exact design tokens (plan palette), Inter + JetBrains Mono, scrollbar styling, animations
- [ ] T019 [P] [US1] Build shared components in frontend/src/components/shared/ — Button, Badge, Modal, Tabs, Table, Tooltip, Dropdown, SearchInput, CodeBlock, SplitPane, LoadingSpinner
- [ ] T020 [P] [US1] Build layout in frontend/src/components/layout/ — Sidebar, TopBar, StatusBar, MainLayout; App.tsx routes for all views; frontend/src/services/api.ts; frontend/src/hooks/useWebSocket.ts (auto-reconnect + resync)
- [ ] T021 [US1] Implement frontend/src/stores/proxyStore.ts + types/proxy.ts + services/proxyService.ts — requests, selection, filters, intercept state, WS event wiring
- [ ] T022 [US1] Build FilterBar.tsx + RequestTable.tsx — live color-coded table (method/status colors), sortable columns, new-row animation
- [ ] T023 [US1] Build RequestDetail.tsx — resizable SplitPane, raw/headers/body tabs both sides
- [ ] T024 [US1] Build InterceptPanel.tsx — held request list, edit-before-forward, forward/drop with intercept_resolved feedback
- [ ] T025 [US1] Compose ProxyView.tsx — toolbar (start/stop, intercept toggle Ctrl+Shift+I), context menu (Send to Repeater/Scanner/AI), tag/note/highlight UI
- [ ] T026 [US1] Verify quickstart Scenarios A + B end-to-end (real curl through proxy)

**Checkpoint**: MVP — proxy capture + intercept + history fully working

---

## Phase 4: User Story 2 - Replay & Modify Requests (Priority: P2)

**Goal**: Repeater with Monaco editor, tab management, response views, send history

**Independent Test**: Quickstart Scenario C (history → Repeater → edit → Ctrl+Enter → response)

### Implementation for User Story 2

- [ ] T027 [P] [US2] Implement frontend/src/types/repeater.ts + services/repeaterService.ts + stores/repeaterStore.ts
- [ ] T028 [US2] Implement backend/api/repeater_routes.py — tabs CRUD, send endpoint parsing raw request (httpx), response persistence, send history
- [ ] T029 [P] [US2] Build RequestEditor.tsx — Monaco raw HTTP editor with syntax highlighting
- [ ] T030 [P] [US2] Build ResponseViewer.tsx — raw/pretty(headers/body/JSON)/hex views + timing
- [ ] T031 [US2] Build RepeaterTabs.tsx + RepeaterView.tsx — tab CRUD, Ctrl+Enter send, loading/error states
- [ ] T032 [US2] Verify quickstart Scenario C end-to-end

**Checkpoint**: Stories 1+2 both independently functional

---

## Phase 5: User Story 3 - Scan for Vulnerabilities (Priority: P3)

**Goal**: Scanner with 10 checks (6 passive, 4+ active), live findings, lifecycle control

**Independent Test**: Quickstart Scenario D (passive scan over history; active scan vs authorized lab target)

### Implementation for User Story 3

- [ ] T033 [P] [US3] Implement backend/core/scanner_engine.py — BaseScanCheck interface, check registry, async orchestrator (pause/resume/stop), findings persistence, scan_progress/scan_finding broadcasts
- [ ] T034 [P] [US3] Implement passive checks in backend/core/scanner_checks/ — cors.py, headers.py, info_disclosure.py, csrf.py, cookies (in headers.py or separate), jwt.py
- [ ] T035 [P] [US3] Implement active checks in backend/core/scanner_checks/ — xss.py, sqli.py, ssrf.py, open_redirect.py, idor.py/auth_bypass.py — httpx senders with timeouts, scope enforcement (403 refusal)
- [ ] T036 [US3] Implement backend/api/scanner_routes.py — scan/scans/findings/status/checks endpoints per contracts/api.md
- [ ] T037 [P] [US3] Implement frontend/src/types/scanner.ts + services/scannerService.ts + stores/scannerStore.ts (WS wiring for scan events)
- [ ] T038 [P] [US3] Build ScanConfig.tsx — target/check selection, scan type, scope reminder
- [ ] T039 [P] [US3] Build FindingsList.tsx + FindingDetail.tsx — severity badges, evidence, dumps, status changes
- [ ] T040 [US3] Build ScanProgress.tsx + ScannerView.tsx — live progress bar, pause/resume/stop controls
- [ ] T041 [US3] Verify quickstart Scenario D end-to-end

**Checkpoint**: Stories 1–3 independently functional

---

## Phase 6: User Story 4 - AI Copilot (Priority: P4)

**Goal**: Streaming AI chat with request/finding context, payload suggestions, graceful unavailability

**Independent Test**: Quickstart Scenario E (streamed analysis with runtime up; clean status when down)

### Implementation for User Story 4

- [ ] T042 [P] [US4] Implement backend/core/ai_engine.py — Ollama-compatible client, status probe, streaming chat, PHANTOM system prompt, payload-suggestion prompts
- [ ] T043 [US4] Implement backend/api/ai_routes.py — SSE streaming endpoints (chat, analyze-request, suggest-payloads), conversations persistence, /api/ai/status
- [ ] T044 [P] [US4] Implement frontend/src/types/ai.ts + services/aiService.ts (SSE consumption) + stores/copilotStore.ts
- [ ] T045 [P] [US4] Build ChatMessage.tsx (markdown + code blocks) + ChatInput.tsx (quick actions: Analyze / Payloads / Report)
- [ ] T046 [P] [US4] Build ContextPanel.tsx — current request/finding context + suggested actions + detected tech
- [ ] T047 [US4] Compose CopilotView.tsx — availability banner, conversation restore, wire Proxy view "AI Analyze" action
- [ ] T048 [US4] Verify quickstart Scenario E end-to-end

**Checkpoint**: Stories 1–4 independently functional

---

## Phase 7: User Story 5 - Dashboard Analytics (Priority: P5)

**Goal**: At-a-glance traffic, severity, host, and technology analytics

**Independent Test**: Quickstart Scenario F

### Implementation for User Story 5

- [ ] T049 [US5] Implement backend/api/dashboard_routes.py — stats/traffic(interval)/technologies/top-findings aggregation queries
- [ ] T050 [P] [US5] Build StatsCards.tsx — totals + severity counts + avg response time
- [ ] T051 [P] [US5] Build TrafficChart.tsx + VulnChart.tsx — Recharts line + severity donut
- [ ] T052 [P] [US5] Build TechStack.tsx — detected technologies with hosts
- [ ] T053 [US5] Compose DashboardView.tsx + services/dashboardService.ts; verify quickstart Scenario F

**Checkpoint**: Stories 1–5 independently functional

---

## Phase 8: User Story 6 - Decoder (Priority: P6)

**Goal**: Chainable codec panels with auto-detect and hashing

**Independent Test**: Quickstart Scenario G

### Implementation for User Story 6

- [ ] T054 [P] [US6] Implement backend/core/decoder_engine.py — base64/url/html/hex/unicode/gzip/jwt codecs, md5/sha1/sha256/sha512, auto-detect
- [ ] T055 [P] [US6] Implement backend/api/decoder_routes.py — encode/decode/auto-detect/hash with 422 on bad input
- [ ] T056 [P] [US6] Build CodecPanel.tsx + services/decoderService.ts
- [ ] T057 [US6] Build CodecChain.tsx + DecoderView.tsx — chain steps, copy buttons; verify quickstart Scenario G

**Checkpoint**: All six stories independently functional

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Settings/scope, desktop shell, robustness, tests, docs

- [ ] T058 [P] Implement backend/api/settings_routes.py (settings + scope CRUD) + frontend Settings view (Proxy/Scanner/AI/UI sections + scope rules management, per FR-016/FR-017)
- [ ] T059 [P] Implement electron/main.ts + preload.ts + electron-builder.yml — spawn backend, load built frontend, lifecycle cleanup
- [ ] T060 Harden UX: toast notifications on all API errors, full keyboard shortcuts (Ctrl+Shift+I, Ctrl+R, Ctrl+Enter), loading skeletons, view transitions, responsive checks
- [ ] T061 [P] Backend API integration tests in backend/tests/ (pytest + TestClient): settings, history, decoder, repeater, scanner registry
- [ ] T062 [P] Complete README.md — setup, quickstart, module guide, authorized-testing statement; scripts/dev.ps1 + scripts/dev.sh
- [ ] T063 Run full quickstart.md validation (Scenarios A–I) and fix all findings

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **User Stories (Phases 3–8)**: Depend on Phase 2; executed sequentially in priority order
  (US1 → US2 → US3 → US4 → US5 → US6); US2+ consume US1's send-to actions but remain
  independently testable via direct API use
- **Polish (Phase 9)**: Depends on the user stories it hardens; T058/T059 can start after US1

### User Story Dependencies

- **US1 (P1)**: Only needs foundations — the MVP
- **US2 (P2)**: Uses history entries as input; independently testable against its own API
- **US3 (P3)**: Uses history (passive) and httpx sends (active); independent via API
- **US4 (P4)**: Uses history/findings as context; independent via its own endpoints
- **US5 (P5)**: Reads aggregates of history/findings; independent once data exists (can seed)
- **US6 (P6)**: Fully independent of all other stories

### Within Each User Story

- Engines/routes before UI where both exist
- Types/stores before view components
- Composition last, then quickstart verification
- Commit after each task or logical group; tree stays green at checkpoints

### Parallel Opportunities

- Phase 2: T006/T007/T009/T010 parallel; Phase 1: T003/T004 parallel
- US1: T018/T019/T020 (all frontend files) parallel with T013 (backend cert manager)
- US2: T027/T029/T030 parallel; US3: T034/T035 parallel; US5: T050/T051/T052 parallel; Phase 9: T058/T059/T061/T062 parallel

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (Proxy)
4. **STOP and VALIDATE**: Quickstart Scenarios A + B
5. MVP delivered — every later phase is an additive increment

### Incremental Delivery

Each subsequent phase adds one independently demonstrable module and ends with its quickstart
verification; any checkpoint is a safe stopping point (Constitution VI).

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] labels map tasks to spec.md user stories for traceability
- Commit after each verified task group; push milestone commits to origin/main
- Constitution gates that apply throughout: II (proxy reliability), IV (dark premium UI),
  V (never fail silently), I (authorized testing only, active scans scope-gated)
