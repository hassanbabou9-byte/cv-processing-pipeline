"""
Junction table linking collaborateurs to projets.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


if TYPE_CHECKING:
    from app.models.collaborateur import Collaborateur
    from app.models.projet import Projet


class CollaborateurProjet(Base):
    __tablename__ = "collaborateur_projets"

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

    projet_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "projets.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    collaborateur: Mapped["Collaborateur"] = relationship(
        back_populates="projets",
    )

    projet: Mapped["Projet"] = relationship(
        back_populates="collaborateurs",
    )