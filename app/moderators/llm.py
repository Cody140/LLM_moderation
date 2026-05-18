import asyncio

from app.moderators.base import (
    BatchModerationResponse,
    ModerationResult,
    ModerationSummary,
)
from app.services.llm_client import LLMClient


class LLMModerator:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    async def moderate_batch(self, texts: list[str]) -> BatchModerationResponse:
        tasks = [self._moderate_one(text) for text in texts]
        results = await asyncio.gather(*tasks)

        total = len(results)
        flagged = sum(1 for item in results if item.status == "ok" and bool(item.violation))
        clean = sum(1 for item in results if item.status == "ok" and item.violation is False)
        processing_errors = total - (flagged + clean)
        rate = flagged / total if total else 0.0
        error_rate = processing_errors / total if total else 0.0

        return BatchModerationResponse(
            method="llm",
            results=results,
            summary=ModerationSummary(
                total_texts=total,
                flagged_texts=flagged,
                clean_texts=clean,
                violation_rate=rate,
                processed_ok=flagged + clean,
                processing_errors=processing_errors,
                error_rate=error_rate,
            ),
        )

    async def _moderate_one(self, text: str) -> ModerationResult:
        try:
            payload = await self.llm_client.moderate_text(text)
        except Exception:
            payload = {
                "status": "error",
                "error_type": "unknown_error",
                "details": {"provider": "llm_client", "exception": "unhandled"},
            }

        if not isinstance(payload, dict):
            payload = {
                "status": "error",
                "error_type": "invalid_response",
                "details": {"provider": "llm_client", "reason": "payload_not_dict"},
            }

        status = payload.get("status", "error")
        error_type = payload.get("error_type")
        details = dict(payload.get("details", {}))

        if status != "ok":
            # Inference error is not a clean prediction and is excluded from quality metrics.
            return ModerationResult(
                text=text,
                violation=None,
                score=None,
                matched_rules=list(payload.get("matched_rules", [])),
                details=details,
                status="error",
                error_type=error_type if isinstance(error_type, str) else "unknown_error",
                decision_type="uncertain",
                route="llm_fallback",
                decision_reason="llm_inference_error",
            )

        violation_raw = payload.get("violation")
        label_raw = payload.get("label") or payload.get("raw_label") or details.get("label")
        if isinstance(violation_raw, bool):
            violation = violation_raw
        elif isinstance(label_raw, str) and label_raw.lower() in {"safe", "unsafe"}:
            violation = label_raw.lower() == "unsafe"
        else:
            return ModerationResult(
                text=text,
                violation=None,
                score=None,
                matched_rules=list(payload.get("matched_rules", [])),
                details={**details, "reason": "missing_violation_or_label"},
                status="error",
                error_type="invalid_response",
                decision_type="uncertain",
                route="llm_fallback",
                decision_reason="invalid_response",
            )

        score_raw = payload.get("score")
        score = float(score_raw) if isinstance(score_raw, (int, float)) else None
        matched_rules_raw = payload.get("matched_rules", [])
        matched_rules = [str(item) for item in matched_rules_raw] if isinstance(matched_rules_raw, list) else []

        return ModerationResult(
            text=text,
            violation=violation,
            score=score,
            matched_rules=matched_rules,
            details=details,
            status="ok",
            error_type=None,
            decision_type="violation" if violation else "clean",
            route="llm_fallback",
            decision_reason="llm_label",
        )
