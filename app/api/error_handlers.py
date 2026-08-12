"""
Centralized exception handling.

Maps domain exceptions (core/exceptions.py) to consistent HTTP JSON
responses. Registered once on the FastAPI app in main.py. This is
what lets services and deeper layers raise typed domain exceptions
without knowing anything about HTTP status codes.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AppException,
    DatabaseError,
    DocumentParsingError,
    EntityNotFoundError,
    FileTooLargeError,
    LLMOutputParsingError,
    LLMProviderError,
    LLMTimeoutError,
    MarkdownExtractionError,
    NormalizationError,
    RepositoryError,
    SchemaValidationError,
    UnsupportedFileFormatError,
)
from app.schemas.api_models import ErrorResponse

logger = logging.getLogger(__name__)

# Maps exception types to the HTTP status code they should produce.
# Order doesn't matter here since we match on exact/subclass type below.
_STATUS_CODE_MAP: dict[type[AppException], int] = {
    UnsupportedFileFormatError: status.HTTP_400_BAD_REQUEST,
    FileTooLargeError: status.HTTP_400_BAD_REQUEST,
    DocumentParsingError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    MarkdownExtractionError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    SchemaValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    NormalizationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    LLMOutputParsingError: status.HTTP_502_BAD_GATEWAY,
    LLMProviderError: status.HTTP_502_BAD_GATEWAY,
    LLMTimeoutError: status.HTTP_504_GATEWAY_TIMEOUT,
    EntityNotFoundError: status.HTTP_404_NOT_FOUND,
    RepositoryError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    DatabaseError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def _resolve_status_code(exc: AppException) -> int:
    for exc_type, status_code in _STATUS_CODE_MAP.items():
        if isinstance(exc, exc_type):
            return status_code
    return status.HTTP_500_INTERNAL_SERVER_ERROR


async def _app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    status_code = _resolve_status_code(exc)
    logger.warning(
        "%s on %s %s: %s", exc.__class__.__name__, request.method, request.url.path, exc.message
    )
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error=exc.__class__.__name__,
            message=exc.message,
            details=exc.details,
        ).model_dump(),
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred.",
        ).model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all centralized exception handlers on the FastAPI app."""
    app.add_exception_handler(AppException, _app_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)