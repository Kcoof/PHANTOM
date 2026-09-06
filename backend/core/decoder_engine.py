"""Decoder engine — encode/decode/hash transforms (contracts/api.md, US6)."""
from __future__ import annotations

import base64
import binascii
import gzip
import hashlib
import html as html_lib
import json
import re
import unicodedata
from urllib.parse import quote, unquote

CODECS = ("base64", "url", "html", "hex", "unicode", "gzip", "jwt")

_B64_RE = re.compile(r"^[A-Za-z0-9+/\n\r]+={0,2}$")
_HEX_RE = re.compile(r"^(?:[0-9a-fA-F]{2})+$")


class DecodeError(ValueError):
    pass


def encode(input_text: str, codec: str) -> str:
    data = input_text.encode("utf-8")
    if codec == "base64":
        return base64.b64encode(data).decode("ascii")
    if codec == "url":
        return quote(input_text, safe="")
    if codec == "html":
        return html_lib.escape(input_text, quote=True)
    if codec == "hex":
        return data.hex()
    if codec == "unicode":
        return "".join(f"\\u{ord(c):04x}" for c in input_text)
    if codec == "gzip":
        return base64.b64encode(gzip.compress(data)).decode("ascii")
    if codec == "jwt":
        raise DecodeError("jwt supports decode only")
    raise DecodeError(f"unknown codec: {codec}")


def decode(input_text: str, codec: str) -> str:
    text = input_text.strip()
    if codec == "base64":
        try:
            return base64.b64decode(text, validate=False).decode("utf-8", errors="replace")
        except (binascii.Error, ValueError) as exc:
            raise DecodeError(f"cannot decode as base64: {exc}")
    if codec == "url":
        return unquote(text)
    if codec == "html":
        return html_lib.unescape(text)
    if codec == "hex":
        if not _HEX_RE.match(text):
            raise DecodeError("not valid hex (even-length 0-9a-f)")
        try:
            return bytes.fromhex(text).decode("utf-8", errors="replace")
        except ValueError as exc:
            raise DecodeError(f"cannot decode as hex: {exc}")
    if codec == "unicode":
        try:
            return text.encode("ascii").decode("unicode_escape")
        except (UnicodeDecodeError, ValueError) as exc:
            raise DecodeError(f"cannot decode unicode escapes: {exc}")
    if codec == "gzip":
        try:
            raw = base64.b64decode(text) if not _is_gzip(text) else text.encode("latin-1")
            return gzip.decompress(raw).decode("utf-8", errors="replace")
        except Exception as exc:
            raise DecodeError(f"cannot gunzip: {exc}")
    if codec == "jwt":
        return _decode_jwt(text)
    raise DecodeError(f"unknown codec: {codec}")


def _is_gzip(text: str) -> bool:
    return text[:2] == "\x1f\x8b"


def _decode_jwt(text: str) -> str:
    parts = text.split(".")
    if len(parts) < 2:
        raise DecodeError("not a JWT (expected header.payload.signature)")
    out = {}
    for name, part in (("header", parts[0]), ("payload", parts[1])):
        padded = part + "=" * (-len(part) % 4)
        try:
            out[name] = json.loads(base64.urlsafe_b64decode(padded))
        except (binascii.Error, json.JSONDecodeError):
            raise DecodeError(f"cannot decode JWT {name}")
    if len(parts) > 2:
        out["signature"] = parts[2]
    return json.dumps(out, indent=2)


def hash_input(input_text: str, algorithm: str) -> str:
    algo = algorithm.lower().replace("-", "")
    mapping = {"md5": hashlib.md5, "sha1": hashlib.sha1, "sha256": hashlib.sha256, "sha512": hashlib.sha512}
    if algo not in mapping:
        raise DecodeError(f"unsupported algorithm: {algorithm}")
    return mapping[algo](input_text.encode("utf-8")).hexdigest()


def auto_detect(input_text: str) -> list[dict]:
    """Try common decodings, best guesses first."""
    text = input_text.strip()
    results: list[dict] = []
    candidates: list[tuple[str, float]] = []

    if _B64_RE.match(text.replace("\n", "").replace("\r", "")) and len(text) >= 4:
        candidates.append(("base64", 0.9))
    if text.startswith("eyJ") and text.count(".") >= 2:
        candidates.append(("jwt", 0.95))
    if _HEX_RE.match(text):
        candidates.append(("hex", 0.85))
    if "%" in text and re.search(r"%[0-9A-Fa-f]{2}", text):
        candidates.append(("url", 0.8))
    if "&#" in text or re.search(r"&[a-z]+;", text):
        candidates.append(("html", 0.8))
    if "\\u" in text:
        candidates.append(("unicode", 0.7))
    if _is_gzip(text):
        candidates.append(("gzip", 0.9))

    for codec, score in sorted(candidates, key=lambda c: -c[1]):
        try:
            output = decode(text, codec)
            printable = sum(1 for ch in output[:200] if ch.isprintable() or ch in "\n\r\t") / max(len(output[:200]), 1)
            results.append(
                {
                    "codec": codec,
                    "output": output[:5000],
                    "confidence": round(score * (0.5 + 0.5 * printable), 2),
                }
            )
        except DecodeError:
            continue
    results.sort(key=lambda r: -r["confidence"])
    return results
