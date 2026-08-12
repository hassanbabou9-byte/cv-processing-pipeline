"""
Models package.

Importing every model here (rather than leaving this empty) ensures
they're all registered on Base's metadata as soon as `app.models` is
imported anywhere — required for SQLAlchemy to resolve the string-based
relationship() references between models (e.g. Collaborateur ->
"Experience"), and for Alembic's autogenerate / Base.metadata.create_all
to see the complete schema.
"""

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

__all__ = [
    "Activite",
    "Certificat",
    "Collaborateur",
    "CollaborateurCompetence",
    "CollaborateurProjet",
    "Competence",
    "Diplome",
    "Experience",
    "Formation",
    "Projet",
]
