<!--
Sync Impact Report
- Version change: (none) → 1.0.0
- Modified principles: N/A (initial ratification)
- Added sections: Core Principles (I–VII), Security & Ethical Constraints, Development Workflow & Quality Gates, Governance
- Removed sections: none
- Follow-up TODOs: none
-->

# PHANTOM Constitution

## Core Principles

### I. Authorized Testing Only (NON-NEGOTIABLE)

PHANTOM is a professional security testing tool for use exclusively against systems the operator
owns or has explicit written authorization to test (own lab, DVWA/Juice Shop, or a signed
engagement scope). Active scanning MUST be opt-in, scoped, and clearly labeled. The README and
application surfaces MUST communicate this restriction. Features MUST NOT be added whose primary
purpose is mass targeting, stealth/evasion against defenders, or bypassing authorization controls.

### II. Proxy-First Reliability

The intercepting proxy engine is the heart of the platform. If the proxy does not work flawlessly,
nothing else matters. Any change that risks proxy correctness (traffic capture fidelity, TLS
interception, intercept/drop/forward semantics, history persistence) MUST be validated
end-to-end before merging. Proxy regressions block releases outright.

### III. Real-Time by Default

The UI MUST reflect proxy traffic, intercept queue state, scan progress, and AI responses in real
time. Live updates MUST use the WebSocket event stream; polling MUST NOT be introduced as a
substitute. AI Copilot responses MUST stream token-by-token (SSE or WebSocket), never appear as
a single blocking wait.

### IV. Premium Dark UI

The application MUST use the dark theme and the exact design tokens defined in the design system
(no plain white backgrounds). HTTP methods MUST be color-coded (GET green, POST purple, PUT
yellow, DELETE red, PATCH pink) and status codes color-coded (2xx green, 3xx blue, 4xx yellow,
5xx red). Technical data (requests, responses, code) MUST render in a monospace font (JetBrains
Mono); UI text uses Inter. Request editing MUST use Monaco Editor — plain textareas are not
acceptable. Request/response panels MUST be resizable split panes. Micro-animations (hover,
transitions, row highlights, loading skeletons) are required; the bar is "VS Code, not Notepad".

### V. Never Fail Silently

Every API call and background operation MUST handle errors and surface them to the user (toast
notifications or inline status). Backend operations MUST log with structured logging. Optional
integrations (e.g., the local LLM runtime) MUST degrade gracefully with a visible status
indicator rather than breaking the workflow.

### VI. Incremental Delivery with Stepwise Verification

Features are built in dependency order (foundation → proxy → UI modules → integrations → shell).
Each increment MUST be tested before the next begins; "build five features, then test" is
forbidden. Each verified increment is a commit. Scope of a session may end at any checkpoint
without leaving the tree broken.

### VII. Local-First by Default

All captured data stays local (embedded SQLite database on the user's machine). AI features
default to a local LLM runtime (Ollama); no cloud dependency is required for any core module.
No telemetry or traffic leaves the operator's machine without explicit opt-in.

## Security & Ethical Constraints

- The tool's own attack surface matters: the backend binds to localhost by default; remote
  bindings require explicit operator action.
- TLS interception uses a locally generated CA; the CA private key MUST stay on the operator's
  machine and never be committed to the repository.
- Scanner findings are advisory; findings MUST carry severity, confidence, and evidence, and
  MUST be markable as false positives.
- Dependencies MUST be pinned with minimum versions and kept auditable.

## Development Workflow & Quality Gates

- **Build order**: follow the dependency-ordered task list in `specs/`; do not skip ahead.
- **Per-step verification**: each step's quickstart/checkpoint must pass before moving on.
- **Commits**: one commit per verified increment; the tree MUST remain green at every checkpoint.
- **Testing**: integration tests for API endpoints; manual end-to-end proxy tests via a real
  client (e.g., curl through the proxy) at each proxy-touching change.
- **Cross-platform**: features MUST work on Windows, macOS, and Linux; scripts avoid
  platform-only constructs or ship per-platform variants.
- **Spec compliance**: implementation MUST stay reconcilable with the active spec/plan/tasks;
  drift is resolved by updating specs first, then code.

## Governance

- This constitution supersedes all other practices when conflicts arise.
- Amendments require: documented rationale, a version bump following semantic versioning
  (MAJOR for removals/redefinitions, MINOR for additions, PATCH for clarifications), and an
  updated Sync Impact Report at the top of this file.
- All reviews MUST verify constitution compliance, notably Principles I, II, and V.
- Runtime development guidance lives in `specs/<feature>/plan.md` and `tasks.md`.

**Version**: 1.0.0 | **Ratified**: 2026-09-06 | **Last Amended**: 2026-09-06
