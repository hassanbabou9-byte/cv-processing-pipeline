"""
Projet model.

Projects are linked to collaborateurs through the
collaborateur_projets junction table.
"""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import StatutProjet, TypeProjet


if TYPE_CHECKING:
    from app.models.collaborateur_projet import CollaborateurProjet


class Projet(Base):
    __tablename__ = "projets"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    nom: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    date_debut: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    date_fin: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    type_projet: Mapped[TypeProjet | None] = mapped_column(
        Enum(
            TypeProjet,
            name="type_projet",
        ),
        nullable=True,
    )

    statut: Mapped[StatutProjet | None] = mapped_column(
        Enum(
            StatutProjet,
            name="statut_projet",
        ),
        nullable=True,
    )

    collaborateurs: Mapped[
        list["CollaborateurProjet"]
    ] = relationship(
        back_populates="projet",
    )