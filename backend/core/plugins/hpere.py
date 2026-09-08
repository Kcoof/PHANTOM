"""Hpere — advanced hidden parameter & header miner (spec 005 upgrade).

Stronger than Arjun + Burp Param Miner by combining:
- deep generated wordlists (fast-60 / smart-300 / deep-2500)
- multi-location injection: query, urlencoded body, JSON body
- stable-baseline normalized diffing (3 baselines; dynamic content
  [timestamps, nonces, long ids] normalized away before comparison)
- header mining phase (~80 high-impact hidden headers)
- bisection + fresh-canary double confirmation (kills coincidental matches)
"""
from __future__ import annotations

import hashlib
import json as jsonlib
import random
import re
import string
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from core.plugin_framework import PhantomPlugin, register, resolve_request_context
from core.scanner_checks.base import send_variant
from db import database
from utils.helpers import url_in_scope
from utils.logger import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------- wordlists

_SEED = [
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
    "permission", "privilege", "level", "status", "active", "enabled", "disabled",
    "hidden", "visible", "public", "preview", "draft", "publish", "archive", "backup",
    "old", "new", "copy", "clone", "restore", "export", "sync", "migrate", "seed",
    "user_id", "userid", "uid", "account", "account_id", "owner", "owner_id", "author",
    "email", "mail", "username", "login", "password", "pass", "pin", "otp", "mfa",
    "price", "amount", "total", "discount", "coupon", "voucher", "promo", "tax",
    "quantity", "qty", "stock", "sku", "product_id", "item_id", "variant_id",
    "order_id", "order", "cart", "checkout", "payment", "invoice", "receipt",
    "reference", "ref", "tracking", "shipment", "delivery", "address", "zip", "phone",
    "first_name", "last_name", "name", "nickname", "display_name", "avatar", "photo",
    "image", "picture", "media", "attachment", "upload", "filename", "extension",
    "mime", "content_type", "charset", "encoding", "compress", "gzip", "plain",
    "json", "xml", "html", "text", "binary", "raw", "stream", "download_url",
    "callback_url", "webhook", "webhook_url", "notify", "notification", "alert",
    "subscribe", "unsubscribe", "optin", "consent", "terms", "policy", "agree",
    "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "referral",
    "channel", "platform", "device", "app", "application", "client", "service",
    "instance", "node", "server", "host", "port", "protocol", "scheme", "domain",
    "subdomain", "tenant", "organization", "org", "company", "workspace", "project",
    "team", "member", "invite", "invitation", "collaborator", "share", "permission_id",
    "flag", "feature", "features", "toggle", "switch", "config", "configuration",
    "setting", "settings", "option", "options", "preference", "preferences",
    "experimental", "beta", "alpha", "stable", "canary", "release", "sandbox",
    "simulate", "mock", "fake", "dummy", "sample", "example", "template_id",
    "bypass", "skip", "ignore", "force", "override", "inject", "method", "rewrite",
    "proxy", "forward", "mirror", "origin", "referer", "referrer", "base", "root",
    "index", "alias", "slug", "permalink", "route", "endpoint", "controller",
    "module", "plugin", "extension", "widget", "component", "block", "section",
    "menu", "navigation", "sidebar", "header", "footer", "banner", "popup", "modal",
    "wizard", "step", "stage", "phase", "iteration", "revision", "history", "audit",
    "log", "verbose", "trace", "metrics", "stats", "analytics", "report", "dashboard",
    "graph", "chart", "table", "grid", "list", "feed", "timeline", "calendar",
    "date", "time", "start", "end", "from", "to", "since", "until", "timezone",
    "duration", "interval", "frequency", "repeat", "recurring", "cron", "schedule",
    "priority", "weight", "score", "rank", "rating", "vote", "poll", "survey",
    "comment", "review", "feedback", "rating_id", "message", "body", "content",
    "title", "subject", "description", "summary", "caption", "label", "tag", "tags",
    "keyword", "keywords", "meta", "metadata", "attribute", "attributes", "property",
    "fields", "values", "data", "payload", "context", "session_id", "request_id",
    "correlation_id", "trace_id", "span_id", "parent_id", "transaction", "batch",
    "bulk", "chunk", "cursor", "token_id", "key_id", "cert", "certificate",
    "signature", "digest", "hash", "checksum", "encrypt", "decrypt", "cipher",
    "salt", "iv", "nonce_id", "otp_code", "recovery", "reset", "forgot", "verify",
    "validate", "confirmation", "approve", "reject", "pending", "queued", "processed",
    "complete", "finished", "done", "success", "error", "warning", "critical",
    "retry", "timeout", "cancel", "abort", "rollback", "commit", "branch", "merge",
    "conflict", "duplicate", "unique", "primary", "foreign", "join", "union",
    "select", "insert", "update", "delete", "truncate", "drop", "alter", "create",
]

_SUFFIX = ["", "_id", "_url", "_key", "_name", "_type", "_value", "_code", "_token", "_flag", "_mode", "_param"]
_PREFIX = ["", "is_", "has_", "enable_", "disable_", "get_", "set_", "show_", "hide_", "x_"]

def _gen(curated: list[str], suffixes: bool, prefixes: bool) -> list[str]:
    out = list(curated)
    if suffixes:
        out += [f"{w}{s}" for w in curated for s in _SUFFIX if s]
    if prefixes:
        out += [f"{p}{w}" for w in curated for p in _PREFIX if p]
    return sorted(set(out))

WORDLISTS: dict[str, list[str]] = {
    "fast-60": [
        "admin", "debug", "test", "internal", "private", "dev", "hidden", "secret",
        "user_id", "account_id", "owner_id", "debug_flag", "trace", "verbose", "log",
        "simulate", "dry_run", "mock", "fake", "bypass", "skip", "ignore", "force",
        "override", "inject", "exec", "cmd", "command", "run", "action", "method",
        "format", "template", "render", "theme", "view", "layout", "preview", "draft",
        "redirect", "next", "url", "return", "goto", "continue", "callback", "hook",
        "token", "key", "api_key", "access_key", "auth", "role", "permission", "level",
        "page", "limit", "offset", "filter", "sort", "lang", "currency", "price",
    ],
    "smart-300": _gen(_SEED[:150], suffixes=True, prefixes=False),
    "deep-2500": _gen(_SEED, suffixes=True, prefixes=True)[:2500],
}

# high-impact hidden headers (cache poisoning, auth bypass, rewrite tricks)
HEADER_LIST = [
    "X-Forwarded-For", "X-Forwarded-Host", "X-Forwarded-Server", "X-Forwarded-Proto",
    "X-Forwarded-Port", "X-Forwarded-Scheme", "X-Forwarded-Protocol", "X-Forwarded-Uri",
    "X-Original-URL", "X-Rewrite-URL", "X-Original-Remote-Addr", "X-Original-Host",
    "X-Real-IP", "X-Client-IP", "X-Host", "X-Server-IP", "True-Client-IP",
    "CF-Connecting-IP", "Fastly-Client-IP", "X-Remote-Addr", "X-Remote-IP",
    "X-Originating-IP", "Forwarded", "Client-IP", "X-URL", "X-Request-URL",
    "Destination", "X-Host-Override", "X-Backend-Server", "X-Proxy", "Via",
    "X-HTTP-Method-Override", "X-HTTP-Method", "X-Method-Override", "X-Override-Method",
    "X-HTTP-Method-Override", "X-Localhost", "X-Internal", "X-Internal-Client",
    "X-Debug", "Debug", "X-Debug-Mode", "X-Disable-Cache", "X-No-Cache",
    "X-Bypass-Cache", "X-Cache", "X-Cacheable", "X-Cache-Control", "X-Varnish",
    "X-Purge-Cache", "X-Admin", "X-Admin-Token", "X-Auth-Token", "X-Api-Key",
    "X-Auth", "X-User", "X-User-Id", "X-Username", "X-Role", "X-Permissions",
    "X-Access-Level", "X-Tenant", "X-Tenant-Id", "X-Org", "X-Organization",
    "X-Account", "X-Account-Id", "X-Env", "X-Environment", "X-Stage",
    "X-Feature-Flags", "X-Flags", "X-Mock", "X-Test", "X-Sandbox", "X-Beta",
    "X-Load-Balancer", "X-Cluster", "X-Region", "X-Zone", "X-Country",
    "X-Lang", "X-Locale", "X-Currency", "X-Timezone", "X-Theme", "X-Template",
    "X-Client", "X-App", "X-Application", "X-Device", "X-Platform", "X-Version",
    "X-Internal-Secret", "X-Site", "X-Site-Id", "X-Shop", "X-Store", "X-Store-Id",
]


def _canary() -> str:
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"hp{rand}"


_DYNAMIC_RE = [
    re.compile(r"\d{10,}"),                      # timestamps
    re.compile(r"\b[0-9a-f]{12,}\b", re.I),      # uuid/hex ids
    re.compile(r"hp[0-9a-z]{8}"),                # our own canaries
    re.compile(r"[A-Za-z0-9+/=_-]{32,}"),        # tokens/hashes
    re.compile(r"\d+"),                          # any numbers (counts, ids)
]


def _normalize(text: str) -> str:
    for rx in _DYNAMIC_RE:
        text = rx.sub("N", text)
    text = re.sub(r"\s+", " ", text)
    return hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest()


class HperePlugin(PhantomPlugin):
    id = "hpere"
    name = "Hpere"
    description = (
        "Advanced hidden parameter & header miner — deep wordlists, query/body/JSON "
        "injection, stable-baseline normalized diffing, and hidden-header probing "
        "(cache poisoning / auth bypass candidates). Stronger than Arjun + Param Miner."
    )
    accepts = ["request"]
    parameters = [
        {"key": "wordlist", "type": "select", "options": list(WORDLISTS), "default": "smart-300"},
        {"key": "mine", "type": "select", "options": ["params+headers", "params", "headers"], "default": "params+headers"},
        {"key": "batch_size", "type": "number", "default": 25},
    ]

    # ---------------------------------------------------------------- run

    async def run(self, context: dict, options: dict, emit) -> None:
        from core.plugin_framework import get_plugin_engine

        engine = get_plugin_engine()
        req = await resolve_request_context(context)
        url, method = req["url"], req["method"]
        if not await url_in_scope(url):
            raise RuntimeError(f"target out of scope: {url} — add an include rule in Settings → Scope")

        base_headers = {k: v for k, v in req["headers"].items()
                        if k.lower() not in ("host", "content-length", "connection", "accept-encoding")}
        ct = req["headers"].get("content-type", "")
        raw_body = req.get("body") or ""
        body_kind = "json" if "json" in ct or raw_body.strip().startswith("{") else (
            "form" if "urlencoded" in ct else None
        )

        # stable baseline: 3 samples decide whether normalized diffing is trustworthy
        baselines = [await self._send(method, url, base_headers, raw_body, None) for _ in range(3)]
        if all(b is None for b in baselines):
            raise RuntimeError(f"baseline request failed: {method} {url}")
        good = [b for b in baselines if b]
        base_norms = {_normalize(b["body"]) for b in good}
        stable = len(base_norms) == 1
        base = good[0]
        base_sig = (base["status"], base["length"])
        await emit(
            "info",
            {"message": f"baseline {base_sig[0]}/{base_sig[1]}B · stable={stable} · history #{context.get('history_id')}",
             "history_id": context.get("history_id")},
        )

        mine = options.get("mine", "params+headers")
        names = WORDLISTS.get(options.get("wordlist", "smart-300"), WORDLISTS["smart-300"])
        batch_size = max(5, min(int(options.get("batch_size", 25)), 50))

        if mine in ("params+headers", "params"):
            await self._mine_params(engine, emit, method, url, base_headers, raw_body, body_kind,
                                    names, batch_size, base, base_sig, stable, context)
        if mine in ("params+headers", "headers"):
            await self._mine_headers(engine, emit, method, url, base_headers, raw_body, base, base_sig, stable, context)

        await emit("summary", {"done": True, "names": None})

    # ---------------------------------------------------------- parameters

    async def _mine_params(self, engine, emit, method, url, base_headers, raw_body, body_kind,
                           names, batch_size, base, base_sig, stable, context):
        canaries = {n: _canary() for n in names}
        done = confirmed = 0
        for i in range(0, len(names), batch_size):
            if engine.is_stopped(context.get("_run_id", "")):
                return
            batch = names[i : i + batch_size]
            resp = await self._send(method, url, base_headers, raw_body, ("params", {n: canaries[n] for n in batch}), body_kind)
            done += len(batch)
            if resp and self._reacts(resp, canaries, batch, base, stable):
                for hit in await self._bisect(method, url, base_headers, raw_body, body_kind, batch, canaries, base, stable):
                    await self._report(emit, url, hit, kind="param")
                    confirmed += 1
            await emit("progress", {"done": done, "total": len(names) + len(HEADER_LIST)})
        if confirmed:
            await emit("info", {"message": f"parameters: {confirmed} confirmed"})

    # ---------------------------------------------------------- headers

    async def _mine_headers(self, engine, emit, method, url, base_headers, raw_body, base, base_sig, stable, context):
        canaries = {h: _canary() for h in HEADER_LIST}
        confirmed = 0
        for i in range(0, len(HEADER_LIST), 15):
            if engine.is_stopped(context.get("_run_id", "")):
                return
            batch = HEADER_LIST[i : i + 15]
            resp = await self._send(method, url, base_headers, raw_body, ("headers", {h: canaries[h] for h in batch}))
            if resp and self._reacts(resp, canaries, batch, base, stable):
                for hit in await self._bisect_h(method, url, base_headers, raw_body, batch, canaries, base, stable):
                    await self._report(emit, url, hit, kind="header")
                    confirmed += 1
            await emit("progress", {"done": i + len(batch), "total": len(HEADER_LIST) + len(WORDLISTS["fast-60"])})
        if confirmed:
            await emit("info", {"message": f"headers: {confirmed} confirmed"})

    # ---------------------------------------------------------- detection

    def _reacts(self, resp, canaries, batch, base, stable) -> bool:
        if any(c in resp["body"] for c in (canaries[n] for n in batch)):
            return True
        if resp["status"] != base["status"]:
            return True
        if not stable:
            return abs(resp["length"] - base["length"]) > 60  # strict on dynamic pages
        return _normalize(resp["body"]) != _normalize(base["body"]) or abs(resp["length"] - base["length"]) > 30

    def _classify(self, resp, canary, base, stable) -> tuple[str, str] | None:
        if canary in resp["body"]:
            return "reflection", f"canary {canary} reflected in response"
        if resp["status"] != base["status"] or abs(resp["length"] - base["length"]) > (60 if not stable else 30):
            return "behavior", f"status/length changed {base['status']}/{base['length']}B -> {resp['status']}/{resp['length']}B"
        if stable and _normalize(resp["body"]) != _normalize(base["body"]):
            return "subtle-diff", f"normalized response content differs (same size class)"
        return None

    async def _confirm(self, method, url, base_headers, raw_body, body_kind, name, base, stable, mode):
        """Two independent confirmations with FRESH canaries each time."""
        hits = []
        for _ in range(2):
            canary = _canary()
            payload = {name: canary}
            resp = await self._send(method, url, base_headers, raw_body, (mode, payload), body_kind)
            if resp is None:
                return None
            verdict = self._classify(resp, canary, base, stable)
            if not verdict:
                return None
            hits.append((verdict[0], f"{verdict[1]} (canary {canary})"))
        return hits[0][0], hits[0][1]

    async def _bisect(self, method, url, base_headers, raw_body, body_kind, batch, canaries, base, stable):
        live = []
        stack = [batch]
        while stack:
            group = stack.pop()
            resp = await self._send(method, url, base_headers, raw_body, ("params", {n: canaries[n] for n in group}), body_kind)
            if resp is None:
                continue
            if not self._reacts(resp, canaries, group, base, stable):
                continue
            if len(group) == 1:
                confirmed = await self._confirm(method, url, base_headers, raw_body, body_kind, group[0], base, stable, "params")
                if confirmed:
                    live.append({"name": group[0], "via": confirmed[0], "evidence": confirmed[1], "location": "query/body"})
                continue
            mid = len(group) // 2
            stack.append(group[:mid])
            stack.append(group[mid:])
        return live

    async def _bisect_h(self, method, url, base_headers, raw_body, batch, canaries, base, stable):
        live = []
        stack = [batch]
        while stack:
            group = stack.pop()
            resp = await self._send(method, url, base_headers, raw_body, ("headers", {n: canaries[n] for n in group}))
            if resp is None:
                continue
            if not self._reacts(resp, canaries, group, base, stable):
                continue
            if len(group) == 1:
                confirmed = await self._confirm(method, url, base_headers, raw_body, None, group[0], base, stable, "headers")
                if confirmed:
                    live.append({"name": group[0], "via": confirmed[0], "evidence": confirmed[1], "location": "header"})
                continue
            mid = len(group) // 2
            stack.append(group[:mid])
            stack.append(group[mid:])
        return live

    # ---------------------------------------------------------- transport

    async def _send(self, method, url, headers, raw_body, inject, body_kind=None):
        params = headers_in = None
        if inject:
            mode, payload = inject
            params = payload if mode == "params" else None
            headers_in = payload if mode == "headers" else None
        body = raw_body
        if params:
            parts = urlsplit(url)
            q = dict(parse_qsl(parts.query, keep_blank_values=True))
            q.update(params)
            url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))
            if body_kind == "form" and method not in ("GET", "HEAD"):
                body_pairs = dict(parse_qsl(raw_body or "", keep_blank_values=True))
                body_pairs.update(params)
                body = urlencode(body_pairs)
            elif body_kind == "json" and method not in ("GET", "HEAD"):
                try:
                    obj = jsonlib.loads(raw_body) if raw_body.strip() else {}
                    if isinstance(obj, dict):
                        obj.update(params)
                        body = jsonlib.dumps(obj)
                except jsonlib.JSONDecodeError:
                    pass
        if headers_in:
            headers = {**headers, **headers_in}
        content = body.encode("utf-8") if body else None
        resp = await send_variant(method, url, headers, content, timeout=15.0)
        if resp is None:
            return None
        return {"status": resp.status_code, "body": resp.text, "length": len(resp.content)}

    # ---------------------------------------------------------- reporting

    async def _report(self, emit, url: str, hit: dict, kind: str) -> None:
        key = "hidden_param" if kind == "param" else "hidden_header"
        await emit(kind, {**hit, "detected_via": hit["via"], "url": url})
        existing = await database.fetch_one(
            "SELECT id FROM scanner_findings WHERE finding_type = ? AND url = ? AND parameter IS ?",
            (key, url, hit["name"]),
        )
        if existing:
            return
        sev = "medium" if kind == "header" or hit["via"] == "reflection" else "info"
        await database.execute(
            """INSERT INTO scanner_findings
               (scan_id, finding_type, severity, confidence, title, description, url,
                parameter, evidence, remediation)
               VALUES ('plugin', ?, ?, 'firm', ?, ?, ?, ?, ?, ?)""",
            (
                key,
                sev,
                f"Hidden {'header' if kind == 'header' else 'parameter'} '{hit['name']}'",
                f"The endpoint reacts to an undocumented {'header' if kind == 'header' else 'parameter'} "
                f"'{hit['name']}' ({hit['evidence']}). Hidden inputs often unlock debug behavior, "
                "bypass logic, or cache poisoning.",
                url,
                hit["name"],
                hit["evidence"],
                "Remove or strictly validate undocumented inputs; assess abuse potential manually.",
            ),
        )


register(HperePlugin())
