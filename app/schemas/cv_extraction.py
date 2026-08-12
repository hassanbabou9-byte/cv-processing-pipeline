"""
CV extraction schema.

This schema is the strict contract between:

    LLM
      ↓
    CVExtraction
      ↓
    Normalization layer

The LLM is allowed to extract:

    - nom
    - prenom
    - email

The following information is intentionally excluded:

    - telephone
    - adresse postale
    - photo
    - date de naissance

The schema is intentionally strict:
    - unknown fields are forbidden
    - strings are stripped
    - descriptions are limited to 500 characters
    - empty lists are represented as []
    - missing strings are represented as ""
"""

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


DESCRIPTION_MAX_LENGTH = 500


_EMAIL_RE = re.compile(
    r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
)


class _StrictBase(BaseModel):
    """
    Base model used by all extraction models.

    Extra fields are forbidden so the LLM cannot silently introduce
    fields that are not part of the database specification.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class Langue(_StrictBase):
    """Language extracted from the CV."""

    nom: str = ""
    niveau: str = ""


class Experience(_StrictBase):
    """Professional experience."""

    entreprise: str = ""
    poste: str = ""
    type: str = ""
    debut: str = ""
    fin: str = ""

    description: str = Field(
        default="",
        max_length=DESCRIPTION_MAX_LENGTH,
    )


class Diplome(_StrictBase):
    """Academic diploma."""

    intitule: str = ""
    etablissement: str = ""
    niveau_academique: str = ""
    specialite: str = ""
    date_obtention: str = ""
    mention: str = ""


class Formation(_StrictBase):
    """Professional training/course."""

    nom: str = ""
    organisme: str = ""
    date_debut: str = ""
    date_fin: str = ""


class Certification(_StrictBase):
    """Professional certification."""

    nom: str = ""
    organisme: str = ""
    date_obtention: str = ""
    id_certificat: str = ""
    url_verification: str = ""


class Projet(_StrictBase):
    """Project extracted from the CV."""

    nom: str = ""
    role: str = ""
    type: str = ""
    debut: str = ""
    fin: str = ""

    description: str = Field(
        default="",
        max_length=DESCRIPTION_MAX_LENGTH,
    )


class Activite(_StrictBase):
    """Professional or extra-professional activity."""

    nom: str = ""
    type: str = ""
    date: str = ""
    lieu_ou_organisme: str = ""

    description: str = Field(
        default="",
        max_length=DESCRIPTION_MAX_LENGTH,
    )

    url: str = ""


class CVExtraction(_StrictBase):
    """
    Complete structured CV extraction.

    This is the exact object expected from the LLM.
    """

    a_propos: str = Field(
        default="",
        max_length=DESCRIPTION_MAX_LENGTH,
    )

    # ---------------------------------------------------------
    # Candidate identity
    # ---------------------------------------------------------

    nom: str = ""

    prenom: str = ""

    email: str = ""

    # ---------------------------------------------------------
    # Competences
    # ---------------------------------------------------------

    competences_techniques: list[str] = Field(
        default_factory=list,
    )

    competences_comportementales: list[str] = Field(
        default_factory=list,
    )

    # ---------------------------------------------------------
    # Languages
    # ---------------------------------------------------------

    langues: list[Langue] = Field(
        default_factory=list,
    )

    # ---------------------------------------------------------
    # Professional information
    # ---------------------------------------------------------

    experiences: list[Experience] = Field(
        default_factory=list,
    )

    diplomes: list[Diplome] = Field(
        default_factory=list,
    )

    formations: list[Formation] = Field(
        default_factory=list,
    )

    certifications: list[Certification] = Field(
        default_factory=list,
    )

    projets: list[Projet] = Field(
        default_factory=list,
    )

    activites: list[Activite] = Field(
        default_factory=list,
    )

    # =========================================================
    # Validators
    # =========================================================

    @field_validator(
        "nom",
        "prenom",
        "email",
        "a_propos",
        mode="before",
    )
    @classmethod
    def _coerce_scalar_strings(
        cls,
        value: Any,
    ) -> str:
        """
        Convert scalar values to strings.

        None becomes "".

        Important:
        We do NOT invent or repair data here.
        """

        if value is None:
            return ""

        if isinstance(value, str):
            return value.strip()

        return str(value).strip()

    @field_validator(
        "competences_techniques",
        "competences_comportementales",
        mode="after",
    )
    @classmethod
    def _clean_competence_lists(
        cls,
        value: list[str],
    ) -> list[str]:
        """
        Remove empty competence entries and whitespace.

        No competence is invented.
        """

        cleaned: list[str] = []

        for item in value:
            if not isinstance(item, str):
                continue

            item = item.strip()

            if item:
                cleaned.append(item)

        return cleaned

    @field_validator(
        "langues",
        "experiences",
        "diplomes",
        "formations",
        "certifications",
        "projets",
        "activites",
        mode="before",
    )
    @classmethod
    def _normalize_missing_lists(
        cls,
        value: Any,
    ) -> Any:
        """
        Convert null list values to [].

        This is useful when an LLM returns null instead of an empty
        list even though the schema expects a list.
        """

        if value is None:
            return []

        return value

    @field_validator(
        "email",
        mode="after",
    )
    @classmethod
    def _validate_email_if_present(
        cls,
        value: str,
    ) -> str:
        """
        Validate an explicitly extracted email.

        We intentionally DO NOT repair malformed emails.

        For example:

            john doe@gmail.com

        is not transformed into:

            john.doe@gmail.com

        because doing so would invent information.

        If the LLM returns an unusual but explicit email format,
        the value is preserved.
        """

        if not value:
            return ""

        # We intentionally do not mutate the value.
        #
        # The regex is only used as an informational validation
        # reference. The CV schema must not invent or repair data.
        #
        # Therefore, even if the value doesn't match the regex,
        # it is preserved exactly as extracted.
        _ = _EMAIL_RE

        return value