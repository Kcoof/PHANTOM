"""Intruder engine — battering-ram fuzzing with baseline + throttle (spec 003)."""
from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from dataclasses import dataclass

import httpx

from api.websocket import broadcast
from core.scanner_checks.base import configure_throttle
from db import database
from utils.logger import get_logger

log = get_logger(__name__)

POSITION = "§"
MAX_RESULTS = 2000
BODY_CAP = 4096

WORDLISTS: dict[str, list[str]] = {
    "numbers-1-100": [str(i) for i in range(1, 101)],
    "null-values": ["null", "nil", "none", "undefined", "-1", "0", "true", "false", "%00", ""],
    "common-users": ["admin", "administrator", "root", "test", "guest", "user", "api", "system", "support", "demo"],
    "common-paths": [
        "admin", "login", "api", "debug", "config", "backup", ".git", ".env", "test",
        "internal", "private", "old", "new", "dev", "stage", "staging", "v1", "v2",
    ],
    "xss-basic": [
        "<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "\"><svg onload=alert(1)>",
        "'-alert(1)-'", "<iframe src=javascript:alert(1)>", "{{7*7}}", "${7*7}",
    ],
    "sqli-basic": [
        "'", "\"", "' OR 1=1--", "\" OR 1=1--", "1' AND '1'='1", "1 UNION SELECT NULL--",
        "1; DROP TABLE x", "admin'--", "1 ORDER BY 10--", "sleep(5)",
    ],
}


@dataclass
class Attack:
    id: str
    name: str
    raw_template: str
    payloads: list[str]
    grep: list[str]
    task: asyncio.Task | None = None
    stopped: bool = False
    done: int = 0


def split_positions(raw: str) -> tuple[str, list[str]]:
    """`GET /x§a§ HTTP/1.1` -> (template with §§-pairs collapsed, originals).

    Returns the raw with each §x§ reduced to a single placeholder '§' and the
    list of original captured values (for the baseline request).
    """
    positions = re.findall(r"§([^§]*)§", raw)
    template = re.sub(r"§[^§]*§", POSITION, raw)
    return template, positions


def render(template: str, payload: str) -> str:
    return template.replace(POSITION, payload)


class IntruderEngine:
    def __init__(self) -> None:
        self.attacks: dict[str, Attack] = {}

    async def start(
        self,
        raw_request: str,
        payloads: list[str],
        grep_patterns: list[str] | None = None,
        name: str | None = None,
    ) -> str:
        if POSITION not in raw_request:
            raise ValueError("no §positions§ marked in the request — select text and press Add §")
        if not payloads:
            raise ValueError("no payloads provided")
        attack_id = uuid.uuid4().hex[:12]
        template, _ = split_positions(raw_request)
        url_match = re.search(r"^(?:GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+(\S+)", template)
        target = url_match.group(1) if url_match else ""
        await database.execute(
            """INSERT INTO intruder_attacks (id, name, raw_template, payloads, grep_patterns, total, status)
               VALUES (?, ?, ?, ?, ?, ?, 'running')""",
            (
                attack_id,
                name or f"attack {time.strftime('%H:%M:%S')}",
                raw_request,
                json.dumps(payloads[:MAX_RESULTS]),
                json.dumps(grep_patterns or []),
                len(payloads),
            ),
        )
        attack = Attack(
            id=attack_id,
            name=name or "attack",
            raw_template=raw_request,
            payloads=payloads[:MAX_RESULTS],
            grep=[p for p in (grep_patterns or []) if p],
        )
        self.attacks[attack_id] = attack
        # politeness: reuse the scanner throttle settings
        delay = await database.fetch_one("SELECT value FROM settings WHERE key = 'scanner_delay_ms'")
        conc = await database.fetch_one("SELECT value FROM settings WHERE key = 'scanner_concurrency'")
        try:
            configure_throttle(int(conc["value"]) if conc else 4, (int(delay["value"]) if delay else 250) / 1000)
        except (TypeError, ValueError):
            configure_throttle(4, 0.25)
        attack.task = asyncio.create_task(self._run(attack), name=f"intruder-{attack_id}")
        log.info("intruder %s started (%d payloads, target %s)", attack_id, len(attack.payloads), target)
        return attack_id

    def stop(self, attack_id: str) -> None:
        attack = self.attacks.get(attack_id)
        if not attack:
            raise KeyError("attack not running")
        attack.stopped = True

    async def _send(self, raw: str) -> dict:
        from api.repeater_routes import parse_raw_request

        parsed = parse_raw_request(raw, fallback_url=None)
        started = time.monotonic()
        headers = {
            k: v for k, v in parsed.headers.items()
            if k.lower() not in ("host", "content-length", "connection", "accept-encoding")
        }
        from core.scanner_checks.base import send_variant

        resp = await send_variant(
            parsed.method, parsed.url, headers,
            parsed.body.encode("utf-8") if parsed.body else None,
            timeout=20.0,
            enforce_scope=False,  # manual tool: the operator aims the target
        )
        elapsed = int((time.monotonic() - started) * 1000)
        if resp is None:
            return {"status": 0, "length": 0, "time_ms": elapsed, "body": "", "url": parsed.url}
        return {
            "status": resp.status_code,
            "length": len(resp.content),
            "time_ms": elapsed,
            "body": resp.text[:BODY_CAP],
            "url": parsed.url,
        }

    def _grep(self, body: str, patterns: list[str]) -> list[str]:
        matched = []
        for p in patterns:
            try:
                if re.search(p, body):
                    matched.append(p)
            except re.error:
                continue
        return matched

    async def _save_result(self, attack: Attack, idx: int, payload: str, result: dict, is_baseline: bool) -> None:
        await database.execute(
            """INSERT INTO intruder_results
               (attack_id, idx, payload, status, length, time_ms, matched, is_baseline, response_body, url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                attack.id, idx, payload, result["status"], result["length"], result["time_ms"],
                json.dumps(self._grep(result["body"], attack.grep)),
                1 if is_baseline else 0,
                result["body"], result["url"],
            ),
        )
        await broadcast(
            "intruder_result",
            {
                "attack_id": attack.id, "idx": idx, "payload": payload,
                "status": result["status"], "length": result["length"],
                "time_ms": result["time_ms"], "is_baseline": is_baseline,
                "url": result["url"],
            },
        )

    async def _run(self, attack: Attack) -> None:
        template, originals = split_positions(attack.raw_template)
        status = "completed"
        try:
            # baseline: original captured values
            baseline_raw = template
            for original in originals:
                baseline_raw = baseline_raw.replace(POSITION, original, 1)
            baseline = await self._send(baseline_raw)
            await self._save_result(attack, -1, "(original)", baseline, True)
            await database.execute(
                "UPDATE intruder_attacks SET baseline_status = ?, baseline_length = ? WHERE id = ?",
                (baseline["status"], baseline["length"], attack.id),
            )
            for i, payload in enumerate(attack.payloads):
                if attack.stopped:
                    status = "stopped"
                    break
                result = await self._send(render(template, payload))
                await self._save_result(attack, i, payload, result, False)
                attack.done += 1
                await database.execute(
                    "UPDATE intruder_attacks SET done = ? WHERE id = ?", (attack.done, attack.id)
                )
                await broadcast(
                    "intruder_progress",
                    {"attack_id": attack.id, "done": attack.done, "total": len(attack.payloads)},
                )
        except Exception:
            log.exception("intruder %s crashed", attack.id)
            status = "failed"
        await database.execute(
            "UPDATE intruder_attacks SET status = ? WHERE id = ?", (status, attack.id)
        )
        await broadcast(
            "intruder_progress",
            {"attack_id": attack.id, "done": attack.done, "total": len(attack.payloads), "status": status},
        )
        self.attacks.pop(attack.id, None)


_engine = IntruderEngine()


def get_intruder_engine() -> IntruderEngine:
    return _engine
