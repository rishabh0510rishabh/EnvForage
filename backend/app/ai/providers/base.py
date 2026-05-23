"""Abstract base class for LLM providers."""
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """
    Pluggable LLM provider interface.
    All providers must return structured Pydantic models — never raw text.
    """

    @abstractmethod
    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> T:
        """
        Send a completion request and return a validated Pydantic model.

        Args:
            system_prompt: System-level instruction for the LLM
            user_message: The user's structured context message
            response_model: Pydantic model class for response parsing

        Returns:
            Validated instance of response_model

        Raises:
            LLMProviderError: If the request fails or response cannot be parsed
        """
        ...

    @abstractmethod
    def stream(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> AsyncIterator[str]:
        """
        Send a completion request and stream the raw token response.

        Args:
            system_prompt: System-level instruction for the LLM
            user_message: The user's structured context message
            response_model: Pydantic model class for response parsing

        Yields:
            Raw tokens (or JSON chunks) as they arrive from the provider.
        """
        ...


class LLMProviderError(Exception):
    """Raised when an LLM provider request fails."""
    def __init__(self, provider: str, reason: str) -> None:
        self.provider = provider
        self.reason = reason
        super().__init__(f"[{provider}] {reason}")
