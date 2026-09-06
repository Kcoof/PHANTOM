---
description: "Task list for Tier-1 hunting upgrade"
---

# Tasks: PHANTOM Hunting Upgrade (Tier 1)

**Input**: spec.md (this feature) · builds on `specs/001-phantom-mvp` (complete)

## Phase 1: Backend — scanner quality

- [x] T101 Dedupe findings on (finding_type, url, parameter) in `backend/core/scanner_engine.py`; count duplicates per scan and include in the final scan_progress event
- [x] T102 [P] Secrets passive check in `backend/core/scanner_checks/secrets.py` (provider formats + generic assignments, per-entry cap, CWE-798) + register in engine
- [x] T103 Throttling in `backend/core/scanner_checks/base.py` `send_variant` (semaphore + delay, configurable), settings loaded at scan start; seed `scanner_delay_ms=250`, `scanner_concurrency=4` in `backend/db/migrations.py`

## Phase 2: Report export

- [x] T104 `GET /api/scanner/report` in `backend/api/scanner_routes.py` (format=markdown|html, severity filter, standalone dark-print HTML)
- [x] T105 "Export Report" dropdown in `frontend/src/components/scanner/ScannerView.tsx` (Markdown / HTML download, respects severity filter)

## Phase 3: Verification

- [x] T106 [P] Tests in `backend/tests/`: dedupe (rescan adds 0), secrets detection unit + endpoint, report contains findings, throttle timing
- [x] T107 Live verification: re-scan microsoft.com passively (dupes ≈ new), synthetic AWS-key history entry → critical finding, export report via API
- [x] T108 Update `.specify/feature.json`, commit + push

## Notes

- All four stories are independent; backend first, UI last.
- Dedupe never resurrects user-marked false positives.
