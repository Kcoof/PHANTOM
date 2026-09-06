"""Passive: leaked secret/credential detection (spec 002, FR-002, CWE-798)."""
from __future__ import annotations

import re

from core.scanner_checks.base import body_of
from core.scanner_engine import BaseScanCheck, register_check

MAX_PER_ENTRY = 5

# (label, regex, severity, confidence)
PATTERNS: list[tuple[str, str, str, str]] = [
    ("AWS access key ID", r"\bAKIA[0-9A-Z]{16}\b", "critical", "firm"),
    ("Google API key", r"\bAIza[0-9A-Za-z\-_]{35}\b", "critical", "firm"),
    ("GitHub token", r"\bgh[pousr]_[A-Za-z0-9]{20,255}\b", "critical", "firm"),
    ("Slack token", r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b", "high", "firm"),
    ("Stripe secret key", r"\b[sr]k_live_[0-9a-zA-Z]{16,}\b", "critical", "firm"),
    ("Twilio API key", r"\bSK[0-9a-fA-F]{32}\b", "high", "firm"),
    ("SendGrid API key", r"\bSG\.[A-Za-z0-9\-_]{16,32}\.[A-Za-z0-9\-_]{16,64}\b", "high", "firm"),
    ("Private key block", r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY(?: BLOCK)?-----", "critical", "certain"),
    ("Firebase API key", r"\bAIzaSy[0-9A-Za-z\-_]{33}\b", "high", "firm"),
    (
        "Generic credential assignment",
        r"(?i)\b(api[_-]?key|secret|access[_-]?token|auth[_-]?token|passwd|password)\b['\"]?\s*[:=]\s*['\"][^'\"\s]{12,}['\"]",
        "medium",
        "tentative",
    ),
]

_COMPILED = [(label, re.compile(rx), sev, conf) for label, rx, sev, conf in PATTERNS]

# keys that look like placeholders commonly shipped in client JS
_PLACEHOLDER_RE = re.compile(
    r"(?i)\b(your[_-]?|my[_-]?|example|xxx|placeholder|<[^>]*>|\$\{|\{\{)", )


def detect_secrets(body: str) -> list[dict]:
    """Pure detector shared with tests: returns dicts of label/match/severity/confidence."""
    hits: list[dict] = []
    seen_spans: list[tuple[int, int]] = []
    for label, rx, sev, conf in _COMPILED:
        for m in rx.finditer(body):
            if any(m.start() < e and m.end() > s for s, e in seen_spans):
                continue  # a more specific pattern already claimed this span
            window = body[max(0, m.start() - 60) : m.start()]
            if _PLACEHOLDER_RE.search(window[-45:]):
                continue  # placeholder text directly precedes the match
            seen_spans.append((m.start(), m.end()))
            hits.append({"label": label, "match": m.group(0), "severity": sev, "confidence": conf})
            if len(hits) >= MAX_PER_ENTRY:
                return hits
    return hits


class SecretsCheck(BaseScanCheck):
    name = "Leaked Secrets"
    check_type = "secrets"
    severity = "critical"
    cwe_id = "CWE-798"
    mode = "passive"

    async def check(self, entry: dict) -> list[dict]:
        body = body_of(entry)
        if not body:
            return []
        findings = []
        for hit in detect_secrets(body[:200_000]):
            findings.append(
                self.finding(
                    title=f"Possible {hit['label']} in response",
                    description=(
                        f"A potential {hit['label']} was found in the response body. "
                        "Verify validity out-of-band before reporting; do not use the credential."
                    ),
                    severity=hit["severity"],
                    confidence=hit["confidence"],
                    cwe_id="CWE-798",
                    url=entry["url"],
                    evidence=hit["match"][:120],
                    remediation="Remove credentials from client-visible responses; rotate any exposed keys.",
                )
            )
        return findings


register_check(SecretsCheck())
