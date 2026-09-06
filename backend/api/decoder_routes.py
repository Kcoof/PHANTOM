"""Decoder API — /api/decoder (contracts/api.md)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from core.decoder_engine import (
    CODECS,
    DecodeError,
    auto_detect,
    decode,
    encode,
    hash_input,
)

router = APIRouter()

ALGORITHMS = ("md5", "sha1", "sha256", "sha512")


class CodecIn(BaseModel):
    input: str
    codec: str

    @field_validator("codec")
    @classmethod
    def _valid_codec(cls, v: str) -> str:
        if v not in CODECS:
            raise ValueError(f"codec must be one of {', '.join(CODECS)}")
        return v


class HashIn(BaseModel):
    input: str
    algorithm: str


class AutoDetectIn(BaseModel):
    input: str


@router.post("/encode")
async def encode_endpoint(body: CodecIn) -> dict:
    try:
        return {"input": body.input, "output": encode(body.input, body.codec), "codec": body.codec}
    except DecodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/decode")
async def decode_endpoint(body: CodecIn) -> dict:
    try:
        return {"input": body.input, "output": decode(body.input, body.codec), "codec": body.codec}
    except DecodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/auto-detect")
async def auto_detect_endpoint(body: AutoDetectIn) -> dict:
    return {"results": auto_detect(body.input)}


@router.post("/hash")
async def hash_endpoint(body: HashIn) -> dict:
    if body.algorithm.lower() not in ALGORITHMS:
        raise HTTPException(status_code=422, detail=f"algorithm must be one of {', '.join(ALGORITHMS)}")
    return {"algorithm": body.algorithm.lower(), "digest": hash_input(body.input, body.algorithm)}
