"""
Database enum types.

These enums mirror only the explicit value lists defined by the
database specification.
"""

import enum


class CategorieCompetence(str, enum.Enum):
    """competences.categorie"""

    HARD_SKILL = "HARD_SKILL"
    SOFT_SKILL = "SOFT_SKILL"
    LANGUE = "LANGUE"


class NiveauCompetence(str, enum.Enum):
    """collaborateur_competences.niveau"""

    DEBUTANT = "DEBUTANT"
    INTERMEDIAIRE = "INTERMEDIAIRE"
    AVANCE = "AVANCE"
    EXPERT = "EXPERT"

    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class TypeExperience(str, enum.Enum):
    """experiences.type"""

    EXTERNE = "EXTERNE"
    INTERNE = "INTERNE"


class NiveauAcademique(str, enum.Enum):
    """diplomes.niveau_academique"""

    BAC_PLUS_2 = "BAC_PLUS_2"
    BAC_PLUS_3 = "BAC_PLUS_3"
    BAC_PLUS_4 = "BAC_PLUS_4"
    BAC_PLUS_5_6 = "BAC_PLUS_5_6"
    DOCTORAT = "DOCTORAT"
    AUTRE = "AUTRE"


class TypeProjet(str, enum.Enum):
    """projets.type_projet"""

    INTERNE = "INTERNE"
    EXTERNE = "EXTERNE"
    PERSONNEL = "PERSONNEL"


class StatutProjet(str, enum.Enum):
    """projets.statut"""

    EN_COURS = "EN_COURS"
    TERMINE = "TERMINE"
    EN_PAUSE = "EN_PAUSE"
    ABANDONNE = "ABANDONNE"


class TypeActivite(str, enum.Enum):
    """activites.type"""

    FORMATION = "FORMATION"
    CONFERENCE = "CONFERENCE"
    BENEVOLAT = "BENEVOLAT"
    PUBLICATION = "PUBLICATION"
    ACTIVITE_SPORTIVE = "ACTIVITE_SPORTIVE"
    HACKATHON = "HACKATHON"
    AUTRE = "AUTRE"