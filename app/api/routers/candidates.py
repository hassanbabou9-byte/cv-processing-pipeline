"""
Candidate API routes.

Provides read-only endpoints used by the Streamlit frontend.

Architecture:

    Streamlit
        |
        | HTTP
        v
    FastAPI
        |
        +---- PostgreSQL
        |       |
        |       +---- Candidate information
        |
        +---- MinIO
                |
                +---- Candidate image

Streamlit never accesses PostgreSQL or MinIO directly.

PostgreSQL stores the candidate information and the MinIO
object key.

MinIO stores the actual candidate image.
"""

import logging
import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.config.settings import Settings, get_settings
from app.models.collaborateur import Collaborateur
from app.repositories.collaborateur_repository import (
    CollaborateurRepository,
)
from app.services.storage.minio_storage import MinIOStorage


logger = logging.getLogger(__name__)


# ======================================================================
# Router
# ======================================================================

router = APIRouter(
    prefix="/candidates",
    tags=["Candidates"],
)


# ======================================================================
# List candidates
# ======================================================================

@router.get("")
def list_candidates(
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Maximum number of candidates to return.",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of candidates to skip.",
    ),
    db: Session = Depends(get_db),
) -> dict:
    """
    Return a paginated list of candidates.

    Candidate information comes from PostgreSQL.

    The actual candidate image is NOT returned here.

    Only the MinIO object key is returned.
    """

    repository = CollaborateurRepository(
        db
    )

    try:

        candidates = repository.list_all(
            limit=limit,
            offset=offset,
        )

    except Exception as exc:

        logger.exception(
            "Failed to retrieve candidates."
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve candidates.",
        ) from exc

    return {
        "total_returned": len(candidates),
        "limit": limit,
        "offset": offset,
        "candidates": [
            _serialize_candidate(candidate)
            for candidate in candidates
        ],
    }


# ======================================================================
# Get candidate by ID
# ======================================================================

@router.get("/{collaborateur_id}")
def get_candidate(
    collaborateur_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    """
    Return one candidate by Collaborateur ID.

    Candidate information is retrieved from PostgreSQL.
    """

    repository = CollaborateurRepository(
        db
    )

    try:

        candidate = repository.get_by_id(
            collaborateur_id
        )

    except Exception as exc:

        logger.warning(
            "Candidate not found: %s",
            collaborateur_id,
        )

        raise HTTPException(
            status_code=404,
            detail="Candidate not found.",
        ) from exc

    return _serialize_candidate(
        candidate
    )


# ======================================================================
# Get candidate image
# ======================================================================

@router.get("/{collaborateur_id}/image")
def get_candidate_image(
    collaborateur_id: uuid.UUID,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    """
    Retrieve a candidate image.

    Flow:

        PostgreSQL
            |
            | image_object_key
            v
        FastAPI
            |
            v
        MinIO
            |
            | image bytes
            v
        HTTP Response
    """

    repository = CollaborateurRepository(
        db
    )

    # ------------------------------------------------------------------
    # Find candidate
    # ------------------------------------------------------------------

    try:

        candidate = repository.get_by_id(
            collaborateur_id
        )

    except Exception as exc:

        logger.warning(
            "Candidate not found while retrieving image: %s",
            collaborateur_id,
        )

        raise HTTPException(
            status_code=404,
            detail="Candidate not found.",
        ) from exc

    # ------------------------------------------------------------------
    # Check image key
    # ------------------------------------------------------------------

    if not candidate.image_object_key:

        logger.info(
            "Candidate has no image: %s",
            collaborateur_id,
        )

        raise HTTPException(
            status_code=404,
            detail="Candidate does not have an image.",
        )

    # ------------------------------------------------------------------
    # Create MinIO storage client
    # ------------------------------------------------------------------

    storage = MinIOStorage(
        settings
    )

    # ------------------------------------------------------------------
    # Verify object exists
    # ------------------------------------------------------------------

    try:

        exists = storage.image_exists(
            candidate.image_object_key
        )

    except Exception as exc:

        logger.exception(
            (
                "Failed to check candidate image "
                "in MinIO: candidate=%s object=%s"
            ),
            candidate.id,
            candidate.image_object_key,
        )

        raise HTTPException(
            status_code=503,
            detail="Unable to access MinIO.",
        ) from exc

    if not exists:

        logger.warning(
            (
                "Candidate image key exists in PostgreSQL "
                "but object does not exist in MinIO: "
                "candidate=%s object=%s"
            ),
            candidate.id,
            candidate.image_object_key,
        )

        raise HTTPException(
            status_code=404,
            detail="Candidate image not found in MinIO.",
        )

    # ------------------------------------------------------------------
    # Retrieve image
    # ------------------------------------------------------------------

    try:

        image_bytes = storage.get_image(
            candidate.image_object_key
        )

    except Exception as exc:

        logger.exception(
            (
                "Failed to retrieve candidate image "
                "from MinIO: candidate=%s object=%s"
            ),
            candidate.id,
            candidate.image_object_key,
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve candidate image.",
        ) from exc

    if not image_bytes:

        logger.warning(
            "MinIO returned an empty image: %s",
            candidate.image_object_key,
        )

        raise HTTPException(
            status_code=404,
            detail="Candidate image is empty.",
        )

    # ------------------------------------------------------------------
    # Determine content type
    # ------------------------------------------------------------------

    content_type = _guess_image_content_type(
        candidate.image_object_key
    )

    # ------------------------------------------------------------------
    # Return image
    # ------------------------------------------------------------------

    return Response(
        content=image_bytes,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=3600",
        },
    )


# ======================================================================
# Serialization
# ======================================================================

def _serialize_candidate(
    candidate: Collaborateur,
) -> dict:
    """
    Convert a Collaborateur ORM entity into an API response.

    The actual image is never embedded in this response.

    PostgreSQL only returns the MinIO object key.
    """

    return {
        "id": str(
            candidate.id
        ),

        "version": candidate.version,

        "nom": candidate.nom,

        "prenom": candidate.prenom,

        "email": candidate.email,

        "telephone_professionnel": (
            candidate.telephone_professionnel
        ),

        "bio_professionnelle": (
            candidate.bio_professionnelle
        ),

        "role": candidate.role,

        "statut": candidate.statut,

        "image_object_key": (
            candidate.image_object_key
        ),
    }


# ======================================================================
# Image content type
# ======================================================================

def _guess_image_content_type(
    object_key: str,
) -> str:
    """
    Determine the HTTP media type from the MinIO object key.
    """

    if "." not in object_key:

        return "application/octet-stream"

    extension = (
        object_key
        .lower()
        .rsplit(".", 1)[-1]
    )

    mapping = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
        "bmp": "image/bmp",
    }

    return mapping.get(
        extension,
        "application/octet-stream",
    )