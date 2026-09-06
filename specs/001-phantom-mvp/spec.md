# Feature Specification: PHANTOM MVP — Web Security Testing Platform

**Feature Branch**: `001-phantom-mvp`

**Created**: 2026-09-06

**Status**: Draft

**Input**: User description: "Build PHANTOM, a web application security testing platform (proxy, repeater, scanner, AI copilot, dashboard, decoder) for pentesters and bug bounty hunters — an AI-native, open-core alternative to Burp Suite, cross-platform desktop app, targeting authorized testing only."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Intercept and Inspect Web Traffic (Priority: P1)

As a security tester, I point my browser at PHANTOM's proxy so that every HTTP(S) request and
response between my browser and the target application is captured, decrypted, stored, and shown
to me live in a filterable history table, so I can understand how the application communicates
and spot interesting requests for deeper testing.

**Why this priority**: The intercepting proxy is the heart of the platform and the entry point
for every other module. Without traffic capture there is nothing to repeat, scan, or analyze.
It alone is a usable MVP (manual inspection workflow).

**Independent Test**: Configure a browser or CLI client to use the proxy, browse an authorized
target, and verify requests appear in the history table in real time with full request/response
detail available on selection.

**Acceptance Scenarios**:

1. **Given** the proxy is started, **When** the user sends an HTTP request through it from any
   client, **Then** the request and its response appear in the traffic history within a second,
   with method, host, path, status code, and timing.
2. **Given** HTTPS traffic is flowing, **When** the user installs PHANTOM's CA certificate in
   the client, **Then** decrypted request/response contents are visible in history.
3. **Given** a populated history, **When** the user filters by method, host, status code, or
   free-text search, **Then** only matching entries are shown.
4. **Given** an entry in history, **When** the user selects it, **Then** full request and
   response (headers, body, raw view) are displayed side by side in resizable panes.
5. **Given** intercept mode is enabled, **When** a matching request arrives, **Then** it is
   paused and queued until the user forwards (optionally after editing) or drops it.
6. **Given** an entry in history, **When** the user tags, notes, or color-highlights it,
   **Then** the annotation persists and is visible in the table.

---

### User Story 2 - Replay and Modify Requests (Priority: P2)

As a security tester, I take a captured request into a Repeater tab so that I can edit any part
of it (method, headers, body) in a proper code editor and resend it repeatedly, comparing
responses, so I can probe how the application behaves under crafted inputs.

**Why this priority**: Request replay/manipulation is the bread-and-butter manual testing loop
after capture; it multiplies the value of the proxy with zero extra setup.

**Independent Test**: Send a captured request to the Repeater, edit a header or body parameter,
send it, and verify the response (with status, headers, body, timing) is displayed and that the
send history for the tab is kept.

**Acceptance Scenarios**:

1. **Given** a request in proxy history, **When** the user sends it to the Repeater, **Then** a
   new tab opens pre-populated with the full raw request in an editable code editor.
2. **Given** an editable request, **When** the user modifies it and sends, **Then** the request
   goes to the server (through TLS as needed) and the response is displayed with raw/headers/
   body views and response time.
3. **Given** repeated sends in one tab, **When** the user reviews the tab, **Then** previous
   request/response exchanges remain accessible for that tab.
4. **Given** multiple tabs, **When** the user switches or closes tabs, **Then** each tab's
   request state is preserved and reopening the app restores saved tabs.

---

### User Story 3 - Scan for Vulnerabilities (Priority: P3)

As a security tester, I launch a scan (passive and/or active) against in-scope requests so that
common vulnerability classes are checked automatically and findings are reported with severity,
confidence, evidence, and remediation advice, so I can focus my manual effort where it matters.

**Why this priority**: Automated checks are the first force multiplier over manual work; they
depend on captured traffic (US1) and reuse the send capability (US2).

**Independent Test**: Run a scan over captured history (passive) and against an authorized test
target (active), and verify findings appear with type, severity, evidence, affected URL and
parameter, and can be marked confirmed/false-positive/fixed.

**Acceptance Scenarios**:

1. **Given** captured traffic, **When** the user starts a passive scan, **Then** checks run over
   stored requests/responses (CORS, security headers, information disclosure, cookie flags,
   CSRF tokens, JWT issues) and findings are listed live as they are found.
2. **Given** an authorized, in-scope target, **When** the user starts an active scan selecting
   check types (reflected XSS, SQL injection, SSRF, open redirect, IDOR/auth patterns), **Then**
   modified requests are sent and findings are reported only when evidence supports them.
3. **Given** a finding, **When** the user opens it, **Then** full details are shown: description,
   evidence snippet, triggering request/response, severity, confidence, CWE reference, and
   remediation guidance.
4. **Given** a running scan, **When** the user pauses, resumes, or stops it, **Then** the scan
   state changes accordingly and progress is visible in real time.
5. **Given** a finding the user knows is a false positive, **When** they mark it as such,
   **Then** it is excluded from active counts and the status persists.

---

### User Story 4 - Ask the AI Copilot (Priority: P4)

As a security tester, I ask PHANTOM's built-in AI assistant to analyze a captured request, a
finding, or a general security question, and receive streamed, specific, actionable guidance
(potential vulnerabilities, suggested payloads, next steps), so I get expert-level triage
without leaving the tool.

**Why this priority**: AI assistance is the differentiating feature; it requires captured
context (US1) and shines when combined with findings (US3), so it lands after both exist.

**Independent Test**: Select a captured request, run "Analyze with AI", and verify a streamed
analysis arrives in the chat; ask a follow-up question in the same conversation and verify
history is preserved.

**Acceptance Scenarios**:

1. **Given** a captured request, **When** the user sends it to the AI Copilot, **Then** the
   assistant analyzes it and streams its response progressively into the chat view.
2. **Given** a chat, **When** the user asks follow-up questions, **Then** conversation context
   is maintained and past messages remain readable across app restarts.
3. **Given** a parameter on an endpoint, **When** the user requests payload suggestions, **Then**
   the assistant proposes concrete, contextual test payloads (e.g., for XSS or SQLi) the user
   can copy into the Repeater.
4. **Given** no local AI runtime is running, **When** the user opens the Copilot, **Then** the
   UI clearly shows AI unavailability with setup guidance, and all other modules keep working.

---

### User Story 5 - See Dashboard Analytics (Priority: P5)

As a security tester, I open the dashboard to see my session at a glance — traffic volume over
time, findings by severity, top hosts, and detected technologies — so I can track coverage and
progress of my testing.

**Why this priority**: Aggregation is valuable once data exists (US1/US3) but adds no new
testing capability; it is a lens, not a lever.

**Independent Test**: Browse several authorized sites through the proxy and run a scan, then
open the dashboard and verify stats, traffic chart, severity chart, and technology list reflect
that activity.

**Acceptance Scenarios**:

1. **Given** captured traffic, **When** the user opens the dashboard, **Then** summary cards
   show totals (requests, findings by severity, average response time, top hosts).
2. **Given** traffic over time, **When** the user views the traffic chart, **Then** request
   volume is plotted by minute/hour/day with a selectable interval.
3. **Given** scan findings, **When** the user views the severity chart, **Then** findings are
   broken down by severity in a visual chart.
4. **Given** responses analyzed, **When** the user views technologies, **Then** detected
   server/framework/library technologies are listed with the host they were seen on.

---

### User Story 6 - Encode, Decode, and Transform Data (Priority: P6)

As a security tester, I paste a token or blob into the Decoder and chain transformations
(decode/encode/hash) to understand and craft values, so I can build the exact payload or
credential material a test requires.

**Why this priority**: The decoder is self-contained and independent, but it is the smallest
standalone utility — valuable at any time, blocking nothing.

**Independent Test**: Paste a Base64/URL/JWT-encoded value, run auto-detect or chained decode
operations, and verify correct decoded output and hashes.

**Acceptance Scenarios**:

1. **Given** encoded input, **When** the user applies decode operations (Base64, URL, HTML
   entities, hex, Unicode, JWT, gzip) in a chain, **Then** the output of each step is shown and
   feeds the next step.
2. **Given** unknown input, **When** the user runs auto-detect, **Then** the most likely
   encodings are attempted and a best-guess decoded result is presented.
3. **Given** any input, **When** the user hashes it (MD5, SHA-1, SHA-256, SHA-512), **Then**
   the digest is displayed and copyable.

---

### Edge Cases

- What happens when the proxy port is already in use or blocked? — The start attempt MUST fail
  with a clear, actionable error; the UI stays usable and can retry on another port.
- What happens when a target uses certificate pinning and TLS interception fails? — The failed
  flow is recorded as an error entry, and the rest of traffic keeps flowing.
- How does the system handle very large request/response bodies (e.g., binaries, multi-MB
  uploads)? — Bodies are stored size-capped with a clear truncation marker so history stays
  responsive.
- What happens when the local database is locked or corrupted? — The error is surfaced; the app
  does not crash; the user can restart or reset storage.
- How does history behave at high request rates (hundreds per second)? — The live table applies
  flow control (batched updates) so the UI remains responsive without dropping entries.
- What happens when a scan target becomes unreachable mid-scan? — Affected checks are marked
  errored, the scan continues or completes with partial results, and the failure is visible.
- What happens when the live update connection to the backend drops? — The UI shows a
  disconnected status and automatically reconnects, refreshing state on reconnect.
- What if the user runs the app offline with no AI runtime? — All non-AI functionality works
  unchanged (Constitution VII).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide an intercepting HTTP(S) proxy that the user can start
  and stop, with configurable host and port.
- **FR-002**: The system MUST capture every request/response pair flowing through the proxy,
  decrypt HTTPS via a locally generated CA (installable by the user), and persist them in a
  local traffic history.
- **FR-003**: The history view MUST update in real time as traffic flows (no manual refresh)
  and MUST support filtering by method, host, status code, and free-text search, plus
  pagination or virtualization for large volumes.
- **FR-004**: Selecting a history entry MUST show full request and response detail (raw,
  headers, body views) in resizable side-by-side panes.
- **FR-005**: The system MUST support an intercept mode that pauses matching requests in a
  queue until the user forwards (with optional modification) or drops them.
- **FR-006**: The system MUST let users annotate history entries with tags, notes, and row
  highlight colors, persisted locally.
- **FR-007**: The system MUST allow sending any history entry to the Repeater as a new
  editable tab pre-populated with the raw request.
- **FR-008**: The Repeater MUST provide a code-editor editing experience for raw requests and
  MUST display responses with status, headers, body (raw/pretty views), and timing; each tab
  MUST retain its send history.
- **FR-009**: The Scanner MUST run passive checks over stored traffic and active checks that
  send modified requests, covering at least: reflected XSS, SQL injection, SSRF, open redirect,
  CORS misconfiguration, missing security headers, information disclosure, missing CSRF tokens,
  insecure cookie flags, and JWT issues.
- **FR-010**: Every finding MUST include type, severity, confidence, affected URL/parameter,
  evidence, triggering request/response, and remediation guidance; users MUST be able to change
  finding status (open/confirmed/fixed/false positive).
- **FR-011**: Scan progress and new findings MUST be pushed to the UI in real time; scans MUST
  support pause/resume/stop.
- **FR-012**: The AI Copilot MUST analyze requests/findings provided as context, answer
  security questions, and generate contextual payload suggestions, streaming responses
  progressively.
- **FR-013**: The AI Copilot MUST operate against a local model runtime by default and MUST
  degrade gracefully (visible status, guidance) when unavailable; no cloud service may be
  required by core modules.
- **FR-014**: The Dashboard MUST present traffic-over-time, findings-by-severity, top hosts,
  average response time, and detected technologies derived from local data.
- **FR-015**: The Decoder MUST support chained encode/decode (Base64, URL, HTML entities, hex,
  Unicode, JWT, gzip), hashing (MD5, SHA-1, SHA-256, SHA-512), and encoding auto-detection.
- **FR-016**: The system MUST provide scope rules (include/exclude by protocol, host pattern,
  port, path) that constrain what active scanning and interception treat as in-scope, with
  active scanning refusing out-of-scope targets.
- **FR-017**: The system MUST expose application settings (proxy, scanner, AI, UI) that
  persist locally and affect behavior without restart where feasible.
- **FR-018**: The UI MUST provide the documented keyboard shortcuts (at minimum: toggle
  intercept, send to repeater, send request in repeater) and toast notifications for action
  success/failure.
- **FR-019**: The application MUST run as a cross-platform desktop app (Windows, macOS,
  Linux) bundling backend and UI, and MUST also be runnable in dev mode as backend + web UI.
- **FR-020**: The system MUST apply method and status color coding and the mandated dark theme
  across all technical views.

### Key Entities *(include if feature involves data)*

- **TrafficEntry**: One intercepted request/response pair — method, scheme, host, port, path,
  query, URL, request headers/body, response status/headers/body, timing, size, intercept
  flag, scope flag, user annotations (tags, notes, highlight), optional AI analysis.
- **InterceptedFlow**: A paused request awaiting user decision — reference to the held
  request content and its disposition (forward modified / drop).
- **Scan**: A scan session — target, type (passive/active/full), selected checks, status
  (running/paused/completed/failed), progress counters, configuration, timestamps.
- **Finding**: A detected issue — type, severity, confidence, title, description, affected
  URL/parameter, payload, evidence, request/response dumps, remediation, CWE id, CVSS score,
  user status.
- **RepeaterTab**: A saved replay unit — name, editable request, last response, send history.
- **ChatMessage**: One AI conversation turn — role, content, linked context (request/finding),
  model used.
- **ScopeRule**: One include/exclude rule — protocol, host pattern, port, path pattern, active
  flag.
- **Setting**: A keyed application preference grouped by category (proxy/scanner/AI/UI).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can configure a browser to the proxy and see captured HTTPS traffic with
  decrypted contents within 5 minutes of first launch (including CA installation).
- **SC-002**: New traffic appears in the history table within 1 second of flowing through the
  proxy, sustained at 100 requests/minute without UI lag.
- **SC-003**: A user can move a request from history to Repeater, edit it, and see a response
  in under 3 interactions (context-menu → edit → send).
- **SC-004**: A passive scan over 1,000 stored request/response pairs completes within 2
  minutes and reports findings live while running.
- **SC-005**: 90% of AI Copilot responses begin streaming to the user within 3 seconds when
  the local runtime is available.
- **SC-006**: All six modules are reachable within one click from persistent navigation, and
  every view renders in under 1 second on interaction.
- **SC-007**: All captured data remains on the operator's machine; no outbound traffic beyond
  the proxied targets and (optionally) the local AI runtime.

## Assumptions

- Users are professional pentesters or bug bounty hunters testing systems they are authorized
  to test; PHANTOM displays and documents this restriction but does not implement target
  whitelisting beyond scope rules.
- A local AI runtime (e.g., a small local model) may be installed by the user; it is optional
  and detected at runtime.
- The operator's machine can generate and trust a local CA for TLS interception; standard
  browsers and CLI clients are in scope for proxying.
- v1 targets manual single-user usage; multi-user collaboration, report export beyond basic
  findings view, and cloud sync are out of scope.
- Browser-based traffic (HTTP/1.x, HTTP/2 where feasible, WebSockets pass-through at minimum)
  is the primary workload; non-HTTP protocols are out of scope for v1.
