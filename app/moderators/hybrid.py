from app.moderators.base import BatchModerationResponse, ModerationResult, ModerationSummary
from app.moderators.classic import ClassicModerator
from app.moderators.llm import LLMModerator


class HybridModerator:
    """Classic-first hybrid with unresolved routing to LLM.

    Strategy:
    - classic decision_type=violation -> final violation
    - classic decision_type=clean -> final clean
    - classic decision_type=uncertain (or error) -> fallback to llm
    """

    def __init__(self, classic: ClassicModerator, llm: LLMModerator) -> None:
        self.classic = classic
        self.llm = llm

    async def moderate_batch(self, texts: list[str]) -> BatchModerationResponse:
        classic_response = await self.classic.moderate_batch(texts)

        final_results: list[ModerationResult] = []
        uncertain_texts: list[str] = []
        uncertain_indices: list[int] = []

        for index, result in enumerate(classic_response.results):
            if result.status != "ok" or result.decision_type == "uncertain":
                result.route = "llm_fallback"
                if result.decision_reason is None:
                    result.decision_reason = "classic_uncertain"
                final_results.append(result)
                uncertain_texts.append(result.text)
                uncertain_indices.append(index)
                continue

            result.route = "classic_only"
            final_results.append(result)

        if uncertain_texts:
            llm_response = await self.llm.moderate_batch(uncertain_texts)
            for idx, llm_result in zip(uncertain_indices, llm_response.results, strict=False):
                merged = llm_result
                existing = final_results[idx]
                merged.details = {
                    **existing.details,
                    **llm_result.details,
                    "hybrid_routed": True,
                    "route": "llm_fallback",
                    "classic_decision_type": existing.decision_type,
                    "classic_decision_reason": existing.decision_reason,
                }
                merged.matched_rules = [
                    *(f"classic:{rule}" for rule in existing.matched_rules),
                    *(f"llm:{rule}" for rule in llm_result.matched_rules),
                ]
                merged.route = "llm_fallback"
                if merged.decision_reason is None:
                    merged.decision_reason = "hybrid_llm_fallback"
                final_results[idx] = merged

        total = len(final_results)
        flagged = sum(1 for item in final_results if item.status == "ok" and bool(item.violation))
        clean = sum(1 for item in final_results if item.status == "ok" and item.violation is False)
        processing_errors = total - (flagged + clean)
        rate = flagged / total if total else 0.0
        error_rate = processing_errors / total if total else 0.0

        return BatchModerationResponse(
            method="hybrid",
            results=final_results,
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
