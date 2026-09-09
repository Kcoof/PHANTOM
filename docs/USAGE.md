# Using PHANTOM — a field guide

This guide walks through every module in the order you'd actually use them during a test session. If you haven't installed PHANTOM yet, start with the [README](../README.md#getting-started) — setup takes about five minutes.

**Throughout this guide, "the target" means the application you're testing — which must be yours or one you have written permission to test.**

---

## The mental model

PHANTOM is organized around one idea: **traffic flows through the Proxy, and everything else works on captured traffic.**

```
                          you browse normally
                                 │
                                 ▼
   ┌──────────┐   HTTP(S)   ┌────────┐   clean copies   ┌────────────┐
   │ Browser  ├────────────►│ PROXY  ├─────────────────►│  History   │
   └──────────┘  :8080      └────────┘                  └─────┬──────┘
                                                       every module
                                                       reads from here
                                ┌───────────────┬─────────────┼──────────────┐
                                ▼               ▼             ▼              ▼
                            REPEATER        INTRUDER      SCANNER        PLUGINS
                            (edit one)      (fuzz many)   (checks)       (hunters)
                                └───────────────┴─────────────┴──────────────┘
                                                │
                                                ▼
                                       FINDINGS + ASSISTANT
                                       (triage, understand, report)
```

The context menu (right-click) is the fastest way to move traffic around: **Send to Repeater**, **Send to Intruder**, **Send to Hpere**, **Scan this request**, **AI Analyze**, **Render response** are all one click from any captured request.

---

## 1. Scope — do this first

**Settings → Scope**

Scope decides what the automated tools are allowed to touch. Before any active scan or plugin run, PHANTOM checks the target against your rules and refuses to run if it doesn't match.

- **Include rules** — targets you're allowed to test. Examples:
  - `example.com` — matches `example.com` **and every subdomain** (`www.example.com`, `api.example.com`, …)
  - `*.example.com` — matches subdomains and the apex domain
  - `staging.example.com:8443` — a specific host with port
- **Exclude rules** — carve-outs that win over includes (e.g. `logout.example.com` to avoid forced logouts mid-scan).

The scope chip appears wherever it matters — in the Proxy filter bar, the Scanner target picker, the Plugins view — so you can always see and toggle "in-scope only".

> The passive parts of PHANTOM (capturing, browsing history, the site map, search) never check scope — they only read what already passed through your proxy. Only tools that *send requests* are gated.

---

## 2. Proxy — capture and inspect traffic

**Location:** sidebar → Proxy · **Listens on** `127.0.0.1:8080`

1. Press **Start**. Configure your browser to use `http://127.0.0.1:8080` as its HTTP proxy (a dedicated testing profile or a browser like Firefox with per-browser proxy settings keeps this clean).
2. For HTTPS sites, trust the PHANTOM CA once (see the [README](../README.md#first-run--three-steps) for per-browser instructions).
3. Browse the target. Requests appear live in the history table — no refresh, ever.

**Reading the table**

- Color-coded method (GET/POST/PUT…) and status (2xx green, 3xx amber, 4xx orange, 5xx red) columns make anomalies pop.
- Click a row to open the detail pane below: request and response, each with **Headers / Body / Hex** views.
- The ** Annotations** column marks requests you've flagged.

**Filtering** — the filter bar above the table narrows what's displayed (the underlying history is never deleted):

- Text search across host, path, and full content
- Scope chip — show only in-scope traffic
- File-type filter (documents vs. scripts vs. images…) like you'd expect from any proxy — hide the `.js`/`.png` noise while mapping
- Status and method filters

**Interception** — press **Intercept: On** to hold matching requests before they reach the server. Held requests appear in the intercept panel where you can edit anything, then **Forward** or **Drop**. Tip: combine with a filter or you'll be forwarding every favicon by hand.

**Match & Replace** (Settings → Match & Replace) — automatic rewrites on every passing request or response: strip a header, rewrite a host for testing, force a debug flag on. Rules apply in order, each can be toggled live.

**Context menu** (right-click a row) — the crossroads of the whole app:

| Action | Where it sends the request |
|---|---|
| Send to Repeater | A new Repeater tab, ready to edit |
| Send to Intruder | Intruder with this request preloaded |
| Send to Hpere | The Hpere miner, pre-aimed at this URL |
| Scan this request | A scanner run on this single request |
| AI Analyze | The Assistant with this request attached |
| Render response | Opens the response in a real browser tab — using the *captured* bytes, so bot-blocking that would break a fresh reload doesn't apply |
| Copy URL / Delete | The basics |

**Clearing history** — the trash button in the history toolbar clears captured traffic (after a two-step confirmation; findings are kept, just unlinked).

---

## 3. Target — the map of what you've seen

**Location:** sidebar → Target

Every host and path you've captured, arranged as an expandable tree (host → path). This is your attack surface at a glance.

- **Filter box** and the **scope toggle** narrow the tree while you're mapping.
- Selecting a path loads the captured entries for it in the middle panel — pick one and its full request/response opens in the detail pane below, without leaving the page.
- From the detail pane, **Open in Proxy** jumps to the request in the Proxy history (same detail, plus everything the Proxy view offers); the ✕ closes the panel.

Typical use: browse the whole target once with the browser, then come here to decide what deserves a Repeater session or a scan — the tree count column shows where the application actually lives.

---

## 4. Repeater — one request, edited and replayed

**Location:** sidebar → Repeater

Send any captured request here (Proxy context menu → *Send to Repeater*, or the ✎ button in detail views) and you get:

- A **Monaco editor** (the VS Code engine) with the raw request — edit method, path, headers, body, anything.
- **Send** (Ctrl+Enter) replays it; the response appears in raw / headers / body / hex views.
- Every tab keeps its own **history of sends** — step back through your edits and compare.
- **Search inside the response**: the 🔍 toggle (or Ctrl+F) opens a find bar with match count, Enter/Shift-Enter navigation, and case toggle — the fastest way to find your reflected canary string.
- **Render** opens the response body in a real browser tab (via a blob with a `<base href>` so relative assets resolve) — useful when the response is HTML and you want to see what a browser would actually show.
- **⛏ Hpere** runs the miner directly on the request you're editing.
- **Intruder** hands the current request over with one click.

The Repeater is where most manual testing happens: tweak a parameter, resend, diff the responses, repeat.

---

## 5. Intruder — one request, many payloads

**Location:** sidebar → Intruder

For fuzzing: define positions in a request, give a list of payloads, and PHANTOM fires one request per payload.

1. Send a request here (context menu in Proxy/Repeater/Target, or paste a raw request).
2. Select the text you want to vary and press **Add §** — you can mark multiple positions.
3. Choose the attack type (single sniper or pitchfork-style multi-position) and paste or load a payload list. Simple starters:
   - `../../etc/passwd` traversal set
   - `'><svg/onload=alert(1)>` reflection set
   - admin / administrator / root for IDOR-ish endpoint probing
4. **Start attack.** Results stream into a table with **payload · status · length · time** columns — sort by length or status to spot the response that didn't belong.

Notes: the Intruder is a *manual* tool, so it does not enforce scope (you aimed it, you own it) — but it does run concurrently and you can stop mid-attack. Right-click a result to open it, or send the winning request to the Repeater for a proper follow-up.

---

## 6. Scanner — automated checks on captured traffic

**Location:** sidebar → Scanner

The scanner runs **12 checks** over your chosen target: reflected XSS, SQL injection (error/timeless heuristics), SSRF candidates, open redirect, CORS misconfiguration, missing security headers, cookie flags (Secure/HttpOnly/SameSite), CSRF token presence, JWT issues (alg=none, weak HMAC), hardcoded secrets/API keys (CWE-798), hidden parameters, and verb tampering.

**Running a scan**

1. Pick a **target**: a specific host, an individual captured request, or **"🎯 In scope only"** — which scans every captured host that matches your scope rules and nothing else.
2. **Start scan.** Progress streams live; findings appear as they're confirmed.
3. The engine is **throttled** (concurrency and per-request delay are tunable in Settings → Scanner) and **deduplicated** — the same finding on the same URL/parameter is reported once, not forty times.

**Working findings**

- Filter by severity, check type, and the scope chip; sort by any column.
- Click a finding for the full evidence: the request that triggered it, the response snippet, and the reasoning.
- **AI Triage** sends un-reviewed findings to the Assistant in batches for a first-pass verdict (exploitable? false positive? what to do next?) — verdicts land in the finding detail with a confidence note. Triage respects provider rate limits and never re-tags what's already reviewed.
- **Analyze with Assistant** on a single finding opens a focused chat with the finding attached.
- **⛏ Run Hpere** continues hunting on the finding's URL.
- **🌳 View in Target** jumps to the site map at the finding's location.
- **Export → Report** produces a Markdown or HTML report (severity-filterable) of everything you've found — ready to drop into your write-up.

---

## 7. Plugins — the hunters

**Location:** sidebar → Plugins

Four focused tools. Each takes a starting request (from the Proxy context menu, the Repeater, or the Plugins view itself), runs against your scope, and streams progress as it works. Results land in the runs list with per-item detail and one-click **Repeater** follow-up on anything interesting.

### Hpere — hidden parameter & header miner

The flagship. It looks for parameters and headers the application *understands* but never advertises — the classic gateway to IDOR, debug modes, and access-control bypasses.

- **How it works:** it injects canary values (a random `hp…` marker) into batches of candidate names, compares normalized responses against a stable baseline (noise like timestamps and tokens is stripped), and **bisects** any batch that reacts to pin the exact name. Every hit is re-confirmed with two *fresh* canaries before it's reported — a reflection alone isn't enough.
- **Where it injects:** query strings, form bodies, and JSON bodies (recursively into nested objects).
- **Wordlists:** `fast` (~60 high-yield names, seconds), `smart` (~300), `deep` (~2500, for when you really want the endpoint).
- **Headers too:** ~90 high-impact headers (`X-Forwarded-For`, `X-Original-URL`, debug and internal variants…).

```
fast → start here; smart → for endpoints that matter; deep → for the final push
```

### CORS Hunter

Sends seven origin probes (attacker domain, subdomain spoofs, prefix/suffix look-alikes, `null`, HTTP downgrade, origin echo) and checks what the server reflects into `Access-Control-Allow-Origin` / `Allow-Credentials`. Reported when an arbitrary origin is reflected with credentials allowed — the readable-from-any-site condition.

### Method Probe

Tries OPTIONS, TRACE, PUT, DELETE, PATCH, HEAD, DEBUG, CONNECT against a GET endpoint and reads the answers: TRACE reflection (cross-site tracing), PUT/DELETE/PATCH accepted where only reads should exist, DEBUG leaks, risky methods advertised in `Allow`, and unexpected 5xx behavior.

### Path Probe

Probes ~37 sensitive paths at the site root of your captured URL — `.git/config`, `.env`, backup archives, `/server-status`, Spring actuator, `swagger.json`, phpinfo, and friends. Content markers plus a soft-404 heuristic separate real files from custom error pages; confirmed hits are graded (a readable `.git/config` is high).

> All four plugins require the target to be in scope. They run in the background — start one, keep working, watch the runs list.

---

## 8. Search — everything you've captured

**Location:** sidebar → Search

Full-text search across every request, response body, and finding in the database. For "where did I see that token / that error string / that host again" moments — the answer usually unlocks three other things you were looking for.

## 9. Decoder — transform chains

**Location:** sidebar → Decoder

Paste anything, and the auto-detect guesses what it is. Then chain transforms: Base64 ↔ URL ↔ HTML-entity ↔ hex ↔ unicode ↔ gzip, JWT decode (header/payload/signature split), and instant MD5/SHA-1/SHA-256 hashes. Each step shows its output as the input of the next — decode twice-encoded blobs by just clicking through.

## 10. Assistant — a second opinion in the room

**Location:** sidebar → Assistant

A chat panel that can see what you're working on. Attach a request from the Proxy context menu (*AI Analyze*), a finding from the Scanner, or just ask a question.

What it's good for:

- "Explain what this header does / whether this finding is exploitable"
- "Give me 10 payloads for this parameter" → then **⚡ Send to Intruder** ships the list straight into an attack
- First-pass triage of a batch of findings (the Scanner's **AI Triage** button)

What it is *not*: it doesn't act on its own, and nothing is sent to the provider unless you trigger it. Configure it under Settings → AI with any OpenAI-compatible endpoint (a free Groq key or a local Ollama both work — the README has the two-line setup). If it's unconfigured, every other module is unaffected.

## 11. Dashboard — the state of the session

**Location:** sidebar → Dashboard

Traffic over time, findings by severity, top hosts, detected technologies. Every stat card is clickable and takes you to the module that explains it (requests → Proxy, findings → Scanner, tech → Target).

## 12. Settings

| Section | What you tune |
|---|---|
| **Scope** | Include/exclude rules (subdomain-aware) |
| **Match & Replace** | Automatic request/response rewrites |
| **Scanner** | Concurrency and per-request delay (be a good neighbor) |
| **AI** | Provider (OpenAI-compatible base URL + key, or local Ollama), model, test button |
| **General** | Data location, clear session data |

---

## Keyboard shortcuts

| Shortcut | Where | Action |
|---|---|---|
| `Ctrl+F` | Repeater / response viewers | Find in response |
| `Enter` / `Shift+Enter` | Find bar | Next / previous match |
| `Ctrl+Enter` | Repeater | Send request |

---

## A complete example session (10 minutes)

Here's the whole loop end to end against a lab target — this is the "map" in practice:

1. **Scope** — Settings → Scope → add `*.juice-shop.example` (your own instance).
2. **Proxy** — Start, set the browser proxy, browse the shop: home, login, a product page, the search box.
3. **Target** — expand the tree; the count column shows the search endpoint and login are the live parts.
4. **Repeater** — send the search request over; type `<h1>phantom</h1>` as the query, Send, Ctrl+F for "phantom" — reflected? Adjust and retry.
5. **Hpere** — from that same request, ⛏ Hpere with the `smart` wordlist; a hidden `debug` or `internal` parameter is exactly what it exists to find.
6. **Scanner** — target "🎯 In scope only", Start; watch findings stream. Click through the top two, send one to the Assistant ("how would you exploit this?").
7. **Intruder** — take the Assistant's payload suggestions straight into an attack on the reflected parameter.
8. **Report** — Scanner → Export → HTML report. Done.

## Where things live

| Data | Location |
|---|---|
| Database (history, findings, everything) | `~/.phantom/phantom.db` (SQLite, WAL) |
| CA certificate | Proxy view → download, or `http://127.0.0.1:8899/api/proxy/ca-cert` |
| Logs | Backend console |

To reset everything: stop the backend and delete `~/.phantom`.
