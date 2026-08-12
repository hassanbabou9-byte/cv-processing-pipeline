"""
API-layer request/response models.

These are HTTP contract models — distinct from schemas/cv_extraction.py,
which models the LLM's output shape. Nothing here is shared with the
LLM layer; the API layer's concern is "what does the client send/receive,"
not "what does the CV JSON look like."
"""

from typing import Literal

from pydantic import BaseModel

from app.schemas.cv_extraction import CVExtraction


class UploadResultItem(BaseModel):
    """Result of processing a single uploaded file within a batch."""

    filename: str
    status: Literal["success", "error"]
    cv_id: str | None = None
    collaborateur_id: str | None = None
    markdown_preview: str | None = None
    character_count: int | None = None
    error_message: str | None = None


class UploadResponse(BaseModel):
    """Response returned by POST /upload for a batch of one or more files."""

    total_files: int
    successful: int
    failed: int
    results: list[UploadResultItem]


class ErrorResponse(BaseModel):
    """Standard error response shape returned by centralized exception handlers."""

    error: str
    message: str
    details: dict = {}


class ProcessResponse(BaseModel):
    """Response returned by POST /process/{cv_id} — the LLM-extracted CV data."""

    cv_id: str
    extraction: CVExtraction