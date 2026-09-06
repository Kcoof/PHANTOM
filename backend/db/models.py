"""Pydantic models mirroring the data model (specs/001-phantom-mvp/data-model.md)."""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Confidence(str, Enum):
    CERTAIN = "certain"
    FIRM = "firm"
    TENTATIVE = "tentative"


class FindingStatus(str, Enum):
    OPEN = "open"
    CONFIRMED = "confirmed"
    FIXED = "fixed"
    FALSE_POSITIVE = "false_positive"


class ScanType(str, Enum):
    ACTIVE = "active"
    PASSIVE = "passive"
    FULL = "full"


class ScanStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class TrafficEntry(BaseModel):
    id: Optional[int] = None
    timestamp: Optional[str] = None
    method: str
    scheme: str = "https"
    host: str
    port: int = 443
    path: str
    query_string: Optional[str] = None
    url: str
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: Optional[str] = None
    request_content_type: Optional[str] = None
    status_code: Optional[int] = None
    response_headers: Optional[dict[str, str]] = None
    response_body: Optional[str] = None
    response_content_type: Optional[str] = None
    response_time_ms: Optional[int] = None
    size_bytes: Optional[int] = None
    is_intercepted: bool = False
    is_in_scope: bool = True
    tags: list[str] = Field(default_factory=list)
    notes: Optional[str] = None
    ai_analysis: Optional[Any] = None
    highlight_color: Optional[str] = None


class Finding(BaseModel):
    id: Optional[int] = None
    scan_id: str
    history_id: Optional[int] = None
    timestamp: Optional[str] = None
    finding_type: str
    severity: Severity
    confidence: Confidence
    title: str
    description: str
    url: str
    parameter: Optional[str] = None
    payload: Optional[str] = None
    evidence: Optional[str] = None
    request_dump: Optional[str] = None
    response_dump: Optional[str] = None
    remediation: Optional[str] = None
    cwe_id: Optional[str] = None
    cvss_score: Optional[float] = None
    is_false_positive: bool = False
    status: FindingStatus = FindingStatus.OPEN


class Scan(BaseModel):
    id: str
    timestamp: Optional[str] = None
    target_url: str
    scan_type: ScanType
    status: ScanStatus = ScanStatus.RUNNING
    total_requests: int = 0
    findings_count: int = 0
    config: Optional[dict] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class RepeaterTab(BaseModel):
    id: Optional[int] = None
    name: str
    timestamp: Optional[str] = None
    method: str
    url: str
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_body: Optional[str] = None
    last_response_status: Optional[int] = None
    last_response_headers: Optional[dict[str, str]] = None
    last_response_body: Optional[str] = None
    last_response_time_ms: Optional[int] = None
    history: Optional[list[dict]] = None


class ChatMessage(BaseModel):
    id: Optional[int] = None
    timestamp: Optional[str] = None
    role: str  # user | assistant | system
    content: str
    context_type: Optional[str] = None
    context_id: Optional[int] = None
    model: Optional[str] = None


class ScopeRule(BaseModel):
    id: Optional[int] = None
    rule_type: str  # include | exclude
    protocol: Optional[str] = None  # http | https | any
    host_pattern: str
    port: Optional[str] = None
    path_pattern: str = ".*"
    is_active: bool = True


class SettingUpdate(BaseModel):
    """Flat {key: value} map in, e.g. {"proxy_port": "8081"}."""
    values: dict[str, str]
