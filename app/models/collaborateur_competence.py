"""
Junction table linking collaborateurs to competences.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import NiveauCompetence


if TYPE_CHECKING:
    from app.models.collaborateur import Collaborateur
    from app.models.competence import Competence


class CollaborateurCompetence(Base):
    __tablename__ = "collaborateur_competences"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    collaborateur_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "collaborateurs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    competence_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "competences.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    niveau: Mapped[NiveauCompetence | None] = mapped_column(
        Enum(
            NiveauCompetence,
            name="niveau_competence",
        ),
        nullable=True,
    )

    collaborateur: Mapped["Collaborateur"] = relationship(
        back_populates="competences",
    )

    competence: Mapped["Competence"] = relationship(
        back_populates="collaborateurs",
    )