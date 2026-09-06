# 🛠️ PHANTOM

**PHANTOM** is an open-core web application security testing platform — an AI-native alternative to Burp Suite built with Python (FastAPI + mitmproxy) and React (TypeScript + Electron).

> ⚠️ **Authorized testing only.** PHANTOM is intended for use against applications you own or have explicit written permission to test (e.g., your own lab, DVWA, OWASP Juice Shop, or an engagement with a signed scope). Always respect the rules of engagement of any program you test.

## Modules (MVP)

| Module | Purpose |
|---|---|
| **Proxy** | Intercepting HTTP(S) proxy (mitmproxy) with live traffic history, filters, and request/response inspection |
| **Repeater** | Send, edit, and replay captured requests (Monaco editor, tabbed) |
| **Scanner** | Active + passive vulnerability checks (XSS, SQLi, SSRF, CORS, headers, JWT, …) |
| **AI Copilot** | Local-first LLM assistant (Ollama) that analyzes requests, suggests payloads, streams findings |
| **Dashboard** | Traffic, severity, and technology analytics |
| **Decoder** | Chainable encode/decode/hash toolkit (Base64, URL, HTML, Hex, JWT, Gzip, hashes) |

## Status

Project is being built spec-first with [GitHub Spec Kit](https://github.com/github/spec-kit). See [`specs/`](specs/) for the constitution, feature specifications, plans, and task lists.

## License

MIT — see [LICENSE](LICENSE).
