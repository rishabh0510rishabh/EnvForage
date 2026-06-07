import asyncio
import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import TypeVar

import httpx
from pydantic import BaseModel

from app.ai.providers.base import LLMProvider, LLMProviderError

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """Direct provider implementation for enterprise OpenAI API integration."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> None:
        if not api_key:
            raise LLMProviderError("openai", "OpenAI API key configuration is missing.")
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

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
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()
                data = response.json()
                choices = data.get("choices", [])
                if not choices:
                    raise LLMProviderError("openai", "No choices in response.")
                content = choices[0].get("message", {}).get("content", "")
                if not content:
                    raise LLMProviderError("openai", "Empty content in response.")

                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                return response_model.model_validate_json(content)
            except httpx.HTTPStatusError as e:
                raise LLMProviderError(
                    "openai", f"OpenAI API error occured: {e.response.text}"
                )
            except LLMProviderError:
                raise
            except Exception as e:
                raise LLMProviderError(
                    "openai",
                    f"Unexpected connection error under OpenAI provider: {str(e)}",
                ) from e

    def stream(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> AsyncIterator[str]:
        """
        Send a completion request to OpenAI and stream the response content.
        This generator yields tokens as they arrive with resilient transient error handling.
        """
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
            "response_format": {"type": "json_object"},
            "stream": True,
        }

        async def generator() -> AsyncIterator[str]:
            max_retries = 3
            base_delay = 2.0

            async with httpx.AsyncClient(timeout=60.0) as client:
                for attempt in range(max_retries):
                    try:
                        async with client.stream(
                            "POST",
                            f"{self.base_url}/chat/completions",
                            json=payload,
                            headers=self.headers,
                        ) as response:
                            if response.status_code == 429:
                                retry_after = response.headers.get("Retry-After")

                                delay = None

                                if retry_after:
                                    if retry_after.isdigit():
                                        delay = max(0, float(retry_after))
                                    else:
                                        try:
                                            retry_at = parsedate_to_datetime(
                                                retry_after
                                            )
                                            now = datetime.now(UTC)

                                            delay = max(
                                                0,
                                                int((retry_at - now).total_seconds()),
                                            )

                                        except (TypeError, ValueError, OverflowError):
                                            delay = None

                                if delay is None:
                                    delay = 2**attempt

                                logger.warning(
                                    "OpenAI rate limited (429). Retrying in %s seconds... (Attempt %d/%d)",
                                    delay,
                                    attempt + 1,
                                    max_retries,
                                )

                                if attempt >= max_retries - 1:
                                    raise LLMProviderError(
                                        "openai",
                                        "Rate limited (429) - OpenAI streaming retry attempts exhausted.",
                                    )

                                await asyncio.sleep(delay)
                                continue

                            if response.status_code in (502, 503):
                                error_body = await response.aread()

                                if attempt >= max_retries - 1:
                                    logger.warning(
                                        "OpenAI returned %d on final attempt (%d/%d).",
                                        response.status_code,
                                        attempt + 1,
                                        max_retries,
                                    )
                                    raise LLMProviderError(
                                        "openai",
                                        f"HTTP {response.status_code} (Bad Gateway/Service Unavailable) - "
                                        f"retry attempts exhausted: {error_body.decode(errors='replace')[:500]}",
                                    )

                                logger.warning(
                                    "OpenAI returned %d. Retrying in %s seconds... (Attempt %d/%d)",
                                    response.status_code,
                                    base_delay ** attempt,
                                    attempt + 1,
                                    max_retries,
                                )
                                await asyncio.sleep(base_delay ** attempt)
                                continue

                            if response.status_code != 200:
                                error_body = await response.aread()
                                raise LLMProviderError(
                                    "openai",
                                    f"HTTP {response.status_code}: {error_body.decode(errors='replace')[:500]}",
                                )

                            async for line in response.aiter_lines():
                                line = line.strip()

                                if not line.startswith("data:"):
                                    continue

                                data_str = line.removeprefix("data:").strip()

                                if not data_str:
                                    continue

                                if data_str == "[DONE]":
                                    break

                                try:
                                    data = json.loads(data_str)
                                except json.JSONDecodeError:
                                    logger.debug(
                                        "Skipping malformed stream chunk: %s", data_str
                                    )
                                    continue

                                choices = data.get("choices", [])

                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")

                                    if content:
                                        yield content

                            # Stream completed successfully, return to exit the generator loop
                            return

                    except httpx.HTTPError as e:
                        # If this is our last attempt, don't sleep; let the loop finish and drop to final exception
                        if attempt >= max_retries - 1:
                            logger.error(
                                "Transient network connection error on final attempt: %s.",
                                str(e),
                            )
                            break

                        delay = float(base_delay**attempt)
                        logger.warning(
                            "Transient network error during OpenAI stream: %s. Retrying in %d seconds... (Attempt %d/%d)",
                            str(e),
                            delay,
                            attempt + 1,
                            max_retries,
                        )
                        await asyncio.sleep(delay or 0.0)
                        continue

                # This is reached if loop finishes completely without returning or hitting a short-circuit raise
                raise LLMProviderError(
                    "openai",
                    "OpenAI streaming failed after maximum retry attempts.",
                )

        return generator()
