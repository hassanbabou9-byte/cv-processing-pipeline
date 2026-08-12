"""
FastAPI dependency wiring.

This is the DI root: every dependency the API layer needs (settings,
services) is exposed here as a callable for Depends(). Routers import
from this module only — never construct services or read settings
directly.
"""

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session
from typing import Annotated

from app.config.settings import Settings, get_settings
from app.db.session import get_db
from app.services.cv_processing_service import CVProcessingService


@lru_cache
def _build_cv_processing_service() -> CVProcessingService:
    """
    Construct the CVProcessingService once per process.

    Cached (rather than rebuilt per request) since it holds no
    per-request state — only a reference to the shared Settings. The
    per-request DB Session is passed into its methods explicitly, not
    stored on the service, so this caching stays safe even for
    DB-touching operations.
    """
    return CVProcessingService(get_settings())


def get_cv_processing_service() -> CVProcessingService:
    """FastAPI dependency: the CV processing/upload orchestration service."""
    return _build_cv_processing_service()


# Convenience type aliases for router signatures, e.g.:
#   def upload(service: CVProcessingServiceDep, db: DbSessionDep): ...
SettingsDep = Annotated[Settings, Depends(get_settings)]
CVProcessingServiceDep = Annotated[CVProcessingService, Depends(get_cv_processing_service)]
DbSessionDep = Annotated[Session, Depends(get_db)]