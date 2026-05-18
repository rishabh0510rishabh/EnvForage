"""Ollama local LLM provider with timeout and connection-error handling."""
import json
import logging
from typing import AsyncIterator, TypeVar

import httpx
from pydantic import BaseModel

from app.ai.providers.base import LLMProvider, LLMProviderError

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)

OLLAMA_TIMEOUT = 30.0  # seconds — per issue #55 requirement
MAX_RETRIES = 2
RETRY_BACKOFF_BASE = 2  # seconds


class OllamaProvider(LLMProvider):
    """
    LLM provider for locally-running Ollama instances.

    Communicates via Ollama's OpenAI-compatible /v1/chat/completions endpoint.
    Implements timeout enforcement and graceful error handling so that a
    crashed or overloaded Ollama daemon never propagates as a 500.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._chat_url = f"{self.base_url}/v1/chat/completions"

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> T:
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        enhanced_system = (
            f"{system_prompt}\n\n"
            f"You MUST respond with ONLY valid JSON matching this exact schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Do NOT include any text outside the JSON object."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": enhanced_system},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": False,
        }

        last_error: LLMProviderError | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
                    response = await client.post(self._chat_url, json=payload)

                if response.status_code >= 500:
                    import asyncio
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(
                        "Ollama server error (%d). Retry %d/%d in %ds",
                        response.status_code, attempt, MAX_RETRIES, wait,
                    )
                    last_error = LLMProviderError(
                        "ollama",
                        f"Ollama returned HTTP {response.status_code} (attempt {attempt}/{MAX_RETRIES})",
                    )
                    await asyncio.sleep(wait)
                    continue

                if response.status_code != 200:
                    raise LLMProviderError(
                        "ollama",
                        f"HTTP {response.status_code}: {response.text[:500]}",
                    )

                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise LLMProviderError("ollama", "No choices in response.")

                content = choices[0].get("message", {}).get("content", "")
                if not content:
                    raise LLMProviderError("ollama", "Empty content in response.")

                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                try:
                    return response_model.model_validate_json(content)
                except Exception as parse_err:
                    raise LLMProviderError(
                        "ollama",
                        f"Failed to parse response into {response_model.__name__}: "
                        f"{parse_err}. Raw content: {content[:300]}",
                    ) from parse_err

            except LLMProviderError:
                raise
            except httpx.TimeoutException:
                last_error = LLMProviderError(
                    "ollama",
                    "LLM Provider is currently unavailable. Please try again later.",
                )
                logger.warning(
                    "Ollama request timed out after %.0fs (attempt %d/%d)",
                    OLLAMA_TIMEOUT, attempt, MAX_RETRIES,
                )
                import asyncio
                await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)
            except httpx.ConnectError:
                last_error = LLMProviderError(
                    "ollama",
                    "LLM Provider is currently unavailable. Please try again later.",
                )
                logger.warning(
                    "Ollama connection refused at %s (attempt %d/%d)",
                    self.base_url, attempt, MAX_RETRIES,
                )
                import asyncio
                await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)
            except httpx.HTTPError as exc:
                last_error = LLMProviderError(
                    "ollama",
                    "LLM Provider is currently unavailable. Please try again later.",
                )
                logger.warning(
                    "Ollama HTTP error: %s (attempt %d/%d)", exc, attempt, MAX_RETRIES,
                )
                import asyncio
                await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)

        raise last_error or LLMProviderError("ollama", "All retries exhausted.")

    async def stream(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> AsyncIterator[str]:
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        enhanced_system = (
            f"{system_prompt}\n\n"
            f"You MUST respond with ONLY valid JSON matching this exact schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Do NOT include any text outside the JSON object."
        )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": enhanced_system},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
                async with client.stream("POST", self._chat_url, json=payload) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        raise LLMProviderError(
                            "ollama",
                            f"HTTP {response.status_code}: {error_body[:500]}",
                        )

                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        except LLMProviderError:
            raise
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                "ollama",
                "LLM Provider is currently unavailable. Please try again later.",
            ) from exc
        except httpx.ConnectError as exc:
            raise LLMProviderError(
                "ollama",
                "LLM Provider is currently unavailable. Please try again later.",
            ) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                "ollama",
                "LLM Provider is currently unavailable. Please try again later.",
            ) from exc
