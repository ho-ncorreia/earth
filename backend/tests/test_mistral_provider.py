import httpx
import pytest

from app.ai_assistant.provider import MistralProvider
from app.core.config import settings


@pytest.mark.anyio
async def test_mistral_provider_posts_server_side_grounded_context(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mistral_api_key", "test-secret")
    seen = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["authorization"] = request.headers["authorization"]
        seen["payload"] = __import__("json").loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Grounded answer."}}]})

    provider = MistralProvider(transport=httpx.MockTransport(handler))
    answer = await provider.answer(
        "What is the current decision?",
        [{"type": "decision", "id": 7, "title": "ADR-1 · Messaging", "excerpt": "Use a managed queue."}],
    )
    assert answer == "Grounded answer."
    assert seen["authorization"] == "Bearer test-secret"
    assert "Use a managed queue." in seen["payload"]["messages"][0]["content"]