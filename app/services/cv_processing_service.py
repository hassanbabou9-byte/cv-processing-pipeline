"""
CV processing service.

Complete pipeline:

    validation
        ↓
    file storage
        ↓
    candidate image extraction
        ↓
    MinIO image storage
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

Image extraction and MinIO storage are optional:
a CV without an image remains a valid CV.

Existing candidates are resolved by email.

When an existing candidate receives a new image:

    new image
        ↓
    upload new MinIO object
        ↓
    update PostgreSQL image_object_key
        ↓
    delete previous MinIO object

When the new CV has no image:

    existing PostgreSQL image is preserved.

The service orchestrates the application pipeline.

Database operations remain inside repositories.
"""


from __future__ import annotations

import logging
import html
import re
import unicodedata
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
from app.llm.chains.cv_extraction_chain import (
    extract_cv_data,
)
from app.mappers.db_mapper import (
    map_to_entities,
)
from app.mappers.normalization.normalizer import (
    normalize_cv,
)
from app.parsers.docling.document_parser import (
    SUPPORTED_EXTENSIONS,
    parse_document,
)
from app.parsers.docling.markdown_extractor import (
    extract_markdown,
    looks_garbled,
)
from app.parsers.docling.text_cleaner import (
    clean_text,
)
from app.repositories.collaborateur_repository import (
    CollaborateurRepository,
)
from app.schemas.api_models import (
    UploadResultItem,
)
from app.schemas.cv_extraction import (
    CVExtraction,
)
from app.services.image_extraction.candidate_image_extractor import (
    CandidateImageExtractor,
)
from app.services.storage.minio_storage import (
    MinIOStorage,
)
from app.utils.file_storage import (
    read_parsed_markdown,
    save_parsed_markdown,
    save_upload,
)


logger = logging.getLogger(__name__)


_PREVIEW_LENGTH = 300

_BIOGRAPHY_HEADINGS = {
    "A PROPOS",
    "OBJECTIF",
    "PROFIL",
    "PROFIL PROFESSIONNEL",
    "PROFILE",
    "PROFESSIONAL SUMMARY",
    "RESUME",
    "SUMMARY",
}

_SECTION_HEADINGS = _BIOGRAPHY_HEADINGS | {
    "ACTIVITES",
    "CERTIFICATIONS",
    "COMPETENCES",
    "COMPETENCES TECHNIQUES",
    "DIPLOMES",
    "EDUCATION",
    "EXPERIENCE",
    "EXPERIENCES",
    "EXPERIENCE PROFESSIONNELLE",
    "FORMATIONS",
    "FORMATION",
    "LANGUES",
    "PROJETS",
    "TECHNICAL SKILLS",
    "TECHNIQUES",
}


def _normalized_heading(line: str) -> str:
    """Normalize a Markdown heading for section matching."""

    without_markup = re.sub(r"[*#_:`]", "", line)
    without_accents = unicodedata.normalize(
        "NFKD",
        without_markup,
    ).encode("ascii", "ignore").decode("ascii")

    return " ".join(without_accents.upper().split())


def _biography_from_markdown(markdown: str) -> str | None:
    """Extract text from an explicitly labelled profile section."""

    lines = markdown.splitlines()
    biography_lines: list[str] = []
    collecting = False

    for line in lines:
        heading = _normalized_heading(line)

        if heading in _BIOGRAPHY_HEADINGS:
            collecting = True
            continue

        if (
            collecting
            and line.lstrip().startswith("#")
        ):
            break

        if collecting and heading in _SECTION_HEADINGS:
            break

        if collecting and line.strip():
            biography_lines.append(line.strip())

    biography = " ".join(biography_lines).strip()

    if biography:
        return biography[:500]

    # Some CV templates put the summary in the header between the
    # candidate's title and the contact details instead of using a section.
    first_line = next(
        (line.strip() for line in lines if line.strip()),
        "",
    )
    bold_parts = re.findall(
        r"\*\*(.+?)\*\*",
        first_line,
    )

    if len(bold_parts) >= 2:
        first_bold = f"**{bold_parts[0]}**"
        second_bold = f"**{bold_parts[1]}**"
        if _normalized_heading(bold_parts[1]) in _SECTION_HEADINGS:
            header_biography = first_line.split(
                first_bold,
                1,
            )[1].split(
                second_bold,
                1,
            )[0]
            header_biography = html.unescape(
                " ".join(header_biography.split())
            ).strip()
            return header_biography[:500] or None
        else:
            header_biography = first_line.split(
                second_bold,
                1,
            )[1]
            header_biography = header_biography.split(
                f"**{bold_parts[2]}**",
                1,
            )[0] if len(bold_parts) >= 3 else header_biography
        header_biography = re.sub(
            r"^\s*\|\s*|\s*\|\s*$",
            "",
            header_biography,
        )
        header_biography = re.split(
            r"\s{2,}",
            header_biography.strip(),
            maxsplit=1,
        )[0]
        header_biography = html.unescape(
            " ".join(header_biography.split())
        ).strip()

        return header_biography[:500] or None

    for index, line in enumerate(lines):
        if not line.lstrip().startswith("#"):
            continue

        heading = _normalized_heading(line)
        if heading in _SECTION_HEADINGS or index + 1 >= len(lines):
            continue

        next_line = next(
            (candidate.strip() for candidate in lines[index + 1:] if candidate.strip()),
            "",
        )
        if next_line and not next_line.startswith("#"):
            return html.unescape(next_line)[:500]

    return None


def _ensure_biography(
    extraction: CVExtraction,
    markdown: str,
) -> CVExtraction:
    """Fill a missing LLM biography from a labelled source section."""

    if not extraction.a_propos.strip():
        biography = _biography_from_markdown(markdown)

        if biography:
            extraction.a_propos = biography
            logger.info(
                "Biography recovered from a labelled Markdown section."
            )

    return extraction


class CVProcessingService:
    """
    Orchestrates the complete CV processing pipeline.
    """

    # ======================================================================
    # Initialization
    # ======================================================================

    def __init__(
        self,
        settings: Settings,
    ) -> None:

        self._settings = settings

        self._image_extractor = (
            CandidateImageExtractor()
        )

        self._minio_storage = (
            MinIOStorage(
                settings
            )
        )

    # ======================================================================
    # Validation
    # ======================================================================

    def _validate(
        self,
        filename: str,
        file_bytes: bytes,
    ) -> None:

        extension = (
            "."
            + filename.rsplit(
                ".",
                1,
            )[-1].lower()
            if "." in filename
            else ""
        )

        if extension not in SUPPORTED_EXTENSIONS:

            raise UnsupportedFileFormatError(
                (
                    f"Unsupported file format: "
                    f"'{extension}'. "
                    f"Supported formats are: "
                    f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}."
                ),
                details={
                    "filename": filename,
                },
            )

        max_bytes = (
            self._settings.max_upload_size_mb
            * 1024
            * 1024
        )

        if len(file_bytes) > max_bytes:

            raise FileTooLargeError(
                (
                    f"File '{filename}' exceeds "
                    f"the maximum allowed size of "
                    f"{self._settings.max_upload_size_mb} MB."
                ),
                details={
                    "filename": filename,
                    "size_bytes": len(file_bytes),
                    "max_size_bytes": max_bytes,
                },
            )

        if not file_bytes:

            raise DocumentParsingError(
                (
                    f"File '{filename}' is empty."
                ),
                details={
                    "filename": filename,
                },
            )

    # ======================================================================
    # Docling parsing
    # ======================================================================

    def _parse_to_clean_markdown(
        self,
        saved_path: Path,
    ) -> str:

        try:

            document = parse_document(
                saved_path
            )

            raw_markdown = extract_markdown(
                document
            )

        except AppException:
            raise

        except Exception as exc:

            logger.exception(
                "Docling parsing failed: %s",
                saved_path.name,
            )

            raise DocumentParsingError(
                (
                    f"Failed to parse "
                    f"'{saved_path.name}'."
                ),
                details={
                    "filename": saved_path.name,
                    "original_error": str(exc),
                },
            ) from exc

        if looks_garbled(
            raw_markdown
        ):

            logger.warning(
                (
                    "Garbled extraction detected for %s; "
                    "retrying with OCR."
                ),
                saved_path.name,
            )

            try:

                document = parse_document(
                    saved_path,
                    force_ocr=True,
                )

                raw_markdown = extract_markdown(
                    document
                )

            except AppException:
                raise

            except Exception as exc:

                logger.exception(
                    "OCR parsing failed for %s",
                    saved_path.name,
                )

                raise DocumentParsingError(
                    (
                        f"OCR parsing failed for "
                        f"'{saved_path.name}'."
                    ),
                    details={
                        "filename": saved_path.name,
                        "original_error": str(exc),
                    },
                ) from exc

            if looks_garbled(
                raw_markdown
            ):

                raise DocumentParsingError(
                    (
                        f"'{saved_path.name}' could not "
                        f"be read correctly even with OCR."
                    ),
                    details={
                        "filename": saved_path.name,
                    },
                )

        markdown = clean_text(
            raw_markdown
        )

        if not markdown.strip():

            raise DocumentParsingError(
                (
                    f"'{saved_path.name}' "
                    f"contains no readable text."
                ),
                details={
                    "filename": saved_path.name,
                },
            )

        return markdown

    # ======================================================================
    # Candidate image extraction + MinIO
    # ======================================================================

    def _extract_and_store_candidate_image(
        self,
        cv_id: str,
        saved_path: Path,
    ) -> str | None:

        try:

            extracted_image = (
                self._image_extractor.extract(
                    saved_path
                )
            )

        except Exception:

            logger.exception(
                (
                    "Candidate image extraction "
                    "failed: filename=%s cv_id=%s"
                ),
                saved_path.name,
                cv_id,
            )

            return None

        if extracted_image is None:

            logger.info(
                (
                    "No candidate image found: "
                    "filename=%s cv_id=%s"
                ),
                saved_path.name,
                cv_id,
            )

            return None

        object_name = (
            f"candidates/"
            f"{cv_id}/"
            f"photo{extracted_image.extension}"
        )

        try:

            stored_object = (
                self._minio_storage.upload_image(
                    object_name=object_name,
                    image_data=extracted_image.data,
                    content_type=(
                        extracted_image.content_type
                    ),
                )
            )

            logger.info(
                (
                    "Candidate image stored successfully: "
                    "filename=%s cv_id=%s object=%s"
                ),
                saved_path.name,
                cv_id,
                stored_object,
            )

            return stored_object

        except Exception:

            logger.exception(
                (
                    "Candidate image upload failed: "
                    "filename=%s cv_id=%s object=%s"
                ),
                saved_path.name,
                cv_id,
                object_name,
            )

            return None

    # ======================================================================
    # Delete old candidate image
    # ======================================================================

    def _delete_old_candidate_image(
        self,
        old_object_key: str | None,
        new_object_key: str | None,
    ) -> None:
        """
        Delete the previous candidate image after the new image reference
        has been successfully persisted.

        The new object is never deleted here.

        If deletion of the old object fails, the candidate remains valid;
        PostgreSQL already points to the new image.
        """

        if not old_object_key:
            return

        if not new_object_key:
            return

        if old_object_key == new_object_key:
            return

        try:

            if self._minio_storage.image_exists(
                old_object_key
            ):

                self._minio_storage.delete_image(
                    old_object_key
                )

                logger.info(
                    (
                        "Deleted previous candidate image: "
                        "old_object=%s new_object=%s"
                    ),
                    old_object_key,
                    new_object_key,
                )

            else:

                logger.debug(
                    (
                        "Previous candidate image does not exist "
                        "in MinIO: %s"
                    ),
                    old_object_key,
                )

        except Exception:

            # -----------------------------------------------------------
            # Do not fail an otherwise successful CV update because an
            # obsolete MinIO object could not be deleted.
            #
            # PostgreSQL already points to the new image.
            # -----------------------------------------------------------

            logger.exception(
                (
                    "Failed to delete previous candidate image: "
                    "%s"
                ),
                old_object_key,
            )

    # ======================================================================
    # Simple upload / parsing flow
    # ======================================================================

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

            self._extract_and_store_candidate_image(
                cv_id,
                saved_path,
            )

            markdown = (
                self._parse_to_clean_markdown(
                    saved_path
                )
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
                markdown_preview=(
                    markdown[
                        :_PREVIEW_LENGTH
                    ]
                ),
                character_count=len(
                    markdown
                ),
            )

        except AppException as exc:

            logger.warning(
                (
                    "Upload failed: "
                    "filename=%s error=%s"
                ),
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
                (
                    "Unexpected upload failure: "
                    "filename=%s"
                ),
                filename,
            )

            return UploadResultItem(
                filename=filename,
                status="error",
                error_message=(
                    f"Unexpected error: {exc}"
                ),
            )

    # ======================================================================
    # Simple batch upload
    # ======================================================================

    def process_uploads(
        self,
        files: list[
            tuple[str, bytes]
        ],
    ) -> list[UploadResultItem]:

        results: list[
            UploadResultItem
        ] = []

        for filename, file_bytes in files:

            result = (
                self.process_single_upload(
                    filename,
                    file_bytes,
                )
            )

            results.append(
                result
            )

        return results

    # ======================================================================
    # LLM extraction
    # ======================================================================

    def process_cv_extraction(
        self,
        cv_id: str,
    ) -> CVExtraction:

        markdown = (
            read_parsed_markdown(
                cv_id,
                self._settings,
            )
        )

        if markdown is None:

            raise EntityNotFoundError(
                (
                    f"No parsed CV found "
                    f"for cv_id='{cv_id}'."
                ),
                details={
                    "cv_id": cv_id,
                },
            )

        logger.info(
            "Starting LLM extraction: cv_id=%s",
            cv_id,
        )

        extraction = extract_cv_data(
            markdown,
            self._settings,
        )

        extraction = _ensure_biography(
            extraction,
            markdown,
        )

        logger.info(
            "LLM extraction completed: cv_id=%s",
            cv_id,
        )

        return extraction

    # ======================================================================
    # Full pipeline
    # ======================================================================

    def process_full_pipeline(
        self,
        filename: str,
        file_bytes: bytes,
        db: Session,
    ) -> UploadResultItem:

        cv_id: str | None = None

        try:

            # ==========================================================
            # 1. Validation
            # ==========================================================

            self._validate(
                filename,
                file_bytes,
            )

            # ==========================================================
            # 2. Store original CV
            # ==========================================================

            cv_id, saved_path = save_upload(
                file_bytes,
                filename,
                self._settings,
            )

            logger.info(
                (
                    "CV stored successfully: "
                    "filename=%s cv_id=%s path=%s"
                ),
                filename,
                cv_id,
                saved_path,
            )

            # ==========================================================
            # 3. Extract candidate image + MinIO
            # ==========================================================

            image_object_key = (
                self._extract_and_store_candidate_image(
                    cv_id,
                    saved_path,
                )
            )

            if image_object_key:

                logger.info(
                    (
                        "Candidate image available: "
                        "cv_id=%s object=%s"
                    ),
                    cv_id,
                    image_object_key,
                )

            else:

                logger.info(
                    (
                        "Candidate has no stored image: "
                        "cv_id=%s"
                    ),
                    cv_id,
                )

            # ==========================================================
            # 4. Parse with Docling / OCR fallback
            # ==========================================================

            markdown = (
                self._parse_to_clean_markdown(
                    saved_path
                )
            )

            # ==========================================================
            # 5. Save parsed Markdown
            # ==========================================================

            save_parsed_markdown(
                cv_id,
                markdown,
                self._settings,
            )

            logger.info(
                (
                    "Markdown saved: "
                    "cv_id=%s characters=%d"
                ),
                cv_id,
                len(markdown),
            )

            # ==========================================================
            # 6. LLM extraction
            # ==========================================================

            logger.info(
                "Starting CV extraction: cv_id=%s",
                cv_id,
            )

            extraction = extract_cv_data(
                markdown,
                self._settings,
            )

            extraction = _ensure_biography(
                extraction,
                markdown,
            )

            logger.info(
                "CV extraction completed: cv_id=%s",
                cv_id,
            )

            # ==========================================================
            # 7. Normalization
            # ==========================================================

            normalized = normalize_cv(
                extraction
            )

            logger.info(
                "CV normalization completed: cv_id=%s",
                cv_id,
            )

            # ==========================================================
            # 8. Find existing candidate BEFORE persistence
            # ==========================================================
            #
            # IMPORTANT:
            #
            # This lookup is delegated to the repository.
            #
            # The service does NOT execute SQL.
            #
            # We need the old image key so that when a new image is
            # successfully persisted we can remove the obsolete MinIO
            # object afterwards.
            # ==========================================================

            repository = (
                CollaborateurRepository(
                    db
                )
            )

            candidate_email = (
                normalized.collaborateur.email
            )

            existing_candidate = (
                repository.get_by_email(
                    candidate_email
                )
            )

            old_image_object_key = None

            if existing_candidate is not None:

                old_image_object_key = (
                    existing_candidate.image_object_key
                )

                logger.info(
                    (
                        "Existing Collaborateur detected: "
                        "email=%s id=%s old_image=%s"
                    ),
                    existing_candidate.email,
                    existing_candidate.id,
                    old_image_object_key or "none",
                )

            # ==========================================================
            # 9. ORM mapping
            # ==========================================================
            #
            # IMPORTANT:
            #
            # The existing extraction, normalization and mapping process
            # is unchanged.
            #
            # The MinIO key is simply passed to the mapper.
            # ==========================================================

            mapped = map_to_entities(
                normalized,
                image_object_key=(
                    image_object_key
                ),
            )

            logger.info(
                (
                    "Database mapping completed: "
                    "cv_id=%s image_object_key=%s"
                ),
                cv_id,
                image_object_key or "NULL",
            )

            # ==========================================================
            # 10. PostgreSQL persistence
            # ==========================================================

            saved = repository.save(
                mapped
            )

            # ==========================================================
            # 11. Verify persisted image reference
            # ==========================================================

            if image_object_key is not None:

                if (
                    saved.image_object_key
                    != image_object_key
                ):

                    logger.error(
                        (
                            "Image object key mismatch after "
                            "PostgreSQL persistence: "
                            "cv_id=%s "
                            "expected=%s "
                            "actual=%s"
                        ),
                        cv_id,
                        image_object_key,
                        saved.image_object_key,
                    )

                    raise RuntimeError(
                        (
                            "Candidate image object key was not "
                            "persisted correctly."
                        )
                    )

            # ==========================================================
            # 12. Delete previous MinIO image
            # ==========================================================
            #
            # Only after PostgreSQL successfully points to the new image.
            #
            # If the new CV has no image:
            #
            #     old image is preserved.
            #
            # If this is a new candidate:
            #
            #     old image does not exist.
            # ==========================================================

            if (
                existing_candidate is not None
                and image_object_key is not None
            ):

                self._delete_old_candidate_image(
                    old_object_key=(
                        old_image_object_key
                    ),
                    new_object_key=(
                        image_object_key
                    ),
                )

            # ==========================================================
            # 13. Success
            # ==========================================================

            logger.info(
                (
                    "CV pipeline succeeded: "
                    "filename=%s "
                    "cv_id=%s "
                    "collaborateur_id=%s "
                    "image=%s"
                ),
                filename,
                cv_id,
                saved.id,
                saved.image_object_key or "none",
            )

            return UploadResultItem(
                filename=filename,
                status="success",
                cv_id=cv_id,
                collaborateur_id=(
                    str(saved.id)
                ),
                markdown_preview=(
                    markdown[
                        :_PREVIEW_LENGTH
                    ]
                ),
                character_count=len(
                    markdown
                ),
            )

        # ==============================================================
        # Application errors
        # ==============================================================

        except AppException as exc:

            logger.warning(
                (
                    "CV pipeline failed: "
                    "filename=%s "
                    "cv_id=%s "
                    "error=%s"
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

        # ==============================================================
        # Unexpected errors
        # ==============================================================

        except Exception as exc:

            logger.exception(
                (
                    "Unexpected CV pipeline failure: "
                    "filename=%s "
                    "cv_id=%s"
                ),
                filename,
                cv_id,
            )

            return UploadResultItem(
                filename=filename,
                status="error",
                cv_id=cv_id,
                error_message=(
                    f"Unexpected error: {exc}"
                ),
            )

    # ======================================================================
    # Full batch pipeline
    # ======================================================================

    def process_uploads_full_pipeline(
        self,
        files: list[
            tuple[str, bytes]
        ],
        db: Session,
    ) -> list[UploadResultItem]:

        results: list[
            UploadResultItem
        ] = []

        for filename, file_bytes in files:

            logger.info(
                (
                    "Starting batch CV processing: "
                    "filename=%s"
                ),
                filename,
            )

            result = (
                self.process_full_pipeline(
                    filename,
                    file_bytes,
                    db,
                )
            )

            results.append(
                result
            )

            logger.info(
                (
                    "Finished batch CV processing: "
                    "filename=%s status=%s"
                ),
                filename,
                result.status,
            )

        return results