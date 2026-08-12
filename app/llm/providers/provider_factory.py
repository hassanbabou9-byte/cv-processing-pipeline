"""
LLM provider factory.
"""

import logging
from functools import lru_cache

from app.config.settings import (
    Settings,
    get_settings,
)
from app.core.exceptions import LLMProviderError
from app.llm.providers.base import LLMProvider
from app.llm.providers.ollama_provider import (
    OllamaProvider,
)
from app.llm.providers.openrouter_provider import (
    OpenRouterProvider,
)


logger = logging.getLogger(__name__)


def get_llm_provider(
    settings: Settings,
) -> LLMProvider:

    provider_name = (
        settings.llm_provider
    )

    logger.info(
        "Initializing LLM provider: %s",
        provider_name,
    )

    if provider_name == "ollama":
        return OllamaProvider(settings)

    if provider_name == "openrouter":
        return OpenRouterProvider(settings)

    raise LLMProviderError(
        (
            f"Unknown LLM provider "
            f"'{provider_name}'."
        ),
        details={
            "configured_provider": provider_name,
        },
    )


@lru_cache
def get_cached_llm_provider() -> LLMProvider:

    return get_llm_provider(
        get_settings()
    )


def get_fallback_llm_provider(
    settings: Settings,
) -> LLMProvider | None:

    fallback_name = (
        "ollama"
        if settings.llm_provider == "openrouter"
        else "openrouter"
    )

    try:

        if fallback_name == "ollama":
            return OllamaProvider(settings)

        return OpenRouterProvider(settings)

    except LLMProviderError as exc:

        logger.warning(
            (
                "Fallback provider '%s' "
                "is unavailable: %s"
            ),
            fallback_name,
            exc.message,
        )

        return None