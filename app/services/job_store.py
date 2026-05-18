from __future__ import annotations

import asyncio
from typing import Any


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def create_job(self, job_id: str, method: str) -> None:
        async with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "method": method,
                "results": None,
                "summary": None,
                "error": None,
            }

    async def set_processing(self, job_id: str) -> None:
        async with self._lock:
            self._jobs[job_id]["status"] = "processing"

    async def set_done(self, job_id: str, results: list[dict], summary: dict) -> None:
        async with self._lock:
            self._jobs[job_id]["status"] = "done"
            self._jobs[job_id]["results"] = results
            self._jobs[job_id]["summary"] = summary

    async def set_failed(self, job_id: str, error: str) -> None:
        async with self._lock:
            self._jobs[job_id]["status"] = "failed"
            self._jobs[job_id]["error"] = error

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        async with self._lock:
            return self._jobs.get(job_id)
