---
description: "Task list for AI auto-triage"
---

# Tasks: PHANTOM AI Auto-Triage

**Input**: spec.md (this feature)

- [x] T401 `ai_verdict` column migration for pre-existing DBs (PRAGMA-guarded ALTER)
- [x] T402 `POST /api/ai/triage` — background job, severity-ordered cap 100, batches of 10,
      strict-JSON prompt with triage heuristics, tolerant verdict parser, WS
      `ai_triage_progress` / `ai_triage_done`, re-triages only untagged findings
- [x] T403 Free-tier resilience: 2.5 s between batches, 3 attempts × 60 s backoff on
      rate-limited batches
- [x] T404 Findings API decodes verdicts; Scanner UI: AI Triage button with live
      progress, verdict badges (AI ✓ REAL / AI ✗ FP / AI ? CHECK) in the list,
      reason + priority + model in the finding detail
- [x] T405 Tests: tolerant parser (prose-wrapped JSON, trailing commas, invalid
      verdicts), endpoint 503/422 contract, column migration (33 passing)
- [x] T406 Live verification via Groq on real findings: verdicts landed including a
      likely-real "Expired JWT accepted" (p5) and sensible likely-fp calls (HSTS on
      static assets); gap-filling re-runs confirmed
