"""Parameter Miner — hidden-parameter discovery (spec 005, Arjun/Param-Miner style).

Batched canary probing + bisection: candidates are probed ~25 at a time with
unique canary values; a batch whose response reflects a canary or deviates
from baseline is bisected to isolate parameters, each confirmed twice alone.
"""
from __future__ import annotations

import random
import string
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from core.plugin_framework import PhantomPlugin, register, resolve_request_context
from core.scanner_checks.base import send_variant
from db import database
from utils.helpers import url_in_scope
from utils.logger import get_logger

log = get_logger(__name__)

WORDLISTS: dict[str, list[str]] = {
    "common-150": [
        "id", "user", "admin", "debug", "test", "dev", "internal", "private",
        "redirect", "url", "next", "return", "returnurl", "goto", "continue", "dest",
        "destination", "target", "r", "link", "site", "source", "callback", "redirect_uri",
        "format", "output", "render", "template", "view", "display", "theme", "layout",
        "lang", "locale", "country", "currency", "page", "size", "limit", "offset", "per_page",
        "sort", "order", "filter", "q", "query", "search", "term", "type", "kind", "category",
        "action", "cmd", "exec", "run", "command", "do", "task", "job", "file", "path", "dir",
        "doc", "document", "download", "load", "fetch", "include", "require", "import",
        "token", "key", "secret", "apikey", "api_key", "access_key", "auth", "session",
        "csrf", "state", "nonce", "code", "access_token", "refresh_token", "client_id",
        "client_secret", "grant_type", "response_type", "scope", "audience", "prompt",
        "v", "version", "ver", "env", "environment", "mode", "profile", "role", "group",
        "permission", "privilege", "level", "status", "state_id", "active", "enabled",
        "hidden", "visible", "public", "preview", "draft", "publish", "archive", "backup",
        "old", "new", "copy", "clone", "restore", "export", "import_data", "sync", "migrate",
        "user_id", "userid", "uid", "account", "account_id", "owner", "owner_id", "author",
        "email", "mail", "username", "login", "password", "pass", "pin", "otp", "mfa",
        "price", "amount", "total", "discount", "coupon", "voucher", "promo", "tax",
        "currency_code", "quantity", "qty", "stock", "sku", "product_id", "item_id",
        "order_id", "order", "cart", "checkout", "payment", "invoice", "receipt",
        "reference", "ref", "tracking", "shipment", "delivery", "address", "zip", "phone",
        "first_name", "last_name", "name", "nickname", "display_name", "avatar", "photo",
        "image", "picture", "media", "attachment", "upload", "filename", "extension",
        "mime", "content_type", "charset", "encoding", "compress", "gzip", "plain",
        "json", "xml", "html", "text", "binary", "raw", "stream", "download_url",
        "callback_url", "webhook", "webhook_url", "notify", "notification", "alert",
        "subscribe", "unsubscribe", "optin", "consent", "terms", "policy", "agree",
        "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "referral",
    ],
    "shallow-60": [
        "admin", "debug", "test", "internal", "private", "dev", "hidden", "secret",
        "user_id", "account_id", "owner_id", "debug_flag", "trace", "verbose", "log",
        "simulate", "dry_run", "mock", "fake", "bypass", "skip", "ignore", "force",
        "override", "inject", "exec", "cmd", "command", "run", "action", "method",
        "format", "template", "render", "theme", "view", "layout", "preview", "draft",
        "redirect", "next", "url", "return", "goto", "continue", "callback", "hook",
        "token", "key", "api_key", "access_key", "auth", "role", "permission", "level",
        "page", "limit", "offset", "filter", "sort", "lang", "currency", "price",
    ],
}


def _canary(prefix: str) -> str:
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}{rand}"


class ParamMinerPlugin(PhantomPlugin):
    id = "param-miner"
    name = "Parameter Miner"
    description = (
        "Discover hidden parameters a request silently accepts via batched canary "
        "probing (reflection + behavior detection). Found parameters become findings."
    )
    accepts = ["request"]
    parameters = [
        {"key": "wordlist", "type": "select", "options": list(WORDLISTS), "default": "common-150"},
        {"key": "batch_size", "type": "number", "default": 25},
    ]

    async def run(self, context: dict, options: dict, emit) -> None:
        from core.plugin_framework import get_plugin_engine

        engine = get_plugin_engine()
        req = await resolve_request_context(context)
        url, method = req["url"], req["method"]
        if not await url_in_scope(url):
            raise RuntimeError(f"target out of scope: {url} — add an include rule in Settings → Scope")

        names = WORDLISTS.get(options.get("wordlist", "common-150"), WORDLISTS["common-150"])
        batch_size = max(5, min(int(options.get("batch_size", 25)), 50))
        base_headers = {k: v for k, v in req["headers"].items()
                        if k.lower() not in ("host", "content-length", "connection", "accept-encoding")}
        body = req.get("body") if "urlencoded" in req["headers"].get("content-type", "").lower() else None

        # canary per candidate, stable for the run
        canaries = {n: _canary("pmt") for n in names}
        baseline = await self._send(method, url, base_headers, body)
        if baseline is None:
            raise RuntimeError(f"baseline request failed: {method} {url}")
        base_sig = (baseline["status"], len(baseline["body"]))
        await emit("info", {"message": f"baseline {base_sig[0]} / {base_sig[1]}B — probing {len(names)} candidates"})

        done = 0
        total = len(names)
        confirmed: dict[str, dict] = {}

        for i in range(0, total, batch_size):
            if engine.is_stopped(context.get("_run_id", "")):
                return
            batch = names[i : i + batch_size]
            resp = await self._send(method, url, base_headers, body, extra_params={n: canaries[n] for n in batch})
            done += len(batch)
            if resp is None:
                await emit("progress", {"done": done, "total": total})
                continue
            if self._detect(resp, canaries, batch) or self._deviates(resp, base_sig):
                for hit in await self._bisect(method, url, base_headers, body, batch, canaries, base_sig):
                    if hit["name"] not in confirmed:
                        confirmed[hit["name"]] = hit
                        await self._report(url, hit, emit)
            await emit("progress", {"done": done, "total": total})

        await emit(
            "summary",
            {"found": len(confirmed), "probed": total, "names": sorted(confirmed)},
        )

    # --- helpers ------------------------------------------------------------

    async def _send(self, method, url, headers, body, extra_params: dict | None = None):
        if extra_params:
            parts = urlsplit(url)
            q = dict(parse_qsl(parts.query, keep_blank_values=True))
            q.update(extra_params)
            url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))
            if body is not None and method not in ("GET", "HEAD"):
                body_pairs = dict(parse_qsl(body or "", keep_blank_values=True))
                body_pairs.update(extra_params)
                body = urlencode(body_pairs)
        content = body.encode("utf-8") if body else None
        resp = await send_variant(method, url, headers, content, timeout=15.0)
        if resp is None:
            return None
        return {"status": resp.status_code, "body": resp.text, "length": len(resp.content)}

    def _detect(self, resp, canaries, batch) -> str | None:
        """Return the reflected canary if any batch canary appears in the response."""
        for n in batch:
            if canaries[n] in resp["body"]:
                return n
        return None

    def _deviates(self, resp, base_sig) -> bool:
        return resp["status"] != base_sig[0] or abs(resp["length"] - base_sig[1]) > 30

    async def _probe_single(self, method, url, headers, body, name, canary, base_sig):
        resp = await self._send(method, url, headers, body, extra_params={name: canary})
        if resp is None:
            return None
        via = "reflection" if canary in resp["body"] else (
            "behavior" if self._deviates(resp, base_sig) else None
        )
        if not via:
            return None
        return {
            "name": name,
            "via": via,
            "evidence": (
                f"canary {canary} reflected in response"
                if via == "reflection"
                else f"status/length changed {base_sig[0]}/{base_sig[1]}B -> {resp['status']}/{resp['length']}B"
            ),
            "status": resp["status"],
            "length": resp["length"],
            "delta": resp["length"] - base_sig[1],
        }

    async def _bisect(self, method, url, headers, body, batch, canaries, base_sig) -> list[dict]:
        """Isolate live parameters inside a reacting batch, confirm each twice."""
        live: list[dict] = []
        stack = [batch]
        while stack:
            group = stack.pop()
            if len(group) == 1:
                name = group[0]
                hits = [
                    await self._probe_single(method, url, headers, body, name, canaries[name], base_sig)
                    for _ in range(2)
                ]
                if hits[0] and hits[1]:
                    live.append(hits[0])
                continue
            resp = await self._send(method, url, headers, body, extra_params={n: canaries[n] for n in group})
            if resp is None:
                continue
            if self._detect(resp, canaries, group) or self._deviates(resp, base_sig):
                mid = len(group) // 2
                stack.append(group[:mid])
                stack.append(group[mid:])
        return live

    async def _report(self, url: str, hit: dict, emit) -> None:
        await emit(
            "param",
            {
                "name": hit["name"],
                "detected_via": hit["via"],
                "evidence": hit["evidence"],
                "status": hit["status"],
                "delta": hit["delta"],
                "url": url,
            },
        )
        # also a finding so it flows into dedupe/triage/report
        existing = await database.fetch_one(
            "SELECT id FROM scanner_findings WHERE finding_type = ? AND url = ? AND parameter IS ?",
            ("hidden_param", url, hit["name"]),
        )
        if existing:
            return
        await database.execute(
            """INSERT INTO scanner_findings
               (scan_id, finding_type, severity, confidence, title, description, url,
                parameter, evidence, remediation, cwe_id)
               VALUES ('plugin', ?, ?, 'firm', ?, ?, ?, ?, ?, ?, ?)""",
            (
                "hidden_param",
                "low" if hit["via"] == "reflection" else "info",
                f"Hidden parameter '{hit['name']}'",
                f"The endpoint silently accepts a '{hit['name']}' parameter ({hit['evidence']}). "
                "Hidden parameters often unlock debug behavior, IDOR, or bypass logic.",
                url,
                hit["name"],
                hit["evidence"],
                "Remove or strictly validate undocumented parameters; watch this one for abuse.",
                None,
            ),
        )


register(ParamMinerPlugin())
