"""Match & Replace engine — live traffic rewriting (spec 003, FR-003)."""
from __future__ import annotations

import re

from db import database
from utils.logger import get_logger

log = get_logger(__name__)


async def load_rules() -> list[dict]:
    return await database.fetch_all(
        "SELECT * FROM match_replace_rules WHERE enabled = 1 ORDER BY id"
    )


def _apply_text(text: str, rules: list[dict], location: str) -> tuple[str, list[str]]:
    applied: list[str] = []
    for rule in rules:
        if rule["location"] != location:
            continue
        try:
            if rule["match_type"] == "regex":
                text = re.sub(rule["match_value"], rule["replace_value"], text)
            else:
                text = text.replace(rule["match_value"], rule["replace_value"])
            applied.append(f"#{rule['id']}")
        except re.error:
            log.warning("match&replace rule %s has invalid regex, skipped", rule["id"])
    return text, applied


async def apply_request_rules(method: str, url: str, headers: dict[str, str], body: str | None) -> tuple[dict[str, str], str | None]:
    """Apply request-side rules. Header names/values and body are rewritten;
    a rule matching 'Header: value' text form also works (whole-request view)."""
    rules = await load_rules()
    if not rules:
        return headers, body
    new_headers = {}
    for name, value in headers.items():
        n2, _ = _apply_text(name, rules, "request")
        v2, _ = _apply_text(value, rules, "request")
        new_headers[n2] = v2
    if body:
        body, _ = _apply_text(body, rules, "request")
    return new_headers, body


async def apply_response_rules(status: int, headers: dict[str, str], body: str | None) -> tuple[dict[str, str], str | None]:
    rules = await load_rules()
    if not rules:
        return headers, body
    new_headers = {}
    for name, value in headers.items():
        n2, _ = _apply_text(name, rules, "response")
        v2, _ = _apply_text(value, rules, "response")
        new_headers[n2] = v2
    if body:
        body, _ = _apply_text(body, rules, "response")
    return new_headers, body
