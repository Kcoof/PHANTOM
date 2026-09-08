# Feature Specification: PHANTOM Plugin System + Parameter Miner

**Feature Branch**: `005-plugin-system`

**Created**: 2026-09-08

**Status**: Draft

**Input**: Approved mockup (docs/mockups/plugin-system-mockup.html): runnable plugins
starting with a Param-Miner-style hidden-parameter discovery, launchable from
Proxy/Repeater/findings, plus an AI→Intruder action bridge.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Discover hidden parameters (Priority: P1)

As a hunter, I point the Parameter Miner at a captured request and it discovers
parameters the app silently accepts (reflection or behavior change) — without
firing one request per candidate — so I find the secret knobs that lead to
IDORs, debug panels, and bypasses.

**Independent Test**: Against a local server with planted hidden params
(2 reflected, 1 behavioral), the miner finds all 3 with zero false positives.

**Acceptance Scenarios**:
1. Batches of ~25 candidates with unique canaries are probed; a batch showing
   reflection or a status/length delta is bisected to isolate the parameter(s),
   each confirmed twice individually.
2. Runs are throttled (existing politeness settings) and scope-gated with a
   clear error for out-of-scope targets.
3. Discovered parameters appear as live results (evidence + response delta)
   AND as findings (type `hidden_param`) that flow into dedupe/triage/report.
4. Runs can be stopped; progress streams over WebSocket.

### User Story 2 - Launch plugins from anywhere (Priority: P1)

From Proxy (right-click → Plugins ▸), Repeater (button), finding detail
(button), or the Plugins view (pick request from targets) — same runner.

**Independent Test**: A run started from the Proxy context menu appears live
in the Plugins view.

### User Story 3 - AI suggestions become attacks (Priority: P2)

When the Copilot suggests payloads, a "Send payloads to Intruder" action
pre-fills the Intruder with the context request (the suggested parameter
auto-marked as a §position§ when known) and the extracted payloads.

**Independent Test**: After a payload suggestion on a captured request, the
Intruder draft contains the request with §positions§ and the payload list.

### User Story 4 - Extensible plugin contract (Priority: P2)

Plugins are Python classes with a small contract (id/name/accepts/parameters/
run(ctx, options, emit)); built-ins ship in-repo and the registry/API/UI are
generic so more plugins follow without framework changes.

## Requirements *(mandatory)*

- **FR-301**: Plugin runs MUST execute as background tasks with WS progress/
  result events, persisted in `plugin_runs`/`plugin_results`, stoppable.
- **FR-302**: The Parameter Miner MUST implement batched canary probing with
  bisection and double confirmation, respect throttle + scope, and emit both
  plugin results and `hidden_param` findings.
- **FR-303**: The UI MUST expose plugin launches from Proxy context menu,
  Repeater, finding detail, and a Plugins view with live results.
- **FR-304**: The Copilot MUST offer a payload→Intruder bridge that extracts
  code-block payloads from its last answer and pre-fills the Intruder.

## Assumptions

- v1 mines query parameters (and urlencoded body params for POST-style
  requests); header/cookie mining is a future plugin.
- The AI payload bridge parses fenced code blocks from the assistant's raw
  text; imprecise extraction is acceptable (user reviews before launching).
