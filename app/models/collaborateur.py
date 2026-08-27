"""
Collaborateur model.

Main candidate/employee profile.

The database specification does not define emplois, fonctions,
or entites tables, therefore this model contains no references
to those entities.

Candidate images are stored in MinIO.
PostgreSQL stores only the MinIO object key.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


if TYPE_CHECKING:
    from app.models.activite import Activite
    from app.models.certificat import Certificat
    from app.models.collaborateur_competence import CollaborateurCompetence
    from app.models.collaborateur_projet import CollaborateurProjet
    from app.models.diplome import Diplome
    from app.models.experience import Experience
    from app.models.formation import Formation


class Collaborateur(Base):
    __tablename__ = "collaborateurs"

    # ================================================================
    # Identity
    # ================================================================

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # ================================================================
    # Personal information
    # ================================================================

    nom: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    prenom: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="",
    )

    email: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    telephone_professionnel: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    bio_professionnelle: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ================================================================
    # Professional information
    # ================================================================

    role: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="COLLABORATEUR",
    )

    statut: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="ACTIF",
    )

    # ================================================================
    # Candidate image
    # ================================================================
    #
    # The actual image is stored in MinIO.
    #
    # PostgreSQL stores only the object key.
    #
    # Example:
    #
    # candidates/
    #   <cv_id>/
    #       photo.png
    #
    # ================================================================

    image_object_key: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    # ================================================================
    # Relationships
    # ================================================================

    experiences: Mapped[list["Experience"]] = relationship(
        back_populates="collaborateur",
        cascade="all, delete-orphan",
    )

    diplomes: Mapped[list["Diplome"]] = relationship(
        back_populates="collaborateur",
        cascade="all, delete-orphan",
    )

    formations: Mapped[list["Formation"]] = relationship(
        back_populates="collaborateur",
        cascade="all, delete-orphan",
    )

    certificats: Mapped[list["Certificat"]] = relationship(
        back_populates="collaborateur",
        cascade="all, delete-orphan",
    )

    activites: Mapped[list["Activite"]] = relationship(
        back_populates="collaborateur",
        cascade="all, delete-orphan",
    )

    competences: Mapped[list["CollaborateurCompetence"]] = relationship(
        back_populates="collaborateur",
        cascade="all, delete-orphan",
    )

    projets: Mapped[list["CollaborateurProjet"]] = relationship(
        back_populates="collaborateur",
        cascade="all, delete-orphan",
    )