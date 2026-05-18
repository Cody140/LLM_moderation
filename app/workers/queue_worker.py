from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

from app.services.job_store import JobStore
from app.services.moderation_service import ModerationService

logger = logging.getLogger(__name__)


class ModerationQueueWorker:
    def __init__(self, queue: asyncio.Queue, job_store: JobStore, moderation_service: ModerationService) -> None:
        self.queue = queue
        self.job_store = job_store
        self.moderation_service = moderation_service

    async def submit_job(self, texts: list[str], method: str) -> str:
        job_id = str(uuid4())
        await self.job_store.create_job(job_id, method)
        await self.queue.put({"job_id": job_id, "texts": texts, "method": method})
        return job_id

    async def run_forever(self) -> None:
        while True:
            job = await self.queue.get()
            job_id = job["job_id"]
            texts = job["texts"]
            method = job["method"]

            try:
                await self.job_store.set_processing(job_id)
                result = await self.moderation_service.process(texts, method)
                await self.job_store.set_done(job_id, result["results"], result["summary"])
            except Exception as exc:
                logger.exception("Job %s failed", job_id)
                await self.job_store.set_failed(job_id, str(exc))
            finally:
                self.queue.task_done()
