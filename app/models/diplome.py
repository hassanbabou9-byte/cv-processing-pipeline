"""
Diplome model.
"""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import NiveauAcademique


if TYPE_CHECKING:
    from app.models.collaborateur import Collaborateur


class Diplome(Base):
    __tablename__ = "diplomes"

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

    intitule: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    etablissement: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    niveau_academique: Mapped[NiveauAcademique] = mapped_column(
        Enum(
            NiveauAcademique,
            name="niveau_academique",
        ),
        nullable=False,
        default=NiveauAcademique.AUTRE,
    )

    specialite: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    date_obtention: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    mention: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    collaborateur: Mapped["Collaborateur"] = relationship(
        back_populates="diplomes",
    )