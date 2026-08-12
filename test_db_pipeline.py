"""
Manual test script for the full pipeline: parsed CV -> LLM extraction
-> normalization -> DB entities -> PostgreSQL persistence.

This exercises code that isn't wired into any HTTP endpoint yet
(normalizer.py, db_mapper.py, repositories/) — the combined batch
endpoint is the next/last step. Until then, this is how to verify the
DB layer actually works.

Prerequisites:
    - alembic upgrade head has been run (tables exist in Postgres)
    - .env's DATABASE_URL points to a real, reachable Postgres instance
    - A CV has already been uploaded (POST /upload) so parsed Markdown
      exists in data/parsed/<cv_id>.md

Usage:
    python test_db_pipeline.py <cv_id>
"""

import sys

from app.config.settings import get_settings
from app.db.session import get_db
from app.llm.chains.cv_extraction_chain import extract_cv_data
from app.mappers.db_mapper import map_to_entities
from app.mappers.normalization.normalizer import normalize_cv
from app.repositories.collaborateur_repository import CollaborateurRepository
from app.utils.file_storage import read_parsed_markdown


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python test_db_pipeline.py <cv_id>")
        sys.exit(1)

    cv_id = sys.argv[1]
    settings = get_settings()

    # --- Step 1: load the parsed Markdown from a prior /upload call ---
    markdown = read_parsed_markdown(cv_id, settings)
    if markdown is None:
        print(f"No parsed markdown found for cv_id='{cv_id}'. Upload it first.")
        sys.exit(1)
    print(f"[1/4] Loaded {len(markdown)} chars of Markdown for cv_id={cv_id}")

    # --- Step 2: LLM extraction ---
    print("[2/4] Running LLM extraction...")
    extraction = extract_cv_data(markdown, settings)
    print(f"      Extracted: {extraction.nom} {extraction.prenom} <{extraction.email}>")

    # --- Step 3: normalize + map to ORM entities ---
    print("[3/4] Normalizing and mapping to DB entities...")
    normalized = normalize_cv(extraction)
    mapped = map_to_entities(normalized)
    print(f"      {len(mapped.new_competences)} competence(s), "
          f"{len(mapped.new_projets)} projet(s), "
          f"{len(mapped.collaborateur.experiences)} experience(s), "
          f"{len(mapped.collaborateur.diplomes)} diplome(s)")

    # --- Step 4: persist ---
    print("[4/4] Persisting to PostgreSQL...")
    db_gen = get_db()
    db = next(db_gen)
    try:
        repo = CollaborateurRepository(db)
        saved = repo.save(mapped)
        print(f"\nSUCCESS — collaborateur persisted with id={saved.id}")
        print(f"  nom={saved.nom!r} prenom={saved.prenom!r} email={saved.email!r}")

        # Read it back to prove it's really in the DB, not just in memory.
        fetched = repo.get_by_id(saved.id)
        print(f"  Re-fetched from DB: {fetched.nom} {fetched.prenom}, "
              f"{len(fetched.experiences)} experience(s), "
              f"{len(fetched.diplomes)} diplome(s), "
              f"{len(fetched.competences)} competence link(s)")
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    main()