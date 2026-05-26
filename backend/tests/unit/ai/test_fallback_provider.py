from collections.abc import AsyncIterator
from typing import TypeVar

import pytest
from pydantic import BaseModel

from app.ai.providers import FallbackProvider, _provider_chain
from app.ai.providers.base import LLMProvider, LLMProviderError

T = TypeVar("T", bound=BaseModel)


class DummyResponse(BaseModel):
    message: str


class DummyProvider(LLMProvider):
    def __init__(self, name: str, *, should_fail: bool = False) -> None:
        self.name = name
        self.model = f"{name}-model"
        self.should_fail = should_fail
        self.calls = 0
        self._last_usage = {"total_tokens": 7}

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> T:
        self.calls += 1
        if self.should_fail:
            raise LLMProviderError(self.name, "temporary failure")
        return response_model(message=f"ok from {self.name}")

    async def stream(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> AsyncIterator[str]:
        self.calls += 1
        if self.should_fail:
            raise LLMProviderError(self.name, "temporary failure")
        yield f"ok from {self.name}"


class SettingsStub:
    envforge_llm_provider = "openrouter"
    envforge_llm_provider_fallbacks = ""


@pytest.mark.asyncio
async def test_fallback_provider_tries_next_provider_after_error():
    primary = DummyProvider("primary", should_fail=True)
    fallback = DummyProvider("fallback")
    provider = FallbackProvider([primary, fallback])

    result = await provider.complete("system", "user", DummyResponse)

    assert result.message == "ok from fallback"
    assert primary.calls == 1
    assert fallback.calls == 1
    assert provider.provider_name == "DummyProvider"
    assert provider.model == "fallback-model"
    assert provider.last_token_usage == {"total_tokens": 7}


@pytest.mark.asyncio
async def test_fallback_provider_raises_after_all_providers_fail():
    provider = FallbackProvider([
        DummyProvider("primary", should_fail=True),
        DummyProvider("fallback", should_fail=True),
    ])

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.complete("system", "user", DummyResponse)

    assert exc_info.value.provider == "fallback"
    assert "All LLM providers failed" in exc_info.value.reason
    assert "[primary] temporary failure" in exc_info.value.reason
    assert "[fallback] temporary failure" in exc_info.value.reason


def test_provider_chain_defaults_to_remaining_real_providers():
    settings = SettingsStub()

    assert _provider_chain(settings) == ["openrouter", "openai", "ollama"]


def test_provider_chain_allows_configured_fallback_order():
    settings = SettingsStub()
    settings.envforge_llm_provider_fallbacks = "ollama, openai, openrouter"

    assert _provider_chain(settings) == ["openrouter", "ollama", "openai"]
