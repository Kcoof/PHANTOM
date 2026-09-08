# Feature Specification: PHANTOM AI Auto-Triage

**Feature Branch**: `004-ai-triage`

**Created**: 2026-09-08

**Status**: Draft

**Input**: Approved next step after multi-provider AI: let the Copilot batch-review findings.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Triage hundreds of findings in minutes (Priority: P1)

As a hunter with 400+ scanner findings, I want the AI to review them in batches
and mark each as likely-real / likely-false-positive / needs-manual with a
one-line reason and priority, so I spend my time only on findings worth
reporting.

**Independent Test**: With the AI runtime online, "AI Triage" completes over
the findings table, verdicts appear as badges in the list and reasons in the
detail view.

**Acceptance Scenarios**:
1. **Given** findings (excluding user-marked false positives), **When** triage
   runs, **Then** each finding gets a stored AI verdict (verdict + reason +
   priority), visible in the UI.
2. **Given** the AI is offline, **When** triage is requested, **Then** a clean
   503 with setup guidance (never a crash) — same contract as chat.
3. **Given** a batch response, **When** the model wraps JSON in prose,
   **Then** the verdict parser still extracts the array tolerantly.
4. **Given** many findings, **When** triage runs as a background job,
   **Then** progress streams over WebSocket and the list refreshes on
   completion.

## Requirements *(mandatory)*

- **FR-201**: `POST /api/ai/triage` MUST batch findings (≤10 per model call,
  severity-ordered, capped at 100/run) into a strict-JSON prompt and store
  parsed verdicts in a new `ai_verdict` column.
- **FR-202**: The findings API MUST decode and return the verdict; the
  Scanner UI MUST show verdict badges, reasons, a "likely real" filter, and a
  Triage button with live progress.
- **FR-203**: Triage MUST respect the existing provider stack (Ollama local or
  OpenAI-compatible) and degrade identically when unavailable.

## Success Criteria *(mandatory)*

- **SC-001**: Live triage over the real findings table completes and tags
  ≥90% of processed findings with parseable verdicts.
- **SC-002**: Likely-false-positive verdicts are visually distinct in the list.

## Assumptions

- Verdicts are advisory; the user's own status (confirmed/false positive)
  remains authoritative and is never overwritten by AI.
