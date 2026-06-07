import json
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from pydantic import BaseModel

from app.ai.providers.base import LLMProviderError
from app.ai.providers.ollama import OllamaProvider


class MockResponse(BaseModel):
    message: str


# -----------------------------
# INIT TESTS
# -----------------------------


def test_empty_base_url():
    with pytest.raises(LLMProviderError):
        OllamaProvider(base_url="")


def test_empty_model():
    with pytest.raises(LLMProviderError):
        OllamaProvider(model="")


# -----------------------------
# COMPLETE SUCCESS TEST
# -----------------------------
async def test_complete_success():
    provider = OllamaProvider()

    mock_response = Mock()
    mock_response.json.return_value = {"response": json.dumps({"message": "Hello"})}
    mock_response.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        result = await provider.complete(
            "system",
            "user",
            MockResponse,
        )

        assert result.message == "Hello"


# -----------------------------
# EMPTY RESPONSE TEST
# -----------------------------
async def test_complete_empty_response():
    provider = OllamaProvider()

    mock_response = Mock()
    mock_response.json.return_value = {"response": ""}
    mock_response.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        with pytest.raises(LLMProviderError):
            await provider.complete(
                "system",
                "user",
                MockResponse,
            )


# -----------------------------
# INVALID JSON TEST
# -----------------------------
async def test_complete_invalid_json():
    provider = OllamaProvider()

    mock_response = Mock()
    mock_response.json.return_value = {"response": "not valid json"}
    mock_response.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        with pytest.raises(LLMProviderError):
            await provider.complete(
                "system",
                "user",
                MockResponse,
            )


# -----------------------------
# CONNECTION ERROR TEST
# -----------------------------
async def test_complete_connection_error():
    provider = OllamaProvider()

    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ConnectError("Connection failed")

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        with pytest.raises(LLMProviderError):
            await provider.complete(
                "system",
                "user",
                MockResponse,
            )


# -----------------------------
# TIMEOUT ERROR TEST (NEW)
# -----------------------------
async def test_complete_timeout_error():
    provider = OllamaProvider()

    mock_client = AsyncMock()
    mock_client.post.side_effect = httpx.ReadTimeout("Request timed out")

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        with pytest.raises(LLMProviderError):
            await provider.complete(
                "system",
                "user",
                MockResponse,
            )


# -----------------------------
# STREAM SUCCESS TEST
# -----------------------------
async def test_stream_success():
    provider = OllamaProvider()

    stream_lines = [
        json.dumps({"response": "Hello"}),
        json.dumps({"response": " World"}),
    ]

    mock_response = Mock()

    async def mock_aiter_lines():
        for line in stream_lines:
            yield line

    mock_response.aiter_lines = mock_aiter_lines
    mock_response.raise_for_status.return_value = None

    # mock_stream handles the async context manager protocol (async with client.stream)
    mock_stream = AsyncMock()
    mock_stream.__aenter__.return_value = mock_response

    # client itself is an AsyncMock, but its .stream attribute must be a regular Mock
    # so calling client.stream() returns mock_stream directly, not a coroutine.
    mock_client = AsyncMock()
    mock_client.stream = Mock(return_value=mock_stream)

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        chunks = []
        async for chunk in provider.stream(
            "system",
            "user",
            MockResponse,
        ):
            chunks.append(chunk)

        assert "".join(chunks) == "Hello World"


# -----------------------------
# STREAM MALFORMED JSON TEST
# -----------------------------
async def test_stream_skips_invalid_json():
    provider = OllamaProvider()

    stream_lines = [
        "invalid json",
        json.dumps({"response": "Hello"}),
    ]

    mock_response = Mock()

    async def mock_aiter_lines():
        for line in stream_lines:
            yield line

    mock_response.aiter_lines = mock_aiter_lines
    mock_response.raise_for_status.return_value = None

    mock_stream = AsyncMock()
    mock_stream.__aenter__.return_value = mock_response

    mock_client = AsyncMock()
    mock_client.stream = Mock(return_value=mock_stream)

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        chunks = []
        async for chunk in provider.stream(
            "system",
            "user",
            MockResponse,
        ):
            chunks.append(chunk)

        assert "".join(chunks) == "Hello"


# -----------------------------
# STREAM CONNECTION ERROR
# -----------------------------
async def test_stream_connection_error():
    provider = OllamaProvider()

    # Using a standard Mock instead of AsyncMock for the attribute method
    # prevents an unawaited coroutine warning when the side_effect fires
    mock_client = AsyncMock()
    mock_client.stream = Mock(side_effect=httpx.ConnectError("Connection failed"))

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        with pytest.raises(LLMProviderError):
            async for _ in provider.stream(
                "system",
                "user",
                MockResponse,
            ):
                pass


# -----------------------------
# STREAM TIMEOUT ERROR (NEW)
# -----------------------------
async def test_stream_timeout_error():
    provider = OllamaProvider()

    mock_client = AsyncMock()
    mock_client.stream = Mock(side_effect=httpx.ReadTimeout("Request timed out"))

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client

        with pytest.raises(LLMProviderError):
            async for _ in provider.stream(
                "system",
                "user",
                MockResponse,
            ):
                pass
