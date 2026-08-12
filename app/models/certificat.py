"""
Certificat model.
"""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


if TYPE_CHECKING:
    from app.models.collaborateur import Collaborateur


class Certificat(Base):
    __tablename__ = "certificats"

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

    nom: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    organisme: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    date_obtention: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    id_certification: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    justification_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    collaborateur: Mapped["Collaborateur"] = relationship(
        back_populates="certificats",
    )