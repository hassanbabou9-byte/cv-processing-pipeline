"""
Markdown extraction from a parsed Docling document.
"""

import logging

from docling_core.types.doc.document import DoclingDocument

from app.core.exceptions import MarkdownExtractionError


logger = logging.getLogger(__name__)


_MIN_VIABLE_MARKDOWN_LENGTH = 20


_SAFE_UNICODE_RANGES: list[tuple[int, int]] = [
    (0x0000, 0x007F),
    (0x0080, 0x00FF),
    (0x0100, 0x024F),

    # Arabic
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),

    (0x2000, 0x206F),
]


_GARBLED_SAFE_CHAR_THRESHOLD = 0.85


def _is_safe_char(char: str) -> bool:

    codepoint = ord(char)

    return any(
        lower <= codepoint <= upper
        for lower, upper
        in _SAFE_UNICODE_RANGES
    )


def looks_garbled(text: str) -> bool:

    if not text or not text.strip():
        return True

    non_whitespace = [
        char
        for char in text
        if not char.isspace()
    ]

    if not non_whitespace:
        return True

    safe_count = sum(
        1
        for char in non_whitespace
        if _is_safe_char(char)
    )

    safe_ratio = (
        safe_count
        / len(non_whitespace)
    )

    return (
        safe_ratio
        < _GARBLED_SAFE_CHAR_THRESHOLD
    )


def extract_markdown(
    document: DoclingDocument,
) -> str:

    try:
        markdown = (
            document
            .export_to_markdown()
        )

    except Exception as exc:

        logger.exception(
            "Docling Markdown export failed"
        )

        raise MarkdownExtractionError(
            "Failed to export parsed document to Markdown.",
            details={
                "original_error": str(exc)
            },
        ) from exc

    if (
        markdown is None
        or len(markdown.strip())
        < _MIN_VIABLE_MARKDOWN_LENGTH
    ):

        raise MarkdownExtractionError(
            (
                "Parsed document produced little "
                "or no extractable text."
            ),
            details={
                "extracted_length": (
                    len(markdown.strip())
                    if markdown
                    else 0
                )
            },
        )

    logger.info(
        "Extracted Markdown: %d characters",
        len(markdown),
    )

    return markdown