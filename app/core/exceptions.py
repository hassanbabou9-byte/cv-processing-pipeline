"""
Domain exception hierarchy.

Every layer of the pipeline (parsing, LLM, validation, normalization,
database) raises one of these instead of a bare Exception. This is
what allows `api/error_handlers.py` to map failures to consistent,
typed HTTP responses without the API layer knowing *how* something
failed internally — only *what kind* of failure it was.

Rule of thumb: if you're about to `raise Exception(...)` or
`raise ValueError(...)` anywhere in app/, raise one of these instead.
"""

from typing import Any


class AppException(Exception):
    """
    Base class for all domain exceptions in the application.

    Attributes:
        message: Human-readable description of what went wrong.
        details: Optional structured context (field names, raw values,
            provider names, etc.) useful for logging and API responses.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, details={self.details!r})"


# ------------------------------------------------------------------
# File / upload layer
# ------------------------------------------------------------------
class UnsupportedFileFormatError(AppException):
    """Raised when an uploaded file's extension/type is not supported."""


class FileTooLargeError(AppException):
    """Raised when an uploaded file exceeds the configured size limit."""


# ------------------------------------------------------------------
# Parsing layer (Docling)
# ------------------------------------------------------------------
class DocumentParsingError(AppException):
    """Raised when Docling fails to parse a PDF/DOCX file (corrupted, unreadable, etc.)."""


class MarkdownExtractionError(AppException):
    """Raised when clean Markdown cannot be extracted from a parsed document."""


# ------------------------------------------------------------------
# LLM layer
# ------------------------------------------------------------------
class LLMProviderError(AppException):
    """Raised when the configured LLM provider fails (API error, network failure)."""


class LLMTimeoutError(AppException):
    """Raised when an LLM call exceeds the configured timeout."""


class LLMOutputParsingError(AppException):
    """Raised when the LLM response is not valid JSON or doesn't match the expected shape."""


# ------------------------------------------------------------------
# Validation / normalization layer
# ------------------------------------------------------------------
class SchemaValidationError(AppException):
    """Raised when extracted data fails Pydantic schema validation."""


class NormalizationError(AppException):
    """Raised when normalization (fallbacks, enum mapping, date parsing) fails."""


# ------------------------------------------------------------------
# Database layer
# ------------------------------------------------------------------
class DatabaseError(AppException):
    """Raised for generic database failures (connection, transaction)."""


class RepositoryError(AppException):
    """Raised when a repository operation fails (constraint violation, not found, etc.)."""


class EntityNotFoundError(RepositoryError):
    """Raised when a requested entity does not exist in the database."""