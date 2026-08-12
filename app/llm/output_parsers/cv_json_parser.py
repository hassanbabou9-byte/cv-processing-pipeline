"""
CV JSON output parser.

Converts the raw LLM response into a validated CVExtraction object.

The parser handles common LLM formatting problems such as:

    ```json
    {...}
    ```

or:

    Here is the JSON:
    {...}

while still enforcing the strict Pydantic schema afterward.
"""

import json
import logging
from typing import Any

from pydantic import ValidationError

from app.core.exceptions import (
    LLMOutputParsingError,
    SchemaValidationError,
)
from app.schemas.cv_extraction import CVExtraction


logger = logging.getLogger(__name__)


def _clean_markdown_fences(
    text: str,
) -> str:
    """
    Remove Markdown JSON fences if present.
    """

    text = text.strip()

    if text.startswith("```json"):
        text = text[
            len("```json"):
        ].strip()

    elif text.startswith("```JSON"):
        text = text[
            len("```JSON"):
        ].strip()

    elif text.startswith("```"):
        text = text[
            len("```"):
        ].strip()

    if text.endswith("```"):
        text = text[
            :-len("```")
        ].strip()

    return text


def _extract_json_object(
    text: str,
) -> str:
    """
    Extract the first balanced JSON object.

    This parser tracks:

        - braces
        - JSON strings
        - escaped characters

    so braces inside a description do not break extraction.
    """

    start = text.find("{")

    if start == -1:
        raise LLMOutputParsingError(
            (
                "LLM response is not valid JSON and "
                "no JSON object could be found."
            ),
            details={
                "raw_response_preview": text[:500],
            },
        )

    depth = 0

    inside_string = False

    escaped = False

    for index in range(
        start,
        len(text),
    ):

        char = text[index]

        # -----------------------------------------------------
        # Inside JSON string
        # -----------------------------------------------------

        if inside_string:

            if escaped:
                escaped = False

            elif char == "\\":
                escaped = True

            elif char == '"':
                inside_string = False

            continue

        # -----------------------------------------------------
        # Outside JSON string
        # -----------------------------------------------------

        if char == '"':
            inside_string = True

        elif char == "{":

            depth += 1

        elif char == "}":

            depth -= 1

            if depth == 0:

                return text[
                    start:index + 1
                ]

    raise LLMOutputParsingError(
        "LLM response contains an incomplete JSON object.",
        details={
            "raw_response_preview": text[:500],
        },
    )


def _format_validation_errors(
    errors: list[dict[str, Any]],
) -> str:
    """
    Render Pydantic validation errors in a compact format.
    """

    lines: list[str] = []

    for error in errors:

        location = ".".join(
            str(part)
            for part in error.get(
                "loc",
                (),
            )
        )

        message = error.get(
            "msg",
            "Unknown validation error",
        )

        error_type = error.get(
            "type",
            "unknown",
        )

        lines.append(
            (
                f"- field='{location}' "
                f"type='{error_type}' "
                f"message='{message}'"
            )
        )

    return "\n".join(lines)


def parse_llm_output(
    raw_text: str,
) -> CVExtraction:
    """
    Parse and validate raw LLM output.

    Returns:
        CVExtraction

    Raises:
        LLMOutputParsingError
        SchemaValidationError
    """

    # ---------------------------------------------------------
    # Basic validation
    # ---------------------------------------------------------

    if not isinstance(
        raw_text,
        str,
    ):
        raise LLMOutputParsingError(
            "LLM returned a non-string response.",
            details={
                "type": type(
                    raw_text
                ).__name__,
            },
        )

    if not raw_text.strip():
        raise LLMOutputParsingError(
            "LLM returned an empty response."
        )

    # ---------------------------------------------------------
    # Remove Markdown fences
    # ---------------------------------------------------------

    cleaned = _clean_markdown_fences(
        raw_text
    )

    # ---------------------------------------------------------
    # Extract JSON object
    # ---------------------------------------------------------

    json_text = _extract_json_object(
        cleaned
    )

    # ---------------------------------------------------------
    # Decode JSON
    # ---------------------------------------------------------

    try:

        parsed_json = json.loads(
            json_text
        )

    except json.JSONDecodeError as exc:

        raise LLMOutputParsingError(
            "LLM response contains malformed JSON.",
            details={
                "raw_response_preview": (
                    cleaned[:500]
                ),
                "error": str(exc),
            },
        ) from exc

    # ---------------------------------------------------------
    # JSON root must be an object
    # ---------------------------------------------------------

    if not isinstance(
        parsed_json,
        dict,
    ):

        raise LLMOutputParsingError(
            (
                "LLM response parsed as JSON "
                "but is not an object."
            ),
            details={
                "parsed_type": type(
                    parsed_json
                ).__name__,
            },
        )

    # ---------------------------------------------------------
    # Pydantic validation
    # ---------------------------------------------------------

    try:

        extraction = (
            CVExtraction.model_validate(
                parsed_json
            )
        )

    except ValidationError as exc:

        errors = exc.errors(
            include_url=False
        )

        formatted_errors = (
            _format_validation_errors(
                errors
            )
        )

        logger.warning(
            (
                "CVExtraction schema "
                "validation failed:\n%s"
            ),
            formatted_errors,
        )

        raise SchemaValidationError(
            (
                "LLM output does not match "
                "the expected CV extraction schema."
            ),
            details={
                "validation_errors": errors,
                "formatted_errors": (
                    formatted_errors
                ),
            },
        ) from exc

    # ---------------------------------------------------------
    # Success
    # ---------------------------------------------------------

    logger.info(
        (
            "Successfully parsed and validated "
            "LLM output into CVExtraction."
        )
    )

    return extraction