"""Mock LLM provider for testing — returns deterministic responses."""
import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import TypeVar

from pydantic import BaseModel

from app.ai.models import SuggestedFix, TroubleshootResponse
from app.ai.providers.base import LLMProvider

T = TypeVar("T", bound=BaseModel)


class MockProvider(LLMProvider):
    """
    Deterministic mock for unit tests and development.
    Never makes network calls.
    """

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> T:
        if response_model is TroubleshootResponse:
            return TroubleshootResponse(  # type: ignore[return-value]
                session_id=str(uuid.uuid4()),
                root_cause="[Mock] CUDA version mismatch detected in diagnostic report.",
                suggested_fixes=[
                    SuggestedFix(
                        step=1,
                        title="Check NVIDIA driver version",
                        description="Run nvidia-smi to verify driver version meets CUDA requirements.",
                        severity="INFO",
                        safe_commands=["nvidia-smi"],
                    ),
                    SuggestedFix(
                        step=2,
                        title="Verify CUDA toolkit version",
                        description="Confirm installed CUDA version matches framework requirements.",
                        severity="WARNING",
                        safe_commands=["nvcc --version"],
                    ),
                ],
                repair_script_available=False,
                confidence=0.5,
            )

        if response_model.__name__ == "AISafetyVerdict":
            return response_model(is_safe=True, reason="[Mock] Safe by default.")

        raise ValueError(f"MockProvider does not support response model: {response_model}")
    async def stream(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> AsyncIterator[str]:
        """Simulate streaming by yielding chunks of the mocked JSON response."""
        response = await self.complete(system_prompt, user_message, response_model)
        full_json = response.model_dump_json()

        # Yield in small chunks to simulate network/LLM latency
        chunk_size = 20
        for i in range(0, len(full_json), chunk_size):
            yield full_json[i:i+chunk_size]
            await asyncio.sleep(0.02)
