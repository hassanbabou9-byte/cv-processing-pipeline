"""
Entity builders.

Small, single-purpose functions converting normalized dataclasses
into SQLAlchemy ORM entities.

These entities are owned by one collaborateur and are therefore
created as fresh ORM objects for each CV.
"""

from app.mappers.normalization.normalizer import (
    NormalizedActivite,
    NormalizedCertificat,
    NormalizedDiplome,
    NormalizedExperience,
    NormalizedFormation,
)

from app.models.activite import Activite
from app.models.certificat import Certificat
from app.models.diplome import Diplome
from app.models.experience import Experience
from app.models.formation import Formation


def build_experience(e: NormalizedExperience) -> Experience:
    return Experience(
        entreprise=e.entreprise,
        poste_occupe=e.poste_occupe,
        date_debut=e.date_debut,
        date_fin=e.date_fin,
        type=e.type,
        description=e.description,
    )


def build_diplome(d: NormalizedDiplome) -> Diplome:
    return Diplome(
        intitule=d.intitule,
        etablissement=d.etablissement,
        niveau_academique=d.niveau_academique,
        specialite=d.specialite,
        date_obtention=d.date_obtention,
        mention=d.mention,
    )


def build_formation(f: NormalizedFormation) -> Formation:
    return Formation(
        nom=f.nom,
        organisme=f.organisme,
        date_debut=f.date_debut,
        date_fin=f.date_fin,
    )


def build_certificat(c: NormalizedCertificat) -> Certificat:
    return Certificat(
        nom=c.nom,
        organisme=c.organisme,
        date_obtention=c.date_obtention,
        id_certification=c.id_certification,
        justification_url=c.justification_url,
    )


def build_activite(a: NormalizedActivite) -> Activite:
    return Activite(
        nom=a.nom,
        type=a.type,
        date=a.date,
        lieu_ou_organisme=a.lieu_ou_organisme,
        description=a.description,
        url=a.url,
    )