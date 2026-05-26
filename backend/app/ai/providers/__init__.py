"""Provider factory and fallback orchestration for LLM providers."""
import logging
from collections.abc import AsyncIterator, Iterable
from typing import TypeVar

from pydantic import BaseModel

from app.ai.providers.base import LLMProvider, LLMProviderError

T = TypeVar("T", bound=BaseModel)
logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = ("mock", "openrouter", "openai", "ollama")
DEFAULT_FALLBACK_ORDER = ("openrouter", "openai", "ollama")


class FallbackProvider(LLMProvider):
    """Try configured LLM providers in order until one succeeds."""

    def __init__(self, providers: Iterable[LLMProvider]) -> None:
        self.providers = list(providers)
        if not self.providers:
            raise LLMProviderError("fallback", "No LLM providers are configured.")
        self.active_provider = self.providers[0]

    @property
    def provider_name(self) -> str:
        return type(self.active_provider).__name__

    @property
    def model(self) -> str:
        return getattr(self.active_provider, "model", "unknown")

    @property
    def last_token_usage(self) -> dict[str, int] | None:
        token_usage = getattr(self.active_provider, "last_token_usage", None)
        if callable(token_usage):
            return token_usage()
        if isinstance(token_usage, dict):
            return token_usage
        fallback_usage = getattr(self.active_provider, "_last_usage", None)
        return fallback_usage if isinstance(fallback_usage, dict) else None

    async def complete(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> T:
        failures: list[str] = []

        for provider in self.providers:
            self.active_provider = provider
            provider_name = type(provider).__name__
            try:
                result = await provider.complete(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    response_model=response_model,
                )
                if failures:
                    logger.info("LLM fallback succeeded with %s", provider_name)
                return result
            except LLMProviderError as exc:
                failures.append(str(exc))
                logger.warning("LLM provider %s failed: %s", provider_name, exc.reason)

        raise LLMProviderError(
            "fallback",
            "All LLM providers failed. Attempts: " + " | ".join(failures),
        )

    async def stream(
        self,
        system_prompt: str,
        user_message: str,
        response_model: type[T],
    ) -> AsyncIterator[str]:
        failures: list[str] = []

        for provider in self.providers:
            self.active_provider = provider
            provider_name = type(provider).__name__
            yielded = False
            try:
                async for chunk in provider.stream(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    response_model=response_model,
                ):
                    yielded = True
                    yield chunk
                return
            except LLMProviderError as exc:
                if yielded:
                    raise
                failures.append(str(exc))
                logger.warning(
                    "LLM stream provider %s failed before yielding: %s",
                    provider_name,
                    exc.reason,
                )

        raise LLMProviderError(
            "fallback",
            "All LLM stream providers failed. Attempts: " + " | ".join(failures),
        )


def get_provider() -> LLMProvider:
    """
    Instantiate the configured LLM provider with fallback providers.

    The primary provider is determined by ``ENVFORGE_LLM_PROVIDER``. For real
    hosted/local providers, fallback order defaults to the remaining providers
    in ``openrouter -> openai -> ollama`` order and can be overridden with the
    comma-separated ``ENVFORGE_LLM_PROVIDER_FALLBACKS`` env var.
    """
    from app.config import get_settings

    settings = get_settings()
    provider_names = _provider_chain(settings)
    providers: list[LLMProvider] = []

    for index, provider_name in enumerate(provider_names):
        try:
            providers.append(_build_provider(provider_name, settings))
        except LLMProviderError:
            if index == 0:
                raise
            logger.warning("Skipping unavailable fallback LLM provider: %s", provider_name)

    if len(providers) == 1:
        return providers[0]
    return FallbackProvider(providers)


def _provider_chain(settings: object) -> list[str]:
    primary = str(getattr(settings, "envforge_llm_provider")).lower()
    fallback_setting = getattr(settings, "envforge_llm_provider_fallbacks", "")

    if primary not in SUPPORTED_PROVIDERS:
        raise LLMProviderError(
            primary,
            f"Unknown LLM provider: '{primary}'. "
            f"Valid options: {', '.join(SUPPORTED_PROVIDERS)}.",
        )

    if primary == "mock":
        return ["mock"]

    configured_fallbacks = _parse_fallbacks(fallback_setting)
    if configured_fallbacks:
        chain = [primary, *configured_fallbacks]
    else:
        primary_index = DEFAULT_FALLBACK_ORDER.index(primary)
        chain = list(DEFAULT_FALLBACK_ORDER[primary_index:])

    return _dedupe_provider_names(chain)


def _parse_fallbacks(value: object) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        names = [name.strip().lower() for name in value.split(",")]
    else:
        names = [str(name).strip().lower() for name in value]

    invalid = [name for name in names if name and name not in SUPPORTED_PROVIDERS]
    if invalid:
        raise LLMProviderError(
            "fallback",
            f"Unknown fallback LLM provider(s): {', '.join(invalid)}. "
            f"Valid options: {', '.join(SUPPORTED_PROVIDERS)}.",
        )
    return [name for name in names if name]


def _dedupe_provider_names(provider_names: Iterable[str]) -> list[str]:
    deduped: list[str] = []
    for provider_name in provider_names:
        if provider_name not in deduped:
            deduped.append(provider_name)
    return deduped


def _build_provider(provider_name: str, settings: object) -> LLMProvider:
    if provider_name == "mock":
        from app.ai.providers.mock import MockProvider

        return MockProvider()

    if provider_name == "openrouter":
        from app.ai.providers.openrouter import OpenRouterProvider

        return OpenRouterProvider(
            api_key=getattr(settings, "openrouter_api_key"),
            model=getattr(settings, "openrouter_model"),
            max_tokens=getattr(settings, "ai_max_tokens"),
            temperature=getattr(settings, "ai_temperature"),
        )

    if provider_name == "openai":
        from app.ai.providers.openai import OpenAIProvider

        return OpenAIProvider(
            api_key=getattr(settings, "openai_api_key"),
            base_url=getattr(settings, "openai_base_url", "https://api.openai.com/v1"),
            model=getattr(settings, "openai_model"),
            max_tokens=getattr(settings, "ai_max_tokens"),
            temperature=getattr(settings, "ai_temperature"),
        )

    if provider_name == "ollama":
        from app.ai.providers.ollama import OllamaProvider

        return OllamaProvider(
            base_url=getattr(settings, "ollama_base_url"),
            model=getattr(settings, "ollama_model"),
        )

    raise LLMProviderError(provider_name, f"Unknown LLM provider: '{provider_name}'.")
