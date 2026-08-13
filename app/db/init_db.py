"""
Database initialization.

The project does not use Alembic.

SQLAlchemy creates missing database tables directly from
the registered ORM models.
"""

import logging

from sqlalchemy.engine import Engine

from app.db.base import Base

# Import all ORM models so SQLAlchemy registers
# their tables before Base.metadata.create_all().
from app.models.activite import Activite
from app.models.certificat import Certificat
from app.models.collaborateur import Collaborateur
from app.models.collaborateur_competence import CollaborateurCompetence
from app.models.collaborateur_projet import CollaborateurProjet
from app.models.competence import Competence
from app.models.diplome import Diplome
from app.models.experience import Experience
from app.models.formation import Formation
from app.models.projet import Projet


logger = logging.getLogger(__name__)


def init_db(
    engine: Engine,
) -> None:
    """
    Create all missing database tables.

    Existing tables are not deleted or modified.
    """

    logger.info(
        "Creating database tables if they do not exist..."
    )

    Base.metadata.create_all(
        bind=engine,
    )

    logger.info(
        "Database tables initialized."
    )