"""
Competence repository.

Resolves competence candidates against existing database rows.

Competences are shared between collaborateurs, therefore existing
competences must be reused instead of inserted again.

Matching is case-insensitive.
"""

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import RepositoryError
from app.models.competence import Competence

logger = logging.getLogger(__name__)


class CompetenceRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def resolve_batch(
        self,
        candidates: list[Competence],
    ) -> list[Competence]:
        """
        Resolve all competence candidates in one database query.

        Existing competences are returned from the database.

        New competences are added to the session only after the lookup.

        The returned list preserves the exact order of candidates.
        """

        if not candidates:
            return []

        # ------------------------------------------------------------
        # Normalize candidate names
        # ------------------------------------------------------------

        names_lower = [
            candidate.nom.strip().lower()
            for candidate in candidates
        ]

        # Remove duplicates while preserving order.
        unique_names = list(dict.fromkeys(names_lower))

        try:
            # --------------------------------------------------------
            # IMPORTANT:
            #
            # Prevent SQLAlchemy from autoflushing pending objects
            # before this lookup.
            # --------------------------------------------------------

            with self._db.no_autoflush:

                stmt = select(Competence).where(
                    func.lower(Competence.nom).in_(unique_names)
                )

                existing_rows = (
                    self._db.execute(stmt)
                    .scalars()
                    .all()
                )

        except Exception as exc:

            raise RepositoryError(
                "Failed to look up existing competences.",
                details={
                    "names": unique_names,
                    "original_error": str(exc),
                },
            ) from exc

        # ------------------------------------------------------------
        # Existing database competences
        # ------------------------------------------------------------

        existing_by_name: dict[str, Competence] = {
            row.nom.strip().lower(): row
            for row in existing_rows
        }

        resolved: list[Competence] = []

        # Keep track of new objects created during THIS batch.
        new_by_name: dict[str, Competence] = {}

        # ------------------------------------------------------------
        # Resolve candidates
        # ------------------------------------------------------------

        for candidate in candidates:

            key = candidate.nom.strip().lower()

            # Existing database row
            if key in existing_by_name:
                resolved.append(
                    existing_by_name[key]
                )
                continue

            # Another candidate in the same CV already represents it
            if key in new_by_name:
                resolved.append(
                    new_by_name[key]
                )
                continue

            # Truly new competence
            self._db.add(candidate)

            new_by_name[key] = candidate
            resolved.append(candidate)

        logger.debug(
            "Competence resolution complete: "
            "candidates=%d existing=%d new=%d",
            len(candidates),
            len(existing_by_name),
            len(new_by_name),
        )

        return resolved