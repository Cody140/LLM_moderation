from typing import Literal

from pydantic import BaseModel, Field


ModerationMethod = Literal["classic", "llm", "hybrid"]


class SubmitModerationRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1)
    method: ModerationMethod = "classic"
