from typing import Any, Literal

from pydantic import BaseModel


JobStatus = Literal["queued", "processing", "done", "failed"]


class ModerationItemResponse(BaseModel):
    text: str
    violation: bool | None
    score: float | None
    matched_rules: list[str]
    details: dict[str, Any]
    status: str = "ok"
    error_type: str | None = None
    decision_type: str | None = None


class ModerationSummaryResponse(BaseModel):
    total_texts: int
    flagged_texts: int
    clean_texts: int
    violation_rate: float
    processed_ok: int
    processing_errors: int
    error_rate: float


class JobSubmitResponse(BaseModel):
    job_id: str
    status: JobStatus
    method: str


class JobResultResponse(BaseModel):
    job_id: str
    status: JobStatus
    method: str
    results: list[ModerationItemResponse] | None = None
    summary: ModerationSummaryResponse | None = None
    error: str | None = None
