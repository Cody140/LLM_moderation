from fastapi import APIRouter, HTTPException

from app.dependencies import job_store, queue_worker
from app.schemas.requests import SubmitModerationRequest
from app.schemas.responses import JobResultResponse, JobSubmitResponse

router = APIRouter()


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/moderate", response_model=JobSubmitResponse)
async def submit_moderation(request: SubmitModerationRequest) -> JobSubmitResponse:
    job_id = await queue_worker.submit_job(request.texts, request.method)
    return JobSubmitResponse(job_id=job_id, status="queued", method=request.method)


@router.get("/moderate/{job_id}", response_model=JobResultResponse)
async def get_moderation_result(job_id: str) -> JobResultResponse:
    job = await job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResultResponse(**job)
