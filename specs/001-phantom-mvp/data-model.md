# Data Model: PHANTOM MVP

**Phase 1 output of `/speckit.plan`.** All entities persist in one local SQLite database.
Full DDL lives in `backend/db/migrations.py`; Pydantic counterparts in `backend/db/models.py`.

## TrafficEntry → `proxy_history`

The unit of captured traffic. One row per request/response pair.

| Field | Type | Notes |
|---|---|---|
| id | INTEGER PK AUTOINCREMENT | |
| timestamp | TEXT | ISO, default now |
| method | TEXT NOT NULL | GET/POST/… |
| scheme | TEXT | http/https |
| host / port | TEXT / INTEGER | |
| path / query_string / url | TEXT | |
| request_headers | TEXT | JSON object |
| request_body | TEXT | size-capped (D10) |
| request_content_type | TEXT | |
| status_code | INTEGER | null while in flight |
| response_headers / response_body / response_content_type | TEXT | response_body capped |
| response_time_ms | INTEGER | |
| size_bytes | INTEGER | |
| is_intercepted | BOOLEAN | was paused in intercept |
| is_in_scope | BOOLEAN | scope-rule evaluation result |
| tags | TEXT | JSON array, user annotations |
| notes | TEXT | |
| ai_analysis | TEXT | JSON, filled by Copilot on demand |
| highlight_color | TEXT | |

Indexes: host, method, status_code, timestamp.

## InterceptedFlow (transient, not persisted)

A paused request: `{ flow_id, method, url, headers, body, event }`. Lives in the proxy
engine's queue only; forward/drop resolves it. The queue is observable via API/WS.

## Scan → `scans`

| Field | Type | Notes |
|---|---|---|
| id | TEXT PK | UUID |
| timestamp | TEXT | |
| target_url | TEXT | |
| scan_type | TEXT | active / passive / full |
| status | TEXT | running / paused / completed / failed |
| total_requests | INTEGER | progress counter |
| findings_count | INTEGER | |
| config | TEXT | JSON (selected checks, threads, timeout) |
| started_at / completed_at | TEXT | |

## Finding → `scanner_findings`

| Field | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| scan_id | TEXT | FK → scans.id |
| history_id | INTEGER | FK → proxy_history.id, nullable |
| timestamp | TEXT | |
| finding_type | TEXT | xss / sqli / ssrf / cors / … |
| severity | TEXT | critical/high/medium/low/info |
| confidence | TEXT | certain/firm/tentative |
| title / description | TEXT | |
| url / parameter / payload | TEXT | |
| evidence | TEXT | response snippet proving the finding |
| request_dump / response_dump | TEXT | |
| remediation | TEXT | |
| cwe_id | TEXT | e.g. CWE-79 |
| cvss_score | REAL | nullable |
| is_false_positive | BOOLEAN | |
| status | TEXT | open/confirmed/fixed/false_positive |

Indexes: severity, scan_id, finding_type.

## RepeaterTab → `repeater_tabs`

| Field | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | |
| timestamp | TEXT | |
| method / url / request_headers / request_body | TEXT | editable request |
| last_response_status / last_response_headers / last_response_body / last_response_time_ms | | last exchange |
| history | TEXT | JSON array of past sends |

## ChatMessage → `ai_conversations`

| Field | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| timestamp | TEXT | |
| role | TEXT | user/assistant/system |
| content | TEXT | |
| context_type | TEXT | request / finding / general |
| context_id | INTEGER | |
| model | TEXT | model name used |

## ScopeRule → `scope_rules`

| Field | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| rule_type | TEXT | include / exclude |
| protocol | TEXT | http/https/any |
| host_pattern | TEXT | e.g. `*.example.com` |
| port | TEXT | numeric or `any` |
| path_pattern | TEXT | default `.*` |
| is_active | BOOLEAN | |

Evaluation: a URL is in scope iff it matches at least one active include rule and no active
exclude rule; with no include rules defined, everything is in scope (opt-in scoping for
active scanning is still enforced — Constitution I).

## Setting → `settings`

`(key TEXT PK, value TEXT, category TEXT)` with seeded defaults:
proxy_port=8080, proxy_host=127.0.0.1, intercept_enabled=false, intercept_filter='',
scanner_threads=10, scanner_timeout=30, ai_provider=ollama, ai_model=mistral,
ai_base_url=http://localhost:11434, theme=dark, font_size=13.

## Projects → `projects` (schema reserved for multi-project use in v1; single default project)

`(id, name, description, created_at, updated_at, db_path)`.

## Entity Relationships

- `scanner_findings.history_id` → `proxy_history.id` (0..1 finding source entry)
- `scanner_findings.scan_id` → `scans.id` (a scan yields many findings)
- `repeater_tabs` are created *from* `proxy_history` entries (loose copy, no FK)
- `ai_conversations.context_id` → `proxy_history.id` or `scanner_findings.id` by `context_type`
- All other entities are independent.

## Validation rules (enforced at API layer via Pydantic)

- Methods restricted to known HTTP verbs; severity/confidence/status enums validated.
- Scope patterns compiled server-side; invalid patterns rejected with 422.
- Body/URL length caps validated before persistence.
