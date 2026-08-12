"""
OpenRouter LLM provider.
"""

import logging

from langchain_openai import ChatOpenAI

from app.config.settings import Settings
from app.core.exceptions import (
    LLMProviderError,
    LLMTimeoutError,
)
from app.llm.providers.base import LLMProvider


logger = logging.getLogger(__name__)


class OpenRouterProvider(LLMProvider):

    def __init__(
        self,
        settings: Settings,
    ) -> None:

        if not settings.openrouter_api_key:
            raise LLMProviderError(
                (
                    "OPENROUTER_API_KEY is not set. "
                    "Required when "
                    "LLM_PROVIDER=openrouter."
                )
            )

        self._model_name = (
            settings.openrouter_model
        )

        self._timeout_seconds = (
            settings.llm_timeout_seconds
        )

        self._client = ChatOpenAI(
            model=settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=settings.llm_temperature,
            max_retries=settings.llm_max_retries,
            timeout=settings.llm_timeout_seconds,
            max_tokens=settings.llm_max_output_tokens,
        )

    @property
    def provider_name(self) -> str:
        return "openrouter"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:

        logger.info(
            "Calling OpenRouter model=%s",
            self._model_name,
        )

        try:

            response = self._client.invoke(
                [
                    (
                        "system",
                        system_prompt,
                    ),
                    (
                        "human",
                        user_prompt,
                    ),
                ]
            )

        except TimeoutError as exc:

            raise LLMTimeoutError(
                (
                    "OpenRouter request timed out "
                    f"after {self._timeout_seconds}s."
                ),
                details={
                    "model": self._model_name,
                },
            ) from exc

        except Exception as exc:

            logger.exception(
                "OpenRouter call failed"
            )

            raise LLMProviderError(
                "OpenRouter request failed.",
                details={
                    "model": self._model_name,
                    "original_error": str(exc),
                },
            ) from exc

        content = getattr(
            response,
            "content",
            None,
        )

        if (
            not isinstance(content, str)
            or not content.strip()
        ):

            raise LLMProviderError(
                "OpenRouter returned an empty response.",
                details={
                    "model": self._model_name,
                },
            )

        logger.info(
            "OpenRouter response received: %d characters",
            len(content),
        )

        return content