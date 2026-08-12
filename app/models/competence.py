"""
Competence model — master dictionary of skills/languages.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import CategorieCompetence


if TYPE_CHECKING:
    from app.models.collaborateur_competence import CollaborateurCompetence


class Competence(Base):
    __tablename__ = "competences"

    __table_args__ = (
        Index(
            "ix_competences_nom_lower",
            func.lower("nom"),
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    nom: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    categorie: Mapped[CategorieCompetence | None] = mapped_column(
        Enum(
            CategorieCompetence,
            name="categorie_competence",
        ),
        nullable=True,
    )

    collaborateurs: Mapped[
        list["CollaborateurCompetence"]
    ] = relationship(
        back_populates="competence",
    )