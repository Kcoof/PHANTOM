# API Contract: PHANTOM Backend

**Phase 1 output of `/speckit.plan`.** The backend exposes a localhost REST + WebSocket API.
Base URL (dev): `http://127.0.0.1:8899`. All bodies are JSON unless noted. Errors use standard
FastAPI envelopes (422 validation, 500 with detail); every endpoint is wrapped so failures
never crash the app (Constitution V).

## Proxy

| Method | Path | Body / Query | Success response |
|---|---|---|---|
| POST | `/api/proxy/start` | `{port?: 8080, host?: "127.0.0.1"}` | `{status: "running", port, host}` |
| POST | `/api/proxy/stop` | — | `{status: "stopped"}` |
| GET  | `/api/proxy/status` | — | `{running, port, host, requests_captured}` |
| POST | `/api/proxy/intercept/toggle` | `{enabled: bool}` | `{intercept: bool}` |
| GET  | `/api/proxy/intercept/queue` | — | `[{flow_id, method, url, headers, body}]` |
| POST | `/api/proxy/intercept/{flow_id}/forward` | `{modified_request?: raw string}` | `{forwarded: true}` |
| POST | `/api/proxy/intercept/{flow_id}/drop` | — | `{dropped: true}` |
| GET  | `/api/proxy/ca-cert` | — | PEM file (application/x-pem-file) |

## History

| Method | Path | Body / Query | Success response |
|---|---|---|---|
| GET | `/api/history` | `?page&limit&method&host&status&search&in_scope` | `{items: TrafficEntry[], total, page, limit}` |
| GET | `/api/history/{id}` | — | `TrafficEntry` (full bodies) |
| DELETE | `/api/history` | — | `{deleted: n}` |
| DELETE | `/api/history/{id}` | — | `{deleted: true}` |
| POST | `/api/history/{id}/tag` | `{tag}` | `{tags: [...]}` |
| POST | `/api/history/{id}/note` | `{note}` | `{note}` |
| POST | `/api/history/{id}/highlight` | `{color}` | `{color}` |
| POST | `/api/history/{id}/send-to-repeater` | — | `{repeater_tab_id}` |
| POST | `/api/history/{id}/send-to-scanner` | `{checks?: [...]}` | `{scan_id}` |
| POST | `/api/history/{id}/send-to-copilot` | — | `{conversation_started: true}` |

## Repeater

| Method | Path | Body | Success response |
|---|---|---|---|
| GET | `/api/repeater/tabs` | — | `[RepeaterTab]` |
| POST | `/api/repeater/tabs` | `{name?, method, url, request_headers, request_body?}` | `RepeaterTab` |
| GET | `/api/repeater/tabs/{id}` | — | `RepeaterTab` |
| PUT | `/api/repeater/tabs/{id}` | partial tab | `RepeaterTab` |
| DELETE | `/api/repeater/tabs/{id}` | — | `{deleted: true}` |
| POST | `/api/repeater/tabs/{id}/send` | `{raw_request?}` (uses stored if absent) | `{status, headers, body, time_ms, size}` |

## Scanner

| Method | Path | Body / Query | Success response |
|---|---|---|---|
| POST | `/api/scanner/scan` | `{target_url?, history_ids?, scan_type: active\|passive\|full, checks?: [..]}` | `{scan_id, status: "running"}` |
| GET | `/api/scanner/scans` | — | `[Scan]` |
| GET | `/api/scanner/scans/{id}` | — | `Scan` with progress |
| POST | `/api/scanner/scans/{id}/pause` \| `/resume` \| `/stop` | — | `{status}` |
| GET | `/api/scanner/findings` | `?severity&type&scan_id&status` | `[Finding]` |
| GET | `/api/scanner/findings/{id}` | — | `Finding` |
| PUT | `/api/scanner/findings/{id}/status` | `{status: confirmed\|fixed\|false_positive\|open}` | `Finding` |
| GET | `/api/scanner/checks` | — | available check registry `[{check_type, name, severity, mode}]` |

Active scans against hosts not matching an active include scope rule are refused with `403`
and an explanatory message (Constitution I).

## AI Copilot

| Method | Path | Body | Success response |
|---|---|---|---|
| POST | `/api/ai/chat` | `{message, context_type?, context_id?}` | **SSE stream**: `data: {"delta": "…"}` … `data: [DONE]` |
| GET | `/api/ai/conversations` | — | `[ChatMessage]` |
| POST | `/api/ai/analyze-request/{history_id}` | — | SSE stream (same format) |
| POST | `/api/ai/suggest-payloads` | `{url, parameter, vuln_type, context?}` | SSE stream |
| GET | `/api/ai/status` | — | `{available: bool, provider, model, base_url, detail?}` |

When the runtime is unavailable, chat endpoints return `503 {detail: "AI runtime unavailable…"}`
without crashing; `/api/ai/status` always returns 200.

## Decoder

| Method | Path | Body | Success response |
|---|---|---|---|
| POST | `/api/decoder/encode` \| `/decode` | `{input, codec: base64\|url\|html\|hex\|unicode\|gzip\|jwt*}` | `{input, output, codec}` (jwt decode-only) |
| POST | `/api/decoder/auto-detect` | `{input}` | `{results: [{codec, output, confidence}]}` |
| POST | `/api/decoder/hash` | `{input, algorithm: md5\|sha1\|sha256\|sha512}` | `{algorithm, digest}` |

Invalid input for a codec → `422 {detail: "cannot decode as base64: …"}` (never 500).

## Dashboard

| Method | Path | Query | Success response |
|---|---|---|---|
| GET | `/api/dashboard/stats` | — | `{total_requests, findings_by_severity, top_hosts, avg_response_time_ms, total_findings}` |
| GET | `/api/dashboard/traffic` | `?interval=minute\|hour\|day` | `[{bucket, count}]` |
| GET | `/api/dashboard/technologies` | — | `[{technology, hosts, source}]` |
| GET | `/api/dashboard/top-findings` | — | `[{finding_type, count, max_severity}]` |

## Settings & Scope

| Method | Path | Body | Success response |
|---|---|---|---|
| GET | `/api/settings` | — | `{categories: {proxy: {…}, scanner: {…}, ai: {…}, ui: {…}}}` |
| PUT | `/api/settings` | `{key: value, …}` | updated settings |
| GET | `/api/settings/scope` | — | `[ScopeRule]` |
| POST | `/api/settings/scope` | `{rule_type, protocol?, host_pattern, port?, path_pattern?}` | `ScopeRule` |
| DELETE | `/api/settings/scope/{id}` | — | `{deleted: true}` |

## WebSocket `/ws`

Server → client JSON frames: `{"event": "<name>", "data": {...}}`

| Event | Payload |
|---|---|
| `new_request` | summary TrafficEntry (id, method, url, host, path, status_code, response_time_ms, size_bytes) |
| `intercept_request` | `{flow_id, method, url}` |
| `intercept_resolved` | `{flow_id, action: forward\|drop}` |
| `proxy_status` | `{running, port}` |
| `scan_progress` | `{scan_id, status, done, total}` |
| `scan_finding` | Finding |
| `ai_status` | `{available}` |

Client → server: `{\"event\": \"ping\"}` keepalive; server responds `pong`. The frontend
auto-reconnects with backoff and re-fetches current state on reconnect.
