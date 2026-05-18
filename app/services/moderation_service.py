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
