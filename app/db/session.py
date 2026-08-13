"""
Database engine and session management.

Single place that knows how to talk to PostgreSQL.

Repositories receive a SQLAlchemy Session through FastAPI's
Depends(get_db). Database connection management remains isolated
from the service layer.
"""

import logging
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import Settings, get_settings


logger = logging.getLogger(__name__)


_engine: Engine | None = None

_session_factory: sessionmaker | None = None


def _get_engine(
    settings: Settings,
) -> Engine:

    global _engine

    if _engine is None:

        logger.info(
            "Creating database engine"
        )

        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
        )

    return _engine


def get_engine() -> Engine:
    """
    Return the application database engine.
    """

    settings = get_settings()

    return _get_engine(
        settings
    )


def _get_session_factory(
    settings: Settings,
) -> sessionmaker:

    global _session_factory

    if _session_factory is None:

        _session_factory = sessionmaker(
            bind=_get_engine(
                settings
            ),
            autoflush=False,
            autocommit=False,
        )

    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """
    Provide a database session for one request.

    The session is always closed after the request.

    Repositories are responsible for:

        - commit()
        - rollback()
    """

    settings = get_settings()

    session_factory = _get_session_factory(
        settings
    )

    db = session_factory()

    try:

        yield db

    finally:

        db.close()