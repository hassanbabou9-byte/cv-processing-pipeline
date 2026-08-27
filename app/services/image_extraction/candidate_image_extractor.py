"""
Candidate image extraction.

Extracts embedded images from PDF and DOCX CV files.

Image extraction is intentionally separated from image storage.

The extractor returns image bytes and metadata; MinIO is responsible
for storing the image later.

The extractor:
    - extracts embedded images from DOCX files
    - extracts embedded images from PDF files
    - ignores very small images
    - uses OpenCV Haar Cascade face detection when available
    - prefers images containing a face
    - falls back to the largest usable image when no face is detected
"""

import io
import logging
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


# ============================================================================
# Optional OpenCV
# ============================================================================

try:
    import cv2

    _OPENCV_AVAILABLE = True

except Exception as exc:
    cv2 = None
    _OPENCV_AVAILABLE = False

    logger.warning(
        "OpenCV is unavailable. Face detection will be disabled: %s",
        exc,
    )


# ============================================================================
# PyMuPDF
# ============================================================================

try:
    import pymupdf

    _PYMUPDF_AVAILABLE = True

except Exception as exc:
    pymupdf = None
    _PYMUPDF_AVAILABLE = False

    logger.warning(
        "PyMuPDF is unavailable. PDF image extraction will be disabled: %s",
        exc,
    )


# ============================================================================
# Extracted image
# ============================================================================


@dataclass
class ExtractedCandidateImage:
    """Image extracted from a candidate CV."""

    data: bytes
    content_type: str
    extension: str


# ============================================================================
# Candidate image extractor
# ============================================================================


class CandidateImageExtractor:
    """
    Extract the most likely candidate photograph from a CV.

    Supported formats:
        - DOCX
        - PDF

    Selection strategy:
        1. Extract all embedded images.
        2. Ignore extremely small images.
        3. Validate images with Pillow.
        4. Detect faces using OpenCV Haar Cascade when available.
        5. Prefer images containing a face.
        6. If no face is detected, fall back to the largest usable image.

    Returns:
        ExtractedCandidateImage | None
    """

    # ------------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------------

    MIN_IMAGE_WIDTH = 100
    MIN_IMAGE_HEIGHT = 100

    # ------------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------------

    def __init__(self) -> None:
        """
        Initialize the candidate image extractor.

        The Haar Cascade is loaded once when the extractor is created.
        """

        self._face_detector = None

        if not _OPENCV_AVAILABLE:
            logger.warning(
                "OpenCV is installed/unavailable. "
                "Face detection will be disabled."
            )
            return

        try:
            cascade_path = (
                Path(cv2.data.haarcascades)
                / "haarcascade_frontalface_default.xml"
            )

            if not cascade_path.exists():
                logger.warning(
                    "Haar Cascade file not found: %s. "
                    "Face detection will be disabled.",
                    cascade_path,
                )
                return

            detector = cv2.CascadeClassifier(
                str(cascade_path)
            )

            if detector.empty():
                logger.warning(
                    "Failed to load Haar Cascade: %s. "
                    "Face detection will be disabled.",
                    cascade_path,
                )
                return

            self._face_detector = detector

            logger.info(
                "Haar Cascade face detector initialized: %s",
                cascade_path,
            )

        except Exception:
            logger.exception(
                "Failed to initialize OpenCV face detector. "
                "Face detection will be disabled."
            )

    # =========================================================================
    # Public API
    # =========================================================================

    def extract(
        self,
        file_path: Path,
    ) -> ExtractedCandidateImage | None:
        """
        Extract the most likely candidate image from a CV.

        Parameters
        ----------
        file_path:
            Path to the PDF or DOCX CV.

        Returns
        -------
        ExtractedCandidateImage | None
            The selected candidate image, or None when no usable
            image is found.
        """

        extension = file_path.suffix.lower()

        if extension == ".docx":
            return self._extract_from_docx(file_path)

        if extension == ".pdf":
            return self._extract_from_pdf(file_path)

        logger.warning(
            "Unsupported file format for image extraction: %s",
            file_path.name,
        )

        return None

    # =========================================================================
    # DOCX
    # =========================================================================

    def _extract_from_docx(
        self,
        file_path: Path,
    ) -> ExtractedCandidateImage | None:
        """
        Extract candidate images from DOCX.

        DOCX files are ZIP archives. Embedded images are stored under:

            word/media/
        """

        try:
            with zipfile.ZipFile(
                file_path,
                "r",
            ) as archive:

                image_files = [
                    name
                    for name in archive.namelist()
                    if name.startswith("word/media/")
                    and not name.endswith("/")
                ]

                if not image_files:
                    logger.info(
                        "No embedded images found in DOCX: %s",
                        file_path.name,
                    )
                    return None

                logger.info(
                    "Found %d embedded image(s) in %s",
                    len(image_files),
                    file_path.name,
                )

                candidates: list[
                    tuple[
                        str,
                        bytes,
                        int,
                        int,
                        int,
                    ]
                ] = []

                for image_name in image_files:

                    try:
                        image_bytes = archive.read(
                            image_name
                        )

                        image = Image.open(
                            io.BytesIO(image_bytes)
                        )

                        width, height = image.size

                        # ----------------------------------------------------
                        # Ignore tiny decorative images/icons
                        # ----------------------------------------------------

                        if (
                            width < self.MIN_IMAGE_WIDTH
                            or height < self.MIN_IMAGE_HEIGHT
                        ):
                            logger.debug(
                                "Ignoring small image %s: %sx%s",
                                image_name,
                                width,
                                height,
                            )
                            continue

                        face_count = self._detect_faces(
                            image_bytes
                        )

                        candidates.append(
                            (
                                image_name,
                                image_bytes,
                                width,
                                height,
                                face_count,
                            )
                        )

                        logger.debug(
                            (
                                "DOCX image candidate: %s "
                                "size=%sx%s faces=%d"
                            ),
                            image_name,
                            width,
                            height,
                            face_count,
                        )

                    except Exception:
                        logger.warning(
                            "Could not read embedded image: %s",
                            image_name,
                            exc_info=True,
                        )

                if not candidates:
                    logger.info(
                        "No usable candidate image found in %s",
                        file_path.name,
                    )
                    return None

                selected = self._select_best_candidate(
                    candidates
                )

                (
                    image_name,
                    image_bytes,
                    width,
                    height,
                    face_count,
                ) = selected

                content_type, extension = (
                    self._detect_image_type(
                        image_bytes
                    )
                )

                logger.info(
                    (
                        "Selected DOCX candidate image: %s "
                        "(%sx%s, faces=%d)"
                    ),
                    image_name,
                    width,
                    height,
                    face_count,
                )

                return ExtractedCandidateImage(
                    data=image_bytes,
                    content_type=content_type,
                    extension=extension,
                )

        except zipfile.BadZipFile:
            logger.exception(
                "Invalid DOCX file: %s",
                file_path,
            )
            return None

        except Exception:
            logger.exception(
                "Unexpected error extracting image from DOCX: %s",
                file_path,
            )
            return None

    # =========================================================================
    # PDF
    # =========================================================================

    def _extract_from_pdf(
        self,
        file_path: Path,
    ) -> ExtractedCandidateImage | None:
        """
        Extract candidate images from PDF using PyMuPDF.

        PyMuPDF is imported using its modern API:

            import pymupdf

        instead of the deprecated:

            import fitz
        """

        if not _PYMUPDF_AVAILABLE:
            logger.warning(
                "PyMuPDF is unavailable. "
                "Cannot extract images from PDF: %s",
                file_path.name,
            )
            return None

        document = None

        try:
            document = pymupdf.open(
                str(file_path)
            )

            candidates: list[
                tuple[
                    int,
                    int,
                    int,
                    bytes,
                    int,
                    int,
                    int,
                ]
            ] = []

            total_images = 0

            # ----------------------------------------------------------------
            # Iterate through all PDF pages
            # ----------------------------------------------------------------

            for page_index in range(
                len(document)
            ):

                page = document[page_index]

                images = page.get_images(
                    full=True
                )

                total_images += len(images)

                for image_index, image_info in enumerate(
                    images
                ):

                    try:
                        xref = image_info[0]

                        extracted = document.extract_image(
                            xref
                        )

                        image_bytes = extracted.get(
                            "image"
                        )

                        if not image_bytes:
                            continue

                        image = Image.open(
                            io.BytesIO(image_bytes)
                        )

                        width, height = image.size

                        # ----------------------------------------------------
                        # Ignore tiny images
                        # ----------------------------------------------------

                        if (
                            width < self.MIN_IMAGE_WIDTH
                            or height < self.MIN_IMAGE_HEIGHT
                        ):
                            logger.debug(
                                (
                                    "Ignoring small PDF image "
                                    "page=%d image=%d size=%sx%s"
                                ),
                                page_index + 1,
                                image_index + 1,
                                width,
                                height,
                            )
                            continue

                        face_count = self._detect_faces(
                            image_bytes
                        )

                        candidates.append(
                            (
                                page_index,
                                image_index,
                                xref,
                                image_bytes,
                                width,
                                height,
                                face_count,
                            )
                        )

                        logger.debug(
                            (
                                "PDF image candidate: "
                                "page=%d image=%d size=%sx%s faces=%d"
                            ),
                            page_index + 1,
                            image_index + 1,
                            width,
                            height,
                            face_count,
                        )

                    except Exception:
                        logger.warning(
                            (
                                "Could not process PDF image "
                                "page=%d image=%d"
                            ),
                            page_index + 1,
                            image_index + 1,
                            exc_info=True,
                        )

            if not candidates:
                logger.info(
                    "No usable candidate image found in PDF: %s",
                    file_path.name,
                )
                return None

            selected = self._select_best_candidate(
                candidates
            )

            (
                page_index,
                image_index,
                xref,
                image_bytes,
                width,
                height,
                face_count,
            ) = selected

            content_type, extension = (
                self._detect_image_type(
                    image_bytes
                )
            )

            logger.info(
                (
                    "Selected PDF candidate image: "
                    "page=%d image=%d xref=%d "
                    "(%sx%s, faces=%d)"
                ),
                page_index + 1,
                image_index + 1,
                xref,
                width,
                height,
                face_count,
            )

            return ExtractedCandidateImage(
                data=image_bytes,
                content_type=content_type,
                extension=extension,
            )

        except Exception:
            logger.exception(
                "Unexpected error extracting image from PDF: %s",
                file_path,
            )
            return None

        finally:
            if document is not None:
                document.close()

    # =========================================================================
    # Face detection
    # =========================================================================

    def _detect_faces(
        self,
        image_bytes: bytes,
    ) -> int:
        """
        Detect faces in an image using OpenCV Haar Cascade.

        Returns:
            Number of detected faces.

        Returns 0 when face detection is unavailable or fails.
        """

        if self._face_detector is None:
            return 0

        try:
            image = Image.open(
                io.BytesIO(image_bytes)
            ).convert("RGB")

            # PIL RGB -> OpenCV BGR
            image_array = cv2.cvtColor(
                __import__(
                    "numpy"
                ).array(image),
                cv2.COLOR_RGB2BGR,
            )

            gray = cv2.cvtColor(
                image_array,
                cv2.COLOR_BGR2GRAY,
            )

            faces = self._face_detector.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(60, 60),
            )

            return len(faces)

        except Exception:
            logger.debug(
                "Face detection failed for image.",
                exc_info=True,
            )
            return 0

    # =========================================================================
    # Candidate selection
    # =========================================================================

    @staticmethod
    def _select_best_candidate(
        candidates,
    ):
        """
        Select the best candidate image.

        Selection priority:

            1. Images containing faces.
            2. Highest number of detected faces.
            3. Largest image area.

        If no image contains a face:

            Largest usable image is selected.
        """

        if not candidates:
            raise ValueError(
                "Cannot select from empty candidate list."
            )

        # --------------------------------------------------------------------
        # Candidates with detected faces
        # --------------------------------------------------------------------

        face_candidates = [
            candidate
            for candidate in candidates
            if candidate[-1] > 0
        ]

        if face_candidates:

            return max(
                face_candidates,
                key=lambda candidate: (
                    candidate[-1],
                    candidate[-3] * candidate[-2],
                ),
            )

        # --------------------------------------------------------------------
        # Fallback: largest image
        # --------------------------------------------------------------------

        return max(
            candidates,
            key=lambda candidate: (
                candidate[-3] * candidate[-2]
            ),
        )

    # =========================================================================
    # Image type
    # =========================================================================

    @staticmethod
    def _detect_image_type(
        image_bytes: bytes,
    ) -> tuple[str, str]:
        """
        Detect image MIME type and file extension.
        """

        image = Image.open(
            io.BytesIO(image_bytes)
        )

        image_format = (
            image.format or "JPEG"
        ).upper()

        mapping = {
            "JPEG": (
                "image/jpeg",
                ".jpg",
            ),
            "JPG": (
                "image/jpeg",
                ".jpg",
            ),
            "PNG": (
                "image/png",
                ".png",
            ),
            "WEBP": (
                "image/webp",
                ".webp",
            ),
            "GIF": (
                "image/gif",
                ".gif",
            ),
            "BMP": (
                "image/bmp",
                ".bmp",
            ),
        }

        return mapping.get(
            image_format,
            (
                "application/octet-stream",
                ".bin",
            ),
        )