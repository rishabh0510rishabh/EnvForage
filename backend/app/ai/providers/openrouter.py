import json
import logging
from collections.abc import AsyncIterator
from typing import TypeVar

import httpx
from pydantic import BaseModel

from app.ai.providers.base import LLMProvider, LLMProviderError

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds


class OpenRouterProvider(LLMProvider):
    """
    LLM provider that calls the OpenRouter API.

    OpenRouter acts as a universal gateway to 100+ LLM models (GPT-4o,
    Claude, Llama 3, Gemini, etc.). The model is selected via config.

    Features:
        - Async HTTP via httpx
        - Enforces JSON-only output mode
        - Retries with exponential backoff on transient failures
        - Parses responses into validated Pydantic models
        - Tracks token usage for audit logging
    """

    def __init__(
        self,
        api_key: str,
        model: str = "meta-llama/llama-3-8b-instruct:free",
        max_tokens: int = 2048,
        temperature: float = 0.3,
    ) -> None:
        if not api_key or api_key == "sk-or-...":
            raise LLMProviderError(
                "openrouter", "OPENROUTER_API_KEY is not configured."
            )
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._last_usage: dict[str, int] | None = None

    @property
    def last_token_usage(self) -> dict[str, int] | None:
        """Return token usage from the most recent API call."""
        return self._last_usage

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> T:
        """
        Send a chat completion request to OpenRouter and return a validated
        Pydantic model instance.

        The request uses JSON mode to ensure the LLM returns parseable JSON
        matching the response_model schema.

        Args:
            system_prompt: System-level instruction for the LLM.
            user_message: The user's structured context message.
            response_model: Pydantic model class for response parsing.

        Returns:
            Validated instance of response_model.

        Raises:
            LLMProviderError: If all retries fail or response cannot be parsed.
        """
        # Build the schema hint for the LLM
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

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://envforage.dev",
            "X-Title": "EnvForage AI Troubleshooter",
        }

        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        OPENROUTER_API_URL,
                        json=payload,
                        headers=headers,
                    )

                if response.status_code == 429:
                    # Rate limited — retry with backoff
                    import asyncio

                    wait = RETRY_BACKOFF_BASE**attempt
                    logger.warning(
                        "OpenRouter rate limited (429). Retry %d/%d in %ds",
                        attempt,
                        MAX_RETRIES,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                if response.status_code >= 500:
                    # Server error — retry
                    import asyncio

                    wait = RETRY_BACKOFF_BASE**attempt
                    logger.warning(
                        "OpenRouter server error (%d). Retry %d/%d in %ds",
                        response.status_code,
                        attempt,
                        MAX_RETRIES,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                if response.status_code != 200:
                    error_body = response.text
                    raise LLMProviderError(
                        "openrouter",
                        f"HTTP {response.status_code}: {error_body[:500]}",
                    )

                # Parse the response
                data = response.json()

                # Track token usage
                usage = data.get("usage")
                if usage:
                    self._last_usage = {
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                        "total_tokens": usage.get("total_tokens", 0),
                    }

                # Extract the content
                choices = data.get("choices", [])
                if not choices:
                    raise LLMProviderError("openrouter", "No choices in response.")

                content = choices[0].get("message", {}).get("content", "")
                if not content:
                    raise LLMProviderError("openrouter", "Empty content in response.")

                # Clean content — strip markdown code fences if present
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                # Parse into Pydantic model
                try:
                    return response_model.model_validate_json(content)
                except Exception as parse_err:
                    raise LLMProviderError(
                        "openrouter",
                        f"Failed to parse response into {response_model.__name__}: "
                        f"{parse_err}. Raw content: {content[:300]}",
                    ) from parse_err

            except LLMProviderError:
                raise
            except httpx.TimeoutException:
                last_error = LLMProviderError(
                    "openrouter", f"Request timed out (attempt {attempt}/{MAX_RETRIES})"
                )
                logger.warning("OpenRouter timeout. Retry %d/%d", attempt, MAX_RETRIES)
                import asyncio

                await asyncio.sleep(RETRY_BACKOFF_BASE**attempt)
            except httpx.HTTPError as exc:
                last_error = LLMProviderError(
                    "openrouter", f"HTTP error: {exc} (attempt {attempt}/{MAX_RETRIES})"
                )
                logger.warning(
                    "OpenRouter HTTP error: %s. Retry %d/%d", exc, attempt, MAX_RETRIES
                )
                import asyncio

                await asyncio.sleep(RETRY_BACKOFF_BASE**attempt)

        # All retries exhausted
        raise last_error or LLMProviderError("openrouter", "All retries exhausted.")

    async def stream(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> AsyncIterator[str]:
        """
        Send a completion request to OpenRouter and stream the response content.
        Useful for providing real-time feedback to the user.
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

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://envforage.dev",
            "X-Title": "EnvForage AI Troubleshooter",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                OPENROUTER_API_URL,
                json=payload,
                headers=headers,
            ) as response:
                if response.status_code != 200:
                    error_body = await response.aread()
                    raise LLMProviderError(
                        "openrouter",
                        f"HTTP {response.status_code}: {error_body.decode(errors='replace')[:500]}",
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
