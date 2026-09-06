---
description: "Task list for Tier-2 power tools"
---

# Tasks: PHANTOM Tier 2 — Power Tools

**Input**: spec.md (this feature)

## Phase 1: Match & Replace

- [x] T201 Rules table (migrations), rewrite engine (`core/rewrite_engine.py`), CRUD API `/api/match-replace`
- [x] T202 Addon integration: request-side rules before intercept, response-side before persistence
- [x] T203 Settings → Match & Replace section (add/delete rules, location/match-type)

## Phase 2: Global search

- [x] T204 `GET /api/search` (literal + regex, request/response/both, snippets, capped 5000-row scan)
- [x] T205 SearchView with results linking into Proxy history detail

## Phase 3: Intruder

- [x] T206 Engine (`core/intruder_engine.py`): §positions§, battering-ram payloads, baseline, throttle reuse, WS progress/results, scope-exempt manual sends
- [x] T207 Attacks/results tables + `/api/intruder` API (start/list/results/stop/delete/wordlists)
- [x] T208 Built-in wordlists (numbers, nulls, users, paths, xss, sqli)
- [x] T209 IntruderView: Monaco template with Add-§ helper, payload editor + wordlist loader, grep patterns, live results table with baseline/deviation highlight, response drawer
- [x] T210 Send-to-Intruder from Proxy context menu and Repeater toolbar

## Phase 4: Verification

- [x] T211 Tests: match-replace (CRUD + apply + regex validation), search (literal/regex/bad-regex), intruder e2e vs localhost (30 passing)
- [x] T212 Live verification: intruder 4/4 results with grep hits, M&R header rewrite visible in stored traffic, search finds rewritten header
- [x] T213 UI verification (Intruder + Search views render with live data); commit + push

## Notes

- Intruder sends are scope-exempt by design (manual tool, like Repeater) but throttled; scanner probes remain scope-gated.
