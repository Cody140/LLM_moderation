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
            try:
                response = await self._client.post(
                    "/api/moderate",
                    json={"text": text},
                )
                response.raise_for_status()
                payload = response.json()
            except httpx.TimeoutException:
                return {
                    "status": "error",
                    "error_type": "timeout",
                    "details": {"provider": "llm_client"},
                }
            except httpx.HTTPStatusError as exc:
                return {
                    "status": "error",
                    "error_type": "http_error",
                    "details": {"provider": "llm_client", "status_code": exc.response.status_code},
                }
            except Exception:
                return {
                    "status": "error",
                    "error_type": "unknown_error",
                    "details": {"provider": "llm_client"},
                }

            if not isinstance(payload, dict):
                return {
                    "status": "error",
                    "error_type": "invalid_response",
                    "details": {"provider": "llm_client"},
                }

            payload.setdefault("status", "ok")
            return payload

    async def close(self) -> None:
        await self._client.aclose()
