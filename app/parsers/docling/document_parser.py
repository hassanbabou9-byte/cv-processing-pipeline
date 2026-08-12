"""
Document parsing via Docling.

Supports PDF and DOCX.

PDFs can optionally be reprocessed using forced full-page OCR when
the normal embedded text extraction appears corrupted.
"""

import logging
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
    PdfPipelineOptions,
)
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
)
from docling_core.types.doc.document import (
    DoclingDocument,
)

from app.core.exceptions import (
    DocumentParsingError,
    UnsupportedFileFormatError,
)


logger = logging.getLogger(__name__)


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
}


_default_converter = DocumentConverter(
    allowed_formats=[
        InputFormat.PDF,
        InputFormat.DOCX,
    ],
)


_ocr_pipeline_options = PdfPipelineOptions()

_ocr_pipeline_options.do_ocr = True
_ocr_pipeline_options.do_table_structure = False

_ocr_pipeline_options.ocr_options = (
    EasyOcrOptions(
        force_full_page_ocr=True
    )
)

_ocr_pipeline_options.images_scale = 4.0


_ocr_converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(
            pipeline_options=(
                _ocr_pipeline_options
            )
        )
    }
)


def parse_document(
    file_path: str | Path,
    force_ocr: bool = False,
) -> DoclingDocument:

    path = Path(file_path)

    if (
        path.suffix.lower()
        not in SUPPORTED_EXTENSIONS
    ):

        raise UnsupportedFileFormatError(
            (
                f"Unsupported file format: "
                f"'{path.suffix}'."
            ),
            details={
                "file_path": str(path),
                "extension": path.suffix,
            },
        )

    if not path.exists():

        raise DocumentParsingError(
            f"File not found: {path}",
            details={
                "file_path": str(path)
            },
        )

    use_ocr = (
        force_ocr
        and path.suffix.lower() == ".pdf"
    )

    converter = (
        _ocr_converter
        if use_ocr
        else _default_converter
    )

    logger.info(
        "Parsing %s force_ocr=%s",
        path.name,
        use_ocr,
    )

    try:

        conversion_result = (
            converter.convert(path)
        )

    except Exception as exc:

        logger.exception(
            "Docling failed to parse %s",
            path.name,
        )

        raise DocumentParsingError(
            (
                f"Failed to parse "
                f"'{path.name}'."
            ),
            details={
                "file_path": str(path),
                "original_error": str(exc),
            },
        ) from exc

    if (
        conversion_result.document
        is None
    ):

        raise DocumentParsingError(
            (
                f"Docling produced no "
                f"document for '{path.name}'."
            ),
            details={
                "file_path": str(path)
            },
        )

    return (
        conversion_result.document
    )