"""
Experience model.
"""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TypeExperience


if TYPE_CHECKING:
    from app.models.collaborateur import Collaborateur


class Experience(Base):
    __tablename__ = "experiences"

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

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    entreprise: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    poste_occupe: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    date_debut: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    date_fin: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    type: Mapped[TypeExperience] = mapped_column(
        Enum(
            TypeExperience,
            name="type_experience",
        ),
        nullable=False,
        default=TypeExperience.EXTERNE,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    collaborateur: Mapped["Collaborateur"] = relationship(
        back_populates="experiences",
    )