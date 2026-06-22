import json
import logging
from collections.abc import AsyncIterator
from typing import TypeVar

import httpx
from pydantic import BaseModel

from app.ai.providers.base import LLMProvider, LLMProviderError

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    # Local LLM provider using Ollama

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
    ) -> None:
        """Initialize Ollama provider with server details."""
        if not base_url:
            raise LLMProviderError(
                "ollama",
                "OLLAMA_BASE_URL is not configured. "
                "Set it to http://localhost:11434 or your Ollama server address.",
            )
        if not model:
            raise LLMProviderError(
                "ollama",
                "OLLAMA_MODEL is not configured. "
                "Set it to a valid Ollama model name (e.g., 'llama3').",
            )

        self.base_url = base_url.rstrip("/")
        self.model = model
        self._generate_url = f"{self.base_url}/api/generate"

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> T:
        # Send a completion request and return validated response.
        full_prompt = f"{system_prompt}\n\n{user_message}"

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                response = await client.post(self._generate_url, json=payload)
                response.raise_for_status()

                ollama_response = response.json()
                raw_text = ollama_response.get("response", "")

                if not raw_text:
                    raise LLMProviderError(
                        "ollama",
                        "Ollama returned an empty response. "
                        "Ensure the model is loaded: ollama pull llama3",
                    )

                try:
                    response_json = json.loads(raw_text)
                    validated_response = response_model(**response_json)
                    return validated_response
                except json.JSONDecodeError as e:
                    raise LLMProviderError(
                        "ollama",
                        f"LLM response was not valid JSON for {response_model.__name__}. "
                        f"Error: {str(e)}",
                    ) from e
                except ValueError as e:
                    raise LLMProviderError(
                        "ollama",
                        f"Response JSON did not match {response_model.__name__} schema. "
                        f"Error: {str(e)}",
                    ) from e

        except httpx.ConnectError:
            raise LLMProviderError(
                "ollama",
                f"Could not connect to Ollama at {self.base_url}. "
                f"Ensure Ollama is running: ollama serve",
            )

        except httpx.TimeoutException:
            raise LLMProviderError(
                 "ollama",
                 "Ollama request timed out. The provider may be overloaded or unavailable."
            )
        except httpx.HTTPStatusError as e:
            raise LLMProviderError(
                "ollama",
                f"Ollama API returned status {e.response.status_code}. ",
            ) from e
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                "ollama",
                f"Unexpected error during Ollama inference: {str(e)}",
            ) from e

    async def stream(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> AsyncIterator[str]:
        """Stream a completion request, yielding tokens as they arrive."""
        full_prompt = f"{system_prompt}\n\n{user_message}"

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0))as client:
                async with client.stream(
                    "POST", self._generate_url, json=payload
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        try:
                            chunk_data = json.loads(line)
                            chunk_text = chunk_data.get("response", "")
                            if chunk_text:
                                yield chunk_text
                        except json.JSONDecodeError:
                            logger.warning(
                                "Skipped malformed Ollama stream line from model=%s (length=%d)",
                                self.model,
                                len(line),
                            )
                            continue

        except httpx.ConnectError:
            raise LLMProviderError(
                "ollama",
                f"Could not connect to Ollama at {self.base_url}. "
                f"Ensure Ollama is running: ollama serve",
            )

        except httpx.TimeoutException:
            raise LLMProviderError(
                "ollama",
                "Ollama streaming request timed out."
            )
        except httpx.HTTPStatusError as e:
            raise LLMProviderError(
                "ollama",
                f"Ollama streaming request failed with status {e.response.status_code}",
            )
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(
                "ollama",
                f"Unexpected error during Ollama streaming: {str(e)}",
            ) from e
