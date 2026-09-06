# Feature Specification: PHANTOM Hunting Upgrade (Tier 1)

**Feature Branch**: `002-hunting-upgrade`

**Created**: 2026-09-07

**Status**: Draft

**Input**: "Just do the best thing" — the four Tier-1 improvements proposed after the MVP review: finding deduplication, secret detection, report export, scanner throttling.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trustworthy findings list (Priority: P1)

As a hunter, when I re-scan the same target I want repeated identical findings
skipped, so my findings list shows unique issues I can actually triage.

**Why this priority**: 784 findings on a microsoft.com passive scan were mostly
duplicates; a noisy list is an ignored list.

**Independent Test**: Scan a target twice; the second scan adds no findings whose
type+URL+parameter already exist.

**Acceptance Scenarios**:
1. **Given** an existing finding (any status, including false positive), **When** a
   new scan produces the same type+URL+parameter, **Then** it is skipped and the
   scan summary reports it as a duplicate.
2. **Given** a finding the user marked false positive, **When** the scanner sees it
   again, **Then** it stays suppressed (the user's judgment wins).

### User Story 2 - Leaked secret detection (Priority: P1)

As a hunter, I want captured responses scanned for leaked credentials (cloud keys,
tokens, private keys, generic secrets) so I can report high-value leaks from traffic
I already captured.

**Independent Test**: A response containing `AKIA...` produces a critical-severity
finding with the matched evidence.

**Acceptance Scenarios**:
1. **Given** captured responses containing provider-format keys (AWS/GCP/GitHub/
   Slack/Stripe/Twilio/SendGrid), **When** a passive scan runs, **Then** findings
   are reported at high/critical severity with evidence and CWE-798.
2. **Given** generic `api_key: "..."` style assignments, **When** found, **Then**
   they are reported as tentative (verify manually).
3. **Given** a long response, **When** many matches exist, **Then** reporting is
   capped per entry to keep the list usable.

### User Story 3 - Report export (Priority: P2)

As a hunter, I want one-click export of my findings as a submission-ready report
(Markdown for pasting, print-ready HTML), so I don't hand-write reports.

**Independent Test**: Export produces a document containing every finding with
severity, URL, evidence, and remediation.

**Acceptance Scenarios**:
1. **Given** findings (optionally filtered by severity), **When** the user exports,
   **Then** a Markdown report downloads with summary counts and per-finding detail.
2. **Given** the same findings, **When** HTML format is chosen, **Then** the report
   renders standalone (inline CSS) and is printable.

### User Story 4 - Polite active scanning (Priority: P2)

As a hunter, I want active scans rate-limited (concurrency cap + delay between
requests), so I respect program rules and don't hammer targets.

**Independent Test**: An active scan with N probes takes at least
`N × delay` seconds and never exceeds the concurrency cap.

**Acceptance Scenarios**:
1. **Given** configurable `scanner_delay_ms` and `scanner_concurrency` settings,
   **When** an active scan runs, **Then** probe requests are spaced by the delay
   and limited to the concurrency cap.
2. **Given** defaults, **Then** they are polite (250 ms / 4 concurrent).

## Requirements *(mandatory)*

- **FR-001**: The scanner MUST skip a finding when an existing finding has the same
  (finding_type, url, parameter) key, and MUST count skipped findings per scan.
- **FR-002**: The scanner MUST detect provider-format secrets (AWS access keys,
  Google API keys, GitHub/Slack/Stripe/Twilio/SendGrid tokens, private key blocks)
  and generic key/secret assignments in captured response bodies, capped per entry.
- **FR-003**: The system MUST export findings as Markdown and standalone HTML via
  API and a Scanner-view button, honoring the severity filter.
- **FR-004**: Active-scan request sending MUST enforce a configurable concurrency
  cap and inter-request delay, seeded polite by default and adjustable in Settings.

## Success Criteria *(mandatory)*

- **SC-001**: Re-running the microsoft.com passive scan adds ~0 new duplicate findings.
- **SC-002**: A synthetic response with an AWS-style key yields exactly one critical finding.
- **SC-003**: Report export contains 100% of visible findings with evidence blocks.
- **SC-004**: 5 sequential active probes with 250 ms delay take ≥ 1.25 s.

## Assumptions

- Dedupe key `(finding_type, url, parameter)` matches reviewer expectations of
  "same issue"; parameter is part of the key because the same URL can host
  distinct per-parameter issues.
- Reports are deterministic summaries; the existing AI "Write report" quick action
  remains the narrative generator — no AI dependency for export.
