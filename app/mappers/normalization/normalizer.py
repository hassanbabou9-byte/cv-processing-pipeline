"""
CV normalization layer.

Transforms validated CVExtraction objects into DB-ready domain objects.

Responsibilities:
    - fallback values
    - personal-data cleanup
    - enum normalization
    - date parsing
    - competence normalization
    - chronological ordering
    - within-CV competence deduplication

No database access occurs here.

Important:
    The database specification used by this project does NOT contain
    emplois, fonctions, or entites tables.

    Therefore this module MUST NOT contain:
        - emploi_id
        - fonction_id
        - entite_id
        - DEFAULT_EMPLOI_ID
        - DEFAULT_FONCTION_ID

Cross-CV competence resolution is handled later by the repository layer.
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import date

from app.models.enums import (
    CategorieCompetence,
    NiveauAcademique,
    NiveauCompetence,
    StatutProjet,
    TypeActivite,
    TypeExperience,
    TypeProjet,
)
from app.schemas.cv_extraction import CVExtraction
from app.utils.date_utils import parse_date_field
from app.utils.uuid_utils import new_uuid, short_uuid_slice


# ============================================================================
# Constants
# ============================================================================

# Values that should never be persisted as actual candidate identity data.
#
# These are placeholders frequently returned by LLMs when the CV does not
# contain the requested information.
_INVALID_IDENTITY_VALUES = {
    "",
    "inconnu",
    "inconnue",
    "unknown",
    "unk",
    "n/a",
    "na",
    "n.a.",
    "non renseigné",
    "non renseigne",
    "non précisé",
    "non precise",
    "non spécifié",
    "non specifie",
    "indisponible",
    "inexistant",
    "undefined",
    "null",
    "none",
    "-",
    "--",
    "néant",
    "neant",
}


# Conservative email validation.

# This is NOT used to invent or modify an email.
# It only detects obviously invalid values.
_EMAIL_PATTERN = re.compile(
    r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
)


# ============================================================================
# Normalized domain objects
# ============================================================================


@dataclass
class NormalizedCollaborateur:
    """
    DB-ready collaborator data.

    Only columns that actually exist in the collaborateurs table are
    represented here.
    """

    id: uuid.UUID
    version: int
    nom: str
    prenom: str
    email: str
    telephone_professionnel: str | None
    bio_professionnelle: str | None
    role: str
    statut: str


@dataclass
class NormalizedCompetence:
    nom: str
    categorie: CategorieCompetence | None
    niveau: NiveauCompetence | None


@dataclass
class NormalizedExperience:
    entreprise: str
    poste_occupe: str
    date_debut: date
    date_fin: date | None
    type: TypeExperience
    description: str | None


@dataclass
class NormalizedDiplome:
    intitule: str
    etablissement: str
    niveau_academique: NiveauAcademique
    specialite: str | None
    date_obtention: date | None
    mention: str | None


@dataclass
class NormalizedFormation:
    nom: str
    organisme: str | None
    date_debut: date
    date_fin: date | None


@dataclass
class NormalizedCertificat:
    nom: str
    organisme: str | None
    date_obtention: date | None
    id_certification: str | None
    justification_url: str | None


@dataclass
class NormalizedProjet:
    nom: str
    description: str | None
    date_debut: date | None
    date_fin: date | None
    type_projet: TypeProjet | None
    statut: StatutProjet | None


@dataclass
class NormalizedActivite:
    nom: str
    type: TypeActivite
    date: date | None
    lieu_ou_organisme: str | None
    description: str | None
    url: str | None


@dataclass
class NormalizedCV:
    collaborateur: NormalizedCollaborateur

    competences: list[NormalizedCompetence] = field(
        default_factory=list
    )

    experiences: list[NormalizedExperience] = field(
        default_factory=list
    )

    diplomes: list[NormalizedDiplome] = field(
        default_factory=list
    )

    formations: list[NormalizedFormation] = field(
        default_factory=list
    )

    certificats: list[NormalizedCertificat] = field(
        default_factory=list
    )

    projets: list[NormalizedProjet] = field(
        default_factory=list
    )

    activites: list[NormalizedActivite] = field(
        default_factory=list
    )


# ============================================================================
# Personal-data normalization
# ============================================================================


def _clean_identity_value(value: str | None) -> str:
    """
    Clean a candidate identity value without guessing.

    This function deliberately does NOT:
        - derive a name from an email
        - derive a surname from a first name
        - swap nom and prenom
        - invent missing information
        - correct an uncertain LLM extraction

    It only removes whitespace and known placeholder values.
    """

    if not value:
        return ""

    cleaned = value.strip()

    if not cleaned:
        return ""

    if cleaned.casefold() in _INVALID_IDENTITY_VALUES:
        return ""

    return cleaned


def _normalize_email(value: str | None) -> str:
    """
    Normalize an explicitly extracted email conservatively.

    We do not construct or repair an email.

    If the extracted value is missing or obviously invalid, the database
    receives the project's deterministic import fallback.
    """

    if not value:
        return ""

    email = value.strip()

    if not email:
        return ""

    if email.casefold() in _INVALID_IDENTITY_VALUES:
        return ""

    # The LLM prompt requires the email to be copied from the CV.
    # Therefore we do not modify internal characters.
    if not _EMAIL_PATTERN.fullmatch(email):
        return ""

    return email


# ============================================================================
# Competence / language levels
# ============================================================================


_CEFR_LEVELS = {
    "a1": NiveauCompetence.A1,
    "a2": NiveauCompetence.A2,
    "b1": NiveauCompetence.B1,
    "b2": NiveauCompetence.B2,
    "c1": NiveauCompetence.C1,
    "c2": NiveauCompetence.C2,
}


_WORD_LEVELS = {
    "débutant": NiveauCompetence.DEBUTANT,
    "debutant": NiveauCompetence.DEBUTANT,
    "intermédiaire": NiveauCompetence.INTERMEDIAIRE,
    "intermediaire": NiveauCompetence.INTERMEDIAIRE,
    "avancé": NiveauCompetence.AVANCE,
    "avance": NiveauCompetence.AVANCE,
    "expert": NiveauCompetence.EXPERT,
}


# ============================================================================
# Academic level normalization
# ============================================================================


_NIVEAU_ACADEMIQUE_KEYWORDS = [
    (
        ("doctorat", "phd"),
        NiveauAcademique.DOCTORAT,
    ),
    (
        (
            "bac+5",
            "bac +5",
            "bac+6",
            "bac +6",
            "master",
            "ingénieur",
            "ingenieur",
        ),
        NiveauAcademique.BAC_PLUS_5_6,
    ),
    (
        (
            "bac+4",
            "bac +4",
        ),
        NiveauAcademique.BAC_PLUS_4,
    ),
    (
        (
            "bac+3",
            "bac +3",
            "licence",
        ),
        NiveauAcademique.BAC_PLUS_3,
    ),
    (
        (
            "bac+2",
            "bac +2",
            "dut",
            "bts",
        ),
        NiveauAcademique.BAC_PLUS_2,
    ),
]


# ============================================================================
# Activity type normalization
# ============================================================================


_ACTIVITE_TYPE_MAP = {
    "formation": TypeActivite.FORMATION,
    "conférence": TypeActivite.CONFERENCE,
    "conference": TypeActivite.CONFERENCE,
    "bénévolat": TypeActivite.BENEVOLAT,
    "benevolat": TypeActivite.BENEVOLAT,
    "publication": TypeActivite.PUBLICATION,
    "sport": TypeActivite.ACTIVITE_SPORTIVE,
    "activité sportive": TypeActivite.ACTIVITE_SPORTIVE,
    "activite sportive": TypeActivite.ACTIVITE_SPORTIVE,
    "hackathon": TypeActivite.HACKATHON,
    "autre": TypeActivite.AUTRE,
}


# ============================================================================
# Enum mapping helpers
# ============================================================================


def _map_niveau_langue(
    raw: str,
) -> NiveauCompetence | None:
    """
    Map a language level such as A1, B2, C1 or 'intermédiaire'
    to the database enum.
    """

    normalized = raw.strip().lower()

    return (
        _CEFR_LEVELS.get(normalized)
        or _WORD_LEVELS.get(normalized)
    )


def _map_niveau_academique(
    raw: str,
) -> NiveauAcademique:
    """
    Map free-text academic level to the database enum.
    """

    normalized = raw.strip().lower()

    for keywords, level in _NIVEAU_ACADEMIQUE_KEYWORDS:

        if any(
            keyword in normalized
            for keyword in keywords
        ):
            return level

    return NiveauAcademique.AUTRE


def _map_type_experience(
    raw: str,
) -> TypeExperience:
    """
    Map experience type.

    Explicit 'interne' becomes INTERNE.

    Everything else becomes EXTERNE, preserving the existing
    database fallback behavior.
    """

    normalized = raw.strip().lower()

    if normalized == "interne":
        return TypeExperience.INTERNE

    return TypeExperience.EXTERNE


def _map_type_projet(
    raw_role: str,
) -> TypeProjet | None:
    """
    Map project JSON field 'role' to database type_projet.
    """

    normalized = raw_role.strip().lower()

    if normalized == "interne":
        return TypeProjet.INTERNE

    if normalized == "externe":
        return TypeProjet.EXTERNE

    if normalized == "personnel":
        return TypeProjet.PERSONNEL

    return None


def _map_statut_projet(
    raw_type: str,
) -> StatutProjet | None:
    """
    Map project JSON field 'type' to database statut.
    """

    normalized = raw_type.strip().lower()

    if normalized == "en cours":
        return StatutProjet.EN_COURS

    if normalized in {
        "terminé",
        "termine",
    }:
        return StatutProjet.TERMINE

    if normalized in {
        "en pause",
        "pause",
    }:
        return StatutProjet.EN_PAUSE

    if normalized in {
        "abandonné",
        "abandonne",
    }:
        return StatutProjet.ABANDONNE

    return None


# ============================================================================
# Collaborateur
# ============================================================================


def _normalize_collaborateur(
    extraction: CVExtraction,
) -> NormalizedCollaborateur:
    """
    Normalize the main collaborator.

    Important:
        No information is inferred.

    nom:
        Uses the explicit extracted surname.
        Falls back to 'Inconnu' because the database column is NOT NULL.

    prenom:
        Uses the explicit extracted first name.
        Empty string is allowed by the database/model.

    email:
        Uses the explicit extracted email.
        If missing/invalid, creates the deterministic import fallback
        required by the existing pipeline behavior.
    """

    nom = _clean_identity_value(
        extraction.nom
    )

    prenom = _clean_identity_value(
        extraction.prenom
    )

    email = _normalize_email(
        extraction.email
    )

    # collaborateurs.nom is NOT NULL.
    if not nom:
        nom = "Inconnu"

    # collaborateurs.email is NOT NULL.
    if not email:
        email = (
            f"cv_{short_uuid_slice()}@import.local"
        )

    bio = (
        extraction.a_propos.strip()
        or None
    )

    return NormalizedCollaborateur(
        id=new_uuid(),
        version=0,
        nom=nom,
        prenom=prenom,
        email=email,
        telephone_professionnel=None,
        bio_professionnelle=bio,
        role="COLLABORATEUR",
        statut="ACTIF",
    )


# ============================================================================
# Competences
# ============================================================================


def _normalize_competences(
    extraction: CVExtraction,
) -> list[NormalizedCompetence]:
    """
    Normalize and deduplicate competences inside one CV.

    Cross-CV/database deduplication is NOT done here.

    The repository's CompetenceRepository is responsible for resolving
    these normalized candidates against existing database rows.
    """

    seen: dict[
        str,
        NormalizedCompetence,
    ] = {}

    def add(
        nom: str,
        categorie: CategorieCompetence,
        niveau: NiveauCompetence | None = None,
    ) -> None:

        cleaned_name = nom.strip()

        if not cleaned_name:
            return

        key = cleaned_name.casefold()

        if key not in seen:

            seen[key] = NormalizedCompetence(
                nom=cleaned_name,
                categorie=categorie,
                niveau=niveau,
            )

    # Technical skills
    for skill in extraction.competences_techniques:

        add(
            skill,
            CategorieCompetence.HARD_SKILL,
        )

    # Soft skills
    for skill in extraction.competences_comportementales:

        add(
            skill,
            CategorieCompetence.SOFT_SKILL,
        )

    # Languages
    for langue in extraction.langues:

        language_name = langue.nom.strip()

        if not language_name:
            continue

        add(
            language_name,
            CategorieCompetence.LANGUE,
            _map_niveau_langue(
                langue.niveau
            ),
        )

    return list(
        seen.values()
    )


# ============================================================================
# Experiences
# ============================================================================


def _normalize_experiences(
    extraction: CVExtraction,
) -> list[NormalizedExperience]:

    experiences: list[
        NormalizedExperience
    ] = []

    for exp in extraction.experiences:

        parsed_start = parse_date_field(
            exp.debut
        )

        # experiences.date_debut is NOT NULL.
        # Preserve the existing fallback behavior.
        if parsed_start is None:
            parsed_start = date.today()

        experiences.append(
            NormalizedExperience(
                entreprise=(
                    exp.entreprise.strip()
                    or "Entreprise non précisée"
                ),
                poste_occupe=(
                    exp.poste.strip()
                    or "Poste non précisé"
                ),
                date_debut=parsed_start,
                date_fin=parse_date_field(
                    exp.fin
                ),
                type=_map_type_experience(
                    exp.type
                ),
                description=(
                    exp.description.strip()
                    or None
                ),
            )
        )

    return sorted(
        experiences,
        key=lambda item: item.date_debut,
        reverse=True,
    )


# ============================================================================
# Diplomes
# ============================================================================


def _normalize_diplomes(
    extraction: CVExtraction,
) -> list[NormalizedDiplome]:

    return [
        NormalizedDiplome(
            intitule=(
                dip.intitule.strip()
                or "Diplôme sans titre"
            ),
            etablissement=(
                dip.etablissement.strip()
                or "Établissement non précisé"
            ),
            niveau_academique=(
                _map_niveau_academique(
                    dip.niveau_academique
                )
            ),
            specialite=(
                dip.specialite.strip()
                or None
            ),
            date_obtention=(
                parse_date_field(
                    dip.date_obtention
                )
            ),
            mention=(
                dip.mention.strip()
                or None
            ),
        )
        for dip in extraction.diplomes
    ]


# ============================================================================
# Formations
# ============================================================================


def _normalize_formations(
    extraction: CVExtraction,
) -> list[NormalizedFormation]:

    formations: list[
        NormalizedFormation
    ] = []

    for formation in extraction.formations:

        nom = formation.nom.strip()

        # 'nom' is required in the DB.
        # The existing normalizer skips unnamed formations instead
        # of inventing a title.
        if not nom:
            continue

        formations.append(
            NormalizedFormation(
                nom=nom,
                organisme=(
                    formation.organisme.strip()
                    or "Non précisé"
                ),
                date_debut=(
                    parse_date_field(
                        formation.date_debut
                    )
                    or date.today()
                ),
                date_fin=(
                    parse_date_field(
                        formation.date_fin
                    )
                ),
            )
        )

    return formations


# ============================================================================
# Certifications
# ============================================================================


def _normalize_certificats(
    extraction: CVExtraction,
) -> list[NormalizedCertificat]:

    return [
        NormalizedCertificat(
            nom=(
                cert.nom.strip()
                or "Certification sans titre"
            ),
            organisme=(
                cert.organisme.strip()
                or "Non précisé"
            ),
            date_obtention=(
                parse_date_field(
                    cert.date_obtention
                )
            ),
            id_certification=(
                cert.id_certificat.strip()
                or None
            ),
            justification_url=(
                cert.url_verification.strip()
                or None
            ),
        )
        for cert in extraction.certifications
    ]


# ============================================================================
# Projects
# ============================================================================


def _normalize_projets(
    extraction: CVExtraction,
) -> list[NormalizedProjet]:

    projets: list[
        NormalizedProjet
    ] = []

    for projet in extraction.projets:

        nom = projet.nom.strip()

        if not nom:
            nom = "Projet sans titre"

        projets.append(
            NormalizedProjet(
                nom=nom,
                description=(
                    projet.description.strip()
                    or None
                ),
                date_debut=(
                    parse_date_field(
                        projet.debut
                    )
                ),
                date_fin=(
                    parse_date_field(
                        projet.fin
                    )
                ),
                type_projet=(
                    _map_type_projet(
                        projet.role
                    )
                ),
                statut=(
                    _map_statut_projet(
                        projet.type
                    )
                ),
            )
        )

    return sorted(
        projets,
        key=lambda item: (
            item.date_debut
            or date.min
        ),
        reverse=True,
    )


# ============================================================================
# Activities
# ============================================================================


def _normalize_activites(
    extraction: CVExtraction,
) -> list[NormalizedActivite]:

    activites: list[
        NormalizedActivite
    ] = []

    for activite in extraction.activites:

        nom = activite.nom.strip()

        # Do not invent an activity name.
        if not nom:
            continue

        activites.append(
            NormalizedActivite(
                nom=nom,
                type=_ACTIVITE_TYPE_MAP.get(
                    activite.type.strip().lower(),
                    TypeActivite.AUTRE,
                ),
                date=parse_date_field(
                    activite.date
                ),
                lieu_ou_organisme=(
                    activite.lieu_ou_organisme.strip()
                    or None
                ),
                description=(
                    activite.description.strip()
                    or None
                ),
                url=(
                    activite.url.strip()
                    or None
                ),
            )
        )

    return activites


# ============================================================================
# Public API
# ============================================================================


def normalize_cv(
    extraction: CVExtraction,
) -> NormalizedCV:
    """
    Transform validated LLM extraction output into DB-ready normalized data.

    Pipeline position:

        CVExtraction
            ↓
        normalize_cv()
            ↓
        NormalizedCV
            ↓
        db_mapper.py
            ↓
        SQLAlchemy entities
            ↓
        repository
            ↓
        PostgreSQL

    No database access is performed here.
    """

    return NormalizedCV(
        collaborateur=_normalize_collaborateur(
            extraction
        ),
        competences=_normalize_competences(
            extraction
        ),
        experiences=_normalize_experiences(
            extraction
        ),
        diplomes=_normalize_diplomes(
            extraction
        ),
        formations=_normalize_formations(
            extraction
        ),
        certificats=_normalize_certificats(
            extraction
        ),
        projets=_normalize_projets(
            extraction
        ),
        activites=_normalize_activites(
            extraction
        ),
    )