from __future__ import annotations

"""Reusable FastAPI dependencies."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from database import get_session


def get_db_session() -> Iterator[Session]:
    """Yield database session dependency."""

    with get_session() as session:
        yield session


DBSessionDep = Annotated[Session, Depends(get_db_session)]
