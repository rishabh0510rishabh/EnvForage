"""Tests for OllamaProvider — timeout, connection-error, and happy-path coverage."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import BaseModel

from app.ai.providers.base import LLMProviderError
from app.ai.providers.ollama import OLLAMA_TIMEOUT, OllamaProvider


class _SimpleResponse(BaseModel):
    answer: str


def _make_httpx_response(status_code: int, body: dict | str) -> httpx.Response:
    content = json.dumps(body).encode() if isinstance(body, dict) else body.encode()
    return httpx.Response(status_code, content=content)


# ── Constructor ────────────────────────────────────────────────────────────────

class TestOllamaProviderInit:
    def test_defaults(self):
        p = OllamaProvider()
        assert p.base_url == "http://localhost:11434"
        assert p.model == "llama3"
        assert p._chat_url == "http://localhost:11434/v1/chat/completions"

    def test_trailing_slash_stripped(self):
        p = OllamaProvider(base_url="http://localhost:11434/")
        assert p._chat_url == "http://localhost:11434/v1/chat/completions"

    def test_custom_params(self):
        p = OllamaProvider(base_url="http://gpu-box:11434", model="mistral", max_tokens=512)
        assert p.model == "mistral"
        assert p.max_tokens == 512


# ── complete() — happy path ────────────────────────────────────────────────────

class TestOllamaProviderComplete:
    @pytest.fixture
    def provider(self):
        return OllamaProvider()

    @pytest.mark.asyncio
    async def test_successful_completion(self, provider):
        response_body = {
            "choices": [{"message": {"content": '{"answer": "42"}'}}]
        }
        mock_response = _make_httpx_response(200, response_body)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await provider.complete("sys", "user", _SimpleResponse)

        assert result.answer == "42"

    @pytest.mark.asyncio
    async def test_strips_markdown_fences(self, provider):
        content = "```json\n{\"answer\": \"hello\"}\n```"
        response_body = {"choices": [{"message": {"content": content}}]}
        mock_response = _make_httpx_response(200, response_body)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await provider.complete("sys", "user", _SimpleResponse)

        assert result.answer == "hello"

    @pytest.mark.asyncio
    async def test_timeout_configured(self, provider):
        """Ensure the AsyncClient is created with the required timeout."""
        response_body = {"choices": [{"message": {"content": '{"answer": "ok"}'}}]}
        mock_response = _make_httpx_response(200, response_body)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            await provider.complete("sys", "user", _SimpleResponse)

        mock_client_cls.assert_called_once_with(timeout=OLLAMA_TIMEOUT)
        assert OLLAMA_TIMEOUT == 30.0


# ── complete() — error handling ────────────────────────────────────────────────

class TestOllamaProviderErrors:
    @pytest.fixture
    def provider(self):
        return OllamaProvider()

    @pytest.mark.asyncio
    async def test_timeout_raises_llm_provider_error(self, provider):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
            mock_client_cls.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(LLMProviderError) as exc_info:
                    await provider.complete("sys", "user", _SimpleResponse)

        assert exc_info.value.provider == "ollama"
        assert "unavailable" in exc_info.value.reason.lower()

    @pytest.mark.asyncio
    async def test_connect_error_raises_llm_provider_error(self, provider):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client_cls.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(LLMProviderError) as exc_info:
                    await provider.complete("sys", "user", _SimpleResponse)

        assert exc_info.value.provider == "ollama"
        assert "unavailable" in exc_info.value.reason.lower()

    @pytest.mark.asyncio
    async def test_http_error_raises_llm_provider_error(self, provider):
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(
                side_effect=httpx.HTTPError("network error")
            )
            mock_client_cls.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(LLMProviderError) as exc_info:
                    await provider.complete("sys", "user", _SimpleResponse)

        assert exc_info.value.provider == "ollama"

    @pytest.mark.asyncio
    async def test_non_200_raises_llm_provider_error(self, provider):
        mock_response = _make_httpx_response(404, {"error": "model not found"})

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            with pytest.raises(LLMProviderError) as exc_info:
                await provider.complete("sys", "user", _SimpleResponse)

        assert "404" in exc_info.value.reason

    @pytest.mark.asyncio
    async def test_empty_choices_raises_llm_provider_error(self, provider):
        mock_response = _make_httpx_response(200, {"choices": []})

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            with pytest.raises(LLMProviderError) as exc_info:
                await provider.complete("sys", "user", _SimpleResponse)

        assert "no choices" in exc_info.value.reason.lower()

    @pytest.mark.asyncio
    async def test_invalid_json_raises_llm_provider_error(self, provider):
        response_body = {"choices": [{"message": {"content": "not json at all"}}]}
        mock_response = _make_httpx_response(200, response_body)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            with pytest.raises(LLMProviderError) as exc_info:
                await provider.complete("sys", "user", _SimpleResponse)

        assert "_SimpleResponse" in exc_info.value.reason

    @pytest.mark.asyncio
    async def test_server_error_retries_then_raises(self, provider):
        mock_response = _make_httpx_response(503, {"error": "overloaded"})

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(LLMProviderError) as exc_info:
                    await provider.complete("sys", "user", _SimpleResponse)

        assert "503" in exc_info.value.reason


# ── Provider factory integration ───────────────────────────────────────────────

class TestProviderFactory:
    def test_factory_returns_ollama_provider(self):
        with patch("app.config.get_settings") as mock_settings:
            settings = MagicMock()
            settings.envforge_llm_provider = "ollama"
            settings.ollama_base_url = "http://localhost:11434"
            settings.ollama_model = "llama3"
            settings.ai_max_tokens = 2048
            settings.ai_temperature = 0.3
            mock_settings.return_value = settings

            from app.ai.providers import get_provider
            provider = get_provider()

        assert isinstance(provider, OllamaProvider)
        assert provider.model == "llama3"
