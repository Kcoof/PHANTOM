# Feature Specification: PHANTOM Tier 2 — Power Tools

**Feature Branch**: `003-tier2-power`

**Created**: 2026-09-07

**Status**: Draft

**Input**: Approved Tier-2 roadmap: Intruder/fuzzer, global regex search, match & replace rules.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Intruder / Fuzzer (Priority: P1)

As a hunter, I want to take a captured request, mark payload positions, load a
wordlist, and fire all variations with throttling — then instantly see which
responses deviate from baseline (status/length/time) and which match my grep
patterns — so I can enumerate IDs, bypass filters, and mine parameters.

**Independent Test**: Attack `http://127.0.0.1:8899/api/health?x=§1§` with 3 payloads
produces 3 results plus a baseline row, live via WebSocket.

**Acceptance Scenarios**:
1. Positions marked `§value§` in the raw request are replaced by each payload
   (all positions share one payload set — battering-ram mode).
2. A baseline request (original values) is sent first; result rows that deviate
   in status or length from baseline are visually flagged.
3. Grep patterns (regex list) mark matching results in a dedicated column.
4. Sending is throttled (reuses scanner politeness settings) and stoppable;
   progress streams live to the UI.
5. Payloads come from manual entry or built-in wordlists; attacks and results
   persist and are re-viewable; requests can be sent from Proxy/Repeater.

### User Story 2 - Global search (Priority: P2)

As a hunter, I want to regex-search every captured request AND response (headers
and bodies) so I can find patterns across a whole session ("every response
mentioning api_key", "every request with an Authorization header").

**Independent Test**: Searching for a string known to exist in a captured response
returns that entry with a snippet; clicking it opens the entry in the Proxy view.

**Acceptance Scenarios**:
1. Search supports literal and regex modes, request/response/both sides, capped
   result counts with snippets around matches.
2. Results link to the full entry in Proxy history.

### User Story 3 - Match & Replace rules (Priority: P2)

As a hunter, I want live rewrite rules on proxied traffic (add header, replace
string/regex, on request or response) so I can inject headers, strip cache
busters, or normalize requests without editing each one.

**Independent Test**: A rule `X-Phantom: on` (request header add) applied while
browsing appears in the captured request headers of subsequent flows.

**Acceptance Scenarios**:
1. Rules are CRUD-managed, individually enableable, applied in order.
2. Literal and regex match types, on request or response side.
3. Modified traffic is stored modified (what you see is what was sent/received).

## Requirements *(mandatory)*

- **FR-101**: Intruder MUST substitute `§…§` positions, send baseline + one request
  per payload, throttle all sends, stream progress/results, persist attacks and
  capped results, and flag deviations from baseline.
- **FR-102**: Global search MUST cover request/response headers+bodies with
  regex and literal modes and return snippets linking to history entries.
- **FR-103**: Match & replace rules MUST be applied live to proxied requests and
  responses before persistence, in rule order, with enable toggles.

## Assumptions

- Intruder is a manual tool (like Repeater): no scope gate, but the politeness
  throttle applies and authorized-use remains the operator's responsibility.
- Battering-ram (one payload set across all positions) covers the dominant
  enumeration/fuzzing cases; per-position sets (cluster bomb) come later.
