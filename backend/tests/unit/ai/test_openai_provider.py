from unittest.mock import AsyncMock, MagicMock, call, patch

import httpx
import pytest
from pydantic import BaseModel

from app.ai.providers.base import LLMProviderError
from app.ai.providers.openai import OpenAIProvider


class DummyModel(BaseModel):
    response: str
async def test_openai_stream_rate_limit_short_circuit():
    """Verify that OpenAIProvider.stream handles 429s, retries, and short-circuits on the final attempt."""
    provider = OpenAIProvider(api_key="test_key")

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 429
    mock_response.headers = httpx.Headers({"Retry-After": "1"})

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "httpx.AsyncClient.stream", return_value=mock_stream_ctx
        ) as mock_stream_call,
        patch("asyncio.sleep", AsyncMock()) as mock_sleep,
    ):
        generator = provider.stream(
            system_prompt="Test system",
            user_message="Test user",
            response_model=DummyModel,
        )

        with pytest.raises(LLMProviderError) as exc_info:
            async for _ in generator:
                pass

        assert "Rate limited (429)" in str(exc_info.value)
        assert mock_stream_call.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_calls([call(1), call(1)])
async def test_openai_stream_network_error_retry_and_exhaustion():
    """Verify that OpenAIProvider.stream retries on httpx.HTTPError and exhausts all retries."""
    provider = OpenAIProvider(api_key="test_key")

    # Simulate a transport layer network drop-out when stream() is called
    with (
        patch(
            "httpx.AsyncClient.stream",
            side_effect=httpx.ConnectError("Connection timed out"),
        ) as mock_stream_call,
        patch("asyncio.sleep", AsyncMock()) as mock_sleep,
    ):
        generator = provider.stream(
            system_prompt="Test system",
            user_message="Test user",
            response_model=DummyModel,
        )

        with pytest.raises(LLMProviderError) as exc_info:
            async for _ in generator:
                pass

        # Verify the trailing exception fallback is reached cleanly
        assert "OpenAI streaming failed after maximum retry attempts." in str(
            exc_info.value
        )

        # Verify the loop attempted the stream 3 times and backed off/slept twice
        assert mock_stream_call.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_calls([call(1.0), call(2.0)])


async def test_openai_stream_502_bad_gateway_retry_and_exhaustion():
    """Verify that OpenAIProvider.stream retries on HTTP 502 (Bad Gateway) and exhausts all retries."""
    provider = OpenAIProvider(api_key="test_key")

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 502
    mock_response.headers = httpx.Headers({})
    mock_response.aread = AsyncMock(return_value=b"Bad Gateway")

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "httpx.AsyncClient.stream", return_value=mock_stream_ctx
        ) as mock_stream_call,
        patch("asyncio.sleep", AsyncMock()) as mock_sleep,
    ):
        generator = provider.stream(
            system_prompt="Test system",
            user_message="Test user",
            response_model=DummyModel,
        )

        with pytest.raises(LLMProviderError) as exc_info:
            async for _ in generator:
                pass

        assert "HTTP 502" in str(exc_info.value)
        assert "retry attempts exhausted" in str(exc_info.value)
        assert "Bad Gateway" in str(exc_info.value)
        assert mock_stream_call.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_calls([call(1.0), call(2.0)])


async def test_openai_stream_503_service_unavailable_retry_and_exhaustion():
    """Verify that OpenAIProvider.stream retries on HTTP 503 (Service Unavailable) and exhausts all retries."""
    provider = OpenAIProvider(api_key="test_key")

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 503
    mock_response.headers = httpx.Headers({})
    mock_response.aread = AsyncMock(return_value=b"Service Unavailable")

    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)

    with (
        patch(
            "httpx.AsyncClient.stream", return_value=mock_stream_ctx
        ) as mock_stream_call,
        patch("asyncio.sleep", AsyncMock()) as mock_sleep,
    ):
        generator = provider.stream(
            system_prompt="Test system",
            user_message="Test user",
            response_model=DummyModel,
        )

        with pytest.raises(LLMProviderError) as exc_info:
            async for _ in generator:
                pass

        assert "HTTP 503" in str(exc_info.value)
        assert "retry attempts exhausted" in str(exc_info.value)
        assert "Service Unavailable" in str(exc_info.value)
        assert mock_stream_call.call_count == 3
        assert mock_sleep.call_count == 2
        mock_sleep.assert_has_calls([call(1.0), call(2.0)])
