"""
CV processing service.

Complete pipeline:

    validation
        ↓
    file storage
        ↓
    Docling
        ↓
    OCR fallback when necessary
        ↓
    text cleaning
        ↓
    LLM extraction
        ↓
    Pydantic validation
        ↓
    normalization
        ↓
    DB mapping
        ↓
    PostgreSQL persistence

Every CV is processed independently.
"""

import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.core.exceptions import (
    AppException,
    DocumentParsingError,
    EntityNotFoundError,
    FileTooLargeError,
    UnsupportedFileFormatError,
)
from app.llm.chains.cv_extraction_chain import extract_cv_data
from app.mappers.db_mapper import map_to_entities
from app.mappers.normalization.normalizer import normalize_cv
from app.parsers.docling.document_parser import (
    SUPPORTED_EXTENSIONS,
    parse_document,
)
from app.parsers.docling.markdown_extractor import (
    extract_markdown,
    looks_garbled,
)
from app.parsers.docling.text_cleaner import clean_text
from app.repositories.collaborateur_repository import (
    CollaborateurRepository,
)
from app.schemas.api_models import UploadResultItem
from app.schemas.cv_extraction import CVExtraction
from app.utils.file_storage import (
    read_parsed_markdown,
    save_parsed_markdown,
    save_upload,
)

logger = logging.getLogger(__name__)

_PREVIEW_LENGTH = 300


class CVProcessingService:
    """Orchestrates the complete CV processing pipeline."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _validate(
        self,
        filename: str,
        file_bytes: bytes,
    ) -> None:

        extension = (
            "."
            + filename.rsplit(".", 1)[-1].lower()
            if "." in filename
            else ""
        )

        if extension not in SUPPORTED_EXTENSIONS:
            raise UnsupportedFileFormatError(
                (
                    f"Unsupported file format: '{extension}'. "
                    f"Supported formats are: "
                    f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}."
                ),
                details={"filename": filename},
            )

        max_bytes = (
            self._settings.max_upload_size_mb
            * 1024
            * 1024
        )

        if len(file_bytes) > max_bytes:
            raise FileTooLargeError(
                (
                    f"File '{filename}' exceeds the maximum "
                    f"allowed size of "
                    f"{self._settings.max_upload_size_mb} MB."
                ),
                details={
                    "filename": filename,
                    "size_bytes": len(file_bytes),
                },
            )

        if not file_bytes:
            raise DocumentParsingError(
                f"File '{filename}' is empty.",
                details={"filename": filename},
            )

    def _parse_to_clean_markdown(
        self,
        saved_path: Path,
    ) -> str:

        document = parse_document(saved_path)

        raw_markdown = extract_markdown(document)

        if looks_garbled(raw_markdown):
            logger.warning(
                "Garbled extraction detected for %s; "
                "retrying with OCR.",
                saved_path.name,
            )

            document = parse_document(
                saved_path,
                force_ocr=True,
            )

            raw_markdown = extract_markdown(document)

            if looks_garbled(raw_markdown):
                raise DocumentParsingError(
                    (
                        f"'{saved_path.name}' could not be read "
                        f"correctly even with OCR."
                    ),
                    details={
                        "filename": saved_path.name,
                    },
                )

        markdown = clean_text(raw_markdown)

        if not markdown.strip():
            raise DocumentParsingError(
                f"'{saved_path.name}' contains no readable text.",
                details={
                    "filename": saved_path.name,
                },
            )

        return markdown

    def process_single_upload(
        self,
        filename: str,
        file_bytes: bytes,
    ) -> UploadResultItem:

        try:
            self._validate(
                filename,
                file_bytes,
            )

            cv_id, saved_path = save_upload(
                file_bytes,
                filename,
                self._settings,
            )

            markdown = self._parse_to_clean_markdown(
                saved_path
            )

            save_parsed_markdown(
                cv_id,
                markdown,
                self._settings,
            )

            return UploadResultItem(
                filename=filename,
                status="success",
                cv_id=cv_id,
                markdown_preview=markdown[:_PREVIEW_LENGTH],
                character_count=len(markdown),
            )

        except AppException as exc:
            logger.warning(
                "Upload failed: %s | %s",
                filename,
                exc.message,
            )

            return UploadResultItem(
                filename=filename,
                status="error",
                error_message=exc.message,
            )

        except Exception as exc:
            logger.exception(
                "Unexpected upload failure: %s",
                filename,
            )

            return UploadResultItem(
                filename=filename,
                status="error",
                error_message=f"Unexpected error: {exc}",
            )

    def process_uploads(
        self,
        files: list[tuple[str, bytes]],
    ) -> list[UploadResultItem]:

        return [
            self.process_single_upload(
                filename,
                file_bytes,
            )
            for filename, file_bytes in files
        ]

    def process_cv_extraction(
        self,
        cv_id: str,
    ) -> CVExtraction:

        markdown = read_parsed_markdown(
            cv_id,
            self._settings,
        )

        if markdown is None:
            raise EntityNotFoundError(
                (
                    f"No parsed CV found for "
                    f"cv_id='{cv_id}'."
                ),
                details={"cv_id": cv_id},
            )

        logger.info(
            "Starting LLM extraction: cv_id=%s",
            cv_id,
        )

        extraction = extract_cv_data(
            markdown,
            self._settings,
        )

        logger.info(
            "LLM extraction completed: cv_id=%s",
            cv_id,
        )

        return extraction

    def process_full_pipeline(
        self,
        filename: str,
        file_bytes: bytes,
        db: Session,
    ) -> UploadResultItem:

        cv_id: str | None = None

        try:
            # ------------------------------------------------------
            # 1. Validation
            # ------------------------------------------------------
            self._validate(
                filename,
                file_bytes,
            )

            # ------------------------------------------------------
            # 2. Store original file
            # ------------------------------------------------------
            cv_id, saved_path = save_upload(
                file_bytes,
                filename,
                self._settings,
            )

            # ------------------------------------------------------
            # 3. Parse with Docling / OCR fallback
            # ------------------------------------------------------
            markdown = self._parse_to_clean_markdown(
                saved_path
            )

            save_parsed_markdown(
                cv_id,
                markdown,
                self._settings,
            )

            # ------------------------------------------------------
            # 4. LLM extraction
            # ------------------------------------------------------
            extraction = extract_cv_data(
                markdown,
                self._settings,
            )

            # ------------------------------------------------------
            # 5. Normalization
            # ------------------------------------------------------
            normalized = normalize_cv(
                extraction
            )

            # ------------------------------------------------------
            # 6. ORM mapping
            # ------------------------------------------------------
            mapped = map_to_entities(
                normalized
            )

            # ------------------------------------------------------
            # 7. Persistence
            # ------------------------------------------------------
            repository = CollaborateurRepository(
                db
            )

            saved = repository.save(
                mapped
            )

            logger.info(
                (
                    "CV pipeline succeeded: "
                    "filename=%s cv_id=%s collaborateur_id=%s"
                ),
                filename,
                cv_id,
                saved.id,
            )

            return UploadResultItem(
                filename=filename,
                status="success",
                cv_id=cv_id,
                collaborateur_id=str(saved.id),
                markdown_preview=markdown[:_PREVIEW_LENGTH],
                character_count=len(markdown),
            )

        except AppException as exc:
            logger.warning(
                (
                    "CV pipeline failed: "
                    "filename=%s cv_id=%s error=%s"
                ),
                filename,
                cv_id,
                exc.message,
            )

            return UploadResultItem(
                filename=filename,
                status="error",
                cv_id=cv_id,
                error_message=exc.message,
            )

        except Exception as exc:
            logger.exception(
                (
                    "Unexpected CV pipeline failure: "
                    "filename=%s cv_id=%s"
                ),
                filename,
                cv_id,
            )

            return UploadResultItem(
                filename=filename,
                status="error",
                cv_id=cv_id,
                error_message=f"Unexpected error: {exc}",
            )

    def process_uploads_full_pipeline(
        self,
        files: list[tuple[str, bytes]],
        db: Session,
    ) -> list[UploadResultItem]:

        """
        Process every CV independently.

        The repository is responsible for the transaction boundary
        of each individual CV. Therefore a failure for one CV must
        not prevent subsequent CVs from being processed.
        """

        results: list[UploadResultItem] = []

        for filename, file_bytes in files:
            result = self.process_full_pipeline(
                filename,
                file_bytes,
                db,
            )

            results.append(result)

        return results