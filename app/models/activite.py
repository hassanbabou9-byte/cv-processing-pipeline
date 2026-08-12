import uuid
from datetime import date as DateType
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import TypeActivite

if TYPE_CHECKING:
    from app.models.collaborateur import Collaborateur


class Activite(Base):
    __tablename__ = "activites"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    collaborateur_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("collaborateurs.id", ondelete="CASCADE"),
        nullable=False,
    )

    nom: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    type: Mapped[TypeActivite] = mapped_column(
        Enum(TypeActivite, name="type_activite"),
        nullable=False,
        default=TypeActivite.AUTRE,
    )

    date: Mapped[DateType | None] = mapped_column(
        Date,
        nullable=True,
    )

    lieu_ou_organisme: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    url: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    collaborateur: Mapped["Collaborateur"] = relationship(
        back_populates="activites",
    )