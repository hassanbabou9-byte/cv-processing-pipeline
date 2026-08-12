"""
CV extraction chain.

Pipeline:

    Markdown
       ↓
    Primary LLM provider
       ↓
    Provider fallback
       ↓
    JSON parsing
       ↓
    Pydantic validation
       ↓
    Semantic correction retry

The chain distinguishes between:

1. Provider failures
   - timeout
   - network/API failure
   - provider unavailable

2. Output failures
   - malformed JSON
   - schema validation failure

Provider failures can trigger provider fallback.

Output failures trigger semantic retries.
"""

import logging

from app.config.settings import Settings
from app.core.exceptions import (
    LLMOutputParsingError,
    LLMProviderError,
    LLMTimeoutError,
    SchemaValidationError,
)
from app.llm.output_parsers.cv_json_parser import (
    parse_llm_output,
)
from app.llm.prompts.cv_extraction_prompt import (
    SYSTEM_PROMPT,
    build_user_prompt,
)
from app.llm.providers.provider_factory import (
    get_fallback_llm_provider,
    get_llm_provider,
)
from app.schemas.cv_extraction import CVExtraction


logger = logging.getLogger(__name__)


def _exception_message(
    exc: Exception,
) -> str:
    """
    Safely extract a useful exception message.
    """

    message = getattr(
        exc,
        "message",
        None,
    )

    if message:
        return str(message)

    return str(exc)


def _build_correction_note(
    exc: Exception,
) -> str:
    """
    Build a focused correction prompt after an invalid LLM response.
    """

    message = _exception_message(exc)

    return f"""

============================================================
CORRECTION — SORTIE PRÉCÉDENTE INVALIDE
============================================================

La réponse précédente n'a pas respecté le contrat de sortie.

Erreur détectée :

{message}

Tu dois maintenant corriger la réponse.

RÈGLES ABSOLUES :

1. Retourne UNIQUEMENT un objet JSON.
2. Aucun texte avant le JSON.
3. Aucun texte après le JSON.
4. Aucun Markdown.
5. Aucun commentaire.
6. Aucun champ supplémentaire.
7. Respecte exactement les noms des champs.
8. Respecte exactement le schéma CVExtraction.
9. Utilise [] pour une liste absente.
10. Utilise "" pour une chaîne absente.
11. N'invente aucune information.
12. "nom" = nom de famille uniquement.
13. "prenom" = prénom uniquement.
14. Ne permute jamais nom et prénom.
15. Extrais l'email uniquement s'il est explicitement présent.
16. Ne déduis jamais le nom depuis l'email.
17. Ne déduis jamais le prénom depuis l'email.
18. N'extrais pas le téléphone.
19. N'extrais pas l'adresse postale.
20. N'extrais pas la photo.
21. N'extrais pas la date de naissance.
22. Les descriptions ne doivent pas dépasser 500 caractères.

Retourne maintenant UNIQUEMENT le JSON corrigé.
"""


def _generate_with_provider(
    provider,
    system_prompt: str,
    user_prompt: str,
) -> str:
    """
    Generate using a specific provider.

    This small helper keeps provider invocation isolated.
    """

    return provider.generate(
        system_prompt,
        user_prompt,
    )


def extract_cv_data(
    cv_markdown: str,
    settings: Settings,
) -> CVExtraction:
    """
    Extract structured CV data from cleaned Markdown.

    Raises:
        LLMOutputParsingError:
            When the LLM output cannot be parsed.

        SchemaValidationError:
            When the JSON does not match CVExtraction.

        LLMProviderError:
            When all available providers fail.

        LLMTimeoutError:
            When the active provider times out.
    """

    # ---------------------------------------------------------
    # Validate input
    # ---------------------------------------------------------

    if not isinstance(
        cv_markdown,
        str,
    ):
        raise LLMOutputParsingError(
            "CV Markdown must be a string."
        )

    if not cv_markdown.strip():
        raise LLMOutputParsingError(
            "Cannot extract CV data from empty Markdown."
        )

    # ---------------------------------------------------------
    # Providers
    # ---------------------------------------------------------

    primary = get_llm_provider(
        settings
    )

    fallback = get_fallback_llm_provider(
        settings
    )

    # ---------------------------------------------------------
    # Prompt
    # ---------------------------------------------------------

    base_user_prompt = build_user_prompt(
        cv_markdown
    )

    current_user_prompt = (
        base_user_prompt
    )

    # ---------------------------------------------------------
    # Retry configuration
    # ---------------------------------------------------------

    max_attempts = max(
        1,
        settings.llm_parse_retries + 1,
    )

    active_provider = primary

    fallback_used = False

    last_output_error: Exception | None = None

    # =========================================================
    # Extraction attempts
    # =========================================================

    for attempt in range(
        1,
        max_attempts + 1,
    ):

        logger.info(
            "CV extraction attempt %d/%d provider=%s",
            attempt,
            max_attempts,
            active_provider.provider_name,
        )

        # -----------------------------------------------------
        # Generate
        # -----------------------------------------------------

        try:

            raw_output = _generate_with_provider(
                active_provider,
                SYSTEM_PROMPT,
                current_user_prompt,
            )

        except (
            LLMProviderError,
            LLMTimeoutError,
        ) as exc:

            logger.warning(
                "Provider '%s' failed on attempt %d: %s",
                active_provider.provider_name,
                attempt,
                _exception_message(exc),
            )

            # -------------------------------------------------
            # Try fallback provider once.
            # -------------------------------------------------

            if (
                active_provider is primary
                and fallback is not None
                and not fallback_used
            ):

                fallback_used = True

                logger.warning(
                    "Switching LLM provider: %s -> %s",
                    primary.provider_name,
                    fallback.provider_name,
                )

                active_provider = fallback

                try:

                    raw_output = _generate_with_provider(
                        active_provider,
                        SYSTEM_PROMPT,
                        current_user_prompt,
                    )

                except (
                    LLMProviderError,
                    LLMTimeoutError,
                ) as fallback_exc:

                    logger.exception(
                        "Fallback provider '%s' failed.",
                        active_provider.provider_name,
                    )

                    raise fallback_exc

            else:

                raise

        # -----------------------------------------------------
        # Parse + validate
        # -----------------------------------------------------

        try:

            result = parse_llm_output(
                raw_output
            )

        except (
            LLMOutputParsingError,
            SchemaValidationError,
        ) as exc:

            last_output_error = exc

            logger.warning(
                (
                    "Invalid LLM output on attempt "
                    "%d/%d provider=%s: %s"
                ),
                attempt,
                max_attempts,
                active_provider.provider_name,
                _exception_message(exc),
            )

            # -------------------------------------------------
            # No more semantic retries.
            # -------------------------------------------------

            if attempt >= max_attempts:
                break

            # -------------------------------------------------
            # Build correction prompt.
            # -------------------------------------------------

            current_user_prompt = (
                base_user_prompt
                + _build_correction_note(exc)
            )

            continue

        # -----------------------------------------------------
        # Success
        # -----------------------------------------------------

        logger.info(
            (
                "CV extraction succeeded "
                "attempt=%d provider=%s"
            ),
            attempt,
            active_provider.provider_name,
        )

        return result

    # =========================================================
    # All output attempts failed
    # =========================================================

    if last_output_error is not None:
        raise last_output_error

    raise LLMOutputParsingError(
        "CV extraction failed."
    )