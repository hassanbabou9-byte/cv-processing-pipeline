"""
Collaborateur repository.

Persists a complete mapped CV.

All SQLAlchemy Session operations remain inside the repository.

Collaborateurs are resolved by email before insertion so that
processing the same CV more than once does not create duplicate
collaborateur rows.

Collaborateur IDs use the required format:

    a1000001-0000-0000-0000-000000000001
    a1000001-0000-0000-0000-000000000002
    ...

The ID allocation is protected by a PostgreSQL transaction-level
advisory lock so it remains safe when multiple CVs are persisted
concurrently.
"""

import logging
import uuid

from sqlalchemy import text, select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    EntityNotFoundError,
    RepositoryError,
)
from app.mappers.db_mapper import MappedCV
from app.models.collaborateur import Collaborateur
from app.repositories.competence_repository import (
    CompetenceRepository,
)
from app.utils.uuid_utils import collaborateur_uuid


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PostgreSQL advisory-lock key
# ---------------------------------------------------------------------------
#
# This is only used to serialize collaborator ID allocation and duplicate
# email checks.
#
# It does NOT lock the entire CV-processing pipeline.
#
# Docling and LLM processing can therefore still run concurrently.
# ---------------------------------------------------------------------------

_COLLABORATEUR_LOCK_KEY = 735291


class CollaborateurRepository:
    """Repository responsible for Collaborateur persistence."""

    def __init__(
        self,
        db: Session,
    ) -> None:

        self._db = db

        self._competence_repo = (
            CompetenceRepository(db)
        )

    # =======================================================================
    # Internal ID allocation
    # =======================================================================

    def _acquire_collaborateur_lock(self) -> None:
        """
        Acquire a PostgreSQL transaction-level advisory lock.

        The lock is automatically released when the current transaction
        commits or rolls back.

        This guarantees that two concurrent requests cannot allocate the
        same Collaborateur sequence number.
        """

        try:

            self._db.execute(
                text(
                    "SELECT pg_advisory_xact_lock(:lock_key)"
                ),
                {
                    "lock_key": _COLLABORATEUR_LOCK_KEY,
                },
            )

            logger.debug(
                "Acquired Collaborateur ID allocation lock."
            )

        except Exception as exc:

            logger.exception(
                "Failed to acquire Collaborateur ID lock."
            )

            raise RepositoryError(
                "Failed to acquire Collaborateur ID allocation lock.",
                details={
                    "original_error": str(exc),
                },
            ) from exc

    def _get_next_collaborateur_id(
        self,
    ) -> uuid.UUID:
        """
        Generate the next required Collaborateur UUID.

        Only IDs matching the required format are considered:

            a1000001-0000-0000-0000-XXXXXXXXXXXX

        The caller must hold the Collaborateur advisory lock before
        invoking this method.
        """

        try:

            # PostgreSQL UUID values are converted to text so that we can
            # extract the final 12 hexadecimal characters.
            #
            # Example:
            #
            # a1000001-0000-0000-0000-000000000017
            #
            # becomes:
            #
            # 000000000017
            #
            # which is converted from hexadecimal to an integer.

            result = self._db.execute(
                text(
                    """
                    SELECT COALESCE(
                        MAX(
                            (
                                'x' ||
                                RIGHT(id::text, 12)
                            )::bit(48)::bigint
                        ),
                        0
                    )
                    FROM collaborateurs
                    WHERE id::text LIKE
                        'a1000001-0000-0000-0000-%'
                    """
                )
            )

            current_max = result.scalar_one()

            next_sequence = int(current_max) + 1

            new_id = collaborateur_uuid(
                next_sequence
            )

            logger.debug(
                "Allocated Collaborateur sequence=%d id=%s",
                next_sequence,
                new_id,
            )

            return new_id

        except Exception as exc:

            logger.exception(
                "Failed to allocate Collaborateur ID."
            )

            raise RepositoryError(
                "Failed to generate Collaborateur ID.",
                details={
                    "original_error": str(exc),
                },
            ) from exc

    # =======================================================================
    # Find by email
    # =======================================================================

    def get_by_email(
        self,
        email: str,
    ) -> Collaborateur | None:
        """
        Find an existing Collaborateur by email.

        Email comparison is case-insensitive and ignores surrounding
        whitespace.

        Returns:
            Existing Collaborateur or None.
        """

        normalized_email = (
            email.strip().lower()
        )

        if not normalized_email:
            return None

        try:

            stmt = (
                select(Collaborateur)
                .where(
                    Collaborateur.email.ilike(
                        normalized_email
                    )
                )
                .limit(1)
            )

            return (
                self._db
                .execute(stmt)
                .scalars()
                .first()
            )

        except Exception as exc:

            logger.exception(
                "Failed to find Collaborateur by email: %s",
                normalized_email,
            )

            raise RepositoryError(
                "Failed to look up Collaborateur by email.",
                details={
                    "email": normalized_email,
                    "original_error": str(exc),
                },
            ) from exc

    # =======================================================================
    # Save
    # =======================================================================

    def save(
        self,
        mapped: MappedCV,
    ) -> Collaborateur:
        """
        Persist the complete CV graph.

        Duplicate handling:

            email
              ↓
            acquire database lock
              ↓
            existing?
              ├── YES → return existing row
              └── NO
                    ↓
              allocate Collaborateur UUID
                    ↓
              resolve competences
                    ↓
              attach relationships
                    ↓
              insert graph
                    ↓
              commit

        The advisory lock protects both:

            1. duplicate email detection
            2. Collaborateur ID allocation

        This makes the operation safe when multiple CVs are persisted
        concurrently.
        """

        try:

            collaborateur = (
                mapped.collaborateur
            )

            # ===============================================================
            # 1. Acquire transaction-level lock
            # ===============================================================
            #
            # This is intentionally done only here, immediately before
            # database persistence.
            #
            # Docling and LLM processing remain outside this lock.
            # ===============================================================

            self._acquire_collaborateur_lock()

            # ===============================================================
            # 2. Normalize email
            # ===============================================================

            normalized_email = (
                collaborateur.email.strip().lower()
            )

            if not normalized_email:

                raise RepositoryError(
                    "Collaborateur email cannot be empty.",
                )

            collaborateur.email = (
                normalized_email
            )

            # ===============================================================
            # 3. Check existing Collaborateur
            # ===============================================================

            existing = self.get_by_email(
                normalized_email
            )

            if existing is not None:

                logger.info(
                    (
                        "Collaborateur already exists. "
                        "Skipping duplicate insertion: "
                        "email=%s id=%s"
                    ),
                    existing.email,
                    existing.id,
                )

                return existing

            # ===============================================================
            # 4. Allocate required Collaborateur UUID
            # ===============================================================

            collaborateur.id = (
                self._get_next_collaborateur_id()
            )

            # ===============================================================
            # 5. Resolve competences
            # ===============================================================

            resolved_competences = (
                self._competence_repo.resolve_batch(
                    mapped.new_competences
                )
            )

            # ===============================================================
            # 6. Attach resolved competences
            # ===============================================================

            for link, competence in zip(
                mapped.competence_links,
                resolved_competences,
                strict=True,
            ):

                link.competence = competence

            # ===============================================================
            # 7. Persist complete graph
            # ===============================================================

            self._db.add(
                collaborateur
            )

            # ===============================================================
            # 8. Commit transaction
            # ===============================================================

            self._db.commit()

            # ===============================================================
            # 9. Refresh root entity
            # ===============================================================

            self._db.refresh(
                collaborateur
            )

            logger.info(
                (
                    "Persisted Collaborateur "
                    "id=%s email=%s"
                ),
                collaborateur.id,
                collaborateur.email,
            )

            return collaborateur

        except RepositoryError:
            self._db.rollback()
            raise

        except Exception as exc:

            self._db.rollback()

            logger.exception(
                "Failed to persist Collaborateur."
            )

            raise RepositoryError(
                "Failed to save CV data to the database.",
                details={
                    "original_error": str(exc),
                },
            ) from exc

    # =======================================================================
    # Get by ID
    # =======================================================================

    def get_by_id(
        self,
        collaborateur_id: uuid.UUID,
    ) -> Collaborateur:

        try:

            result = self._db.get(
                Collaborateur,
                collaborateur_id,
            )

        except Exception as exc:

            raise RepositoryError(
                (
                    "Failed to fetch Collaborateur "
                    f"'{collaborateur_id}'."
                ),
                details={
                    "collaborateur_id": str(
                        collaborateur_id
                    ),
                    "original_error": str(exc),
                },
            ) from exc

        if result is None:

            raise EntityNotFoundError(
                (
                    "No Collaborateur found with id "
                    f"'{collaborateur_id}'."
                ),
                details={
                    "collaborateur_id": str(
                        collaborateur_id
                    ),
                },
            )

        return result

    # =======================================================================
    # List
    # =======================================================================

    def list_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Collaborateur]:

        try:

            stmt = (
                select(Collaborateur)
                .limit(limit)
                .offset(offset)
            )

            return list(
                self._db
                .execute(stmt)
                .scalars()
                .all()
            )

        except Exception as exc:

            raise RepositoryError(
                "Failed to list Collaborateurs.",
                details={
                    "original_error": str(exc),
                },
            ) from exc