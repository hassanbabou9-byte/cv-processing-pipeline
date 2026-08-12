"""
Text cleaning for extracted Markdown.

Only performs structural cleanup.
"""

import logging
import re
import unicodedata

from app.core.exceptions import MarkdownExtractionError


logger = logging.getLogger(__name__)


_EXCESS_BLANK_LINES_RE = re.compile(
    r"\n{3,}"
)

_TRAILING_WHITESPACE_RE = re.compile(
    r"[ \t]+$",
    flags=re.MULTILINE,
)


_EMAIL_BEFORE_AT_RE = re.compile(
    r"(?<=\w)\s+@\s*"
)

_EMAIL_AFTER_AT_RE = re.compile(
    r"(?<=@)\s+"
)


_COMMON_TLDS = (
    "com",
    "org",
    "net",
    "edu",
    "gov",
    "io",
    "co",
    "info",
    "biz",
    "fr",
    "ma",
    "be",
    "ch",
    "ca",
    "uk",
    "de",
    "es",
    "it",
)


_DOMAIN_DOT_SPACING_RE = re.compile(
    r"\s*\.\s+("
    + "|".join(_COMMON_TLDS)
    + r")\b",
    flags=re.IGNORECASE,
)


def _tighten_email_spacing(
    text: str,
) -> str:

    text = _EMAIL_BEFORE_AT_RE.sub(
        "@",
        text,
    )

    text = _EMAIL_AFTER_AT_RE.sub(
        "",
        text,
    )

    text = _DOMAIN_DOT_SPACING_RE.sub(
        r".\1",
        text,
    )

    return text


def clean_text(
    markdown: str,
) -> str:

    if not markdown:
        raise MarkdownExtractionError(
            "Cannot clean empty Markdown content."
        )

    text = (
        markdown
        .replace("\r\n", "\n")
        .replace("\r", "\n")
    )

    text = "".join(
        char
        for char in text
        if (
            char in ("\n", "\t")
            or unicodedata.category(char)[0]
            != "C"
        )
    )

    text = _TRAILING_WHITESPACE_RE.sub(
        "",
        text,
    )

    text = _EXCESS_BLANK_LINES_RE.sub(
        "\n\n",
        text,
    )

    text = _tighten_email_spacing(
        text
    )

    text = text.strip()

    if not text:
        raise MarkdownExtractionError(
            (
                "Markdown content was empty "
                "after cleaning."
            )
        )

    logger.debug(
        "Cleaned Markdown: %d characters "
        "(from %d raw)",
        len(text),
        len(markdown),
    )

    return text