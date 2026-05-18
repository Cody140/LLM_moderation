# FastAPI moderation service scaffold

## Project structure

```text
moderation_service/
├─ app/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ config.py
│  ├─ dependencies.py
│  ├─ schemas/
│  │  ├─ __init__.py
│  │  ├─ requests.py
│  │  └─ responses.py
│  ├─ services/
│  │  ├─ __init__.py
│  │  ├─ job_store.py
│  │  ├─ moderation_service.py
│  │  └─ llm_client.py
│  ├─ moderators/
│  │  ├─ __init__.py
│  │  ├─ base.py
│  │  ├─ classic.py
│  │  ├─ ml.py
│  │  └─ hybrid.py
│  ├─ workers/
│  │  ├─ __init__.py
│  │  └─ queue_worker.py
│  └─ api/
│     ├─ __init__.py
│     └─ routes.py
├─ tests/
│  ├─ __init__.py
│  ├─ test_classic.py
│  └─ test_api.py
├─ requirements.txt
├─ .env.example
├─ Dockerfile
└─ docker-compose.yml
```

## Why this structure

- `api/` — HTTP endpoints.
- `schemas/` — Pydantic request/response models.
- `moderators/` — concrete moderation strategies: classic, ml, hybrid.
- `services/` — orchestration, job storage, external clients.
- `workers/` — async background workers consuming queue jobs.
- `config.py` — central settings.
- `main.py` — FastAPI app startup and shutdown.

---

## `app/config.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Moderation Service"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    queue_maxsize: int = 1000
    worker_count: int = 2

    llm_base_url: str = "http://localhost:11434"
    llm_timeout_seconds: float = 30.0
    llm_max_concurrency: int = 4

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
```

---

## `app/schemas/requests.py`

```python
from typing import Literal
from pydantic import BaseModel, Field


ModerationMethod = Literal["classic", "ml", "hybrid"]


class SubmitModerationRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1)
    method: ModerationMethod = "classic"
```

---

## `app/schemas/responses.py`

```python
from typing import Any, Literal
from pydantic import BaseModel


JobStatus = Literal["queued", "processing", "done", "failed"]


class ModerationItemResponse(BaseModel):
    text: str
    violation: bool
    score: int
    matched_rules: list[str]
    details: dict[str, Any]


class ModerationSummaryResponse(BaseModel):
    total_texts: int
    flagged_texts: int
    clean_texts: int
    violation_rate: float


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
```

---

## `app/moderators/base.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ModerationResult:
    text: str
    violation: bool
    score: int
    matched_rules: list[str]
    details: dict[str, Any]


@dataclass
class ModerationSummary:
    total_texts: int
    flagged_texts: int
    clean_texts: int
    violation_rate: float


@dataclass
class BatchModerationResponse:
    method: str
    results: list[ModerationResult]
    summary: ModerationSummary


class BaseModerator(Protocol):
    async def moderate_batch(self, texts: list[str]) -> BatchModerationResponse:
        ...
```

---

## `app/moderators/classic.py`

```python
import asyncio
import re

from app.moderators.base import (
    BatchModerationResponse,
    ModerationResult,
    ModerationSummary,
)


class ClassicModerator:
    def __init__(self) -> None:
        self.blacklist = {
            "idiot",
            "stupid",
            "moron",
            "hate",
            "kill",
            "trash",
            "loser",
        }

        self.char_map = {
            "@": "a",
            "4": "a",
            "0": "o",
            "1": "i",
            "3": "e",
            "$": "s",
            "5": "s",
            "!": "i",
        }

        self.regex_patterns = {
            "threat_pattern": re.compile(r"\b(i\s*will\s*kill\s*you|kill\s*you)\b", re.IGNORECASE),
            "insult_pattern": re.compile(r"\b(you\s+are\s+(an?\s+)?(idiot|moron|loser|stupid))\b", re.IGNORECASE),
            "hate_pattern": re.compile(r"\b(i\s+hate\s+you|hate\s+you)\b", re.IGNORECASE),
        }

    async def moderate_batch(self, texts: list[str]) -> BatchModerationResponse:
        return await asyncio.to_thread(self._moderate_sync, texts)

    def _moderate_sync(self, texts: list[str]) -> BatchModerationResponse:
        results = [self._moderate_one(text) for text in texts]

        total = len(results)
        flagged = sum(1 for item in results if item.violation)
        clean = total - flagged
        rate = flagged / total if total else 0.0

        return BatchModerationResponse(
            method="classic",
            results=results,
            summary=ModerationSummary(
                total_texts=total,
                flagged_texts=flagged,
                clean_texts=clean,
                violation_rate=rate,
            ),
        )

    def _moderate_one(self, text: str) -> ModerationResult:
        normalized = self._normalize_text(text)

        matched_rules: list[str] = []
        matched_rules.extend(self._check_blacklist(normalized))
        matched_rules.extend(self._check_regex(text))
        matched_rules.extend(self._check_rules(normalized, text))

        score = len(matched_rules)
        violation = score > 0

        return ModerationResult(
            text=text,
            violation=violation,
            score=score,
            matched_rules=matched_rules,
            details={"normalized_text": normalized},
        )

    def _normalize_text(self, text: str) -> str:
        text = text.lower()
        for old, new in self.char_map.items():
            text = text.replace(old, new)

        text = re.sub(r"[^a-z0-9\s]", " ", text)
        text = re.sub(r"(.)\1{2,}", r"\1\1", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _check_blacklist(self, text: str) -> list[str]:
        return [f"blacklist:{word}" for word in text.split() if word in self.blacklist]

    def _check_regex(self, original_text: str) -> list[str]:
        matched = []
        for name, pattern in self.regex_patterns.items():
            if pattern.search(original_text):
                matched.append(f"regex:{name}")
        return matched

    def _check_rules(self, normalized_text: str, original_text: str) -> list[str]:
        matched = []

        letters = [ch for ch in original_text if ch.isalpha()]
        if letters:
            upper_ratio = sum(1 for ch in letters if ch.isupper()) / len(letters)
            if upper_ratio > 0.7 and len(letters) >= 6:
                matched.append("rule:too_many_caps")

        if original_text.count("!") >= 5:
            matched.append("rule:too_many_exclamations")

        if re.search(r"\byou\b", normalized_text) and re.search(r"\b(idiot|moron|stupid|loser)\b", normalized_text):
            matched.append("rule:direct_insult")

        return matched
```

---

## `app/services/llm_client.py`

```python
from __future__ import annotations

import asyncio
from typing import Any

import httpx


class LLMClient:
    def __init__(self, base_url: str, timeout_seconds: float, max_concurrency: int) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout_seconds)
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def moderate_text(self, text: str) -> dict[str, Any]:
        async with self._semaphore:
            response = await self._client.post(
                "/api/moderate",
                json={"text": text},
            )
            response.raise_for_status()
            return response.json()

    async def close(self) -> None:
        await self._client.aclose()
```

---

## `app/moderators/ml.py`

```python
import asyncio

from app.moderators.base import (
    BatchModerationResponse,
    ModerationResult,
    ModerationSummary,
)
from app.services.llm_client import LLMClient


class MLModerator:
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    async def moderate_batch(self, texts: list[str]) -> BatchModerationResponse:
        tasks = [self._moderate_one(text) for text in texts]
        results = await asyncio.gather(*tasks)

        total = len(results)
        flagged = sum(1 for item in results if item.violation)
        clean = total - flagged
        rate = flagged / total if total else 0.0

        return BatchModerationResponse(
            method="ml",
            results=results,
            summary=ModerationSummary(
                total_texts=total,
                flagged_texts=flagged,
                clean_texts=clean,
                violation_rate=rate,
            ),
        )

    async def _moderate_one(self, text: str) -> ModerationResult:
        payload = await self.llm_client.moderate_text(text)

        return ModerationResult(
            text=text,
            violation=bool(payload.get("violation", False)),
            score=int(payload.get("score", 0)),
            matched_rules=list(payload.get("matched_rules", [])),
            details=dict(payload.get("details", {})),
        )
```

---

## `app/moderators/hybrid.py`

```python
from app.moderators.base import BatchModerationResponse, ModerationResult, ModerationSummary
from app.moderators.classic import ClassicModerator
from app.moderators.ml import MLModerator


class HybridModerator:
    def __init__(self, classic: ClassicModerator, ml: MLModerator) -> None:
        self.classic = classic
        self.ml = ml

    async def moderate_batch(self, texts: list[str]) -> BatchModerationResponse:
        classic_response = await self.classic.moderate_batch(texts)

        final_results: list[ModerationResult] = []
        uncertain_texts: list[str] = []
        uncertain_indices: list[int] = []

        for index, result in enumerate(classic_response.results):
            if result.violation:
                final_results.append(result)
            else:
                final_results.append(result)
                uncertain_texts.append(result.text)
                uncertain_indices.append(index)

        if uncertain_texts:
            ml_response = await self.ml.moderate_batch(uncertain_texts)
            for idx, ml_result in zip(uncertain_indices, ml_response.results, strict=False):
                final_results[idx] = ml_result

        total = len(final_results)
        flagged = sum(1 for item in final_results if item.violation)
        clean = total - flagged
        rate = flagged / total if total else 0.0

        return BatchModerationResponse(
            method="hybrid",
            results=final_results,
            summary=ModerationSummary(
                total_texts=total,
                flagged_texts=flagged,
                clean_texts=clean,
                violation_rate=rate,
            ),
        )
```

---

## `app/services/job_store.py`

```python
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
```

---

## `app/services/moderation_service.py`

```python
from __future__ import annotations

from dataclasses import asdict

from app.moderators.base import BaseModerator


class ModerationService:
    def __init__(self, moderators: dict[str, BaseModerator]) -> None:
        self.moderators = moderators

    async def process(self, texts: list[str], method: str) -> dict:
        if method not in self.moderators:
            available = ", ".join(self.moderators.keys())
            raise ValueError(f"Unknown method '{method}'. Available methods: {available}")

        response = await self.moderators[method].moderate_batch(texts)
        return {
            "method": response.method,
            "results": [asdict(item) for item in response.results],
            "summary": asdict(response.summary),
        }
```

---

## `app/workers/queue_worker.py`

```python
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
```

---

## `app/dependencies.py`

```python
from __future__ import annotations

import asyncio

from app.config import settings
from app.moderators.classic import ClassicModerator
from app.moderators.hybrid import HybridModerator
from app.moderators.ml import MLModerator
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
ml_moderator = MLModerator(llm_client)
hybrid_moderator = HybridModerator(classic_moderator, ml_moderator)

moderation_service = ModerationService(
    moderators={
        "classic": classic_moderator,
        "ml": ml_moderator,
        "hybrid": hybrid_moderator,
    }
)

queue_worker = ModerationQueueWorker(queue, job_store, moderation_service)
```

---

## `app/api/routes.py`

```python
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
```

---

## `app/main.py`

```python
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
```

---

## `requirements.txt`

```txt
fastapi==0.115.8
uvicorn[standard]==0.34.0
httpx==0.28.1
pydantic==2.10.6
pydantic-settings==2.7.1
pytest==8.3.4
pytest-asyncio==0.25.3
```

---

## `.env.example`

```env
APP_NAME=Moderation Service
APP_HOST=0.0.0.0
APP_PORT=8000
QUEUE_MAXSIZE=1000
WORKER_COUNT=2
LLM_BASE_URL=http://localhost:11434
LLM_TIMEOUT_SECONDS=30.0
LLM_MAX_CONCURRENCY=4
```

---

## `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## `docker-compose.yml`

```yaml
version: "3.9"

services:
  moderation-api:
    build: .
    container_name: moderation-api
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
```

---

## How to run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

---

## Example API flow

### Submit a job

```bash
curl -X POST "http://localhost:8000/moderate" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "classic",
    "texts": [
      "Hello, how are you?",
      "YOU ARE AN IDIOT!!!",
      "I will kill you"
    ]
  }'
```

### Read result by `job_id`

```bash
curl "http://localhost:8000/moderate/<job_id>"
```

---

## What to improve next

1. Move `JobStore` from memory to Redis or PostgreSQL.
2. Add retries and timeout wrappers for LLM calls.
3. Add per-item status for very large batches.
4. Add request validation limits for maximum batch size.
5. Add logging and metrics.
6. Add a real local LLM endpoint adapter for Ollama / vLLM / TGI.
7. Add confidence thresholds in `hybrid.py` instead of sending all clean items to ML.
```

