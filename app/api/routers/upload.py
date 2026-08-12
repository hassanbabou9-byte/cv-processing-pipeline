"""
CV upload router.

Accepts up to 100 CV files (PDF/DOCX) in a single
multipart/form-data request.

Each CV is processed independently through the complete pipeline:

    Upload
        ↓
    Docling parsing
        ↓
    Markdown extraction
        ↓
    LLM extraction
        ↓
    Pydantic validation
        ↓
    Normalization
        ↓
    ORM mapping
        ↓
    PostgreSQL persistence

A failure on one CV does not stop the remaining CVs.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.api.dependencies import CVProcessingServiceDep, DbSessionDep
from app.schemas.api_models import UploadResponse


logger = logging.getLogger(__name__)

router = APIRouter(tags=["upload"])


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_FILES_PER_BATCH = 100


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=UploadResponse,
)
async def upload_cvs(
    service: CVProcessingServiceDep,
    db: DbSessionDep,
    files: Annotated[
        list[UploadFile],
        File(
            ...,
            description=(
                "CV files (PDF or DOCX). "
                "Maximum 100 files per request."
            ),
        ),
    ],
) -> UploadResponse:
    """
    Upload up to 100 CV files.

    Each CV is processed independently.

    Supported formats:
        - PDF
        - DOCX

    Maximum:
        - 100 files per request

    A failure while processing one CV does not stop the processing
    of the remaining CVs.
    """

    # ------------------------------------------------------------------
    # Validate that at least one file was provided
    # ------------------------------------------------------------------

    if not files:
        raise HTTPException(
            status_code=400,
            detail="At least one CV file must be provided.",
        )

    # ------------------------------------------------------------------
    # Validate maximum batch size
    # ------------------------------------------------------------------

    if len(files) > MAX_FILES_PER_BATCH:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Too many files. Maximum {MAX_FILES_PER_BATCH} "
                "CV files are allowed per request."
            ),
        )

    logger.info(
        "Received CV upload batch: %d file(s)",
        len(files),
    )

    # ------------------------------------------------------------------
    # Read uploaded files
    # ------------------------------------------------------------------

    file_data: list[tuple[str, bytes]] = []

    for upload_file in files:
        filename = upload_file.filename or "unnamed_file"

        logger.debug(
            "Reading uploaded file: %s",
            filename,
        )

        try:
            content = await upload_file.read()

        except Exception as exc:
            logger.exception(
                "Failed to read uploaded file: %s",
                filename,
            )

            raise HTTPException(
                status_code=400,
                detail=(
                    f"Failed to read uploaded file '{filename}'."
                ),
            ) from exc

        if not content:
            logger.warning(
                "Uploaded file is empty: %s",
                filename,
            )

        file_data.append(
            (
                filename,
                content,
            )
        )

    # ------------------------------------------------------------------
    # Process complete batch
    # ------------------------------------------------------------------
    #
    # IMPORTANT:
    #
    # The service is responsible for processing each CV independently.
    # Do NOT wrap the entire call in a transaction here.
    #
    # If CV #3 fails, the service must still process CV #4, #5, etc.
    # ------------------------------------------------------------------

    results = service.process_uploads_full_pipeline(
        file_data,
        db,
    )

    # ------------------------------------------------------------------
    # Calculate batch statistics
    # ------------------------------------------------------------------

    successful = sum(
        1
        for result in results
        if result.status == "success"
    )

    failed = len(results) - successful

    logger.info(
        "CV batch completed: total=%d successful=%d failed=%d",
        len(results),
        successful,
        failed,
    )

    # ------------------------------------------------------------------
    # Return batch response
    # ------------------------------------------------------------------

    return UploadResponse(
        total_files=len(results),
        successful=successful,
        failed=failed,
        results=results,
    )