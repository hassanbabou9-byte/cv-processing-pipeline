"""
Ollama LLM provider.

Uses LangChain's ChatOllama with structured JSON output based directly
on the CVExtraction Pydantic schema.

This prevents the model from freely inventing the JSON structure.
"""

import logging

from langchain_ollama import ChatOllama

from app.config.settings import Settings
from app.core.exceptions import (
    LLMProviderError,
    LLMTimeoutError,
)
from app.llm.providers.base import LLMProvider
from app.schemas.cv_extraction import CVExtraction


logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """
    Ollama implementation of the LLMProvider interface.
    """

    def __init__(
        self,
        settings: Settings,
    ) -> None:

        self._model_name = (
            settings.ollama_model
        )

        self._timeout_seconds = (
            settings.llm_timeout_seconds
        )

        # ---------------------------------------------------------
        # Generate the JSON schema directly from Pydantic.
        # ---------------------------------------------------------

        extraction_schema = (
            CVExtraction.model_json_schema()
        )

        # ---------------------------------------------------------
        # ChatOllama
        # ---------------------------------------------------------
        #
        # format accepts:
        #
        #     "json"
        #
        # or a JSON schema dictionary.
        #
        # Using the actual Pydantic JSON schema gives Ollama
        # substantially stronger structural guidance.
        # ---------------------------------------------------------

        self._client = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout_seconds,
            num_predict=settings.llm_max_output_tokens,
            num_ctx=settings.llm_context_window,
            format=extraction_schema,
        )

    @property
    def provider_name(self) -> str:
        """
        Provider identifier used by the extraction chain.
        """

        return "ollama"

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """
        Generate structured CV extraction JSON.
        """

        logger.info(
            "Calling Ollama model=%s",
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
                    "Ollama request timed out "
                    f"after {self._timeout_seconds}s."
                ),
                details={
                    "model": self._model_name,
                },
            ) from exc

        except Exception as exc:

            logger.exception(
                "Ollama call failed."
            )

            raise LLMProviderError(
                "Ollama request failed.",
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

        if not isinstance(content, str):
            raise LLMProviderError(
                "Ollama returned a non-string response.",
                details={
                    "model": self._model_name,
                    "response_type": type(
                        content
                    ).__name__,
                },
            )

        content = content.strip()

        if not content:
            raise LLMProviderError(
                "Ollama returned an empty response.",
                details={
                    "model": self._model_name,
                },
            )

        logger.info(
            "Ollama response received: %d characters",
            len(content),
        )

        return content