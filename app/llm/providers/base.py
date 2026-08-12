"""
LLM provider interface.

Every concrete provider (OpenRouter, Ollama, and any future addition)
implements this interface. Nothing above this layer — chains, services,
the API — should ever import a concrete provider class directly; they
depend only on this abstraction, obtained via provider_factory.get_llm_provider().

A provider's only job is: given a system prompt and a user prompt,
return the raw text response. It knows nothing about CVs, JSON schemas,
or retry orchestration at the chain level — just "send prompt, get text."
"""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract base class all LLM providers must implement."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Send a system + user prompt to the LLM and return its raw text response.

        Args:
            system_prompt: Instructions defining the LLM's role and output rules.
            user_prompt: The actual content to process (e.g. cleaned CV Markdown).

        Returns:
            The raw text response from the LLM. Callers are responsible for
            parsing/validating this text (see llm/output_parsers/).

        Raises:
            core.exceptions.LLMProviderError: on provider/API failure.
            core.exceptions.LLMTimeoutError: if the call exceeds the configured timeout.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Short identifier for logging/diagnostics, e.g. 'openrouter' or 'ollama'."""
        raise NotImplementedError