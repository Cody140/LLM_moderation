from __future__ import annotations

import asyncio

from app.config import settings
from app.moderators.classic import ClassicModerator
from app.moderators.hybrid import HybridModerator
from app.moderators.llm import LLMModerator
from app.services.job_store import JobStore
from app.services.llm_client import LLMClient
from app.services.moderation_service import ModerationService
from app.workers.queue_worker import ModerationQueueWorker


queue: asyncio.Queue = asyncio.Queue(maxsize=settings.queue_maxsize)
job_store = JobStore()
llm_client = LLMClient(
    base_url=settings.llm_base_url,
    timeout_seconds=settings.llm_timeout_seconds,
    max_concurrency=settings.llm_max_concurrency,
)

classic_moderator = ClassicModerator()
llm_moderator = LLMModerator(llm_client)
hybrid_moderator = HybridModerator(classic_moderator, llm_moderator)

moderation_service = ModerationService(
    moderators={
        "classic": classic_moderator,
        "llm": llm_moderator,
        "hybrid": hybrid_moderator,
    }
)

queue_worker = ModerationQueueWorker(queue, job_store, moderation_service)
