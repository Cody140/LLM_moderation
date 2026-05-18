import pytest

from app.moderators.classic import ClassicModerator


@pytest.mark.asyncio
async def test_classic_flags_direct_insult() -> None:
    moderator = ClassicModerator()
    response = await moderator.moderate_batch(["You are an idiot!!!"])

    assert response.summary.total_texts == 1
    assert response.results[0].violation is True
    assert response.results[0].score >= 1
