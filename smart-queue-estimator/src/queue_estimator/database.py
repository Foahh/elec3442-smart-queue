from __future__ import annotations

"""Database engine and session helpers."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

import queue_estimator.db_models  # noqa: F401
from queue_estimator.config import get_settings


def _build_engine():
    """Create and return the SQLModel engine."""

    settings = get_settings()
    return create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
    )


ENGINE = _build_engine()


def create_db_and_tables() -> None:
    """Create database tables if missing."""

    SQLModel.metadata.create_all(ENGINE)


@contextmanager
def get_session() -> Iterator[Session]:
    """Yield a short-lived database session."""

    with Session(ENGINE) as session:
        yield session

