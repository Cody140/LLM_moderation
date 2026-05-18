from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config import settings
from app.dependencies import llm_client, queue_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_tasks = [
        asyncio.create_task(queue_worker.run_forever())
        for _ in range(settings.worker_count)
    ]
    try:
        yield
    finally:
        for task in worker_tasks:
            task.cancel()
        await asyncio.gather(*worker_tasks, return_exceptions=True)
        await llm_client.close()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)
