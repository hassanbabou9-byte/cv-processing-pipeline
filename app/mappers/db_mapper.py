"""
Database mapper.

Converts normalized CV data into a complete SQLAlchemy ORM graph.

The mapper does NOT access the database.

Shared competence resolution is performed later by
CollaborateurRepository / CompetenceRepository.

Candidate images are stored in MinIO.
Only the MinIO object key is stored in the Collaborateur entity.
"""

from dataclasses import dataclass, field

from app.mappers.entity_builders import (
    build_activite,
    build_certificat,
    build_diplome,
    build_experience,
    build_formation,
)
from app.mappers.normalization.normalizer import NormalizedCV
from app.models.collaborateur import Collaborateur
from app.models.collaborateur_competence import CollaborateurCompetence
from app.models.collaborateur_projet import CollaborateurProjet
from app.models.competence import Competence
from app.models.projet import Projet


@dataclass
class MappedCV:
    """ORM graph ready for repository persistence."""

    collaborateur: Collaborateur

    new_competences: list[Competence] = field(
        default_factory=list
    )

    competence_links: list[CollaborateurCompetence] = field(
        default_factory=list
    )

    new_projets: list[Projet] = field(
        default_factory=list
    )

    projet_links: list[CollaborateurProjet] = field(
        default_factory=list
    )


def map_to_entities(
    normalized: NormalizedCV,
    image_object_key: str | None = None,
) -> MappedCV:
    """
    Convert normalized CV data into SQLAlchemy entities.

    Parameters
    ----------
    normalized:
        Normalized CV data.

    image_object_key:
        Optional MinIO object key for the candidate image.

    The mapper does not communicate with MinIO.
    It only stores the already-resolved object key
    on the Collaborateur entity.
    """

    n = normalized.collaborateur

    # ================================================================
    # Collaborateur
    # ================================================================

    collaborateur = Collaborateur(
        id=n.id,
        version=n.version,
        nom=n.nom,
        prenom=n.prenom,
        email=n.email,
        telephone_professionnel=n.telephone_professionnel,
        bio_professionnelle=n.bio_professionnelle,
        role=n.role,
        statut=n.statut,
        image_object_key=image_object_key,
    )

    # ================================================================
    # Experiences
    # ================================================================

    collaborateur.experiences = [
        build_experience(experience)
        for experience in normalized.experiences
    ]

    # ================================================================
    # Diplomes
    # ================================================================

    collaborateur.diplomes = [
        build_diplome(diplome)
        for diplome in normalized.diplomes
    ]

    # ================================================================
    # Formations
    # ================================================================

    collaborateur.formations = [
        build_formation(formation)
        for formation in normalized.formations
    ]

    # ================================================================
    # Certifications
    # ================================================================

    collaborateur.certificats = [
        build_certificat(certificat)
        for certificat in normalized.certificats
    ]

    # ================================================================
    # Activites
    # ================================================================

    collaborateur.activites = [
        build_activite(activity)
        for activity in normalized.activites
    ]

    # ================================================================
    # Competences
    # ================================================================

    new_competences: list[Competence] = []
    competence_links: list[CollaborateurCompetence] = []

    for normalized_competence in normalized.competences:

        competence = Competence(
            nom=normalized_competence.nom.strip(),
            categorie=normalized_competence.categorie,
        )

        link = CollaborateurCompetence(
            niveau=normalized_competence.niveau,
        )

        # CompetenceRepository resolves the competence later.

        new_competences.append(competence)
        competence_links.append(link)

    collaborateur.competences = competence_links

    # ================================================================
    # Projets
    # ================================================================

    new_projets: list[Projet] = []
    projet_links: list[CollaborateurProjet] = []

    for normalized_project in normalized.projets:

        projet = Projet(
            nom=normalized_project.nom,
            description=normalized_project.description,
            date_debut=normalized_project.date_debut,
            date_fin=normalized_project.date_fin,
            type_projet=normalized_project.type_projet,
            statut=normalized_project.statut,
        )

        link = CollaborateurProjet()

        link.projet = projet

        new_projets.append(projet)
        projet_links.append(link)

    collaborateur.projets = projet_links

    # ================================================================
    # Return
    # ================================================================

    return MappedCV(
        collaborateur=collaborateur,
        new_competences=new_competences,
        competence_links=competence_links,
        new_projets=new_projets,
        projet_links=projet_links,
    )