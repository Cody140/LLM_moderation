from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol


ResultStatus = Literal["ok", "error"]
ErrorType = Literal["timeout", "http_error", "parse_error", "invalid_response", "unknown_error"]
DecisionType = Literal["violation", "clean", "uncertain"]
RouteType = Literal["classic_only", "llm_fallback"]


@dataclass
class ModerationResult:
    text: str
    violation: bool | None
    score: float | None
    matched_rules: list[str]
    details: dict[str, Any]
    status: ResultStatus = "ok"
    error_type: ErrorType | None = None
    decision_type: DecisionType | None = None
    route: RouteType | None = None
    decision_reason: str | None = None


@dataclass
class ModerationSummary:
    total_texts: int
    flagged_texts: int
    clean_texts: int
    violation_rate: float
    processed_ok: int
    processing_errors: int
    error_rate: float


@dataclass
class BatchModerationResponse:
    method: str
    results: list[ModerationResult]
    summary: ModerationSummary


class BaseModerator(Protocol):
    async def moderate_batch(self, texts: list[str]) -> BatchModerationResponse:
        ...
